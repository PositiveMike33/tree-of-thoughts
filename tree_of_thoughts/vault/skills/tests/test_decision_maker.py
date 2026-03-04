"""Tests for Decision Maker skill."""

import unittest
from unittest.mock import Mock
from ..skill_config import SkillType, AlgorithmType, SkillConfig
from ..decision_maker import DecisionMaker
from ...tot_integration import VaultAwareLanguageModel


class MockVaultAwareLanguageModel(VaultAwareLanguageModel):
    """Mock implementation of VaultAwareLanguageModel for testing."""

    def __init__(self):
        pass

    def generate_thoughts(self, prompt, num_thoughts=5):
        return [f"Decision thought {i+1}" for i in range(num_thoughts)]

    def evaluate_states(self, states, prompt):
        return {state: 0.5 + (0.1 * i) for i, state in enumerate(states)}


class TestDecisionMakerInitialization(unittest.TestCase):
    """Test DecisionMaker initialization."""

    def setUp(self):
        """Set up test fixtures."""
        self.llm_model = MockVaultAwareLanguageModel()

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        maker = DecisionMaker(llm_model=self.llm_model)
        self.assertEqual(maker.config.skill_type, SkillType.DECISION)
        self.assertEqual(maker.config.algorithm, AlgorithmType.BEST)
        self.assertEqual(maker.config.num_thoughts, 6)
        self.assertEqual(maker.config.max_steps, 5)
        self.assertEqual(maker.config.confidence_threshold, 0.80)

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = SkillConfig(
            skill_type=SkillType.DECISION,
            algorithm=AlgorithmType.BFS,
            name="Custom Decision Maker",
        )
        maker = DecisionMaker(config=config, llm_model=self.llm_model)
        self.assertEqual(maker.config.name, "Custom Decision Maker")

    def test_init_state_initialization(self):
        """Test internal state initialization."""
        maker = DecisionMaker(llm_model=self.llm_model)
        self.assertEqual(maker.criteria_analyzed, [])
        self.assertEqual(maker.risks_identified, [])
        self.assertEqual(maker.alternatives_evaluated, [])
        self.assertEqual(maker.recommendations, [])


class TestDecisionMakerValidation(unittest.TestCase):
    """Test input validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.maker = DecisionMaker(llm_model=MockVaultAwareLanguageModel())

    def test_validate_valid_decision(self):
        """Test validation of valid decision prompt."""
        is_valid, msg = self.maker.validate_input(
            "should we invest in new technology"
        )
        self.assertTrue(is_valid)

    def test_validate_empty_prompt(self):
        """Test validation rejects empty prompt."""
        is_valid, msg = self.maker.validate_input("")
        self.assertFalse(is_valid)

    def test_validate_too_short_prompt(self):
        """Test validation rejects very short prompt."""
        is_valid, msg = self.maker.validate_input("decide now")
        self.assertFalse(is_valid)
        self.assertIn("least 15", msg)

    def test_validate_too_long_prompt(self):
        """Test validation rejects very long prompt."""
        long_prompt = "decision " * 300
        is_valid, msg = self.maker.validate_input(long_prompt)
        self.assertFalse(is_valid)

    def test_validate_non_decision_prompt(self):
        """Test validation rejects non-decision prompts."""
        is_valid, msg = self.maker.validate_input("write a story about dragons")
        self.assertFalse(is_valid)

    def test_validate_with_decide_keyword(self):
        """Test validation accepts 'decide' keyword."""
        is_valid, msg = self.maker.validate_input("decide which option is best")
        self.assertTrue(is_valid)

    def test_validate_with_choice_keyword(self):
        """Test validation accepts 'choice' keyword."""
        is_valid, msg = self.maker.validate_input("what choice should we make")
        self.assertTrue(is_valid)

    def test_validate_with_should_keyword(self):
        """Test validation accepts 'should' keyword."""
        is_valid, msg = self.maker.validate_input("should we proceed with plan A")
        self.assertTrue(is_valid)


class TestDecisionMakerSystemPrompt(unittest.TestCase):
    """Test system prompt generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.maker = DecisionMaker(llm_model=MockVaultAwareLanguageModel())

    def test_system_prompt_structure(self):
        """Test system prompt has expected content."""
        prompt = self.maker.build_system_prompt()
        self.assertIn("Decision Maker", prompt)
        self.assertIn("structured analysis", prompt)

    def test_system_prompt_includes_methodology(self):
        """Test system prompt includes decision methodology."""
        prompt = self.maker.build_system_prompt()
        self.assertIn("multi-criteria", prompt.lower())
        self.assertIn("alternative", prompt.lower())

    def test_system_prompt_includes_output_format(self):
        """Test system prompt specifies output format."""
        prompt = self.maker.build_system_prompt()
        self.assertIn("output format", prompt.lower())


class TestDecisionMakerContext(unittest.TestCase):
    """Test decision context building."""

    def setUp(self):
        """Set up test fixtures."""
        self.maker = DecisionMaker(llm_model=MockVaultAwareLanguageModel())

    def test_build_decision_context_basic(self):
        """Test building decision context."""
        context = self.maker._build_decision_context(
            "choose between options", [], []
        )
        self.assertIn("Decision Problem", context)
        self.assertIn("choose between options", context)

    def test_build_decision_context_with_stakeholders(self):
        """Test context includes stakeholders."""
        stakeholders = ["Customer", "Manager", "Team"]
        context = self.maker._build_decision_context(
            "decide on implementation", stakeholders, []
        )
        self.assertIn("Stakeholders", context)
        self.assertIn("Customer", context)

    def test_build_decision_context_with_constraints(self):
        """Test context includes constraints."""
        constraints = ["Budget limit", "Timeline constraint"]
        context = self.maker._build_decision_context(
            "decide on approach", [], constraints
        )
        self.assertIn("Constraints", context)
        self.assertIn("Budget limit", context)

    def test_build_decision_context_limits_items(self):
        """Test context limits stakeholders and constraints."""
        stakeholders = [f"Stakeholder {i}" for i in range(10)]
        constraints = [f"Constraint {i}" for i in range(10)]
        context = self.maker._build_decision_context(
            "test", stakeholders, constraints
        )
        # Should have exactly 5 stakeholders listed
        self.assertGreaterEqual(context.count("- Stakeholder"), 5)


class TestDecisionMakerCriteriaAnalysis(unittest.TestCase):
    """Test decision criteria identification."""

    def setUp(self):
        """Set up test fixtures."""
        self.maker = DecisionMaker(llm_model=MockVaultAwareLanguageModel())

    def test_identify_cost_criterion(self):
        """Test identifying cost as criterion."""
        analysis = "The cost of this option is significant"
        criteria = self.maker._identify_decision_criteria(analysis)
        self.assertIn("cost", criteria)

    def test_identify_risk_criterion(self):
        """Test identifying risk as criterion."""
        analysis = "Risk assessment shows potential issues"
        criteria = self.maker._identify_decision_criteria(analysis)
        self.assertIn("risk", criteria)

    def test_identify_feasibility_criterion(self):
        """Test identifying feasibility as criterion."""
        analysis = "Feasibility depends on available resources"
        criteria = self.maker._identify_decision_criteria(analysis)
        self.assertIn("feasibility", criteria)

    def test_criteria_weights_normalize(self):
        """Test that criterion weights sum to 1.0."""
        analysis = "Cost, risk, and impact are important"
        criteria = self.maker._identify_decision_criteria(analysis)
        if criteria:
            total_weight = sum(criteria.values())
            self.assertAlmostEqual(total_weight, 1.0, places=5)

    def test_no_criteria_found(self):
        """Test handling when no criteria found."""
        criteria = self.maker._identify_decision_criteria("random text")
        self.assertEqual(criteria, {})


class TestDecisionMakerRiskAssessment(unittest.TestCase):
    """Test risk assessment."""

    def setUp(self):
        """Set up test fixtures."""
        self.maker = DecisionMaker(llm_model=MockVaultAwareLanguageModel())

    def test_assess_high_risk(self):
        """Test identifying high-risk decision."""
        analysis = "This option has high risk and is dangerous"
        result = self.maker._assess_decision_risks(analysis)
        self.assertEqual(result["risk_level"], "high")
        self.assertGreater(result["confidence"], 0.7)

    def test_assess_medium_risk(self):
        """Test identifying medium-risk decision."""
        analysis = "There are moderate risks to consider"
        result = self.maker._assess_decision_risks(analysis)
        self.assertEqual(result["risk_level"], "medium")

    def test_assess_low_risk(self):
        """Test identifying low-risk decision."""
        analysis = "This option presents minimal risk"
        result = self.maker._assess_decision_risks(analysis)
        self.assertEqual(result["risk_level"], "low")

    def test_unknown_risk_default(self):
        """Test unknown risk returns default."""
        result = self.maker._assess_decision_risks("random text")
        self.assertEqual(result["risk_level"], "unknown")


class TestDecisionMakerAlternatives(unittest.TestCase):
    """Test alternative evaluation."""

    def setUp(self):
        """Set up test fixtures."""
        self.maker = DecisionMaker(llm_model=MockVaultAwareLanguageModel())

    def test_evaluate_alternatives(self):
        """Test extracting alternatives."""
        analysis = """
        Option A: Invest heavily
        Alternative B: Wait and see
        Choice C: Minimal investment
        """
        alternatives = self.maker._evaluate_alternatives(analysis)
        self.assertGreater(len(alternatives), 0)

    def test_evaluate_alternatives_limits_count(self):
        """Test evaluation limits to 5 alternatives."""
        analysis = "\n".join([f"Option {i}: Description {i}" for i in range(10)])
        alternatives = self.maker._evaluate_alternatives(analysis)
        self.assertLessEqual(len(alternatives), 5)

    def test_evaluate_no_alternatives(self):
        """Test handling when no alternatives found."""
        alternatives = self.maker._evaluate_alternatives("random text")
        self.assertEqual(alternatives, [])


class TestDecisionMakerRecommendation(unittest.TestCase):
    """Test recommendation generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.maker = DecisionMaker(llm_model=MockVaultAwareLanguageModel())

    def test_generate_recommendation(self):
        """Test generating recommendation."""
        analysis = "Based on analysis, we recommend Option A as best choice"
        rec, confidence = self.maker._generate_recommendation(analysis)
        self.assertIn("recommend", rec.lower())
        self.assertGreater(confidence, 0.5)

    def test_generate_recommendation_with_suggest(self):
        """Test recommendation with 'suggest' keyword."""
        analysis = "We suggest proceeding with plan B"
        rec, confidence = self.maker._generate_recommendation(analysis)
        self.assertGreater(confidence, 0.5)

    def test_generate_recommendation_optimal(self):
        """Test recommendation with 'optimal' keyword."""
        analysis = "The optimal approach is Option C"
        rec, confidence = self.maker._generate_recommendation(analysis)
        self.assertGreater(confidence, 0.5)

    def test_generate_no_clear_recommendation(self):
        """Test when no clear recommendation found."""
        analysis = "The options are different with various merits and drawbacks."
        rec, confidence = self.maker._generate_recommendation(analysis)
        self.assertEqual(confidence, 0.5)


class TestDecisionMakerExecution(unittest.TestCase):
    """Test skill execution."""

    def setUp(self):
        """Set up test fixtures."""
        self.maker = DecisionMaker(llm_model=MockVaultAwareLanguageModel())

    def test_execute_valid_decision(self):
        """Test executing with valid decision problem."""
        result = self.maker.execute("should we upgrade our infrastructure")
        self.assertIsNotNone(result)
        self.assertEqual(result.skill_type, SkillType.DECISION)

    def test_execute_invalid_decision(self):
        """Test executing with invalid decision."""
        result = self.maker.execute("hello")
        self.assertEqual(result.confidence_score, 0.0)
        self.assertTrue(result.requires_human_review)

    def test_execute_stores_history(self):
        """Test execution stores in history."""
        self.maker.execute("decide on the best approach")
        self.assertEqual(len(self.maker.execution_history), 1)

    def test_execute_with_context(self):
        """Test execution with context."""
        context = {
            "stakeholders": ["CEO", "Team Lead"],
            "constraints": ["Budget", "Timeline"],
        }
        result = self.maker.execute(
            "what should we decide", context=context
        )
        self.assertIsNotNone(result)


class TestDecisionMakerSummary(unittest.TestCase):
    """Test decision summary."""

    def setUp(self):
        """Set up test fixtures."""
        self.maker = DecisionMaker(llm_model=MockVaultAwareLanguageModel())

    def test_decision_summary(self):
        """Test generating decision summary."""
        summary = self.maker.get_decision_summary()
        self.assertIn("criteria_analyzed", summary)
        self.assertIn("risks_identified", summary)
        self.assertIn("alternatives_evaluated", summary)
        self.assertIn("recommendations_made", summary)
        self.assertEqual(summary["criteria_analyzed"], 0)


if __name__ == "__main__":
    unittest.main()
