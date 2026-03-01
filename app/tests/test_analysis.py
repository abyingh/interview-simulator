import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

import numpy as np
from django.test import TestCase
from django.contrib.auth.models import User

from app.models import InterviewSession, Conversation, ExtractedAction
from app.analysis import (
    normalize_embeddings,
    find_best_k,
    cluster_items,
    build_embeddings,
    extract_items_for_conversation,
    extract_all_items,
    summarize_top_clusters,
    run_analysis,
)
from app.schemas import ThemeSummarySchema


class NormalizeEmbeddingsTest(TestCase):

    def test_normalize_unit_vectors(self):
        embeddings = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        result = normalize_embeddings(embeddings)
        np.testing.assert_array_almost_equal(result, embeddings)

    def test_normalize_non_unit_vectors(self):
        embeddings = [[3.0, 4.0]]
        result = normalize_embeddings(embeddings)
        norm = np.linalg.norm(result, axis=1)
        np.testing.assert_array_almost_equal(norm, [1.0])

    def test_normalize_shape(self):
        embeddings = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]
        result = normalize_embeddings(embeddings)
        self.assertEqual(result.shape, (3, 3))

    def test_normalize_preserves_direction(self):
        embeddings = [[2.0, 2.0]]
        result = normalize_embeddings(embeddings)
        expected = np.array([[1 / np.sqrt(2), 1 / np.sqrt(2)]])
        np.testing.assert_array_almost_equal(result, expected)


class FindBestKTest(TestCase):

    def test_find_best_k_returns_valid_k(self):
        np.random.seed(42)
        # Create 3 clear clusters
        c1 = np.random.randn(20, 5) + [5, 0, 0, 0, 0]
        c2 = np.random.randn(20, 5) + [0, 5, 0, 0, 0]
        c3 = np.random.randn(20, 5) + [0, 0, 5, 0, 0]
        X = np.vstack([c1, c2, c3])
        X = X / np.linalg.norm(X, axis=1, keepdims=True)

        items = [{"action": f"action_{i}", "quote": f"quote_{i}"} for i in range(60)]
        best_k = find_best_k(X, items)

        self.assertGreaterEqual(best_k, 3)
        self.assertLessEqual(best_k, 50)

    def test_find_best_k_respects_bounds(self):
        np.random.seed(42)
        X = np.random.randn(10, 5)
        X = X / np.linalg.norm(X, axis=1, keepdims=True)
        items = [{"action": f"a{i}", "quote": f"q{i}"} for i in range(10)]

        best_k = find_best_k(X, items)
        self.assertGreaterEqual(best_k, 3)
        self.assertLessEqual(best_k, 9)  # min(50, len - 1)


class ClusterItemsTest(TestCase):

    def test_cluster_items_basic(self):
        np.random.seed(42)
        X = np.random.randn(20, 3)
        X = X / np.linalg.norm(X, axis=1, keepdims=True)
        items = [{"action": f"action_{i}", "quote": f"quote_{i}"} for i in range(20)]

        clusters = cluster_items(X, items, best_k=3)

        self.assertEqual(len(clusters), 3)
        # All items accounted for
        total = sum(len(c[1]) for c in clusters)
        self.assertEqual(total, 20)

    def test_cluster_items_sorted_by_size(self):
        np.random.seed(42)
        X = np.random.randn(30, 3)
        X = X / np.linalg.norm(X, axis=1, keepdims=True)
        items = [{"action": f"a{i}", "quote": f"q{i}"} for i in range(30)]

        clusters = cluster_items(X, items, best_k=4)
        sizes = [len(c[1]) for c in clusters]
        self.assertEqual(sizes, sorted(sizes, reverse=True))

    def test_cluster_items_single_cluster(self):
        np.random.seed(42)
        X = np.random.randn(10, 3)
        X = X / np.linalg.norm(X, axis=1, keepdims=True)
        items = [{"action": f"a{i}", "quote": f"q{i}"} for i in range(10)]

        clusters = cluster_items(X, items, best_k=1)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(len(clusters[0][1]), 10)


class ExtractItemsForConversationTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.session = InterviewSession.objects.create(
            user=self.user, company_description='Test', num_interviews=1
        )
        self.conv = Conversation.objects.create(
            session=self.session,
            employee_role='Engineer',
            messages=[
                {"role": "interviewer", "content": "What needs improvement?"},
                {"role": "employee", "content": "We need better tooling."},
            ],
        )

    @patch('app.analysis.sync_to_async')
    @patch('app.analysis.extract_actions', new_callable=AsyncMock)
    def test_extract_items(self, mock_extract, mock_sync_to_async):
        mock_extract.return_value = [
            {"action": "Improve CI/CD", "quote": "We need better tooling"},
        ]
        # Mock sync_to_async to return an async no-op (avoid SQLite threading issues)
        mock_sync_to_async.side_effect = lambda fn: AsyncMock(return_value=MagicMock())

        sem = asyncio.Semaphore(5)
        result = asyncio.run(extract_items_for_conversation(self.conv, sem))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['action'], 'Improve CI/CD')
        mock_extract.assert_called_once_with(self.conv.messages)


class ExtractAllItemsTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.session = InterviewSession.objects.create(
            user=self.user, company_description='Test', num_interviews=2
        )
        self.conv1 = Conversation.objects.create(
            session=self.session, employee_role='CTO', messages=[{"role": "employee", "content": "msg1"}]
        )
        self.conv2 = Conversation.objects.create(
            session=self.session, employee_role='VP Eng', messages=[{"role": "employee", "content": "msg2"}]
        )

    @patch('app.analysis.sync_to_async')
    @patch('app.analysis.extract_actions', new_callable=AsyncMock)
    def test_extract_all(self, mock_extract, mock_sync_to_async):
        mock_extract.side_effect = [
            [{"action": "Action A", "quote": "Quote A"}],
            [{"action": "Action B", "quote": "Quote B"}, {"action": "Action C", "quote": "Quote C"}],
        ]
        mock_sync_to_async.side_effect = lambda fn: AsyncMock(return_value=MagicMock())

        result = asyncio.run(extract_all_items([self.conv1, self.conv2]))

        self.assertEqual(len(result), 3)
        self.assertEqual(mock_extract.call_count, 2)


class BuildEmbeddingsTest(TestCase):

    @patch('app.analysis.get_embeddings', new_callable=AsyncMock)
    def test_build_embeddings_single_batch(self, mock_embed):
        mock_embed.return_value = [[0.1, 0.2], [0.3, 0.4]]
        texts = ['action 1', 'action 2']

        result = asyncio.run(build_embeddings(texts))

        self.assertEqual(len(result), 2)
        mock_embed.assert_called_once_with(['action 1', 'action 2'])

    @patch('app.analysis.get_embeddings', new_callable=AsyncMock)
    def test_build_embeddings_multiple_batches(self, mock_embed):
        # 150 items should be split into 2 batches (100 + 50)
        mock_embed.side_effect = [
            [[0.1] * 3] * 100,
            [[0.2] * 3] * 50,
        ]
        texts = [f'action {i}' for i in range(150)]

        result = asyncio.run(build_embeddings(texts))

        self.assertEqual(len(result), 150)
        self.assertEqual(mock_embed.call_count, 2)


class SummarizeTopClustersTest(TestCase):

    @patch('app.analysis.summarize_theme', new_callable=AsyncMock)
    def test_summarize_top_3(self, mock_summarize):
        mock_summarize.side_effect = [
            ThemeSummarySchema(theme_name='Theme A', summary='Summary A', key_quotes=['q1']),
            ThemeSummarySchema(theme_name='Theme B', summary='Summary B', key_quotes=['q2']),
            ThemeSummarySchema(theme_name='Theme C', summary='Summary C', key_quotes=['q3']),
        ]
        clusters = [
            (0, [{"action": "a1", "quote": "q1"}, {"action": "a2", "quote": "q2"}]),
            (1, [{"action": "a3", "quote": "q3"}]),
            (2, [{"action": "a4", "quote": "q4"}]),
            (3, [{"action": "a5", "quote": "q5"}]),  # 4th cluster should be ignored
        ]

        result = asyncio.run(summarize_top_clusters(clusters))

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['theme_name'], 'Theme A')
        self.assertEqual(result[0]['action_count'], 2)
        self.assertEqual(mock_summarize.call_count, 3)

    @patch('app.analysis.summarize_theme', new_callable=AsyncMock)
    def test_summarize_fewer_than_3(self, mock_summarize):
        mock_summarize.return_value = ThemeSummarySchema(
            theme_name='Only Theme', summary='Summary', key_quotes=['q1']
        )
        clusters = [(0, [{"action": "a1", "quote": "q1"}])]

        result = asyncio.run(summarize_top_clusters(clusters))
        self.assertEqual(len(result), 1)


class RunAnalysisIntegrationTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.session = InterviewSession.objects.create(
            user=self.user, company_description='Test', num_interviews=3
        )
        self.conversations = []
        for role in ['CTO', 'VP Eng', 'Lead Dev']:
            conv = Conversation.objects.create(
                session=self.session,
                employee_role=role,
                messages=[
                    {"role": "interviewer", "content": "Question?"},
                    {"role": "employee", "content": f"Answer from {role}."},
                ],
            )
            self.conversations.append(conv)

    @patch('app.analysis.sync_to_async')
    @patch('app.analysis.summarize_theme', new_callable=AsyncMock)
    @patch('app.analysis.get_embeddings', new_callable=AsyncMock)
    @patch('app.analysis.extract_actions', new_callable=AsyncMock)
    def test_run_analysis_full_pipeline(self, mock_extract, mock_embed, mock_summarize, mock_sync_to_async):
        # Each conversation produces 2 actions
        mock_extract.return_value = [
            {"action": "Improve X", "quote": "We need X"},
            {"action": "Fix Y", "quote": "Y is broken"},
        ]
        # Mock sync_to_async to return async no-ops (avoid SQLite threading issues)
        mock_sync_to_async.side_effect = lambda fn: AsyncMock(return_value=MagicMock())

        # 6 actions total — create varied embeddings that form distinct clusters
        np.random.seed(42)
        mock_embed.return_value = (np.random.randn(6, 10) + np.array(
            [[5, 0, 0, 0, 0, 0, 0, 0, 0, 0],
             [5, 0, 0, 0, 0, 0, 0, 0, 0, 0],
             [0, 5, 0, 0, 0, 0, 0, 0, 0, 0],
             [0, 5, 0, 0, 0, 0, 0, 0, 0, 0],
             [0, 0, 5, 0, 0, 0, 0, 0, 0, 0],
             [0, 0, 5, 0, 0, 0, 0, 0, 0, 0]]
        )).tolist()

        mock_summarize.return_value = ThemeSummarySchema(
            theme_name='Operations', summary='Improve operations', key_quotes=['q1', 'q2']
        )
        mock_set_status = AsyncMock()

        themes = asyncio.run(run_analysis(self.conversations, mock_set_status))

        self.assertGreater(len(themes), 0)
        self.assertEqual(mock_extract.call_count, 3)
        mock_set_status.assert_any_call('clustering')
        mock_set_status.assert_any_call('summarizing')

    @patch('app.analysis.sync_to_async')
    @patch('app.analysis.extract_actions', new_callable=AsyncMock)
    def test_run_analysis_no_items(self, mock_extract, mock_sync_to_async):
        mock_extract.return_value = []
        mock_sync_to_async.side_effect = lambda fn: AsyncMock(return_value=MagicMock())
        mock_set_status = AsyncMock()

        themes = asyncio.run(run_analysis(self.conversations, mock_set_status))
        self.assertEqual(themes, [])
