"""Tests for Problem Solver skill."""

import unittest
from unittest.mock import Mock
from ..skill_config import SkillType, AlgorithmType, SkillConfig
from ..problem_solver import ProblemSolver
from ...tot_integration import VaultAwareLanguageModel


class MockVaultAwareLanguageModel(VaultAwareLanguageModel):
    """Mock implementation of VaultAwareLanguageModel for testing."""

    def __init__(self):
        pass

    def generate_thoughts(self, prompt, num_thoughts=5):
        return [f"Solution thought {i+1}" for i in range(num_thoughts)]

    def evaluate_states(self, states, prompt):
        return {state: 0.5 + (0.1 * i) for i, state in enumerate(states)}


class TestProblemSolverInitialization(unittest.TestCase):
    """Test ProblemSolver initialization."""

    def setUp(self):
        """Set up test fixtures."""
        self.llm_model = MockVaultAwareLanguageModel()

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        solver = ProblemSolver(llm_model=self.llm_model)
        self.assertEqual(solver.config.skill_type, SkillType.PROBLEM)
        self.assertEqual(solver.config.algorithm, AlgorithmType.BFS)
        self.assertEqual(solver.config.num_thoughts, 7)
        self.assertEqual(solver.config.max_steps, 8)

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = SkillConfig(
            skill_type=SkillType.PROBLEM,
            algorithm=AlgorithmType.DFS,
            name="Custom Problem Solver",
        )
        solver = ProblemSolver(config=config, llm_model=self.llm_model)
        self.assertEqual(solver.config.name, "Custom Problem Solver")

    def test_init_state_initialization(self):
        """Test internal state initialization."""
        solver = ProblemSolver(llm_model=self.llm_model)
        self.assertEqual(solver.problems_analyzed, [])
        self.assertEqual(solver.solutions_explored, [])
        self.assertEqual(solver.constraints_identified, [])


class TestProblemSolverValidation(unittest.TestCase):
    """Test input validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.solver = ProblemSolver(llm_model=MockVaultAwareLanguageModel())

    def test_validate_valid_problem(self):
        """Test validation of valid problem."""
        is_valid, msg = self.solver.validate_input(
            "How can we optimize our database performance"
        )
        self.assertTrue(is_valid)

    def test_validate_empty_prompt(self):
        """Test validation rejects empty prompt."""
        is_valid, msg = self.solver.validate_input("")
        self.assertFalse(is_valid)

    def test_validate_too_short_prompt(self):
        """Test validation rejects very short prompt."""
        is_valid, msg = self.solver.validate_input("solve this")
        self.assertFalse(is_valid)

    def test_validate_too_long_prompt(self):
        """Test validation rejects very long prompt."""
        long_problem = "problem " * 500
        is_valid, msg = self.solver.validate_input(long_problem)
        self.assertFalse(is_valid)

    def test_validate_non_problem_prompt(self):
        """Test validation rejects non-problem prompts."""
        is_valid, msg = self.solver.validate_input("tell me a funny story about cats")
        self.assertFalse(is_valid)

    def test_validate_with_problem_keyword(self):
        """Test validation accepts 'problem' keyword."""
        is_valid, msg = self.solver.validate_input("What is the main problem here")
        self.assertTrue(is_valid)

    def test_validate_with_solve_keyword(self):
        """Test validation accepts 'solve' keyword."""
        is_valid, msg = self.solver.validate_input("How can we solve this challenge")
        self.assertTrue(is_valid)


class TestProblemSolverSystemPrompt(unittest.TestCase):
    """Test system prompt generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.solver = ProblemSolver(llm_model=MockVaultAwareLanguageModel())

    def test_system_prompt_structure(self):
        """Test system prompt has expected content."""
        prompt = self.solver.build_system_prompt()
        self.assertIn("Problem Solver", prompt)
        self.assertIn("decompose", prompt.lower())

    def test_system_prompt_includes_methodology(self):
        """Test system prompt includes problem methodology."""
        prompt = self.solver.build_system_prompt()
        self.assertIn("solution", prompt.lower())
        self.assertIn("feasibility", prompt.lower())


class TestProblemSolverContext(unittest.TestCase):
    """Test problem context building."""

    def setUp(self):
        """Set up test fixtures."""
        self.solver = ProblemSolver(llm_model=MockVaultAwareLanguageModel())

    def test_build_problem_context_basic(self):
        """Test building problem context."""
        context = self.solver._build_problem_context(
            "optimize performance", "software", [], {}
        )
        self.assertIn("software", context.lower())
        self.assertIn("optimize", context)

    def test_build_problem_context_with_constraints(self):
        """Test context includes constraints."""
        constraints = ["Budget limit", "Time constraint"]
        context = self.solver._build_problem_context(
            "select solution", "engineering", constraints, {}
        )
        self.assertIn("Constraints", context)
        self.assertIn("Budget", context)

    def test_build_problem_context_with_resources(self):
        """Test context includes resources."""
        resources = {"team_size": 5, "budget": "$50k"}
        context = self.solver._build_problem_context(
            "allocate resources", "business", [], resources
        )
        self.assertIn("Resources", context)
        self.assertIn("team_size", context)


class TestProblemSolverSolutionExtraction(unittest.TestCase):
    """Test solution extraction from analysis."""

    def setUp(self):
        """Set up test fixtures."""
        self.solver = ProblemSolver(llm_model=MockVaultAwareLanguageModel())

    def test_extract_solutions(self):
        """Test extracting solutions."""
        analysis = """
        Solution 1: Implement caching layer
        Alternative approach: Use database optimization
        Strategy: Parallel processing
        """
        solutions = self.solver._extract_solutions(analysis)
        self.assertGreater(len(solutions), 0)

    def test_extract_solutions_limits_count(self):
        """Test extraction limits to 5."""
        analysis = "\n".join(
            [f"Solution {i}: Approach {i}" for i in range(10)]
        )
        solutions = self.solver._extract_solutions(analysis)
        self.assertLessEqual(len(solutions), 5)

    def test_extract_no_solutions(self):
        """Test when no solutions found."""
        solutions = self.solver._extract_solutions("just some random text here")
        self.assertEqual(len(solutions), 0)


class TestProblemSolverFeasibility(unittest.TestCase):
    """Test solution feasibility assessment."""

    def setUp(self):
        """Set up test fixtures."""
        self.solver = ProblemSolver(llm_model=MockVaultAwareLanguageModel())

    def test_assess_high_feasibility(self):
        """Test assessing high feasibility solution."""
        solution = "Simple and straightforward approach"
        assessment = self.solver._assess_solution_feasibility(solution)
        self.assertEqual(assessment["feasibility_level"], "high")
        self.assertEqual(assessment["estimated_effort"], "low")

    def test_assess_low_feasibility(self):
        """Test assessing low feasibility solution."""
        solution = "Complex and difficult approach requiring extensive work"
        assessment = self.solver._assess_solution_feasibility(solution)
        self.assertEqual(assessment["feasibility_level"], "low")
        self.assertEqual(assessment["estimated_effort"], "high")

    def test_assess_medium_feasibility(self):
        """Test assessing medium feasibility solution."""
        solution = "A moderate approach"
        assessment = self.solver._assess_solution_feasibility(solution)
        self.assertEqual(assessment["feasibility_level"], "medium")


class TestConstraintIdentification(unittest.TestCase):
    """Test constraint identification."""

    def setUp(self):
        """Set up test fixtures."""
        self.solver = ProblemSolver(llm_model=MockVaultAwareLanguageModel())

    def test_identify_budget_constraint(self):
        """Test identifying budget constraint."""
        analysis = "We have budget constraints to consider"
        constraints = self.solver._identify_constraints(analysis)
        self.assertGreater(len(constraints), 0)

    def test_identify_multiple_constraints(self):
        """Test identifying multiple constraints."""
        analysis = """
        Constraint: Budget must be under $100k
        Limitation: Cannot hire new staff
        Requirement: Must be completed in 3 months
        """
        constraints = self.solver._identify_constraints(analysis)
        self.assertGreater(len(constraints), 0)

    def test_identify_no_constraints(self):
        """Test when no constraints found."""
        constraints = self.solver._identify_constraints("random text")
        self.assertEqual(len(constraints), 0)


class TestAssumptionValidation(unittest.TestCase):
    """Test assumption validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.solver = ProblemSolver(llm_model=MockVaultAwareLanguageModel())

    def test_validate_solution_with_assumptions(self):
        """Test validating solution with assumptions."""
        solution = "Assume we have access to resource X and need team support"
        validation = self.solver._validate_assumptions(solution)
        self.assertGreater(validation["assumptions_identified"], 0)
        self.assertGreater(validation["risk_score"], 0.3)

    def test_validate_solution_without_assumptions(self):
        """Test validating solution without assumptions."""
        solution = "Use existing tools and processes"
        validation = self.solver._validate_assumptions(solution)
        self.assertEqual(validation["assumptions_identified"], 0)

    def test_assumption_validation_risk_bounds(self):
        """Test risk score is bounded."""
        solution = "assume require depend need must have resources"
        validation = self.solver._validate_assumptions(solution)
        self.assertGreaterEqual(validation["risk_score"], 0.0)
        self.assertLessEqual(validation["risk_score"], 1.0)


class TestProblemSolverExecution(unittest.TestCase):
    """Test skill execution."""

    def setUp(self):
        """Set up test fixtures."""
        self.solver = ProblemSolver(llm_model=MockVaultAwareLanguageModel())

    def test_execute_valid_problem(self):
        """Test executing with valid problem."""
        result = self.solver.execute("How can we improve system scalability")
        self.assertIsNotNone(result)
        self.assertEqual(result.skill_type, SkillType.PROBLEM)

    def test_execute_invalid_problem(self):
        """Test executing with invalid problem."""
        result = self.solver.execute("hello")
        self.assertEqual(result.confidence_score, 0.0)
        self.assertTrue(result.requires_human_review)

    def test_execute_stores_history(self):
        """Test execution stores in history."""
        self.solver.execute("How should we approach this problem")
        self.assertEqual(len(self.solver.execution_history), 1)

    def test_execute_with_context(self):
        """Test execution with context."""
        context = {
            "domain": "software-engineering",
            "constraints": ["Budget", "Timeline"],
            "resources": {"team": 3},
        }
        result = self.solver.execute(
            "How can we solve this technical problem", context=context
        )
        self.assertIsNotNone(result)


class TestProblemSolverSummary(unittest.TestCase):
    """Test problem summary generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.solver = ProblemSolver(llm_model=MockVaultAwareLanguageModel())

    def test_problem_summary(self):
        """Test generating problem summary."""
        summary = self.solver.get_problem_summary()
        self.assertIn("problems_analyzed", summary)
        self.assertIn("solutions_explored", summary)
        self.assertIn("constraints_identified", summary)
        self.assertIn("assumptions_validated", summary)
        self.assertEqual(summary["problems_analyzed"], 0)


if __name__ == "__main__":
    unittest.main()
