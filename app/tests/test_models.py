from django.test import TestCase
from django.contrib.auth.models import User

from app.models import InterviewSession, Conversation, ExtractedAction, AnalysisResult


class InterviewSessionModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_create_session_with_defaults(self):
        session = InterviewSession.objects.create(
            user=self.user,
            company_description='A fintech startup',
            num_interviews=5,
        )
        self.assertEqual(session.status, 'pending')
        self.assertEqual(session.completed_interviews, 0)
        self.assertEqual(session.roles, [])
        self.assertIsNotNone(session.created_at)

    def test_create_session_with_all_fields(self):
        roles = ['CTO', 'VP Engineering', 'Product Manager']
        session = InterviewSession.objects.create(
            user=self.user,
            company_description='An e-commerce platform',
            num_interviews=10,
            completed_interviews=3,
            status='running',
            roles=roles,
        )
        self.assertEqual(session.status, 'running')
        self.assertEqual(session.completed_interviews, 3)
        self.assertEqual(session.roles, roles)
        self.assertEqual(session.num_interviews, 10)

    def test_str_representation(self):
        session = InterviewSession.objects.create(
            user=self.user,
            company_description='Test company',
            num_interviews=5,
        )
        self.assertEqual(str(session), f"Session {session.id}: pending")

    def test_status_choices(self):
        valid_statuses = ['pending', 'running', 'extracting', 'clustering', 'summarizing', 'completed', 'failed']
        for s in valid_statuses:
            session = InterviewSession.objects.create(
                user=self.user,
                company_description='Test',
                num_interviews=1,
                status=s,
            )
            self.assertEqual(session.status, s)

    def test_user_cascade_delete(self):
        session = InterviewSession.objects.create(
            user=self.user,
            company_description='Test',
            num_interviews=1,
        )
        session_id = session.id
        self.user.delete()
        self.assertFalse(InterviewSession.objects.filter(id=session_id).exists())


class ConversationModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.session = InterviewSession.objects.create(
            user=self.user,
            company_description='A tech company',
            num_interviews=5,
        )

    def test_create_conversation(self):
        messages = [
            {"role": "interviewer", "content": "Hello, how are you?"},
            {"role": "employee", "content": "I'm doing well, thanks."},
        ]
        conv = Conversation.objects.create(
            session=self.session,
            employee_role='Software Engineer',
            messages=messages,
        )
        self.assertEqual(conv.session, self.session)
        self.assertEqual(conv.employee_role, 'Software Engineer')
        self.assertEqual(len(conv.messages), 2)
        self.assertIsNotNone(conv.created_at)

    def test_default_messages(self):
        conv = Conversation.objects.create(
            session=self.session,
            employee_role='Designer',
        )
        self.assertEqual(conv.messages, [])

    def test_str_representation(self):
        conv = Conversation.objects.create(
            session=self.session,
            employee_role='Data Scientist',
        )
        self.assertEqual(str(conv), f"Session {self.session.id}: Data Scientist")

    def test_related_name(self):
        Conversation.objects.create(session=self.session, employee_role='Role A')
        Conversation.objects.create(session=self.session, employee_role='Role B')
        self.assertEqual(self.session.conversations.count(), 2)

    def test_session_cascade_delete(self):
        conv = Conversation.objects.create(session=self.session, employee_role='PM')
        conv_id = conv.id
        self.session.delete()
        self.assertFalse(Conversation.objects.filter(id=conv_id).exists())


class ExtractedActionModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.session = InterviewSession.objects.create(
            user=self.user,
            company_description='Test company',
            num_interviews=1,
        )
        self.conversation = Conversation.objects.create(
            session=self.session,
            employee_role='Engineer',
        )

    def test_create_extracted_action(self):
        action = ExtractedAction.objects.create(
            conversation=self.conversation,
            action_text='Improve CI/CD pipeline',
            embedding=[0.1, 0.2, 0.3],
        )
        self.assertEqual(action.conversation, self.conversation)
        self.assertEqual(action.action_text, 'Improve CI/CD pipeline')
        self.assertEqual(action.embedding, [0.1, 0.2, 0.3])

    def test_embedding_nullable(self):
        action = ExtractedAction.objects.create(
            conversation=self.conversation,
            action_text='Some action',
        )
        self.assertIsNone(action.embedding)

    def test_str_representation(self):
        action = ExtractedAction.objects.create(
            conversation=self.conversation,
            action_text='This is a very long action text that should be truncated in the string representation',
        )
        self.assertEqual(str(action), 'This is a very long action tex')  # first 30 chars

    def test_related_name(self):
        ExtractedAction.objects.create(conversation=self.conversation, action_text='Action 1')
        ExtractedAction.objects.create(conversation=self.conversation, action_text='Action 2')
        self.assertEqual(self.conversation.actions.count(), 2)

    def test_conversation_cascade_delete(self):
        action = ExtractedAction.objects.create(
            conversation=self.conversation,
            action_text='Test action',
        )
        action_id = action.id
        self.conversation.delete()
        self.assertFalse(ExtractedAction.objects.filter(id=action_id).exists())


class AnalysisResultModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.session = InterviewSession.objects.create(
            user=self.user,
            company_description='Test company',
            num_interviews=1,
        )

    def test_create_analysis_result(self):
        themes = [
            {"theme_name": "Leadership", "summary": "Improve leadership", "key_quotes": ["Quote 1"], "action_count": 5},
        ]
        result = AnalysisResult.objects.create(
            session=self.session,
            themes=themes,
        )
        self.assertEqual(result.session, self.session)
        self.assertEqual(len(result.themes), 1)
        self.assertEqual(result.themes[0]['theme_name'], 'Leadership')
        self.assertIsNotNone(result.created_at)

    def test_default_themes(self):
        result = AnalysisResult.objects.create(session=self.session)
        self.assertEqual(result.themes, [])

    def test_str_representation(self):
        result = AnalysisResult.objects.create(session=self.session)
        self.assertEqual(str(result), f"Session {self.session.id}: Analysis")

    def test_one_to_one_relationship(self):
        AnalysisResult.objects.create(session=self.session, themes=[])
        analysis = self.session.analysis
        self.assertIsNotNone(analysis)

    def test_session_cascade_delete(self):
        result = AnalysisResult.objects.create(session=self.session)
        result_id = result.id
        self.session.delete()
        self.assertFalse(AnalysisResult.objects.filter(id=result_id).exists())
