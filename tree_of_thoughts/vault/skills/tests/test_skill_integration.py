"""Integration tests for skills system."""

import json
import unittest
from unittest.mock import Mock, patch

from ..skill_config import SkillType, AlgorithmType, SkillConfig
from ..research_analyst import ResearchAnalyst
from ..decision_maker import DecisionMaker
from ..code_reviewer import CodeReviewer
from ..thesis_validator import ThesisValidator
from ..problem_solver import ProblemSolver
from ..expert_simulator import ExpertSimulator
from ..skills_cli import SkillsCLI
from ...tot_integration import VaultAwareLanguageModel


class MockVaultAwareLanguageModel(VaultAwareLanguageModel):
    """Mock implementation for integration tests."""

    def __init__(self):
        pass

    def generate_thoughts(self, prompt, num_thoughts=5):
        return [f"Thought {i+1}" for i in range(num_thoughts)]

    def evaluate_states(self, states, prompt):
        return {state: 0.5 + (0.1 * i) for i, state in enumerate(states)}


class TestSkillsCLI(unittest.TestCase):
    """Test the unified CLI interface."""

    def setUp(self):
        """Set up CLI instance."""
        self.mock_llm = MockVaultAwareLanguageModel()
        self.cli = SkillsCLI(llm_model=self.mock_llm)

    def test_cli_list_skills(self):
        """Test listing available skills."""
        result = self.cli.list_skills()
        self.assertIn("available_skills", result)
        self.assertEqual(len(result["available_skills"]), 6)

    def test_cli_get_skill_research(self):
        """Test getting research analyst skill."""
        skill = self.cli.get_skill("research")
        self.assertIsNotNone(skill)
        self.assertIsInstance(skill, ResearchAnalyst)

    def test_cli_get_skill_decision(self):
        """Test getting decision maker skill."""
        skill = self.cli.get_skill("decision")
        self.assertIsNotNone(skill)
        self.assertIsInstance(skill, DecisionMaker)

    def test_cli_get_skill_code(self):
        """Test getting code reviewer skill."""
        skill = self.cli.get_skill("code")
        self.assertIsNotNone(skill)
        self.assertIsInstance(skill, CodeReviewer)

    def test_cli_get_skill_thesis(self):
        """Test getting thesis validator skill."""
        skill = self.cli.get_skill("thesis")
        self.assertIsNotNone(skill)
        self.assertIsInstance(skill, ThesisValidator)

    def test_cli_get_skill_problem(self):
        """Test getting problem solver skill."""
        skill = self.cli.get_skill("problem")
        self.assertIsNotNone(skill)
        self.assertIsInstance(skill, ProblemSolver)

    def test_cli_get_skill_expert(self):
        """Test getting expert simulator skill."""
        skill = self.cli.get_skill("expert")
        self.assertIsNotNone(skill)
        self.assertIsInstance(skill, ExpertSimulator)

    def test_cli_get_unknown_skill(self):
        """Test getting unknown skill."""
        skill = self.cli.get_skill("unknown")
        self.assertIsNone(skill)

    def test_cli_execute_research(self):
        """Test executing research skill via CLI."""
        result = self.cli.execute_skill(
            "research", "What are recent AI breakthroughs in 2026"
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["skill"], "research")
        self.assertIn("confidence_score", result)

    def test_cli_execute_decision(self):
        """Test executing decision maker skill via CLI."""
        result = self.cli.execute_skill(
            "decision", "Should we migrate to cloud infrastructure"
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["skill"], "decision")

    def test_cli_execute_problem(self):
        """Test executing problem solver skill via CLI."""
        result = self.cli.execute_skill(
            "problem", "How can we improve system scalability significantly"
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["skill"], "problem")

    def test_cli_execute_expert(self):
        """Test executing expert simulator skill via CLI."""
        result = self.cli.execute_skill(
            "expert", "What expert recommendation for architecture design"
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["skill"], "expert")

    def test_cli_execute_with_context(self):
        """Test executing skill with context."""
        context = {"domain": "software-engineering"}
        result = self.cli.execute_skill(
            "research", "What are latest DevOps practices", context=context
        )
        self.assertTrue(result["success"])

    def test_cli_execute_invalid_skill(self):
        """Test executing invalid skill."""
        result = self.cli.execute_skill("invalid", "some prompt")
        self.assertIn("error", result)
        self.assertIn("available_skills", result)


class TestSkillInteroperability(unittest.TestCase):
    """Test that skills work well together."""

    def setUp(self):
        """Set up skills with mock LLM."""
        self.llm = MockVaultAwareLanguageModel()

    def test_all_skills_have_same_interface(self):
        """Test that all skills implement the same interface."""
        skills = [
            ResearchAnalyst(llm_model=self.llm),
            DecisionMaker(llm_model=self.llm),
            CodeReviewer(llm_model=self.llm),
            ThesisValidator(llm_model=self.llm),
            ProblemSolver(llm_model=self.llm),
            ExpertSimulator(llm_model=self.llm),
        ]

        for skill in skills:
            # All skills should have these methods
            self.assertTrue(hasattr(skill, "validate_input"))
            self.assertTrue(hasattr(skill, "build_system_prompt"))
            self.assertTrue(hasattr(skill, "execute"))
            self.assertTrue(callable(skill.validate_input))
            self.assertTrue(callable(skill.build_system_prompt))
            self.assertTrue(callable(skill.execute))

    def test_all_skills_have_config(self):
        """Test that all skills have proper config."""
        skills = [
            ResearchAnalyst(llm_model=self.llm),
            DecisionMaker(llm_model=self.llm),
            CodeReviewer(llm_model=self.llm),
            ThesisValidator(llm_model=self.llm),
            ProblemSolver(llm_model=self.llm),
            ExpertSimulator(llm_model=self.llm),
        ]

        for skill in skills:
            self.assertIsNotNone(skill.config)
            self.assertIn(skill.config.skill_type, SkillType)
            self.assertIn(skill.config.algorithm, AlgorithmType)

    def test_all_skills_use_different_algorithms(self):
        """Test that each skill uses a unique algorithm."""
        skills_with_algorithms = [
            (ResearchAnalyst(llm_model=self.llm), AlgorithmType.A_STAR),
            (DecisionMaker(llm_model=self.llm), AlgorithmType.BEST),
            (CodeReviewer(llm_model=self.llm), AlgorithmType.BFS),
            (ThesisValidator(llm_model=self.llm), AlgorithmType.MCTS),
            (ProblemSolver(llm_model=self.llm), AlgorithmType.BFS),
            (ExpertSimulator(llm_model=self.llm), AlgorithmType.DFS),
        ]

        for skill, expected_algo in skills_with_algorithms:
            self.assertEqual(skill.config.algorithm, expected_algo)

    def test_all_skills_have_execution_history(self):
        """Test that all skills track execution history."""
        skills = [
            ResearchAnalyst(llm_model=self.llm),
            DecisionMaker(llm_model=self.llm),
            CodeReviewer(llm_model=self.llm),
            ThesisValidator(llm_model=self.llm),
            ProblemSolver(llm_model=self.llm),
            ExpertSimulator(llm_model=self.llm),
        ]

        for skill in skills:
            self.assertTrue(hasattr(skill, "execution_history"))
            self.assertEqual(len(skill.execution_history), 0)


class TestSkillWorkflow(unittest.TestCase):
    """Test complex workflows with multiple skills."""

    def setUp(self):
        """Set up skills."""
        self.llm = MockVaultAwareLanguageModel()

    def test_sequential_skill_execution(self):
        """Test executing multiple skills in sequence."""
        research = ResearchAnalyst(llm_model=self.llm)
        decision = DecisionMaker(llm_model=self.llm)

        # Execute research first
        research_result = research.execute(
            "What are cloud infrastructure best practices"
        )
        self.assertIsNotNone(research_result)

        # Execute decision based on research
        decision_result = decision.execute(
            "Should we adopt cloud infrastructure for our systems"
        )
        self.assertIsNotNone(decision_result)

    def test_skill_error_handling_cascade(self):
        """Test that skill errors don't cascade to other skills."""
        research = ResearchAnalyst(llm_model=self.llm)
        problem = ProblemSolver(llm_model=self.llm)

        # Execute with invalid input to first skill
        research_result = research.execute("invalid")
        # Result should have confidence of 0 for invalid input
        self.assertEqual(research_result.confidence_score, 0.0)

        # Second skill should still work
        problem_result = problem.execute(
            "How can we solve performance issues"
        )
        self.assertIsNotNone(problem_result)

    def test_skill_summary_methods_exist(self):
        """Test that all skills have summary methods."""
        skills_with_methods = [
            (ResearchAnalyst(llm_model=self.llm), "get_research_summary"),
            (DecisionMaker(llm_model=self.llm), "get_decision_summary"),
            (CodeReviewer(llm_model=self.llm), "get_review_summary"),
            (ThesisValidator(llm_model=self.llm), "get_validation_summary"),
            (ProblemSolver(llm_model=self.llm), "get_problem_summary"),
            (ExpertSimulator(llm_model=self.llm), "get_expert_summary"),
        ]

        for skill, method_name in skills_with_methods:
            self.assertTrue(hasattr(skill, method_name))
            summary = getattr(skill, method_name)()
            self.assertIsInstance(summary, dict)
            self.assertGreater(len(summary), 0)


class TestSkillValidation(unittest.TestCase):
    """Test validation across all skills."""

    def setUp(self):
        """Set up skills."""
        self.llm = MockVaultAwareLanguageModel()

    def test_all_skills_validate_empty_input(self):
        """Test that all skills reject empty input."""
        skills = [
            ResearchAnalyst(llm_model=self.llm),
            DecisionMaker(llm_model=self.llm),
            CodeReviewer(llm_model=self.llm),
            ThesisValidator(llm_model=self.llm),
            ProblemSolver(llm_model=self.llm),
            ExpertSimulator(llm_model=self.llm),
        ]

        for skill in skills:
            is_valid, msg = skill.validate_input("")
            self.assertFalse(is_valid)

    def test_all_skills_validate_short_input(self):
        """Test that all skills reject very short input."""
        skills = [
            ResearchAnalyst(llm_model=self.llm),
            DecisionMaker(llm_model=self.llm),
            CodeReviewer(llm_model=self.llm),
            ThesisValidator(llm_model=self.llm),
            ProblemSolver(llm_model=self.llm),
            ExpertSimulator(llm_model=self.llm),
        ]

        for skill in skills:
            is_valid, msg = skill.validate_input("short")
            self.assertFalse(is_valid)

    def test_all_skills_validate_long_input(self):
        """Test that all skills reject very long input."""
        skills = [
            ResearchAnalyst(llm_model=self.llm),
            DecisionMaker(llm_model=self.llm),
            CodeReviewer(llm_model=self.llm),
            ThesisValidator(llm_model=self.llm),
            ProblemSolver(llm_model=self.llm),
            ExpertSimulator(llm_model=self.llm),
        ]

        long_input = "word " * 1000

        for skill in skills:
            is_valid, msg = skill.validate_input(long_input)
            self.assertFalse(is_valid)


class TestSkillPerformance(unittest.TestCase):
    """Test performance characteristics of skills."""

    def setUp(self):
        """Set up skills."""
        self.llm = MockVaultAwareLanguageModel()

    def test_skill_execution_has_timing(self):
        """Test that execution results include timing information."""
        skill = ResearchAnalyst(llm_model=self.llm)
        result = skill.execute("What are recent technology trends")

        self.assertIsNotNone(result.execution_time)
        self.assertGreater(result.execution_time, 0)

    def test_skill_execution_produces_output(self):
        """Test that skill execution produces output."""
        skill = DecisionMaker(llm_model=self.llm)
        result = skill.execute("Should we invest in new technology")

        self.assertIsNotNone(result.output)
        self.assertGreater(len(result.output), 0)

    def test_skill_produces_confidence_scores(self):
        """Test that all skills produce confidence scores."""
        skills = [
            ResearchAnalyst(llm_model=self.llm),
            DecisionMaker(llm_model=self.llm),
            CodeReviewer(llm_model=self.llm),
            ThesisValidator(llm_model=self.llm),
            ProblemSolver(llm_model=self.llm),
            ExpertSimulator(llm_model=self.llm),
        ]

        for skill in skills:
            result = skill.execute(self._get_valid_prompt_for_skill(skill))
            self.assertIsNotNone(result.confidence_score)
            self.assertGreaterEqual(result.confidence_score, 0.0)
            self.assertLessEqual(result.confidence_score, 1.0)

    def _get_valid_prompt_for_skill(self, skill):
        """Get valid prompt for skill type."""
        if isinstance(skill, ResearchAnalyst):
            return "What are recent AI breakthroughs"
        elif isinstance(skill, DecisionMaker):
            return "Should we adopt new technology"
        elif isinstance(skill, CodeReviewer):
            return "Review this code for security issues"
        elif isinstance(skill, ThesisValidator):
            return "Thesis: Technology improves society"
        elif isinstance(skill, ProblemSolver):
            return "How can we improve performance"
        elif isinstance(skill, ExpertSimulator):
            return "What expert recommendation for design"
        return "Valid test prompt"


if __name__ == "__main__":
    unittest.main()
