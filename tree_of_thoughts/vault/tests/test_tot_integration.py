"""Tests for tot_integration module."""

import unittest
from unittest.mock import Mock, MagicMock, patch
from ..tot_integration import (
    VaultAwareLanguageModel,
    ValidatedThought,
    ToTSearchResult,
    ConfidenceLevel,
)
from ..validation_engine import ValidationIssueType


class TestValidatedThought(unittest.TestCase):
    """Test ValidatedThought dataclass."""

    def test_create_valid_thought(self):
        """Test creating a validated thought."""
        thought = ValidatedThought(
            text="The sky is blue",
            evaluation_score=0.8,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
            is_valid=True,
        )
        self.assertEqual(thought.text, "The sky is blue")
        self.assertEqual(thought.evaluation_score, 0.8)
        self.assertTrue(thought.is_valid)

    def test_thought_with_issues(self):
        """Test thought with validation issues."""
        thought = ValidatedThought(
            text="Incomplete thought...",
            evaluation_score=0.4,
            confidence=0.3,
            confidence_level=ConfidenceLevel.LOW,
            is_valid=False,
            validation_issues=["INCOMPLETE", "TRUNCATED"],
        )
        self.assertEqual(len(thought.validation_issues), 2)


class TestToTSearchResult(unittest.TestCase):
    """Test ToTSearchResult dataclass."""

    def test_create_search_result(self):
        """Test creating search result."""
        result = ToTSearchResult(
            solution="The answer is 42",
            best_state="reasoning step",
            confidence_score=0.75,
            confidence_level=ConfidenceLevel.HIGH,
            search_depth=3,
            nodes_explored=12,
            validation_report={},
            fact_check_report={},
            blind_validation_report={},
        )
        self.assertEqual(result.solution, "The answer is 42")
        self.assertEqual(result.confidence_score, 0.75)
        self.assertFalse(result.requires_review)

    def test_result_requires_review(self):
        """Test flagging results that need review."""
        result = ToTSearchResult(
            solution="Low confidence answer",
            best_state="poor reasoning",
            confidence_score=0.3,
            confidence_level=ConfidenceLevel.LOW,
            search_depth=1,
            nodes_explored=2,
            validation_report={"is_valid": False},
            fact_check_report={},
            blind_validation_report={},
            requires_review=True,
        )
        self.assertTrue(result.requires_review)


class TestVaultAwareLanguageModel(unittest.TestCase):
    """Test VaultAwareLanguageModel class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_llm = Mock()
        self.model = VaultAwareLanguageModel(
            llm_client=self.mock_llm,
            vault_root=None,  # Don't use real vault
            validate_thoughts=True,
            fact_check=False,
            blind_validate=False,
            persist_to_vault=False,
        )

    def test_initialization(self):
        """Test model initialization."""
        self.assertIsNotNone(self.model.llm_client)
        self.assertIsNotNone(self.model.validator)
        self.assertIsNotNone(self.model.fact_checker)
        self.assertTrue(self.model.validate_thoughts)
        self.assertFalse(self.model.persist_to_vault)

    def test_generate_thoughts(self):
        """Test thought generation."""
        self.mock_llm.call.return_value = "Next thought: analyze the problem"

        prompt = "Solve this problem"
        thoughts = self.model.generate_thoughts(prompt, k=3)

        self.assertEqual(len(thoughts), 3)
        self.assertEqual(self.mock_llm.call.call_count, 3)

    def test_generate_thoughts_with_tuple_state(self):
        """Test thought generation from tuple state."""
        self.mock_llm.call.return_value = "Continue reasoning"

        state = ("step 1", "step 2")
        thoughts = self.model.generate_thoughts(state, k=2)

        self.assertEqual(len(thoughts), 2)
        # Verify the state was converted to string
        call_args = self.mock_llm.call.call_args_list[0]
        self.assertIn("step 1 → step 2", call_args[1]["prompt"])

    def test_evaluate_states_single(self):
        """Test evaluating a single state."""
        self.mock_llm.call.return_value = "0.75"

        states = {"reasoning state": 0.0}
        evaluations = self.model.evaluate_states(states)

        self.assertEqual(len(evaluations), 1)
        self.assertEqual(evaluations["reasoning state"], 0.75)

    def test_evaluate_states_multiple(self):
        """Test evaluating multiple states."""
        self.mock_llm.call.side_effect = ["0.8", "0.6", "0.4"]

        states = {
            "state 1": 0.0,
            "state 2": 0.0,
            "state 3": 0.0,
        }
        evaluations = self.model.evaluate_states(states)

        self.assertEqual(len(evaluations), 3)
        self.assertEqual(evaluations["state 1"], 0.8)
        self.assertEqual(evaluations["state 2"], 0.6)
        self.assertEqual(evaluations["state 3"], 0.4)

    def test_evaluate_states_clamping(self):
        """Test that scores are clamped to [0, 1]."""
        self.mock_llm.call.side_effect = ["1.5", "-0.5"]

        states = {"too high": 0.0, "too low": 0.0}
        evaluations = self.model.evaluate_states(states)

        self.assertEqual(evaluations["too high"], 1.0)
        self.assertEqual(evaluations["too low"], 0.0)

    def test_evaluate_states_invalid_response(self):
        """Test handling invalid evaluation response."""
        self.mock_llm.call.return_value = "not a number"

        states = {"state": 0.0}
        evaluations = self.model.evaluate_states(states)

        # Should default to 0.5 on parsing error
        self.assertEqual(evaluations["state"], 0.5)

    def test_evaluate_states_caching(self):
        """Test that evaluated states are cached."""
        self.mock_llm.call.return_value = "0.7"

        state_text = "test state"
        states = {state_text: 0.0}

        # First evaluation
        result1 = self.model.evaluate_states(states)
        first_call_count = self.mock_llm.call.call_count

        # Second evaluation of same state
        result2 = self.model.evaluate_states(states)

        # Should use cache, so call count shouldn't increase
        self.assertEqual(self.mock_llm.call.call_count, first_call_count)
        self.assertEqual(result1[state_text], result2[state_text])

    def test_generate_solution(self):
        """Test solution generation from state."""
        self.mock_llm.call.return_value = "Final answer based on reasoning"

        best_state = "reasoning step 1 → step 2"
        solution = self.model.generate_solution("What is the answer?", best_state)

        self.assertIn("answer", solution.lower())

    def test_generate_solution_with_tuple_state(self):
        """Test solution generation from tuple state."""
        self.mock_llm.call.return_value = "Solution"

        best_state = ("step 1", "step 2", "step 3")
        solution = self.model.generate_solution("Problem", best_state)

        self.assertIsNotNone(solution)

    def test_confidence_mapping(self):
        """Test confidence score to level mapping."""
        test_cases = [
            (0.95, ConfidenceLevel.CERTAIN),
            (0.75, ConfidenceLevel.HIGH),
            (0.55, ConfidenceLevel.MEDIUM),
            (0.35, ConfidenceLevel.LOW),
            (0.15, ConfidenceLevel.VERY_LOW),
        ]

        for score, expected_level in test_cases:
            if score >= 0.9:
                self.assertEqual(expected_level, ConfidenceLevel.CERTAIN)
            elif score >= 0.7:
                self.assertEqual(expected_level, ConfidenceLevel.HIGH)
            elif score >= 0.5:
                self.assertEqual(expected_level, ConfidenceLevel.MEDIUM)
            elif score >= 0.3:
                self.assertEqual(expected_level, ConfidenceLevel.LOW)
            else:
                self.assertEqual(expected_level, ConfidenceLevel.VERY_LOW)

    def test_search_with_validation(self):
        """Test complete search with validation."""
        # Mock LLM responses
        self.mock_llm.call.side_effect = [
            "Thought 1",  # generate_thoughts call 1
            "Thought 2",  # generate_thoughts call 2
            "Thought 3",  # generate_thoughts call 3
            "0.8",  # evaluate Thought 1
            "0.6",  # evaluate Thought 2
            "0.7",  # evaluate Thought 3
            "The complete solution",  # generate_solution
        ]

        result = self.model.search_with_validation(
            "Solve this problem",
            section="BRAIN",
            search_depth=3,
        )

        self.assertIsNotNone(result)
        self.assertIsNotNone(result.solution)
        self.assertEqual(result.search_depth, 3)
        self.assertGreater(result.nodes_explored, 0)

    def test_search_result_confidence_calculation(self):
        """Test confidence calculation in search results."""
        self.mock_llm.call.side_effect = [
            "Thought 1",
            "Thought 2",
            "0.9",
            "0.8",
            "Final solution",
        ]

        result = self.model.search_with_validation("Problem")

        # Confidence should be combination of validation, fact-check, and evaluation
        self.assertGreaterEqual(result.confidence_score, 0.0)
        self.assertLessEqual(result.confidence_score, 1.0)
        self.assertIsNotNone(result.confidence_level)

    def test_get_search_report(self):
        """Test report generation."""
        # Create a mock result
        result = ToTSearchResult(
            solution="Test solution",
            best_state="test state",
            confidence_score=0.75,
            confidence_level=ConfidenceLevel.HIGH,
            search_depth=3,
            nodes_explored=9,
            validation_report={"is_valid": True, "issues": []},
            fact_check_report={"total_claims": 5, "verifiable_claims": 4},
            blind_validation_report={"consensus": {"final_score": 0.78}},
        )
        self.model.current_search = result

        report = self.model.get_search_report()

        self.assertIn("TREE OF THOUGHTS SEARCH REPORT", report)
        self.assertIn("Test solution", report)
        self.assertIn("75.0%", report)  # Format is 75.0% not 75%
        self.assertIn("high", report)  # Level is lowercase

    def test_get_search_report_no_results(self):
        """Test report when no search has been run."""
        self.model.current_search = None
        report = self.model.get_search_report()

        self.assertIn("No search results available", report)

    def test_explored_states_tracking(self):
        """Test that explored states are tracked."""
        self.model.explored_states.add("state 1")
        self.model.explored_states.add("state 2")

        self.assertEqual(len(self.model.explored_states), 2)
        self.assertIn("state 1", self.model.explored_states)

    def test_state_validation_storage(self):
        """Test storage of validated thoughts."""
        thought = ValidatedThought(
            text="test",
            evaluation_score=0.8,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
            is_valid=True,
        )
        self.model.state_validations["test"] = thought

        self.assertEqual(self.model.state_validations["test"].confidence, 0.9)

    def test_model_without_validation(self):
        """Test model can run without validation."""
        model_no_val = VaultAwareLanguageModel(
            llm_client=self.mock_llm,
            vault_root=None,
            validate_thoughts=False,
        )

        self.mock_llm.call.return_value = "0.7"
        states = {"state": 0.0}
        evaluations = model_no_val.evaluate_states(states)

        # Should evaluate without validation checks
        self.assertEqual(evaluations["state"], 0.7)

    def test_model_without_vault_persistence(self):
        """Test model works without vault persistence."""
        model_no_vault = VaultAwareLanguageModel(
            llm_client=self.mock_llm,
            vault_root=None,
            persist_to_vault=False,
        )

        self.assertFalse(model_no_vault.persist_to_vault)
        self.assertIsNone(model_no_vault.vault)


class TestVaultAwareLanguageModelIntegration(unittest.TestCase):
    """Integration tests for complete workflows."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_llm = Mock()
        self.model = VaultAwareLanguageModel(
            llm_client=self.mock_llm,
            vault_root=None,
            validate_thoughts=True,
            fact_check=True,
            blind_validate=False,
            persist_to_vault=False,
        )

    def test_complete_reasoning_cycle(self):
        """Test complete cycle: generate → evaluate → generate solution."""
        self.mock_llm.call.side_effect = [
            "First reasoning step",  # generate_thoughts
            "Second reasoning step",  # generate_thoughts
            "0.8",  # evaluate first thought
            "0.6",  # evaluate second thought
            "Therefore, the answer is X",  # generate_solution
        ]

        # Simulate a complete reasoning cycle
        initial_prompt = "What is the meaning?"
        thoughts = self.model.generate_thoughts(initial_prompt, k=2)
        evaluations = self.model.evaluate_states({t: 0.0 for t in thoughts})
        best_thought = max(evaluations.items(), key=lambda x: x[1])
        solution = self.model.generate_solution(initial_prompt, best_thought[0])

        self.assertEqual(len(thoughts), 2)
        self.assertEqual(len(evaluations), 2)
        self.assertIn("answer", solution.lower())


if __name__ == "__main__":
    unittest.main()
