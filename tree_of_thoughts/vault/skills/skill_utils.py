"""
Utility functions for Tree of Thoughts skills.

Provides reusable helpers for state management, confidence calculations,
validation aggregation, and vault integration.
"""

import logging
from typing import List, Dict, Any, Union, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# STATE MANAGEMENT UTILITIES
# ============================================================================


def format_state(state: Union[str, List, Tuple]) -> str:
    """Normalize state representation to string.

    Args:
        state: State as string, list, or tuple

    Returns:
        Formatted state string
    """
    if isinstance(state, str):
        return state
    elif isinstance(state, (list, tuple)):
        return " → ".join(str(s) for s in state)
    else:
        return str(state)


def extract_state_history(states: Dict[str, float]) -> List[str]:
    """Extract reasoning path from state dictionary.

    Args:
        states: Dictionary mapping states to scores

    Returns:
        List of state strings in order
    """
    return [format_state(state) for state in states.keys()]


# ============================================================================
# CONFIDENCE SCORING UTILITIES
# ============================================================================


def merge_confidence_scores(
    scores: List[float],
    weights: Optional[List[float]] = None
) -> float:
    """Merge multiple confidence scores with optional weighting.

    Args:
        scores: List of confidence scores (0.0-1.0)
        weights: Optional weights for each score (sums to 1.0)

    Returns:
        Merged confidence score
    """
    if not scores:
        return 0.0

    if weights is None:
        weights = [1.0 / len(scores)] * len(scores)

    if len(weights) != len(scores):
        raise ValueError("Length of weights must match length of scores")

    # Normalize weights to sum to 1.0
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    # Calculate weighted average
    merged = sum(s * w for s, w in zip(scores, normalized_weights))

    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, merged))


def apply_confidence_penalty(
    score: float,
    issues: List[str],
    penalty_per_issue: float = 0.05
) -> float:
    """Apply confidence penalty based on validation issues.

    Args:
        score: Original confidence score
        issues: List of validation issue descriptions
        penalty_per_issue: Penalty amount per issue

    Returns:
        Adjusted confidence score
    """
    penalty = len(issues) * penalty_per_issue
    adjusted = score - penalty
    return max(0.0, min(1.0, adjusted))


def normalize_score(
    score: float,
    min_val: float = 0.0,
    max_val: float = 1.0
) -> float:
    """Normalize score to range [min_val, max_val].

    Args:
        score: Raw score to normalize
        min_val: Minimum value of range
        max_val: Maximum value of range

    Returns:
        Normalized score
    """
    if max_val <= min_val:
        return min_val
    return max(min_val, min(max_val, score))


# ============================================================================
# VALIDATION AGGREGATION UTILITIES
# ============================================================================


def aggregate_validation_reports(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate multiple validation reports.

    Args:
        reports: List of validation report dictionaries

    Returns:
        Aggregated validation report
    """
    if not reports:
        return {}

    aggregated = {
        "total_reports": len(reports),
        "all_valid": all(r.get("is_valid", False) for r in reports),
        "validation_agreement": sum(
            1 for r in reports if r.get("is_valid", False)
        ) / len(reports),
        "unique_issues": set(),
        "average_confidence": 0.0,
    }

    # Collect all unique issues
    for report in reports:
        issues = report.get("issues", [])
        if isinstance(issues, list):
            aggregated["unique_issues"].update(str(i) for i in issues)

    # Calculate average confidence
    confidences = [
        r.get("confidence", 0.5)
        for r in reports
        if "confidence" in r
    ]
    if confidences:
        aggregated["average_confidence"] = sum(confidences) / len(confidences)

    aggregated["unique_issues"] = list(aggregated["unique_issues"])

    return aggregated


def calculate_overall_confidence(
    validation_score: float = 0.7,
    factuality_score: float = 0.7,
    blind_score: float = 0.7,
    weights: Optional[Tuple[float, float, float]] = None
) -> float:
    """Calculate overall confidence from three validation layers.

    Args:
        validation_score: Syntactic/semantic validation confidence
        factuality_score: Fact-checking confidence
        blind_score: Triple-blind validation consensus score
        weights: Tuple of (validation_weight, factuality_weight, blind_weight)

    Returns:
        Overall confidence score
    """
    if weights is None:
        # Default weights: validation=0.35, factuality=0.35, blind=0.30
        weights = (0.35, 0.35, 0.30)

    scores = [validation_score, factuality_score, blind_score]

    return merge_confidence_scores(scores, list(weights))


# ============================================================================
# RESULT FORMATTING UTILITIES
# ============================================================================


def format_skill_result(
    output: str,
    confidence_score: float,
    reasoning_path: List[str],
    validation_issues: Optional[List[str]] = None,
    alternatives: Optional[List[Tuple[str, float]]] = None,
) -> Dict[str, Any]:
    """Format skill execution result in standard structure.

    Args:
        output: Primary output/answer
        confidence_score: Overall confidence score
        reasoning_path: Reasoning path taken
        validation_issues: Any validation issues found
        alternatives: Alternative solutions with scores

    Returns:
        Formatted result dictionary
    """
    return {
        "output": output,
        "confidence_score": confidence_score,
        "confidence_level": _score_to_level(confidence_score),
        "reasoning_path": reasoning_path,
        "path_length": len(reasoning_path),
        "validation_issues": validation_issues or [],
        "alternatives": alternatives or [],
        "timestamp": datetime.now().isoformat(),
    }


def create_summary_report(result: Dict[str, Any]) -> str:
    """Create human-readable summary of skill result.

    Args:
        result: Formatted skill result

    Returns:
        Summary text
    """
    lines = [
        f"Output: {result.get('output', 'N/A')[:200]}...",
        f"Confidence: {result.get('confidence_level', 'UNKNOWN')} " +
        f"({result.get('confidence_score', 0):.2f})",
        f"Reasoning steps: {result.get('path_length', 0)}",
    ]

    issues = result.get('validation_issues', [])
    if issues:
        lines.append(f"Issues found: {len(issues)}")

    return "\n".join(lines)


def extract_alternatives(
    result: Dict[str, Any],
    top_k: int = 3
) -> List[Tuple[str, float]]:
    """Extract top alternatives from result.

    Args:
        result: Skill result dictionary
        top_k: Number of top alternatives to return

    Returns:
        List of (alternative_text, confidence_score) tuples
    """
    alternatives = result.get("alternatives", [])
    if isinstance(alternatives, list):
        return sorted(alternatives, key=lambda x: x[1] if len(x) > 1 else 0, reverse=True)[:top_k]
    return []


# ============================================================================
# VAULT INTEGRATION UTILITIES
# ============================================================================


def create_skill_metadata(
    skill_name: str,
    algorithm: str,
    confidence_score: float,
    execution_time: float
) -> Dict[str, Any]:
    """Create metadata for vault persistence.

    Args:
        skill_name: Name of the skill
        algorithm: ToT algorithm used
        confidence_score: Final confidence score
        execution_time: Time taken to execute (seconds)

    Returns:
        Metadata dictionary
    """
    return {
        "skill_name": skill_name,
        "algorithm": algorithm,
        "confidence_score": confidence_score,
        "confidence_level": _score_to_level(confidence_score),
        "execution_time": execution_time,
        "timestamp": datetime.now().isoformat(),
    }


def tag_result_by_confidence(confidence_score: float) -> List[str]:
    """Generate tags based on confidence level.

    Args:
        confidence_score: Confidence score

    Returns:
        List of appropriate tags
    """
    tags = ["skill-result"]

    level = _score_to_level(confidence_score)
    tags.append(f"confidence-{level.lower()}")

    if confidence_score >= 0.85:
        tags.append("high-confidence")
    elif confidence_score < 0.5:
        tags.append("requires-review")

    return tags


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _score_to_level(score: float) -> str:
    """Convert numeric score to confidence level string.

    Args:
        score: Confidence score (0.0-1.0)

    Returns:
        Confidence level as string
    """
    if score >= 0.9:
        return "CERTAIN"
    elif score >= 0.7:
        return "HIGH"
    elif score >= 0.5:
        return "MEDIUM"
    elif score >= 0.3:
        return "LOW"
    else:
        return "VERY_LOW"


def score_from_level(level: str) -> float:
    """Convert confidence level string to representative score.

    Args:
        level: Confidence level string

    Returns:
        Representative score
    """
    level_map = {
        "CERTAIN": 0.95,
        "HIGH": 0.80,
        "MEDIUM": 0.60,
        "LOW": 0.40,
        "VERY_LOW": 0.15,
    }
    return level_map.get(level.upper(), 0.5)
