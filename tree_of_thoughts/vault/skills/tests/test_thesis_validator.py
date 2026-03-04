"""Tests for Thesis Validator skill."""

import unittest
from unittest.mock import Mock
from ..skill_config import SkillType, AlgorithmType, SkillConfig
from ..thesis_validator import ThesisValidator
from ...tot_integration import VaultAwareLanguageModel


class MockVaultAwareLanguageModel(VaultAwareLanguageModel):
    """Mock implementation of VaultAwareLanguageModel for testing."""

    def __init__(self):
        pass

    def generate_thoughts(self, prompt, num_thoughts=5):
        return [f"Validation thought {i+1}" for i in range(num_thoughts)]

    def evaluate_states(self, states, prompt):
        return {state: 0.5 + (0.1 * i) for i, state in enumerate(states)}


class TestThesisValidatorInitialization(unittest.TestCase):
    """Test ThesisValidator initialization."""

    def setUp(self):
        """Set up test fixtures."""
        self.llm_model = MockVaultAwareLanguageModel()

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        validator = ThesisValidator(llm_model=self.llm_model)
        self.assertEqual(validator.config.skill_type, SkillType.THESIS)
        self.assertEqual(validator.config.algorithm, AlgorithmType.MCTS)
        self.assertEqual(validator.config.num_thoughts, 7)
        self.assertEqual(validator.config.max_steps, 8)

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = SkillConfig(
            skill_type=SkillType.THESIS,
            algorithm=AlgorithmType.A_STAR,
            name="Custom Thesis Validator",
        )
        validator = ThesisValidator(config=config, llm_model=self.llm_model)
        self.assertEqual(validator.config.name, "Custom Thesis Validator")

    def test_init_state_initialization(self):
        """Test internal state initialization."""
        validator = ThesisValidator(llm_model=self.llm_model)
        self.assertEqual(validator.theses_analyzed, [])
        self.assertEqual(validator.fallacies_detected, [])
        self.assertEqual(validator.counter_arguments, [])


class TestThesisValidatorValidation(unittest.TestCase):
    """Test input validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ThesisValidator(llm_model=MockVaultAwareLanguageModel())

    def test_validate_valid_thesis(self):
        """Test validation of valid thesis."""
        is_valid, msg = self.validator.validate_input(
            "Thesis: The internet has fundamentally changed society"
        )
        self.assertTrue(is_valid)

    def test_validate_empty_prompt(self):
        """Test validation rejects empty prompt."""
        is_valid, msg = self.validator.validate_input("")
        self.assertFalse(is_valid)

    def test_validate_too_short_prompt(self):
        """Test validation rejects very short prompt."""
        is_valid, msg = self.validator.validate_input("short thesis")
        self.assertFalse(is_valid)

    def test_validate_too_long_prompt(self):
        """Test validation rejects very long prompt."""
        long_thesis = "thesis " * 1000
        is_valid, msg = self.validator.validate_input(long_thesis)
        self.assertFalse(is_valid)

    def test_validate_non_thesis_prompt(self):
        """Test validation rejects non-thesis content."""
        is_valid, msg = self.validator.validate_input("tell me a story about dragons")
        self.assertFalse(is_valid)

    def test_validate_with_claim_keyword(self):
        """Test validation accepts 'claim' keyword."""
        is_valid, msg = self.validator.validate_input("I claim that education is essential")
        self.assertTrue(is_valid)

    def test_validate_with_argument_keyword(self):
        """Test validation accepts 'argument' keyword."""
        is_valid, msg = self.validator.validate_input("My argument is that climate change is real")
        self.assertTrue(is_valid)

    def test_validate_with_demonstrate_keyword(self):
        """Test validation accepts 'demonstrate' keyword."""
        is_valid, msg = self.validator.validate_input("I will demonstrate that this is true")
        self.assertTrue(is_valid)


class TestThesisValidatorSystemPrompt(unittest.TestCase):
    """Test system prompt generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ThesisValidator(llm_model=MockVaultAwareLanguageModel())

    def test_system_prompt_includes_structure(self):
        """Test system prompt includes analysis structure."""
        prompt = self.validator.build_system_prompt()
        self.assertIn("Thesis Validator", prompt)
        self.assertIn("argument", prompt.lower())

    def test_system_prompt_includes_fallacies(self):
        """Test system prompt includes fallacy detection."""
        prompt = self.validator.build_system_prompt()
        self.assertIn("fallacy", prompt.lower())
        self.assertIn("ad hominem", prompt.lower())


class TestThesisValidatorContext(unittest.TestCase):
    """Test thesis validation context building."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ThesisValidator(llm_model=MockVaultAwareLanguageModel())

    def test_build_validation_context_basic(self):
        """Test building validation context."""
        thesis = "Technology improves society"
        context = self.validator._build_validation_context(
            thesis, "technology", "academic"
        )
        self.assertIn("technology", context.lower())
        self.assertIn("improves", context)

    def test_build_validation_context_with_subject(self):
        """Test context includes subject area."""
        context = self.validator._build_validation_context(
            "test thesis", "philosophy", "general"
        )
        self.assertIn("philosophy", context)


class TestFallacyDetection(unittest.TestCase):
    """Test logical fallacy detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ThesisValidator(llm_model=MockVaultAwareLanguageModel())

    def test_detect_ad_hominem(self):
        """Test detecting ad hominem fallacy."""
        analysis = "This argument attacks the person rather than the idea"
        fallacies = self.validator._detect_fallacies(analysis)
        self.assertTrue(any("ad_hominem" in f for f in fallacies))

    def test_detect_straw_man(self):
        """Test detecting straw man fallacy."""
        analysis = "The argument misrepresents the original position"
        fallacies = self.validator._detect_fallacies(analysis)
        self.assertTrue(any("straw_man" in f for f in fallacies))

    def test_detect_false_dilemma(self):
        """Test detecting false dilemma fallacy."""
        analysis = "This presents either or choices when more options exist"
        fallacies = self.validator._detect_fallacies(analysis)
        self.assertTrue(any("false_dilemma" in f for f in fallacies))

    def test_detect_begging_question(self):
        """Test detecting begging the question fallacy."""
        analysis = "The argument assumes the conclusion in its premises"
        fallacies = self.validator._detect_fallacies(analysis)
        self.assertTrue(any("begging_question" in f for f in fallacies))

    def test_no_fallacies_found(self):
        """Test when no fallacies are found."""
        analysis = "This argument is well-reasoned and logically sound"
        fallacies = self.validator._detect_fallacies(analysis)
        self.assertEqual(len(fallacies), 0)


class TestArgumentStrengthAssessment(unittest.TestCase):
    """Test argument strength evaluation."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ThesisValidator(llm_model=MockVaultAwareLanguageModel())

    def test_assess_strong_argument(self):
        """Test assessing strong argument."""
        analysis = "This is a strong argument with clear evidence and logical flow"
        strength = self.validator._assess_argument_strength(analysis)
        self.assertGreater(strength, 0.6)

    def test_assess_weak_argument(self):
        """Test assessing weak argument."""
        analysis = "This weak argument lacks support and has logical flaws"
        strength = self.validator._assess_argument_strength(analysis)
        self.assertLess(strength, 0.5)

    def test_assess_balanced_argument(self):
        """Test assessing balanced argument."""
        analysis = "This argument has some strengths and some weaknesses"
        strength = self.validator._assess_argument_strength(analysis)
        self.assertGreater(strength, 0.3)
        self.assertLess(strength, 0.7)

    def test_strength_bounded_01(self):
        """Test that strength stays between 0 and 1."""
        analysis = "Some argument text"
        strength = self.validator._assess_argument_strength(analysis)
        self.assertGreaterEqual(strength, 0.0)
        self.assertLessEqual(strength, 1.0)


class TestCounterArgumentExtraction(unittest.TestCase):
    """Test counter-argument extraction."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ThesisValidator(llm_model=MockVaultAwareLanguageModel())

    def test_extract_counter_arguments(self):
        """Test extracting counter-arguments."""
        analysis = """
        Main argument: Technology is beneficial
        Counter-argument: Some believe technology causes harm
        Objection: Technology dependency is growing
        """
        arguments = self.validator._extract_counter_arguments(analysis)
        self.assertGreater(len(arguments), 0)

    def test_extract_counter_arguments_limits(self):
        """Test extraction limits to 5."""
        analysis = "\n".join(
            [f"Counter-argument {i}: Some point" for i in range(10)]
        )
        arguments = self.validator._extract_counter_arguments(analysis)
        self.assertLessEqual(len(arguments), 5)

    def test_no_counter_arguments(self):
        """Test when no counter-arguments found."""
        analysis = "Just a simple argument without counters"
        arguments = self.validator._extract_counter_arguments(analysis)
        self.assertEqual(len(arguments), 0)


class TestEvidenceQualityAssessment(unittest.TestCase):
    """Test evidence quality evaluation."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ThesisValidator(llm_model=MockVaultAwareLanguageModel())

    def test_assess_high_quality_evidence(self):
        """Test assessing high-quality evidence."""
        analysis = "Uses peer-reviewed academic sources and primary sources"
        assessment = self.validator._evaluate_evidence_quality(analysis)
        self.assertEqual(assessment["evidence_quality"], "high")

    def test_assess_medium_quality_evidence(self):
        """Test assessing medium-quality evidence."""
        analysis = "Uses secondary sources and reputable publications"
        assessment = self.validator._evaluate_evidence_quality(analysis)
        self.assertEqual(assessment["evidence_quality"], "medium")

    def test_assess_low_quality_evidence(self):
        """Test assessing low-quality evidence."""
        analysis = "Evidence is unreliable and weak"
        assessment = self.validator._evaluate_evidence_quality(analysis)
        self.assertEqual(assessment["evidence_quality"], "low")

    def test_credibility_score_bounds(self):
        """Test credibility score stays within bounds."""
        analysis = "Some evidence assessment"
        assessment = self.validator._evaluate_evidence_quality(analysis)
        self.assertGreaterEqual(assessment["source_credibility"], 0.0)
        self.assertLessEqual(assessment["source_credibility"], 1.0)


class TestThesisValidatorExecution(unittest.TestCase):
    """Test skill execution."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ThesisValidator(llm_model=MockVaultAwareLanguageModel())

    def test_execute_valid_thesis(self):
        """Test executing with valid thesis."""
        result = self.validator.execute(
            "Thesis: Online education should be widely adopted"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.skill_type, SkillType.THESIS)

    def test_execute_invalid_thesis(self):
        """Test executing with invalid thesis."""
        result = self.validator.execute("hello")
        self.assertEqual(result.confidence_score, 0.0)
        self.assertTrue(result.requires_human_review)

    def test_execute_stores_history(self):
        """Test execution stores in history."""
        self.validator.execute("Argument: The world is round")
        self.assertEqual(len(self.validator.execution_history), 1)

    def test_execute_with_context(self):
        """Test execution with context."""
        context = {
            "subject": "physics",
            "audience": "graduate",
        }
        result = self.validator.execute(
            "Thesis: Quantum mechanics requires interpretation",
            context=context
        )
        self.assertIsNotNone(result)


class TestThesisValidatorSummary(unittest.TestCase):
    """Test validation summary."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ThesisValidator(llm_model=MockVaultAwareLanguageModel())

    def test_validation_summary_empty(self):
        """Test summary with no validations."""
        summary = self.validator.get_validation_summary()
        self.assertEqual(summary["theses_analyzed"], 0)
        self.assertEqual(summary["fallacies_detected_total"], 0)

    def test_validation_summary_includes_fields(self):
        """Test summary includes all fields."""
        summary = self.validator.get_validation_summary()
        self.assertIn("theses_analyzed", summary)
        self.assertIn("fallacies_detected_total", summary)
        self.assertIn("arguments_evaluated", summary)
        self.assertIn("counter_arguments_identified", summary)


if __name__ == "__main__":
    unittest.main()
