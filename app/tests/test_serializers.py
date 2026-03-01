from django.test import TestCase
from django.contrib.auth.models import User

from app.models import InterviewSession, AnalysisResult
from app.serializers import SessionCreateSerializer, SessionSerializer, AnalysisSerializer


class SessionCreateSerializerTest(TestCase):

    def test_valid_data(self):
        data = {'company_description': 'A cloud computing company'}
        ser = SessionCreateSerializer(data=data)
        self.assertTrue(ser.is_valid())
        self.assertEqual(ser.validated_data['company_description'], 'A cloud computing company')

    def test_missing_company_description(self):
        ser = SessionCreateSerializer(data={})
        self.assertFalse(ser.is_valid())
        self.assertIn('company_description', ser.errors)

    def test_empty_company_description(self):
        ser = SessionCreateSerializer(data={'company_description': ''})
        self.assertFalse(ser.is_valid())
        self.assertIn('company_description', ser.errors)

    def test_extra_fields_ignored(self):
        data = {'company_description': 'Test', 'extra_field': 'ignored'}
        ser = SessionCreateSerializer(data=data)
        self.assertTrue(ser.is_valid())
        self.assertNotIn('extra_field', ser.validated_data)


class SessionSerializerTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.session = InterviewSession.objects.create(
            user=self.user,
            company_description='A SaaS platform for HR',
            num_interviews=10,
            status='running',
            completed_interviews=3,
            roles=['CTO', 'VP Engineering'],
        )

    def test_serializes_all_fields(self):
        ser = SessionSerializer(self.session)
        data = ser.data
        self.assertEqual(data['id'], self.session.id)
        self.assertEqual(data['company_description'], 'A SaaS platform for HR')
        self.assertEqual(data['num_interviews'], 10)
        self.assertEqual(data['status'], 'running')
        self.assertEqual(data['completed_interviews'], 3)
        self.assertEqual(data['roles'], ['CTO', 'VP Engineering'])
        self.assertEqual(data['user'], self.user.id)
        self.assertIn('created_at', data)

    def test_serializes_multiple_sessions(self):
        InterviewSession.objects.create(
            user=self.user, company_description='Company B', num_interviews=5
        )
        qs = InterviewSession.objects.filter(user=self.user)
        ser = SessionSerializer(qs, many=True)
        self.assertEqual(len(ser.data), 2)


class AnalysisSerializerTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.session = InterviewSession.objects.create(
            user=self.user,
            company_description='Test',
            num_interviews=5,
        )
        self.themes = [
            {"theme_name": "Culture", "summary": "Improve culture", "key_quotes": ["q1"], "action_count": 10},
        ]
        self.analysis = AnalysisResult.objects.create(session=self.session, themes=self.themes)

    def test_serializes_analysis(self):
        ser = AnalysisSerializer(self.analysis)
        data = ser.data
        self.assertEqual(data['id'], self.analysis.id)
        self.assertEqual(data['session'], self.session.id)
        self.assertEqual(data['themes'], self.themes)
        self.assertIn('created_at', data)
