import asyncio, threading, traceback, os, random, itertools

from django.db.models import F
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import close_old_connections
from django.http import HttpResponse
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import sync_to_async # For calling sync DB operations from async code

from .models import InterviewSession, Conversation, AnalysisResult
from .serializers import SessionCreateSerializer, SessionSerializer
from .openai_service import generate_roles, run_single_interview
from .analysis import run_analysis
from .board_deck import generate_board_deck

NUM_CONCURRENT_INTERVIEWS = int(os.environ.get('NUM_CONCURRENT_INTERVIEWS'))

# Web views: login, logout, dashboard. Receive HTTP requests from browser, return HTML pages
def login_view(request): # POST + GET
    if request.method == 'POST':
        user = authenticate(request,
                            username=request.POST.get('username'),
                            password=request.POST.get('password'))
        if user:
            login(request, user)
            return redirect('dashboard')
        return render(request, 'app/login.html', {'error': 'Invalid credentials'})
    return render(request, 'app/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
@ensure_csrf_cookie # Ensure CSRF cookie is set for the dashboard page for post reqs
def dashboard(request):
    return render(request, 'app/dashboard.html', {'num_interviews_default': settings.NUM_INTERVIEWS,})


# Run interviews and analysis in background
def run_background(session_id): 
    """Entry point for background thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_interviews(session_id))
    except Exception:
        InterviewSession.objects.filter(id=session_id).update(status='failed')
        traceback.print_exc()
    finally:
        loop.close()
        close_old_connections()


async def run_interviews(session_id):
    session = await sync_to_async(InterviewSession.objects.get)(id=session_id)
    company = session.company_description

    @sync_to_async # Update session status in DB
    def set_status(s):
        InterviewSession.objects.filter(id=session_id).update(status=s)

    @sync_to_async # Save conversation to DB
    def save_conv(role, msgs):
        conv = Conversation.objects.create(session_id=session_id, employee_role=role, messages=msgs)
        InterviewSession.objects.filter(id=session_id).update(completed_interviews=F('completed_interviews') + 1) # Increment completed_interviews value in DB
        session = InterviewSession.objects.get(id=session_id)

    await set_status('running')
    roles = await generate_roles(company) # Generate 10 distinct roles for interviews

    @sync_to_async # Save generated roles to DB
    def save_roles(roles_list):
        InterviewSession.objects.filter(id=session_id).update(roles=roles_list)

    await save_roles(roles)

    # Loop through roles in a cycle till interviews are done
    role_cycle = list(itertools.islice(itertools.cycle(roles), session.num_interviews))

    sem = asyncio.Semaphore(int(NUM_CONCURRENT_INTERVIEWS))

    async def run_one(role, idx): # Run a single interview
        async with sem:
            msgs = await run_single_interview(company, role, interview_number=idx, max_turns=random.randint(5, 10)) # randomize turns to dynamically vary num questions
            await asyncio.sleep(1) # Add delay between interviews to avoid hitting openai's rate limits
            await save_conv(role, msgs)
            
    # Run interviews concurrently
    await asyncio.gather(*[run_one(r, i + 1) for i, r in enumerate(role_cycle)])

    await set_status('extracting')
    convs = await sync_to_async(list)(Conversation.objects.filter(session_id=session_id)) # Get all conversations for this session from DB
    themes = await run_analysis(convs, set_status) # Run analysis to get themes from conversations
    ar = await sync_to_async(AnalysisResult.objects.create)(session_id=session_id, themes=themes) # Save analysis result to DB
    await set_status('completed')


# API views: return JSON data for frontend
class SessionListCreateView(APIView): # List and create interview sessions
    permission_classes = [IsAuthenticated] # Only logged users

    def get(self, request):
        qs = InterviewSession.objects.filter(user=request.user).order_by('-created_at')
        return Response(SessionSerializer(qs, many=True).data)

    def post(self, request):
        ser = SessionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        session = InterviewSession.objects.create(user=request.user,
                                                  company_description=ser.validated_data['company_description'],
                                                  num_interviews=ser.validated_data.get('num_interviews', settings.NUM_INTERVIEWS))
        return Response(SessionSerializer(session).data, status=http_status.HTTP_201_CREATED)


class StartInterviewsView(APIView): # Start interviews for a session in background thread
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = InterviewSession.objects.get(id=session_id, user=request.user)
        if session.status != 'pending':
            return Response({'error': 'Already started'}, status=400)
        threading.Thread(target=run_background, args=(session_id,), daemon=True).start()
        return Response({'status': 'started'})


class ProgressView(APIView): # Show progress of interviews
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        s = InterviewSession.objects.get(id=session_id, user=request.user)
        return Response({'status': s.status, 'completed': s.completed_interviews, 'total': s.num_interviews, 'roles': s.roles or []})


class AnalysisView(APIView): # Return analysis results
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        s = InterviewSession.objects.get(id=session_id, user=request.user)
        if s.status != 'completed':
            return Response({'error': 'Analysis not ready yet'}, status=404)
        a = s.analysis
        return Response({'company': s.company_description, 'themes': a.themes, 'interview_count': s.num_interviews, 'created_at': a.created_at})


class BoardDeckView(APIView): # Generate board deck
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        s = InterviewSession.objects.get(id=session_id, user=request.user)
        roles = list(s.conversations.values_list('employee_role', flat=True))
        buf = generate_board_deck(s.company_description, s.analysis.themes, roles)
        resp = HttpResponse(buf.getvalue(),
                            content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation')
        resp['Content-Disposition'] = 'attachment; filename="Board_Deck.pptx"'

        return resp


class ConversationsListView(APIView): # List conversations
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        s = InterviewSession.objects.get(id=session_id, user=request.user)
        convs = s.conversations.order_by('id')
        data = []

        for idx, c in enumerate(convs, start=1):
            data.append({'id': c.id, 'interview_number': idx, 'employee_role': c.employee_role})

        return Response(data)


class ConversationDetailView(APIView): # Show details of selected conversation
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id, conversation_id):
        s = InterviewSession.objects.get(id=session_id, user=request.user)
        conv = s.conversations.get(id=conversation_id)
        
        # Build markdown from the stored messages
        lines = []

        for msg in conv.messages:
            role = msg.get('role', 'unknown').title()
            label = 'Interviewer' if role == 'Interviewer' else 'Employee'
            lines.append(f'**{label}:** {msg["content"]}')
        markdown = '\n\n'.join(lines)

        return Response({'id': conv.id, 'employee_role': conv.employee_role, 'markdown': markdown})
