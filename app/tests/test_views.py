from unittest.mock import patch, MagicMock
import io

from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from app.models import InterviewSession, Conversation, AnalysisResult


# Note: Several views use .get() without try/except, so DoesNotExist
# exceptions propagate unhandled. Tests for "not found" scenarios
# verify this by expecting the exception.


class LoginViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_get_login_page(self):
        resp = self.client.get(reverse('login'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'app/login.html')

    def test_login_success(self):
        resp = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'testpass123'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('dashboard'))

    def test_login_failure(self):
        resp = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'wrongpass'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Invalid credentials')

    def test_login_missing_fields(self):
        resp = self.client.post(reverse('login'), {})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Invalid credentials')


class LogoutViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_logout_redirects(self):
        self.client.login(username='testuser', password='testpass123')
        resp = self.client.get(reverse('logout'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_logout_clears_session(self):
        self.client.login(username='testuser', password='testpass123')
        self.client.get(reverse('logout'))
        resp = self.client.get(reverse('dashboard'))
        # Should redirect to login since logged out
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)


class DashboardViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_dashboard_authenticated(self):
        self.client.login(username='testuser', password='testpass123')
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'app/dashboard.html')

    def test_dashboard_has_csrf_cookie(self):
        self.client.login(username='testuser', password='testpass123')
        resp = self.client.get(reverse('dashboard'))
        self.assertIn('csrftoken', resp.cookies)


class SessionListCreateViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass123')
        self.client.force_authenticate(user=self.user)

    def test_list_sessions_empty(self):
        resp = self.client.get(reverse('sessions'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, [])

    def test_list_sessions(self):
        InterviewSession.objects.create(
            user=self.user, company_description='Company A', num_interviews=5
        )
        InterviewSession.objects.create(
            user=self.user, company_description='Company B', num_interviews=10
        )
        resp = self.client.get(reverse('sessions'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_list_sessions_only_own(self):
        InterviewSession.objects.create(
            user=self.user, company_description='My company', num_interviews=5
        )
        InterviewSession.objects.create(
            user=self.other_user, company_description='Other company', num_interviews=5
        )
        resp = self.client.get(reverse('sessions'))
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['company_description'], 'My company')

    def test_create_session(self):
        resp = self.client.post(reverse('sessions'), {'company_description': 'New startup'})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['company_description'], 'New startup')
        self.assertEqual(resp.data['status'], 'pending')
        self.assertEqual(InterviewSession.objects.count(), 1)

    def test_create_session_missing_description(self):
        resp = self.client.post(reverse('sessions'), {})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_access(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(reverse('sessions'))
        self.assertIn(resp.status_code, [401, 403])


class StartInterviewsViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.session = InterviewSession.objects.create(
            user=self.user, company_description='Test', num_interviews=5
        )

    @patch('app.views.threading.Thread')
    def test_start_interviews(self, mock_thread):
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        resp = self.client.post(reverse('start', args=[self.session.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'started')
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()

    @patch('app.views.threading.Thread')
    def test_start_interviews_already_started(self, mock_thread):
        self.session.status = 'running'
        self.session.save()
        resp = self.client.post(reverse('start', args=[self.session.id]))
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.data)
        mock_thread.assert_not_called()

    def test_start_interviews_wrong_user(self):
        other_user = User.objects.create_user(username='other', password='testpass123')
        session = InterviewSession.objects.create(
            user=other_user, company_description='Other', num_interviews=5
        )
        with self.assertRaises(InterviewSession.DoesNotExist):
            self.client.post(reverse('start', args=[session.id]))

    def test_start_interviews_not_found(self):
        with self.assertRaises(InterviewSession.DoesNotExist):
            self.client.post(reverse('start', args=[9999]))


class ProgressViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.session = InterviewSession.objects.create(
            user=self.user,
            company_description='Test',
            num_interviews=10,
            completed_interviews=4,
            status='running',
            roles=['CTO', 'VP Eng'],
        )

    def test_get_progress(self):
        resp = self.client.get(reverse('progress', args=[self.session.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'running')
        self.assertEqual(resp.data['completed'], 4)
        self.assertEqual(resp.data['total'], 10)
        self.assertEqual(resp.data['roles'], ['CTO', 'VP Eng'])

    def test_progress_not_found(self):
        with self.assertRaises(InterviewSession.DoesNotExist):
            self.client.get(reverse('progress', args=[9999]))


class AnalysisViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.session = InterviewSession.objects.create(
            user=self.user,
            company_description='Test Corp',
            num_interviews=5,
            status='completed',
        )
        self.themes = [{"theme_name": "Innovation", "summary": "Drive innovation", "key_quotes": ["q1"]}]
        self.analysis = AnalysisResult.objects.create(session=self.session, themes=self.themes)

    def test_get_analysis_completed(self):
        resp = self.client.get(reverse('analysis', args=[self.session.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['company'], 'Test Corp')
        self.assertEqual(resp.data['themes'], self.themes)
        self.assertEqual(resp.data['interview_count'], 5)
        self.assertIn('created_at', resp.data)

    def test_get_analysis_not_ready(self):
        session = InterviewSession.objects.create(
            user=self.user, company_description='Test', num_interviews=5, status='running'
        )
        resp = self.client.get(reverse('analysis', args=[session.id]))
        self.assertEqual(resp.status_code, 404)
        self.assertIn('error', resp.data)


class BoardDeckViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.session = InterviewSession.objects.create(
            user=self.user,
            company_description='Test Corp',
            num_interviews=5,
            status='completed',
        )
        self.themes = [
            {"theme_name": "Culture", "summary": "Improve culture", "key_quotes": ["q1"], "action_count": 5,
             "sample_actions": ["a1"]},
        ]
        AnalysisResult.objects.create(session=self.session, themes=self.themes)
        Conversation.objects.create(
            session=self.session, employee_role='CTO',
            messages=[{"role": "interviewer", "content": "Hi"}, {"role": "employee", "content": "Hello"}]
        )

    def test_get_board_deck(self):
        resp = self.client.get(reverse('board_deck', args=[self.session.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp['Content-Type'],
            'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        )
        self.assertIn('Board_Deck.pptx', resp['Content-Disposition'])
        self.assertGreater(len(resp.content), 0)

    def test_board_deck_not_found(self):
        with self.assertRaises(InterviewSession.DoesNotExist):
            self.client.get(reverse('board_deck', args=[9999]))


class ConversationsListViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.session = InterviewSession.objects.create(
            user=self.user, company_description='Test', num_interviews=5, status='completed'
        )

    def test_list_conversations_empty(self):
        resp = self.client.get(reverse('conversations', args=[self.session.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, [])

    def test_list_conversations(self):
        Conversation.objects.create(session=self.session, employee_role='CTO', messages=[])
        Conversation.objects.create(session=self.session, employee_role='VP Eng', messages=[])
        resp = self.client.get(reverse('conversations', args=[self.session.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)
        self.assertEqual(resp.data[0]['interview_number'], 1)
        self.assertEqual(resp.data[1]['interview_number'], 2)
        self.assertEqual(resp.data[0]['employee_role'], 'CTO')
        self.assertIn('id', resp.data[0])


class ConversationDetailViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.session = InterviewSession.objects.create(
            user=self.user, company_description='Test', num_interviews=5, status='completed'
        )
        self.messages = [
            {"role": "interviewer", "content": "What are the biggest challenges?"},
            {"role": "employee", "content": "We need better tooling."},
            {"role": "interviewer", "content": "Can you elaborate?"},
            {"role": "employee", "content": "Our CI/CD pipeline is slow."},
        ]
        self.conv = Conversation.objects.create(
            session=self.session, employee_role='Software Engineer', messages=self.messages
        )

    def test_get_conversation_detail(self):
        resp = self.client.get(
            reverse('conversation_detail', args=[self.session.id, self.conv.id])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['id'], self.conv.id)
        self.assertEqual(resp.data['employee_role'], 'Software Engineer')
        self.assertIn('**Interviewer:**', resp.data['markdown'])
        self.assertIn('**Employee:**', resp.data['markdown'])
        self.assertIn('What are the biggest challenges?', resp.data['markdown'])
        self.assertIn('Our CI/CD pipeline is slow.', resp.data['markdown'])

    def test_conversation_not_found(self):
        with self.assertRaises(Conversation.DoesNotExist):
            self.client.get(
                reverse('conversation_detail', args=[self.session.id, 9999])
            )

    def test_conversation_wrong_session(self):
        other_session = InterviewSession.objects.create(
            user=self.user, company_description='Other', num_interviews=1
        )
        with self.assertRaises(Conversation.DoesNotExist):
            self.client.get(
                reverse('conversation_detail', args=[other_session.id, self.conv.id])
            )
