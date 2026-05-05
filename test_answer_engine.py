#!/usr/bin/env python3
"""Unit tests for answer_question in answer-engine."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_spec = importlib.util.spec_from_file_location(
    'answer_engine', Path(__file__).parent / 'answer-engine.py'
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

answer_question = _mod.answer_question
Classification = _mod.Classification
Stats = _mod.Stats
DEFAULT_MESSAGE = _mod.DEFAULT_MESSAGE


class TestAnswerQuestion(unittest.TestCase):

    def setUp(self):
        self.client = MagicMock()
        self.clf_system = 'classify'
        self.system = 'answer'
        self.question = 'What is Python?'
        self.stats = Stats()
        self.cache = {}

    def test_information_seeking_wiki_returns_model_answer(self):
        with (
            patch.object(_mod, '_classify_question') as mock_classify,
            patch.object(_mod, 'get_answer') as mock_get_answer,
        ):
            mock_classify.return_value = Classification(
                intent='information-seeking', topic='wiki'
            )
            mock_get_answer.return_value = 'Python is a programming language.'
            result = answer_question(
                self.client, self.clf_system, self.system,
                self.question, self.stats, self.cache,
            )
            self.assertEqual(result, 'Python is a programming language.')
            mock_get_answer.assert_called_once_with(
                self.client, self.system, self.question, self.stats, False
            )

    def test_other_intent_returns_default_message(self):
        with (
            patch.object(_mod, '_classify_question') as mock_classify,
            patch.object(_mod, 'get_answer') as mock_get_answer,
        ):
            mock_classify.return_value = Classification(
                intent='other', topic='wiki'
            )
            result = answer_question(
                self.client, self.clf_system, self.system,
                self.question, self.stats, self.cache,
            )
            self.assertEqual(result, DEFAULT_MESSAGE)
            mock_get_answer.assert_not_called()

    def test_non_wiki_topic_returns_default_message(self):
        with (
            patch.object(_mod, '_classify_question') as mock_classify,
            patch.object(_mod, 'get_answer') as mock_get_answer,
        ):
            mock_classify.return_value = Classification(
                intent='information-seeking', topic='non-wiki'
            )
            result = answer_question(
                self.client, self.clf_system, self.system,
                self.question, self.stats, self.cache,
            )
            self.assertEqual(result, DEFAULT_MESSAGE)
            mock_get_answer.assert_not_called()

    def test_cached_question_skips_api_calls(self):
        self.cache[self.question] = 'Cached answer.'
        with (
            patch.object(_mod, '_classify_question') as mock_classify,
            patch.object(_mod, 'get_answer') as mock_get_answer,
        ):
            result = answer_question(
                self.client, self.clf_system, self.system,
                self.question, self.stats, self.cache,
            )
            self.assertEqual(result, 'Cached answer.')
            mock_classify.assert_not_called()
            mock_get_answer.assert_not_called()

    def test_answer_is_stored_in_cache(self):
        with (
            patch.object(_mod, '_classify_question') as mock_classify,
            patch.object(_mod, 'get_answer') as mock_get_answer,
        ):
            mock_classify.return_value = Classification(
                intent='information-seeking', topic='wiki'
            )
            mock_get_answer.return_value = 'Python is a programming language.'
            answer_question(
                self.client, self.clf_system, self.system,
                self.question, self.stats, self.cache,
            )
            self.assertEqual(
                self.cache[self.question], 'Python is a programming language.'
            )


if __name__ == '__main__':
    unittest.main()
