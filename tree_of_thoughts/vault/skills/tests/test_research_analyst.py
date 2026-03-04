"""Tests for Research Analyst skill."""

import unittest
from unittest.mock import Mock, patch
from ..skill_config import SkillType, AlgorithmType, SkillConfig
from ..research_analyst import ResearchAnalyst
from ...tot_integration import VaultAwareLanguageModel


class MockVaultAwareLanguageModel(VaultAwareLanguageModel):
    """Mock implementation of VaultAwareLanguageModel for testing."""

    def __init__(self):
        pass

    def generate_thoughts(self, prompt, num_thoughts=5):
        return [f"Research thought {i+1}" for i in range(num_thoughts)]

    def evaluate_states(self, states, prompt):
        return {state: 0.5 + (0.1 * i) for i, state in enumerate(states)}


class TestResearchAnalystInitialization(unittest.TestCase):
    """Test ResearchAnalyst initialization."""

    def setUp(self):
        """Set up test fixtures."""
        self.llm_model = MockVaultAwareLanguageModel()

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        analyst = ResearchAnalyst(llm_model=self.llm_model)
        self.assertEqual(analyst.config.skill_type, SkillType.RESEARCH)
        self.assertEqual(analyst.config.algorithm, AlgorithmType.A_STAR)
        self.assertEqual(analyst.config.num_thoughts, 8)
        self.assertEqual(analyst.config.max_steps, 7)

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = SkillConfig(
            skill_type=SkillType.RESEARCH,
            algorithm=AlgorithmType.BFS,
            name="Custom Research",
            num_thoughts=5,
        )
        analyst = ResearchAnalyst(config=config, llm_model=self.llm_model)
        self.assertEqual(analyst.config.name, "Custom Research")
        self.assertEqual(analyst.config.algorithm, AlgorithmType.BFS)

    def test_init_state_initialization(self):
        """Test that internal state is properly initialized."""
        analyst = ResearchAnalyst(llm_model=self.llm_model)
        self.assertEqual(analyst.sources_consulted, [])
        self.assertEqual(analyst.key_findings, [])
        self.assertEqual(analyst.contradictions_found, [])

    def test_init_with_vault(self):
        """Test initialization with vault."""
        vault = Mock()
        analyst = ResearchAnalyst(llm_model=self.llm_model, vault=vault)
        self.assertIsNotNone(analyst.vault)


class TestResearchAnalystValidation(unittest.TestCase):
    """Test input validation for Research Analyst."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyst = ResearchAnalyst(llm_model=MockVaultAwareLanguageModel())

    def test_validate_valid_research_prompt(self):
        """Test validation of valid research prompt."""
        is_valid, msg = self.analyst.validate_input(
            "research the impact of climate change on agriculture"
        )
        self.assertTrue(is_valid)
        self.assertEqual(msg, "")

    def test_validate_empty_prompt(self):
        """Test validation rejects empty prompt."""
        is_valid, msg = self.analyst.validate_input("")
        self.assertFalse(is_valid)
        self.assertIn("non-empty", msg)

    def test_validate_too_short_prompt(self):
        """Test validation rejects very short prompt."""
        is_valid, msg = self.analyst.validate_input("research")
        self.assertFalse(is_valid)
        self.assertIn("least 10 characters", msg)

    def test_validate_too_long_prompt(self):
        """Test validation rejects very long prompt."""
        long_prompt = "research " * 300  # Very long
        is_valid, msg = self.analyst.validate_input(long_prompt)
        self.assertFalse(is_valid)
        self.assertIn("exceeds maximum", msg)

    def test_validate_non_research_prompt(self):
        """Test validation rejects non-research prompts."""
        is_valid, msg = self.analyst.validate_input("write a poem about cats")
        self.assertFalse(is_valid)
        self.assertIn("research-oriented", msg)

    def test_validate_with_research_keyword_analyze(self):
        """Test validation accepts 'analyze' keyword."""
        is_valid, msg = self.analyst.validate_input("analyze the economic trends")
        self.assertTrue(is_valid)

    def test_validate_with_research_keyword_investigate(self):
        """Test validation accepts 'investigate' keyword."""
        is_valid, msg = self.analyst.validate_input("investigate climate patterns")
        self.assertTrue(is_valid)

    def test_validate_with_research_keyword_study(self):
        """Test validation accepts 'study' keyword."""
        is_valid, msg = self.analyst.validate_input("study the effects of sleep")
        self.assertTrue(is_valid)

    def test_validate_none_input(self):
        """Test validation rejects None input."""
        is_valid, msg = self.analyst.validate_input(None)
        self.assertFalse(is_valid)


class TestResearchAnalystSystemPrompt(unittest.TestCase):
    """Test system prompt generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyst = ResearchAnalyst(llm_model=MockVaultAwareLanguageModel())

    def test_system_prompt_structure(self):
        """Test system prompt has expected structure."""
        prompt = self.analyst.build_system_prompt()
        self.assertIn("Research Analyst", prompt)
        self.assertIn("comprehensive analysis", prompt)

    def test_system_prompt_includes_responsibilities(self):
        """Test system prompt includes key responsibilities."""
        prompt = self.analyst.build_system_prompt()
        self.assertIn("research", prompt.lower())
        self.assertIn("sources", prompt.lower())
        self.assertIn("confidence", prompt.lower())

    def test_system_prompt_includes_approach(self):
        """Test system prompt includes methodology."""
        prompt = self.analyst.build_system_prompt()
        self.assertIn("multiple", prompt.lower())
        self.assertIn("source", prompt.lower())


class TestResearchAnalystContext(unittest.TestCase):
    """Test research context building."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyst = ResearchAnalyst(llm_model=MockVaultAwareLanguageModel())

    def test_build_research_context_basic(self):
        """Test building research context."""
        context = self.analyst._build_research_context(
            "analyze climate change", "environmental science", []
        )
        self.assertIn("climate change", context)
        self.assertIn("environmental science", context)

    def test_build_research_context_with_sources(self):
        """Test research context includes sources."""
        sources = ["Source A", "Source B", "Source C"]
        context = self.analyst._build_research_context(
            "analyze climate change", "environmental science", sources
        )
        self.assertIn("Suggested Sources", context)
        self.assertIn("Source A", context)

    def test_build_research_context_limits_sources(self):
        """Test context limits number of sources."""
        sources = [f"Source {i}" for i in range(10)]
        context = self.analyst._build_research_context(
            "test", "test domain", sources
        )
        # Should have max 5 sources
        source_count = context.count("- Source")
        self.assertLessEqual(source_count, 5)


class TestResearchAnalystFindingExtraction(unittest.TestCase):
    """Test key finding extraction."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyst = ResearchAnalyst(llm_model=MockVaultAwareLanguageModel())

    def test_extract_findings_with_markers(self):
        """Test extracting findings with markers."""
        output = """
        Finding: Climate change is accelerating
        Result: Impact on agriculture is significant
        Key insight: Adaptation strategies are crucial
        - Water management is essential
        """
        findings = self.analyst._extract_key_findings(output)
        self.assertGreater(len(findings), 0)
        self.assertIn("climate change", findings[0].lower())

    def test_extract_findings_empty_output(self):
        """Test extracting from empty output."""
        findings = self.analyst._extract_key_findings("")
        self.assertEqual(findings, [])

    def test_extract_findings_no_markers(self):
        """Test extracting from output without markers."""
        output = "Just some text without finding markers"
        findings = self.analyst._extract_key_findings(output)
        self.assertEqual(findings, [])

    def test_extract_findings_limits_count(self):
        """Test that extraction limits to top 5 findings."""
        output = "\n".join([f"Finding: Finding {i}" for i in range(10)])
        findings = self.analyst._extract_key_findings(output)
        self.assertLessEqual(len(findings), 5)


class TestResearchAnalystValidationLogic(unittest.TestCase):
    """Test research findings validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyst = ResearchAnalyst(llm_model=MockVaultAwareLanguageModel())

    def test_validate_findings_with_citations(self):
        """Test validation with citations."""
        findings = "Climate change is real [source: IPCC 2021] and worsening."
        result = self.analyst._validate_research_findings(findings)
        self.assertGreater(result["confidence"], 0.5)

    def test_validate_findings_without_citations(self):
        """Test validation without citations."""
        findings = "Climate change is real and worsening."
        result = self.analyst._validate_research_findings(findings)
        self.assertTrue(any("citation" in i.lower() for i in result["issues"]))

    def test_validate_findings_with_contradictions(self):
        """Test validation detects contradictions."""
        findings = "Some studies show X. However, other research contradicts this finding."
        result = self.analyst._validate_research_findings(findings)
        self.assertTrue(result["has_contradictions"])

    def test_validate_findings_no_contradictions(self):
        """Test validation without contradictions."""
        findings = "Research clearly shows consistent results across studies."
        result = self.analyst._validate_research_findings(findings)
        self.assertFalse(result["has_contradictions"])

    def test_validate_findings_perspective_count(self):
        """Test perspective counting."""
        findings = "Research shows X. Studies indicate Y. Experts argue Z."
        result = self.analyst._validate_research_findings(findings)
        self.assertGreaterEqual(result["perspective_count"], 2)

    def test_validate_findings_low_perspective(self):
        """Test validation penalizes low perspectives."""
        findings = "Studies show one finding only."
        result = self.analyst._validate_research_findings(findings)
        self.assertTrue(any("perspective" in i.lower() for i in result["issues"]))

    def test_validate_findings_confidence_bounds(self):
        """Test confidence stays within bounds."""
        findings = "Some finding with no citations."
        result = self.analyst._validate_research_findings(findings)
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)


class TestResearchAnalystSummary(unittest.TestCase):
    """Test research summary generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyst = ResearchAnalyst(llm_model=MockVaultAwareLanguageModel())

    def test_research_summary_empty(self):
        """Test summary with no research conducted."""
        summary = self.analyst.get_research_summary()
        self.assertEqual(summary["sources_consulted"], 0)
        self.assertEqual(summary["key_findings_count"], 0)
        self.assertEqual(summary["contradictions_found"], 0)

    def test_research_summary_includes_required_fields(self):
        """Test summary includes all required fields."""
        summary = self.analyst.get_research_summary()
        self.assertIn("sources_consulted", summary)
        self.assertIn("key_findings_count", summary)
        self.assertIn("contradictions_found", summary)
        self.assertIn("execution_history", summary)


class TestResearchAnalystExecution(unittest.TestCase):
    """Test Research Analyst skill execution."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyst = ResearchAnalyst(llm_model=MockVaultAwareLanguageModel())

    def test_execute_valid_prompt(self):
        """Test executing with valid prompt."""
        result = self.analyst.execute("research the history of machine learning")
        self.assertIsNotNone(result)
        self.assertEqual(result.skill_name, "Research Analyst")
        self.assertEqual(result.skill_type, SkillType.RESEARCH)

    def test_execute_invalid_prompt(self):
        """Test executing with invalid prompt."""
        result = self.analyst.execute("invalid")
        self.assertEqual(result.confidence_score, 0.0)
        self.assertTrue(result.requires_human_review)

    def test_execute_stores_history(self):
        """Test execution stores in history."""
        self.analyst.execute("research climate change effects")
        self.assertEqual(len(self.analyst.execution_history), 1)

    def test_execute_with_context(self):
        """Test execution with context."""
        context = {
            "domain": "environmental science",
            "sources": ["EPA", "IPCC"],
        }
        result = self.analyst.execute(
            "research climate change", context=context
        )
        self.assertIsNotNone(result)

    def test_execute_updates_current_result(self):
        """Test execution updates current result."""
        self.assertIsNone(self.analyst.current_result)
        self.analyst.execute("research artificial intelligence")
        self.assertIsNotNone(self.analyst.current_result)


if __name__ == "__main__":
    unittest.main()
