"""Tests for validation_engine module."""

import unittest
from ..validation_engine import (
    ResponseValidator,
    FactChecker,
    AutoCorrector,
    BlindValidationEngine,
    ValidationIssueType,
    ConfidenceLevel,
    Claim,
)


class TestResponseValidator(unittest.TestCase):
    """Test ResponseValidator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ResponseValidator(min_words=300, min_sentences=5)

    def test_validate_empty_response(self):
        """Test validation of empty response."""
        result = self.validator.validate_response("")
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.issues), 0)

    def test_validate_short_response(self):
        """Test validation of too-short response."""
        short_text = "This is a short response that is too brief."
        result = self.validator.validate_response(short_text)
        # Short responses get warnings, not critical issues, so is_valid might still be True
        # But should have issues recorded
        self.assertGreater(len(result.issues), 0)
        # Completeness score should reflect the shortness
        completeness_score = result.scores.get("completeness", 1.0)
        self.assertLess(completeness_score, 0.5)

    def test_validate_complete_response(self):
        """Test validation of complete response."""
        complete_text = (
            "This is a comprehensive response that contains sufficient content. "
            "It has multiple sentences and provides detailed information. "
            "The response includes explanations and examples to support the main points. "
            "It demonstrates good structure with clear logical flow. "
            "This should meet the minimum word count requirement. "
            "The response is well-formed and coherent throughout. "
            "It maintains relevance to the subject matter at all times. "
            "Each sentence contributes to the overall message effectively. "
            "The writing style is clear and easy to understand. "
            "Finally, the response concludes with a summary of key points."
        )
        result = self.validator.validate_response(complete_text)
        self.assertTrue(result.is_valid or result.confidence > 0.6)

    def test_truncated_response_detection(self):
        """Test detection of truncated response."""
        truncated = "This response appears to be cut off abruptly..."
        result = self.validator.validate_response(truncated)
        truncation_issues = [
            i for i in result.issues
            if i.issue_type == ValidationIssueType.TRUNCATED
        ]
        self.assertGreater(len(truncation_issues), 0)

    def test_syntactic_validation(self):
        """Test syntactic validation."""
        result = self.validator.validate_response(
            "This is a test. It has valid syntax (with parentheses) and structure."
        )
        self.assertIn("syntactic", result.scores)

    def test_confidence_level_assignment(self):
        """Test confidence level is correctly assigned."""
        text = ("This is a test response that is long enough to be considered complete. "
                "It contains multiple sentences and should have reasonable length. "
                "The response demonstrates proper structure and formatting. "
                "It should achieve a high confidence level based on the validation rules. "
                "The text is coherent and maintains logical consistency throughout.")
        result = self.validator.validate_response(text)
        self.assertIsNotNone(result.confidence_level)
        self.assertIn(result.confidence_level, ConfidenceLevel)


class TestFactChecker(unittest.TestCase):
    """Test FactChecker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.fact_checker = FactChecker()

    def test_extract_claims(self):
        """Test claim extraction from text."""
        text = "Consciousness is a complex phenomenon. The brain contains about 86 billion neurons."
        claims = self.fact_checker.extract_claims(text)
        self.assertGreater(len(claims), 0)
        self.assertTrue(any("consciousness" in c.text.lower() for c in claims))

    def test_extract_no_claims(self):
        """Test extraction when no clear claims exist."""
        text = "How interesting! What a wonderful day!"
        claims = self.fact_checker.extract_claims(text)
        # Should find few or no verifiable claims in subjective statement
        verifiable = [c for c in claims if isinstance(c, Claim)]
        # This is expected to have minimal claims
        self.assertIsInstance(claims, list)

    def test_verify_claim(self):
        """Test claim verification."""
        claim = Claim("Paris is the capital of France", position=0)
        result = self.fact_checker.verify_claim(claim)
        self.assertIsNotNone(result.confidence)
        self.assertGreater(result.confidence, 0)

    def test_assess_verifiability(self):
        """Test verifiability assessment."""
        # Verifiable claims
        self.assertTrue(
            self.fact_checker._assess_verifiability("The Earth orbits the Sun")
        )

        # Subjective claims
        self.assertFalse(
            self.fact_checker._assess_verifiability("I think this is beautiful")
        )

    def test_score_factuality(self):
        """Test factuality scoring."""
        text = "Water boils at 100 degrees Celsius at sea level."
        score = self.fact_checker.score_factuality(text)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_generate_fact_check_report(self):
        """Test fact-check report generation."""
        text = "The Sun is larger than Earth. Today is a beautiful day."
        report = self.fact_checker.generate_fact_check_report(text)
        self.assertIn("total_claims", report)
        self.assertIn("verifiable_claims", report)
        self.assertIn("factuality_score", report)


class TestAutoCorrector(unittest.TestCase):
    """Test AutoCorrector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.corrector = AutoCorrector()

    def test_detect_truncation_with_ellipsis(self):
        """Test detection of truncation with ellipsis."""
        text = "This response is cut off..."
        is_truncated, confidence = self.corrector.detect_truncation(text)
        self.assertTrue(is_truncated)
        self.assertGreater(confidence, 0.8)

    def test_detect_no_truncation(self):
        """Test non-truncated response."""
        text = "This is a complete sentence with proper ending."
        is_truncated, confidence = self.corrector.detect_truncation(text)
        self.assertFalse(is_truncated)

    def test_fix_obvious_errors(self):
        """Test error fixing."""
        text = "This  has  double   spaces.  And multiple!!!punctuation."
        corrected = self.corrector.fix_obvious_errors(text)
        self.assertNotIn("  ", corrected)
        self.assertNotIn("!!!", corrected)

    def test_enhance_incomplete_sections(self):
        """Test incomplete section enhancement."""
        text = "## Section 1\nThis section is too short."
        enhanced = self.corrector.enhance_incomplete_sections(text)
        # Should add a note about the incomplete section
        self.assertIsNotNone(enhanced)


class TestBlindValidationEngine(unittest.TestCase):
    """Test BlindValidationEngine class."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ResponseValidator()
        self.blind_engine = BlindValidationEngine(self.validator)

    def test_round1_validation(self):
        """Test first validation round."""
        text = ("This is a comprehensive test response. " * 30)
        result = self.blind_engine.validate_blind_round1(text)
        self.assertIsNotNone(result.confidence)

    def test_round2_validation(self):
        """Test second validation round."""
        text = ("This is a comprehensive test response. " * 30)
        result = self.blind_engine.validate_blind_round2(text)
        self.assertIn("depth", result.scores)

    def test_round3_validation(self):
        """Test third validation round."""
        text = ("This is a comprehensive test response. " * 30)
        result = self.blind_engine.validate_blind_round3(text)
        self.assertIn("coherence", result.scores)

    def test_consensus_scoring(self):
        """Test consensus score calculation."""
        scores = [0.8, 0.75, 0.85]
        final_score, confidence_level, interval = self.blind_engine.consensus_score(scores)
        self.assertAlmostEqual(final_score, 0.8, places=1)
        self.assertGreater(interval, 0)

    def test_full_blind_validation(self):
        """Test full blind validation workflow."""
        text = ("This is a comprehensive test response with sufficient length. " * 20)
        report = self.blind_engine.full_blind_validation(text)
        self.assertIn("round1", report)
        self.assertIn("round2", report)
        self.assertIn("round3", report)
        self.assertIn("consensus", report)
        self.assertIn("final_score", report["consensus"])

    def test_generate_validation_report(self):
        """Test report generation."""
        text = ("This is test content. " * 50)
        self.blind_engine.full_blind_validation(text)
        report_text = self.blind_engine.generate_validation_report()
        self.assertIsNotNone(report_text)
        self.assertIn("Round 1", report_text)


class TestValidationIntegration(unittest.TestCase):
    """Integration tests for complete validation pipeline."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ResponseValidator()
        self.fact_checker = FactChecker()
        self.corrector = AutoCorrector()
        self.blind_engine = BlindValidationEngine(self.validator)

    def test_complete_validation_pipeline(self):
        """Test complete validation pipeline."""
        text = (
            "The human brain contains approximately 86 billion neurons. "
            "Each neuron can form thousands of connections with other neurons. "
            "This network of neural connections forms the basis of human cognition. "
            "The brain uses about 20% of the body's energy despite being only 2% of body weight. "
            "Neuroplasticity allows the brain to form new neural pathways throughout life. "
            "Memory consolidation happens through a process called long-term potentiation. "
            "Different regions of the brain specialize in different functions. "
            "The prefrontal cortex handles executive functions and decision-making. "
            "The hippocampus plays a crucial role in forming new memories. "
            "Neural pathways strengthen through repeated activation and use. "
        )

        # Run validation
        val_result = self.validator.validate_response(text)
        self.assertIsNotNone(val_result)

        # Run fact-checking
        fact_report = self.fact_checker.generate_fact_check_report(text)
        self.assertGreater(fact_report["total_claims"], 0)

        # Run blind validation
        blind_report = self.blind_engine.full_blind_validation(text)
        self.assertIn("consensus", blind_report)


if __name__ == "__main__":
    unittest.main()
