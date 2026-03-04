"""Tests for Code Reviewer skill."""

import unittest
from unittest.mock import Mock
from ..skill_config import SkillType, AlgorithmType, SkillConfig
from ..code_reviewer import CodeReviewer
from ...tot_integration import VaultAwareLanguageModel


class MockVaultAwareLanguageModel(VaultAwareLanguageModel):
    """Mock implementation of VaultAwareLanguageModel for testing."""

    def __init__(self):
        pass

    def generate_thoughts(self, prompt, num_thoughts=5):
        return [f"Review thought {i+1}" for i in range(num_thoughts)]

    def evaluate_states(self, states, prompt):
        return {state: 0.5 + (0.1 * i) for i, state in enumerate(states)}


class TestCodeReviewerInitialization(unittest.TestCase):
    """Test CodeReviewer initialization."""

    def setUp(self):
        """Set up test fixtures."""
        self.llm_model = MockVaultAwareLanguageModel()

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        reviewer = CodeReviewer(llm_model=self.llm_model)
        self.assertEqual(reviewer.config.skill_type, SkillType.CODE_REVIEW)
        self.assertEqual(reviewer.config.algorithm, AlgorithmType.BFS)
        self.assertEqual(reviewer.config.num_thoughts, 5)
        self.assertEqual(reviewer.config.max_steps, 6)

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = SkillConfig(
            skill_type=SkillType.CODE_REVIEW,
            algorithm=AlgorithmType.DFS,
            name="Custom Code Reviewer",
        )
        reviewer = CodeReviewer(config=config, llm_model=self.llm_model)
        self.assertEqual(reviewer.config.name, "Custom Code Reviewer")

    def test_init_state_initialization(self):
        """Test internal state initialization."""
        reviewer = CodeReviewer(llm_model=self.llm_model)
        self.assertEqual(reviewer.issues_found, [])
        self.assertEqual(reviewer.recommendations, [])
        self.assertEqual(reviewer.security_issues, [])


class TestCodeReviewerValidation(unittest.TestCase):
    """Test input validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.reviewer = CodeReviewer(llm_model=MockVaultAwareLanguageModel())

    def test_validate_valid_code(self):
        """Test validation of valid code review request."""
        is_valid, msg = self.reviewer.validate_input(
            "review this code: def function(): pass"
        )
        self.assertTrue(is_valid)

    def test_validate_empty_prompt(self):
        """Test validation rejects empty prompt."""
        is_valid, msg = self.reviewer.validate_input("")
        self.assertFalse(is_valid)

    def test_validate_too_short_prompt(self):
        """Test validation rejects very short prompt."""
        is_valid, msg = self.reviewer.validate_input("code review")
        self.assertFalse(is_valid)

    def test_validate_too_long_prompt(self):
        """Test validation rejects very long prompt."""
        long_code = "code " * 1500
        is_valid, msg = self.reviewer.validate_input(long_code)
        self.assertFalse(is_valid)

    def test_validate_non_code_prompt(self):
        """Test validation rejects non-code prompts."""
        is_valid, msg = self.reviewer.validate_input("tell me a funny story about dogs")
        self.assertFalse(is_valid)

    def test_validate_with_code_keyword(self):
        """Test validation accepts 'code' keyword."""
        is_valid, msg = self.reviewer.validate_input("review my code implementation")
        self.assertTrue(is_valid)

    def test_validate_with_function_keyword(self):
        """Test validation accepts 'function' keyword."""
        is_valid, msg = self.reviewer.validate_input("review this function logic")
        self.assertTrue(is_valid)

    def test_validate_with_performance_keyword(self):
        """Test validation accepts 'performance' keyword."""
        is_valid, msg = self.reviewer.validate_input("improve performance efficiency")
        self.assertTrue(is_valid)


class TestCodeReviewerSystemPrompt(unittest.TestCase):
    """Test system prompt generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.reviewer = CodeReviewer(llm_model=MockVaultAwareLanguageModel())

    def test_system_prompt_structure(self):
        """Test system prompt has expected content."""
        prompt = self.reviewer.build_system_prompt()
        self.assertIn("Code Reviewer", prompt)
        self.assertIn("expert", prompt.lower())

    def test_system_prompt_includes_categories(self):
        """Test system prompt includes review categories."""
        prompt = self.reviewer.build_system_prompt()
        self.assertIn("Functionality", prompt)
        self.assertIn("Security", prompt)
        self.assertIn("Performance", prompt)


class TestCodeReviewerContext(unittest.TestCase):
    """Test code review context building."""

    def setUp(self):
        """Set up test fixtures."""
        self.reviewer = CodeReviewer(llm_model=MockVaultAwareLanguageModel())

    def test_build_review_context_basic(self):
        """Test building review context."""
        code = "def hello(): print('world')"
        context = self.reviewer._build_review_context(code, "python", [], [])
        self.assertIn("python", context.lower())
        self.assertIn("hello", context)

    def test_build_review_context_with_frameworks(self):
        """Test context includes frameworks."""
        frameworks = ["Django", "Flask"]
        code = "code here"
        context = self.reviewer._build_review_context(code, "python", frameworks, [])
        self.assertIn("Frameworks", context)
        self.assertIn("Django", context)

    def test_build_review_context_with_standards(self):
        """Test context includes standards."""
        standards = ["PEP8", "SOLID"]
        code = "code here"
        context = self.reviewer._build_review_context(code, "python", [], standards)
        self.assertIn("Standards", context)
        self.assertIn("PEP8", context)


class TestCodeComplexityAssessment(unittest.TestCase):
    """Test code complexity analysis."""

    def setUp(self):
        """Set up test fixtures."""
        self.reviewer = CodeReviewer(llm_model=MockVaultAwareLanguageModel())

    def test_assess_low_complexity_code(self):
        """Test assessing low complexity code."""
        code = "x = 1\ny = 2\nz = x + y"
        assessment = self.reviewer._assess_code_complexity(code)
        self.assertEqual(assessment["complexity_level"], "low")
        self.assertLessEqual(assessment["nesting_depth"], 1)

    def test_assess_medium_complexity_code(self):
        """Test assessing medium complexity code."""
        code = """
def function():
    if True:
        for i in range(10):
            print(i)
"""
        assessment = self.reviewer._assess_code_complexity(code)
        self.assertIn(assessment["complexity_level"], ["low", "medium"])

    def test_assess_high_complexity_code(self):
        """Test assessing high complexity code."""
        code = """
def function():
    if True:
        if True:
            if True:
                if True:
                    if True:
                        print('deep')
"""
        assessment = self.reviewer._assess_code_complexity(code)
        self.assertIn(assessment["complexity_level"], ["high", "very_high"])

    def test_function_count(self):
        """Test counting functions in code."""
        code = """
def func1():
    pass
def func2():
    pass
class MyClass:
    pass
"""
        assessment = self.reviewer._assess_code_complexity(code)
        self.assertGreater(assessment["function_count"], 0)


class TestSecurityDetection(unittest.TestCase):
    """Test security issue detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.reviewer = CodeReviewer(llm_model=MockVaultAwareLanguageModel())

    def test_detect_hardcoded_secrets(self):
        """Test detecting hardcoded secrets."""
        code = "api_key = 'sk-1234567890'"
        issues = self.reviewer._detect_security_issues(code)
        self.assertTrue(any("secret" in issue for issue in issues))

    def test_detect_sql_injection_risk(self):
        """Test detecting SQL injection patterns."""
        code = "execute(query + user_input)"
        issues = self.reviewer._detect_security_issues(code)
        self.assertTrue(len(issues) > 0)

    def test_detect_xss_vulnerability(self):
        """Test detecting XSS vulnerabilities."""
        code = "element.innerHTML = user_data"
        issues = self.reviewer._detect_security_issues(code)
        self.assertTrue(len(issues) > 0)

    def test_no_security_issues(self):
        """Test code with no security issues."""
        code = "x = 1 + 2\nresult = x * 3"
        issues = self.reviewer._detect_security_issues(code)
        self.assertEqual(len(issues), 0)


class TestIssueExtraction(unittest.TestCase):
    """Test issue extraction from reviews."""

    def setUp(self):
        """Set up test fixtures."""
        self.reviewer = CodeReviewer(llm_model=MockVaultAwareLanguageModel())

    def test_extract_critical_issues(self):
        """Test extracting critical issues."""
        review = "CRITICAL: Security vulnerability detected in line 42"
        issues = self.reviewer._extract_issues(review)
        self.assertTrue(any(i["severity"] == "critical" for i in issues))

    def test_extract_major_issues(self):
        """Test extracting major issues."""
        review = "MAJOR: Bug found in error handling"
        issues = self.reviewer._extract_issues(review)
        self.assertTrue(any(i["severity"] == "major" for i in issues))

    def test_extract_minor_issues(self):
        """Test extracting minor issues."""
        review = "Minor: Style issue with naming convention"
        issues = self.reviewer._extract_issues(review)
        self.assertTrue(any(i["severity"] == "minor" for i in issues))

    def test_extract_issues_limits_count(self):
        """Test that issue extraction limits to 20."""
        review = "\n".join([f"Issue {i}: critical problem" for i in range(50)])
        issues = self.reviewer._extract_issues(review)
        self.assertLessEqual(len(issues), 20)

    def test_extract_no_issues(self):
        """Test extracting from review with no issues."""
        review = "Code looks good, no issues found"
        issues = self.reviewer._extract_issues(review)
        self.assertEqual(len(issues), 0)


class TestCodeReviewerExecution(unittest.TestCase):
    """Test skill execution."""

    def setUp(self):
        """Set up test fixtures."""
        self.reviewer = CodeReviewer(llm_model=MockVaultAwareLanguageModel())

    def test_execute_valid_code(self):
        """Test executing with valid code."""
        code = "review this function implementation carefully"
        result = self.reviewer.execute(code)
        self.assertIsNotNone(result)
        self.assertEqual(result.skill_type, SkillType.CODE_REVIEW)

    def test_execute_invalid_code(self):
        """Test executing with invalid request."""
        result = self.reviewer.execute("hello")
        self.assertEqual(result.confidence_score, 0.0)
        self.assertTrue(result.requires_human_review)

    def test_execute_stores_history(self):
        """Test execution stores in history."""
        self.reviewer.execute("review this code implementation now")
        self.assertEqual(len(self.reviewer.execution_history), 1)

    def test_execute_with_context(self):
        """Test execution with context."""
        context = {
            "language": "python",
            "frameworks": ["Django"],
            "standards": ["PEP8"],
        }
        result = self.reviewer.execute(
            "review this code implementation", context=context
        )
        self.assertIsNotNone(result)


class TestCodeReviewerSummary(unittest.TestCase):
    """Test review summary generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.reviewer = CodeReviewer(llm_model=MockVaultAwareLanguageModel())

    def test_review_summary_empty(self):
        """Test summary with no reviews."""
        summary = self.reviewer.get_review_summary()
        self.assertEqual(summary["total_issues"], 0)
        self.assertEqual(summary["critical_issues"], 0)
        self.assertEqual(summary["security_concerns"], 0)

    def test_review_summary_includes_fields(self):
        """Test summary includes all fields."""
        summary = self.reviewer.get_review_summary()
        self.assertIn("total_issues", summary)
        self.assertIn("critical_issues", summary)
        self.assertIn("major_issues", summary)
        self.assertIn("minor_issues", summary)
        self.assertIn("security_concerns", summary)


if __name__ == "__main__":
    unittest.main()
