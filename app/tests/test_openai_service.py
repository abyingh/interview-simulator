import asyncio
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock

from django.test import TestCase

from app.openai_service import (
    generate_roles,
    run_single_interview,
    extract_actions,
    get_embeddings,
    summarize_theme,
)
from app.schemas import (
    InterviewerResponseSchema,
    ExtractedActionsSchema,
    ExtractedActionItem,
    RoleListSchema,
    ThemeSummarySchema,
)


def _make_parsed_response(parsed_obj):
    """Helper to build a mock OpenAI structured-output response."""
    mock_message = MagicMock()
    mock_message.parsed = parsed_obj
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


def _make_chat_response(content: str):
    """Helper to build a mock OpenAI chat completion response."""
    mock_message = MagicMock()
    mock_message.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


class GenerateRolesTest(TestCase):

    @patch('app.openai_service.get_client')
    def test_generate_roles(self, mock_get_client):
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client

        roles_list = ['CTO', 'VP Engineering', 'Product Manager', 'Data Scientist',
                       'Software Engineer', 'Designer', 'HR Director', 'CFO',
                       'Sales Lead', 'DevOps Engineer']
        parsed = RoleListSchema(roles=roles_list)
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=_make_parsed_response(parsed))

        result = asyncio.run(generate_roles('A fintech startup'))

        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], 'CTO')
        mock_client.beta.chat.completions.parse.assert_called_once()

    @patch('app.openai_service.get_client')
    def test_generate_roles_truncates_to_10(self, mock_get_client):
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client

        roles_list = [f'Role {i}' for i in range(15)]  # More than 10
        parsed = RoleListSchema(roles=roles_list)
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=_make_parsed_response(parsed))

        result = asyncio.run(generate_roles('Company'))
        self.assertEqual(len(result), 10)


class RunSingleInterviewTest(TestCase):

    @patch('app.openai_service.get_client')
    def test_interview_completes_on_flag(self, mock_get_client):
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client

        # Turn 1: interviewer asks, turn 1: employee answers, then interviewer marks complete
        interviewer_responses = [
            _make_parsed_response(InterviewerResponseSchema(
                message="Hello! What are the biggest challenges?", is_interview_complete=False
            )),
            _make_parsed_response(InterviewerResponseSchema(
                message="Thank you for your time.", is_interview_complete=True
            )),
        ]
        employee_response = _make_chat_response("We need better tooling and processes.")

        mock_client.beta.chat.completions.parse = AsyncMock(side_effect=interviewer_responses)
        mock_client.chat.completions.create = AsyncMock(return_value=employee_response)

        result = asyncio.run(run_single_interview('Test company', 'CTO', interview_number=1, max_turns=5))

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        # Should have: interviewer, employee, interviewer (complete)
        self.assertEqual(result[0]['role'], 'interviewer')
        self.assertEqual(result[1]['role'], 'employee')
        self.assertEqual(result[2]['role'], 'interviewer')

    @patch('app.openai_service.get_client')
    def test_interview_hard_stop_at_max_turns(self, mock_get_client):
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client

        # Interviewer never sets complete, so it should hard stop
        interviewer_response = _make_parsed_response(InterviewerResponseSchema(
            message="Tell me more.", is_interview_complete=False
        ))
        employee_response = _make_chat_response("We have various issues.")

        mock_client.beta.chat.completions.parse = AsyncMock(return_value=interviewer_response)
        mock_client.chat.completions.create = AsyncMock(return_value=employee_response)

        result = asyncio.run(run_single_interview('Test company', 'CTO', interview_number=1, max_turns=2))

        # max_turns=2: turn 1 (Q+A), turn 2 (Q+A), then hard stop message
        self.assertIsInstance(result, list)
        # The last message should be the hard-stop
        self.assertEqual(result[-1]['role'], 'interviewer')
        self.assertIn('concludes', result[-1]['content'].lower())


class ExtractActionsTest(TestCase):

    @patch('app.openai_service.get_client')
    def test_extract_actions(self, mock_get_client):
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client

        parsed = ExtractedActionsSchema(actions=[
            ExtractedActionItem(action="Improve CI/CD pipeline", quote="Our builds are too slow"),
            ExtractedActionItem(action="Invest in training", quote="We need more learning resources"),
        ])
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=_make_parsed_response(parsed))

        messages = [
            {"role": "interviewer", "content": "What needs improvement?"},
            {"role": "employee", "content": "Our builds are too slow and we need more learning resources."},
        ]
        result = asyncio.run(extract_actions(messages))

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['action'], 'Improve CI/CD pipeline')
        self.assertEqual(result[0]['quote'], 'Our builds are too slow')

    @patch('app.openai_service.get_client')
    def test_extract_actions_empty(self, mock_get_client):
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client

        parsed = ExtractedActionsSchema(actions=[])
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=_make_parsed_response(parsed))

        result = asyncio.run(extract_actions([{"role": "interviewer", "content": "Hi"}]))
        self.assertEqual(result, [])


class GetEmbeddingsTest(TestCase):

    @patch('app.openai_service.get_client')
    def test_get_embeddings(self, mock_get_client):
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client

        mock_item1 = MagicMock()
        mock_item1.embedding = [0.1, 0.2, 0.3]
        mock_item2 = MagicMock()
        mock_item2.embedding = [0.4, 0.5, 0.6]
        mock_response = MagicMock()
        mock_response.data = [mock_item1, mock_item2]

        mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        result = asyncio.run(get_embeddings(["text 1", "text 2"]))

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], [0.1, 0.2, 0.3])
        self.assertEqual(result[1], [0.4, 0.5, 0.6])


class SummarizeThemeTest(TestCase):

    @patch('app.openai_service.get_client')
    def test_summarize_theme(self, mock_get_client):
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client

        parsed = ThemeSummarySchema(
            theme_name="Operational Excellence",
            summary="Focus on improving operational processes.",
            key_quotes=["We need better processes", "Operations are chaotic"],
        )
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=_make_parsed_response(parsed))

        items = [
            {"action": "Streamline ops", "quote": "We need better processes"},
            {"action": "Automate tasks", "quote": "Operations are chaotic"},
        ]
        result = asyncio.run(summarize_theme(items))

        self.assertIsInstance(result, ThemeSummarySchema)
        self.assertEqual(result.theme_name, "Operational Excellence")
        self.assertEqual(len(result.key_quotes), 2)
