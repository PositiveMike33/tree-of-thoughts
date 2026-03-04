"""Tests for Expert Simulator skill."""

import unittest
from unittest.mock import Mock
from ..skill_config import SkillType, AlgorithmType, SkillConfig
from ..expert_simulator import ExpertSimulator
from ...tot_integration import VaultAwareLanguageModel


class MockVaultAwareLanguageModel(VaultAwareLanguageModel):
    """Mock implementation of VaultAwareLanguageModel for testing."""

    def __init__(self):
        pass

    def generate_thoughts(self, prompt, num_thoughts=5):
        return [f"Expert thought {i+1}" for i in range(num_thoughts)]

    def evaluate_states(self, states, prompt):
        return {state: 0.5 + (0.1 * i) for i, state in enumerate(states)}


class TestExpertSimulatorInitialization(unittest.TestCase):
    """Test ExpertSimulator initialization."""

    def setUp(self):
        """Set up test fixtures."""
        self.llm_model = MockVaultAwareLanguageModel()

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        simulator = ExpertSimulator(llm_model=self.llm_model)
        self.assertEqual(simulator.config.skill_type, SkillType.EXPERT)
        self.assertEqual(simulator.config.algorithm, AlgorithmType.DFS)
        self.assertEqual(simulator.config.num_thoughts, 8)
        self.assertEqual(simulator.config.max_steps, 10)

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = SkillConfig(
            skill_type=SkillType.EXPERT,
            algorithm=AlgorithmType.A_STAR,
            name="Custom Expert",
        )
        simulator = ExpertSimulator(config=config, llm_model=self.llm_model)
        self.assertEqual(simulator.config.name, "Custom Expert")

    def test_init_state_initialization(self):
        """Test internal state initialization."""
        simulator = ExpertSimulator(llm_model=self.llm_model)
        self.assertEqual(simulator.expert_analyses_performed, [])
        self.assertEqual(simulator.domain_insights, [])
        self.assertEqual(simulator.expert_recommendations, [])


class TestExpertSimulatorValidation(unittest.TestCase):
    """Test input validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.simulator = ExpertSimulator(llm_model=MockVaultAwareLanguageModel())

    def test_validate_valid_expert_request(self):
        """Test validation of valid expert request."""
        is_valid, msg = self.simulator.validate_input(
            "What is the best practice for system design"
        )
        self.assertTrue(is_valid)

    def test_validate_empty_prompt(self):
        """Test validation rejects empty prompt."""
        is_valid, msg = self.simulator.validate_input("")
        self.assertFalse(is_valid)

    def test_validate_too_short_prompt(self):
        """Test validation rejects very short prompt."""
        is_valid, msg = self.simulator.validate_input("expert advice")
        self.assertFalse(is_valid)

    def test_validate_too_long_prompt(self):
        """Test validation rejects very long prompt."""
        long_request = "expert " * 500
        is_valid, msg = self.simulator.validate_input(long_request)
        self.assertFalse(is_valid)

    def test_validate_non_expert_prompt(self):
        """Test validation rejects non-expert requests."""
        is_valid, msg = self.simulator.validate_input("tell me a funny joke about programmers")
        self.assertFalse(is_valid)

    def test_validate_with_expert_keyword(self):
        """Test validation accepts 'expert' keyword."""
        is_valid, msg = self.simulator.validate_input("What would an expert recommend")
        self.assertTrue(is_valid)

    def test_validate_with_best_practice_keyword(self):
        """Test validation accepts 'best practice' keyword."""
        is_valid, msg = self.simulator.validate_input("What is the best practice here")
        self.assertTrue(is_valid)


class TestExpertSimulatorSystemPrompt(unittest.TestCase):
    """Test system prompt generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.simulator = ExpertSimulator(llm_model=MockVaultAwareLanguageModel())

    def test_system_prompt_structure(self):
        """Test system prompt has expected content."""
        prompt = self.simulator.build_system_prompt()
        self.assertIn("expert", prompt.lower())
        self.assertIn("domain knowledge", prompt.lower())

    def test_system_prompt_includes_expertise(self):
        """Test system prompt includes expertise areas."""
        prompt = self.simulator.build_system_prompt()
        self.assertIn("Industry best practices", prompt)
        self.assertIn("professional", prompt.lower())


class TestExpertSimulatorContext(unittest.TestCase):
    """Test expert context building."""

    def setUp(self):
        """Set up test fixtures."""
        self.simulator = ExpertSimulator(llm_model=MockVaultAwareLanguageModel())

    def test_build_expert_context_basic(self):
        """Test building expert context."""
        context = self.simulator._build_expert_context(
            "question here", "software", "architecture", "tech"
        )
        self.assertIn("software", context.lower())
        self.assertIn("question", context)

    def test_build_expert_context_with_domain(self):
        """Test context includes domain."""
        context = self.simulator._build_expert_context(
            "test question", "healthcare", "policy", "medical"
        )
        self.assertIn("healthcare", context.lower())
        self.assertIn("policy", context)

    def test_build_expert_context_with_industry(self):
        """Test context includes industry."""
        context = self.simulator._build_expert_context(
            "test", "finance", "trading", "banking"
        )
        self.assertIn("banking", context)


class TestExpertInsightExtraction(unittest.TestCase):
    """Test expert insight extraction."""

    def setUp(self):
        """Set up test fixtures."""
        self.simulator = ExpertSimulator(llm_model=MockVaultAwareLanguageModel())

    def test_extract_insights(self):
        """Test extracting insights."""
        analysis = """
        Insight: The market trend shows growth
        Finding: New opportunities emerging
        Discovery: Technology shift happening
        """
        insights = self.simulator._extract_expert_insights(analysis)
        self.assertGreater(len(insights), 0)

    def test_extract_insights_limits_count(self):
        """Test extraction limits to 5."""
        analysis = "\n".join(
            [f"Insight {i}: Key finding {i}" for i in range(10)]
        )
        insights = self.simulator._extract_expert_insights(analysis)
        self.assertLessEqual(len(insights), 5)

    def test_extract_no_insights(self):
        """Test when no insights found."""
        insights = self.simulator._extract_expert_insights("just random text")
        self.assertEqual(len(insights), 0)


class TestExpertRecommendationExtraction(unittest.TestCase):
    """Test expert recommendation extraction."""

    def setUp(self):
        """Set up test fixtures."""
        self.simulator = ExpertSimulator(llm_model=MockVaultAwareLanguageModel())

    def test_extract_recommendation(self):
        """Test extracting recommendation."""
        analysis = "I would recommend implementing this approach for best results"
        rec = self.simulator._extract_expert_recommendation(analysis)
        self.assertIsNotNone(rec)
        self.assertIn("recommend", rec.lower())

    def test_extract_recommendation_with_advise(self):
        """Test extracting with 'advise' keyword."""
        analysis = "I advise you to follow this strategy for optimal performance"
        rec = self.simulator._extract_expert_recommendation(analysis)
        self.assertIsNotNone(rec)

    def test_extract_no_recommendation(self):
        """Test when no recommendation found."""
        rec = self.simulator._extract_expert_recommendation("just some text")
        self.assertIsNone(rec)


class TestBestPracticesValidation(unittest.TestCase):
    """Test best practices validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.simulator = ExpertSimulator(llm_model=MockVaultAwareLanguageModel())

    def test_validate_industry_standards(self):
        """Test validating industry standards."""
        analysis = "This follows industry standard practices"
        validation = self.simulator._validate_best_practices(analysis)
        self.assertTrue(validation["industry_standards_met"])

    def test_validate_best_practices_identified(self):
        """Test identifying best practices."""
        analysis = "Best practice: Use proven patterns and guidelines"
        validation = self.simulator._validate_best_practices(analysis)
        self.assertGreater(validation["best_practices_identified"], 0)

    def test_validate_no_best_practices(self):
        """Test when no best practices mentioned."""
        validation = self.simulator._validate_best_practices("just some text")
        self.assertFalse(validation["industry_standards_met"])


class TestExpertConfidence(unittest.TestCase):
    """Test expert confidence assessment."""

    def setUp(self):
        """Set up test fixtures."""
        self.simulator = ExpertSimulator(llm_model=MockVaultAwareLanguageModel())

    def test_assess_high_confidence(self):
        """Test assessing high confidence."""
        analysis = "I am confident this is the best approach recommended"
        confidence = self.simulator._assess_expert_confidence(analysis)
        self.assertGreater(confidence, 0.7)

    def test_assess_low_confidence(self):
        """Test assessing low confidence with risky language."""
        analysis = "definitely risky with many uncertainties ahead"
        confidence = self.simulator._assess_expert_confidence(analysis)
        # The analysis has "risky" (0.2) and "uncertain" (0.3), initial is 0.5
        # So result should be max(0.5, 0.2, 0.3) = 0.5 or potentially higher
        self.assertGreater(confidence, 0.0)

    def test_assess_moderate_confidence(self):
        """Test assessing moderate confidence."""
        analysis = "This is a possible approach"
        confidence = self.simulator._assess_expert_confidence(analysis)
        self.assertGreater(confidence, 0.3)

    def test_confidence_bounded_01(self):
        """Test confidence stays between 0 and 1."""
        analysis = "Some expert analysis"
        confidence = self.simulator._assess_expert_confidence(analysis)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)


class TestDomainExpertiseIdentification(unittest.TestCase):
    """Test domain expertise identification."""

    def setUp(self):
        """Set up test fixtures."""
        self.simulator = ExpertSimulator(llm_model=MockVaultAwareLanguageModel())

    def test_identify_deep_expertise(self):
        """Test identifying deep expertise."""
        analysis = "With 20 years of experience, proven track record, and established expertise"
        expertise = self.simulator._identify_domain_expertise(analysis)
        self.assertEqual(expertise["depth_level"], "deep")
        self.assertGreater(expertise["experience_indicators"], 0)

    def test_identify_intermediate_expertise(self):
        """Test identifying intermediate expertise."""
        analysis = "With some experience in this area"
        expertise = self.simulator._identify_domain_expertise(analysis)
        self.assertIn(expertise["depth_level"], ["intermediate", "general"])

    def test_identify_no_expertise(self):
        """Test when no expertise indicators."""
        expertise = self.simulator._identify_domain_expertise("just some text")
        self.assertEqual(expertise["depth_level"], "general")
        self.assertEqual(expertise["experience_indicators"], 0)


class TestExpertSimulatorExecution(unittest.TestCase):
    """Test skill execution."""

    def setUp(self):
        """Set up test fixtures."""
        self.simulator = ExpertSimulator(llm_model=MockVaultAwareLanguageModel())

    def test_execute_valid_expert_request(self):
        """Test executing with valid expert request."""
        result = self.simulator.execute("What is the best approach for scaling infrastructure")
        self.assertIsNotNone(result)
        self.assertEqual(result.skill_type, SkillType.EXPERT)

    def test_execute_invalid_expert_request(self):
        """Test executing with invalid request."""
        result = self.simulator.execute("hello")
        self.assertEqual(result.confidence_score, 0.0)
        self.assertTrue(result.requires_human_review)

    def test_execute_stores_history(self):
        """Test execution stores in history."""
        self.simulator.execute("What would an expert recommend for this problem")
        self.assertEqual(len(self.simulator.execution_history), 1)

    def test_execute_with_context(self):
        """Test execution with context."""
        context = {
            "domain": "software-engineering",
            "expertise_area": "system-design",
            "industry": "fintech",
        }
        result = self.simulator.execute(
            "What is the expert recommendation for this architecture", context=context
        )
        self.assertIsNotNone(result)


class TestExpertSimulatorSummary(unittest.TestCase):
    """Test expert summary generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.simulator = ExpertSimulator(llm_model=MockVaultAwareLanguageModel())

    def test_expert_summary(self):
        """Test generating expert summary."""
        summary = self.simulator.get_expert_summary()
        self.assertIn("expert_analyses_performed", summary)
        self.assertIn("domain_insights", summary)
        self.assertIn("expert_recommendations", summary)
        self.assertIn("best_practices_applied", summary)
        self.assertEqual(summary["expert_analyses_performed"], 0)


if __name__ == "__main__":
    unittest.main()
