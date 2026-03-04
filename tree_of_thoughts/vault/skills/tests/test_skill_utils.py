"""Tests for skill_utils module."""

import unittest
from datetime import datetime
from ..skill_utils import (
    format_state,
    extract_state_history,
    merge_confidence_scores,
    apply_confidence_penalty,
    normalize_score,
    aggregate_validation_reports,
    calculate_overall_confidence,
    format_skill_result,
    create_summary_report,
    extract_alternatives,
    create_skill_metadata,
    tag_result_by_confidence,
    _score_to_level,
    score_from_level,
)


class TestStateManagementUtilities(unittest.TestCase):
    """Test state management utility functions."""

    def test_format_state_with_string(self):
        """Test formatting string state."""
        result = format_state("Initial state")
        self.assertEqual(result, "Initial state")

    def test_format_state_with_list(self):
        """Test formatting list state."""
        result = format_state(["State A", "State B", "State C"])
        self.assertEqual(result, "State A → State B → State C")

    def test_format_state_with_tuple(self):
        """Test formatting tuple state."""
        result = format_state(("Step 1", "Step 2"))
        self.assertEqual(result, "Step 1 → Step 2")

    def test_format_state_with_numbers(self):
        """Test formatting state with numbers."""
        result = format_state([1, 2, 3])
        self.assertEqual(result, "1 → 2 → 3")

    def test_format_state_with_other_type(self):
        """Test formatting other types."""
        result = format_state(42)
        self.assertEqual(result, "42")

    def test_extract_state_history(self):
        """Test extracting state history from dictionary."""
        states = {"State A": 0.5, "State B": 0.7, "State C": 0.9}
        result = extract_state_history(states)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "State A")
        self.assertEqual(result[1], "State B")
        self.assertEqual(result[2], "State C")

    def test_extract_state_history_empty(self):
        """Test extracting from empty state dictionary."""
        result = extract_state_history({})
        self.assertEqual(result, [])


class TestConfidenceScoringUtilities(unittest.TestCase):
    """Test confidence scoring utility functions."""

    def test_merge_confidence_scores_equal_weights(self):
        """Test merging scores with equal weights."""
        scores = [0.8, 0.6, 0.9]
        result = merge_confidence_scores(scores)
        self.assertAlmostEqual(result, (0.8 + 0.6 + 0.9) / 3)

    def test_merge_confidence_scores_custom_weights(self):
        """Test merging scores with custom weights."""
        scores = [0.8, 0.6]
        weights = [0.7, 0.3]
        result = merge_confidence_scores(scores, weights)
        expected = 0.8 * 0.7 + 0.6 * 0.3
        self.assertAlmostEqual(result, expected)

    def test_merge_confidence_scores_normalizes_weights(self):
        """Test that weights are normalized to sum to 1.0."""
        scores = [0.8, 0.6]
        weights = [2.0, 1.0]  # Will be normalized to [2/3, 1/3]
        result = merge_confidence_scores(scores, weights)
        expected = 0.8 * (2.0 / 3.0) + 0.6 * (1.0 / 3.0)
        self.assertAlmostEqual(result, expected)

    def test_merge_confidence_scores_clamps_to_01(self):
        """Test that result is clamped to [0.0, 1.0]."""
        scores = [1.5, -0.5]  # Would exceed bounds
        result = merge_confidence_scores(scores)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)

    def test_merge_confidence_scores_empty(self):
        """Test merging empty scores list."""
        result = merge_confidence_scores([])
        self.assertEqual(result, 0.0)

    def test_merge_confidence_scores_weight_length_mismatch(self):
        """Test error when weights length doesn't match scores."""
        scores = [0.8, 0.6, 0.9]
        weights = [0.5, 0.5]  # Wrong length
        with self.assertRaises(ValueError):
            merge_confidence_scores(scores, weights)

    def test_apply_confidence_penalty_no_issues(self):
        """Test applying penalty with no issues."""
        result = apply_confidence_penalty(0.8, [])
        self.assertEqual(result, 0.8)

    def test_apply_confidence_penalty_with_issues(self):
        """Test applying penalty with validation issues."""
        result = apply_confidence_penalty(0.8, ["Issue 1", "Issue 2"])
        expected = 0.8 - (2 * 0.05)
        self.assertEqual(result, expected)

    def test_apply_confidence_penalty_custom_penalty(self):
        """Test applying penalty with custom penalty amount."""
        result = apply_confidence_penalty(0.8, ["Issue 1"], penalty_per_issue=0.1)
        expected = 0.8 - 0.1
        self.assertEqual(result, expected)

    def test_apply_confidence_penalty_clamps_to_zero(self):
        """Test that penalty is clamped to 0.0."""
        result = apply_confidence_penalty(0.2, ["Issue 1", "Issue 2", "Issue 3", "Issue 4"])
        self.assertEqual(result, 0.0)

    def test_normalize_score_default_range(self):
        """Test normalizing score with default range."""
        result = normalize_score(0.75)
        self.assertEqual(result, 0.75)

    def test_normalize_score_clamps_above_max(self):
        """Test normalizing score above max."""
        result = normalize_score(1.5, min_val=0.0, max_val=1.0)
        self.assertEqual(result, 1.0)

    def test_normalize_score_clamps_below_min(self):
        """Test normalizing score below min."""
        result = normalize_score(-0.5, min_val=0.0, max_val=1.0)
        self.assertEqual(result, 0.0)

    def test_normalize_score_invalid_range(self):
        """Test with invalid range (max <= min)."""
        result = normalize_score(0.5, min_val=0.8, max_val=0.8)
        self.assertEqual(result, 0.8)


class TestValidationAggregation(unittest.TestCase):
    """Test validation aggregation utilities."""

    def test_aggregate_validation_reports_empty(self):
        """Test aggregating empty reports."""
        result = aggregate_validation_reports([])
        self.assertEqual(result, {})

    def test_aggregate_validation_reports_single(self):
        """Test aggregating single report."""
        reports = [
            {
                "is_valid": True,
                "confidence": 0.8,
                "issues": [],
            }
        ]
        result = aggregate_validation_reports(reports)
        self.assertEqual(result["total_reports"], 1)
        self.assertTrue(result["all_valid"])
        self.assertEqual(result["validation_agreement"], 1.0)

    def test_aggregate_validation_reports_multiple(self):
        """Test aggregating multiple reports."""
        reports = [
            {
                "is_valid": True,
                "confidence": 0.8,
                "issues": ["Issue A"],
            },
            {
                "is_valid": True,
                "confidence": 0.7,
                "issues": ["Issue B"],
            },
            {
                "is_valid": False,
                "confidence": 0.5,
                "issues": ["Issue A", "Issue C"],
            },
        ]
        result = aggregate_validation_reports(reports)
        self.assertEqual(result["total_reports"], 3)
        self.assertFalse(result["all_valid"])
        self.assertAlmostEqual(result["validation_agreement"], 2.0 / 3.0)
        self.assertEqual(len(result["unique_issues"]), 3)

    def test_aggregate_validation_reports_average_confidence(self):
        """Test average confidence calculation."""
        reports = [
            {"is_valid": True, "confidence": 0.6},
            {"is_valid": True, "confidence": 0.8},
            {"is_valid": True, "confidence": 1.0},
        ]
        result = aggregate_validation_reports(reports)
        expected_avg = (0.6 + 0.8 + 1.0) / 3
        self.assertAlmostEqual(result["average_confidence"], expected_avg)

    def test_calculate_overall_confidence_defaults(self):
        """Test calculating overall confidence with default weights."""
        result = calculate_overall_confidence(
            validation_score=0.8,
            factuality_score=0.7,
            blind_score=0.9,
        )
        # Default weights: (0.35, 0.35, 0.30)
        expected = 0.8 * 0.35 + 0.7 * 0.35 + 0.9 * 0.30
        self.assertAlmostEqual(result, expected)

    def test_calculate_overall_confidence_custom_weights(self):
        """Test calculating overall confidence with custom weights."""
        result = calculate_overall_confidence(
            validation_score=0.8,
            factuality_score=0.7,
            blind_score=0.9,
            weights=(0.5, 0.3, 0.2),
        )
        expected = 0.8 * 0.5 + 0.7 * 0.3 + 0.9 * 0.2
        self.assertAlmostEqual(result, expected)

    def test_calculate_overall_confidence_clamps_result(self):
        """Test that result is clamped to [0.0, 1.0]."""
        result = calculate_overall_confidence(
            validation_score=0.9,
            factuality_score=0.95,
            blind_score=1.0,
        )
        self.assertLessEqual(result, 1.0)
        self.assertGreaterEqual(result, 0.0)


class TestResultFormatting(unittest.TestCase):
    """Test result formatting utilities."""

    def test_format_skill_result_minimal(self):
        """Test formatting skill result with minimal fields."""
        result = format_skill_result(
            output="Test output",
            confidence_score=0.8,
            reasoning_path=["Step 1", "Step 2"],
        )
        self.assertEqual(result["output"], "Test output")
        self.assertEqual(result["confidence_score"], 0.8)
        self.assertEqual(result["confidence_level"], "HIGH")
        self.assertEqual(result["path_length"], 2)
        self.assertEqual(result["validation_issues"], [])
        self.assertEqual(result["alternatives"], [])

    def test_format_skill_result_full(self):
        """Test formatting skill result with all fields."""
        issues = ["Issue 1", "Issue 2"]
        alternatives = [("Alt 1", 0.7), ("Alt 2", 0.6)]
        result = format_skill_result(
            output="Complete output",
            confidence_score=0.75,
            reasoning_path=["A", "B", "C"],
            validation_issues=issues,
            alternatives=alternatives,
        )
        self.assertEqual(result["output"], "Complete output")
        self.assertEqual(result["validation_issues"], issues)
        self.assertEqual(result["alternatives"], alternatives)
        self.assertIn("timestamp", result)

    def test_create_summary_report(self):
        """Test creating human-readable summary."""
        result = {
            "output": "This is a very long output that should be truncated when displayed in the summary report format.",
            "confidence_level": "HIGH",
            "confidence_score": 0.82,
            "path_length": 5,
            "validation_issues": ["Issue A", "Issue B"],
        }
        summary = create_summary_report(result)
        self.assertIn("Output:", summary)
        self.assertIn("Confidence:", summary)
        self.assertIn("HIGH", summary)
        self.assertIn("0.82", summary)
        self.assertIn("5", summary)
        self.assertIn("Issues found: 2", summary)

    def test_extract_alternatives_top_k(self):
        """Test extracting top K alternatives."""
        result = {
            "alternatives": [
                ("Option A", 0.8),
                ("Option B", 0.6),
                ("Option C", 0.9),
                ("Option D", 0.5),
            ]
        }
        alternatives = extract_alternatives(result, top_k=2)
        self.assertEqual(len(alternatives), 2)
        # Should be sorted by score descending
        self.assertEqual(alternatives[0][1], 0.9)
        self.assertEqual(alternatives[1][1], 0.8)

    def test_extract_alternatives_default_top_k(self):
        """Test extracting alternatives with default top_k."""
        result = {
            "alternatives": [
                ("Option A", 0.8),
                ("Option B", 0.6),
                ("Option C", 0.9),
            ]
        }
        alternatives = extract_alternatives(result)
        self.assertEqual(len(alternatives), 3)

    def test_extract_alternatives_empty(self):
        """Test extracting from empty alternatives."""
        result = {"alternatives": []}
        alternatives = extract_alternatives(result)
        self.assertEqual(alternatives, [])


class TestVaultIntegration(unittest.TestCase):
    """Test vault integration utilities."""

    def test_create_skill_metadata(self):
        """Test creating skill metadata."""
        metadata = create_skill_metadata(
            skill_name="Research Analyst",
            algorithm="a_star",
            confidence_score=0.82,
            execution_time=5.3,
        )
        self.assertEqual(metadata["skill_name"], "Research Analyst")
        self.assertEqual(metadata["algorithm"], "a_star")
        self.assertEqual(metadata["confidence_score"], 0.82)
        self.assertEqual(metadata["confidence_level"], "HIGH")
        self.assertEqual(metadata["execution_time"], 5.3)
        self.assertIn("timestamp", metadata)

    def test_tag_result_by_confidence_very_high(self):
        """Test tagging result with very high confidence."""
        tags = tag_result_by_confidence(0.95)
        self.assertIn("skill-result", tags)
        self.assertIn("confidence-certain", tags)
        self.assertIn("high-confidence", tags)

    def test_tag_result_by_confidence_high(self):
        """Test tagging result with high confidence."""
        tags = tag_result_by_confidence(0.85)
        self.assertIn("confidence-high", tags)
        self.assertIn("high-confidence", tags)

    def test_tag_result_by_confidence_medium(self):
        """Test tagging result with medium confidence."""
        tags = tag_result_by_confidence(0.65)
        self.assertIn("confidence-medium", tags)
        self.assertNotIn("high-confidence", tags)
        self.assertNotIn("requires-review", tags)

    def test_tag_result_by_confidence_low(self):
        """Test tagging result with low confidence."""
        tags = tag_result_by_confidence(0.4)
        self.assertIn("confidence-low", tags)
        self.assertIn("requires-review", tags)

    def test_tag_result_by_confidence_very_low(self):
        """Test tagging result with very low confidence."""
        tags = tag_result_by_confidence(0.15)
        self.assertIn("confidence-very_low", tags)
        self.assertIn("requires-review", tags)


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions."""

    def test_score_to_level_certain(self):
        """Test converting high scores to CERTAIN."""
        self.assertEqual(_score_to_level(0.95), "CERTAIN")
        self.assertEqual(_score_to_level(1.0), "CERTAIN")
        self.assertEqual(_score_to_level(0.90), "CERTAIN")

    def test_score_to_level_high(self):
        """Test converting mid-high scores to HIGH."""
        self.assertEqual(_score_to_level(0.85), "HIGH")
        self.assertEqual(_score_to_level(0.75), "HIGH")
        self.assertEqual(_score_to_level(0.70), "HIGH")

    def test_score_to_level_medium(self):
        """Test converting mid scores to MEDIUM."""
        self.assertEqual(_score_to_level(0.65), "MEDIUM")
        self.assertEqual(_score_to_level(0.60), "MEDIUM")
        self.assertEqual(_score_to_level(0.50), "MEDIUM")

    def test_score_to_level_low(self):
        """Test converting low scores to LOW."""
        self.assertEqual(_score_to_level(0.45), "LOW")
        self.assertEqual(_score_to_level(0.30), "LOW")
        self.assertEqual(_score_to_level(0.40), "LOW")

    def test_score_to_level_very_low(self):
        """Test converting very low scores to VERY_LOW."""
        self.assertEqual(_score_to_level(0.25), "VERY_LOW")
        self.assertEqual(_score_to_level(0.0), "VERY_LOW")
        self.assertEqual(_score_to_level(0.1), "VERY_LOW")

    def test_score_from_level_certain(self):
        """Test converting CERTAIN to score."""
        self.assertEqual(score_from_level("CERTAIN"), 0.95)

    def test_score_from_level_high(self):
        """Test converting HIGH to score."""
        self.assertEqual(score_from_level("HIGH"), 0.80)

    def test_score_from_level_medium(self):
        """Test converting MEDIUM to score."""
        self.assertEqual(score_from_level("MEDIUM"), 0.60)

    def test_score_from_level_low(self):
        """Test converting LOW to score."""
        self.assertEqual(score_from_level("LOW"), 0.40)

    def test_score_from_level_very_low(self):
        """Test converting VERY_LOW to score."""
        self.assertEqual(score_from_level("VERY_LOW"), 0.15)

    def test_score_from_level_case_insensitive(self):
        """Test that level conversion is case insensitive."""
        self.assertEqual(score_from_level("high"), 0.80)
        self.assertEqual(score_from_level("High"), 0.80)
        self.assertEqual(score_from_level("HIGH"), 0.80)

    def test_score_from_level_unknown(self):
        """Test unknown level returns default."""
        self.assertEqual(score_from_level("UNKNOWN"), 0.5)


class TestUtilityIntegration(unittest.TestCase):
    """Test integration of utility functions."""

    def test_confidence_pipeline(self):
        """Test complete confidence calculation pipeline."""
        # Start with three validation scores
        validation_score = 0.8
        factuality_score = 0.75
        blind_score = 0.85

        # Calculate overall confidence
        overall = calculate_overall_confidence(validation_score, factuality_score, blind_score)
        self.assertGreater(overall, 0.0)
        self.assertLess(overall, 1.0)

        # Apply penalty for issues
        issues = ["Minor issue"]
        adjusted = apply_confidence_penalty(overall, issues)
        self.assertLess(adjusted, overall)

        # Convert to level
        level = _score_to_level(adjusted)
        self.assertIn(level, ["CERTAIN", "HIGH", "MEDIUM", "LOW", "VERY_LOW"])

    def test_result_formatting_pipeline(self):
        """Test complete result formatting pipeline."""
        output = "Test finding"
        confidence = 0.80
        path = ["Analysis 1", "Analysis 2"]

        # Format result
        formatted = format_skill_result(output, confidence, path)
        self.assertIn("output", formatted)
        self.assertIn("timestamp", formatted)

        # Create metadata
        metadata = create_skill_metadata(
            skill_name="Test",
            algorithm="bfs",
            confidence_score=confidence,
            execution_time=2.5,
        )
        self.assertIn("skill_name", metadata)

        # Tag by confidence
        tags = tag_result_by_confidence(confidence)
        self.assertIn("confidence-high", tags)


if __name__ == "__main__":
    unittest.main()
