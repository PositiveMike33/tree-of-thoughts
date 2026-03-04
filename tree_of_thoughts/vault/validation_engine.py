"""
Validation Engine for Vault Integration

Multi-level validation system for LLM responses including:
- Syntactic validation (structure and format)
- Completeness validation (content length and structure)
- Consistency validation (no internal contradictions)
- Reference validation (cite-ability and traceability)
- Fact-checking with meta-evaluation
- Auto-correction of common issues
- Blind validation with consensus scoring
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ValidationIssueType(Enum):
    """Types of validation issues."""
    INCOMPLETE = "incomplete"  # Too short or incomplete
    TRUNCATED = "truncated"  # Appears to be cut off
    INCOHERENT = "incoherent"  # Doesn't make sense
    INCONSISTENT = "inconsistent"  # Contradicts itself
    POOR_STRUCTURE = "poor_structure"  # Bad formatting
    MISSING_CONTEXT = "missing_context"  # Lacks necessary context
    UNVERIFIABLE = "unverifiable"  # Claims can't be verified


class ConfidenceLevel(Enum):
    """Confidence levels for validation results."""
    CERTAIN = "certain"  # 0.9-1.0
    HIGH = "high"  # 0.7-0.9
    MEDIUM = "medium"  # 0.5-0.7
    LOW = "low"  # 0.3-0.5
    VERY_LOW = "very_low"  # 0.0-0.3


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    issue_type: ValidationIssueType
    severity: str  # "critical", "warning", "info"
    message: str
    position: Optional[int] = None  # Character position in text
    suggested_fix: Optional[str] = None

    def __str__(self):
        return f"[{self.severity.upper()}] {self.issue_type.value}: {self.message}"


@dataclass
class ValidationResult:
    """Complete validation result for a response."""
    is_valid: bool
    confidence: float  # 0.0-1.0
    confidence_level: ConfidenceLevel
    issues: List[ValidationIssue] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)  # Component scores
    recommendations: List[str] = field(default_factory=list)
    requires_human_review: bool = False
    validation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    validation_details: Dict[str, str] = field(default_factory=dict)

    def add_issue(self, issue: ValidationIssue):
        """Add an issue to this result."""
        self.issues.append(issue)
        if issue.severity == "critical":
            self.is_valid = False

    def add_recommendation(self, recommendation: str):
        """Add a recommendation."""
        if recommendation not in self.recommendations:
            self.recommendations.append(recommendation)

    def get_summary(self) -> str:
        """Get human-readable summary of validation result."""
        status = "✓ VALID" if self.is_valid else "✗ INVALID"
        return f"{status} | Confidence: {self.confidence:.1%} ({self.confidence_level.value})"


@dataclass
class Claim:
    """Represents a factual claim in text."""
    text: str
    position: int
    confidence: float = 0.5  # How confident is the claim itself?


@dataclass
class FactCheckResult:
    """Result of fact-checking a claim."""
    claim: Claim
    is_verifiable: bool
    confidence: float  # 0.0-1.0
    reasoning: str
    suggested_source: Optional[str] = None


class ResponseValidator:
    """Basic multi-level validation of LLM responses."""

    def __init__(self, min_words: int = 300, min_sentences: int = 5):
        """Initialize validator.

        Args:
            min_words: Minimum word count for valid response
            min_sentences: Minimum sentence count
        """
        self.min_words = min_words
        self.min_sentences = min_sentences

    def validate_response(self, text: str, section: str = "BRAIN") -> ValidationResult:
        """Perform complete validation of response.

        Args:
            text: Response text to validate
            section: Vault section (for context-aware validation)

        Returns:
            ValidationResult with all checks
        """
        result = ValidationResult(
            is_valid=True,
            confidence=1.0,
            confidence_level=ConfidenceLevel.CERTAIN,
        )

        # Run all validation checks
        self._check_syntactic(text, result)
        self._check_completeness(text, result)
        self._check_consistency(text, result)
        self._check_references(text, result)

        # Calculate overall confidence based on issues
        result.confidence = self._calculate_confidence(result)
        result.confidence_level = self._confidence_to_level(result.confidence)

        # Determine if requires human review
        critical_issues = [i for i in result.issues if i.severity == "critical"]
        result.requires_human_review = len(critical_issues) > 0

        logger.debug(f"Validation complete: {result.get_summary()}")
        return result

    def _check_syntactic(self, text: str, result: ValidationResult):
        """Check syntactic validity (structure, format)."""
        if not text or len(text.strip()) == 0:
            issue = ValidationIssue(
                issue_type=ValidationIssueType.INCOMPLETE,
                severity="critical",
                message="Response is empty",
            )
            result.add_issue(issue)
            result.is_valid = False
            return

        # Check for obvious truncation markers
        if text.strip().endswith(("...", "....", "- ", "* ", "1. ")):
            issue = ValidationIssue(
                issue_type=ValidationIssueType.TRUNCATED,
                severity="warning",
                message="Response may be truncated (ends with ellipsis or list marker)",
                position=len(text) - 10,
            )
            result.add_issue(issue)

        # Check balanced brackets/quotes
        if not self._check_balanced_brackets(text):
            issue = ValidationIssue(
                issue_type=ValidationIssueType.POOR_STRUCTURE,
                severity="warning",
                message="Unbalanced brackets or quotes detected",
            )
            result.add_issue(issue)

        result.scores["syntactic"] = 0.9 if not result.issues else 0.7

    def _check_completeness(self, text: str, result: ValidationResult):
        """Check if response is complete (sufficient length/structure)."""
        word_count = len(text.split())
        sentence_count = len(re.split(r'[.!?]+', text.strip()))

        if word_count < self.min_words:
            issue = ValidationIssue(
                issue_type=ValidationIssueType.INCOMPLETE,
                severity="warning",
                message=f"Response too short ({word_count} words, minimum {self.min_words})",
            )
            result.add_issue(issue)
            result.add_recommendation(f"Expand response to at least {self.min_words} words")

        if sentence_count < self.min_sentences:
            issue = ValidationIssue(
                issue_type=ValidationIssueType.INCOMPLETE,
                severity="info",
                message=f"Few sentences ({sentence_count}, minimum {self.min_sentences})",
            )
            result.add_issue(issue)

        completeness_score = min(word_count / self.min_words, 1.0)
        result.scores["completeness"] = completeness_score

    def _check_consistency(self, text: str, result: ValidationResult):
        """Check for internal contradictions."""
        # Simple consistency check: look for obvious contradictions
        contradictions = self._find_contradictions(text)

        for contradiction in contradictions:
            issue = ValidationIssue(
                issue_type=ValidationIssueType.INCONSISTENT,
                severity="warning",
                message=contradiction,
            )
            result.add_issue(issue)
            result.add_recommendation("Review and resolve contradictions")

        result.scores["consistency"] = 0.9 if not contradictions else 0.6

    def _check_references(self, text: str, result: ValidationResult):
        """Check for verifiable references and citations."""
        # Count different types of references
        citations = len(re.findall(r'\[.*?\]', text))  # [citation] style
        quotes = len(re.findall(r'"[^"]{10,}"', text))  # Quoted material
        links = len(re.findall(r'http[s]?://\S+', text))  # URLs

        reference_score = min((citations + quotes + links) / 5, 1.0)
        result.scores["references"] = reference_score

        if reference_score < 0.2:
            result.add_recommendation("Consider adding sources or citations to support claims")

    def _check_balanced_brackets(self, text: str) -> bool:
        """Check if brackets and quotes are balanced."""
        stack = []
        pairs = {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"}

        for char in text:
            if char in pairs and char not in ('"', "'"):
                stack.append(char)
            elif char in pairs.values() and char not in ('"', "'"):
                if not stack or pairs[stack.pop()] != char:
                    return False
            elif char in ('"', "'"):
                if stack and stack[-1] == char:
                    stack.pop()
                else:
                    stack.append(char)

        return len(stack) == 0

    def _find_contradictions(self, text: str) -> List[str]:
        """Simple contradiction detection."""
        contradictions = []

        # Pattern: "X is Y" followed by "X is not Y"
        statements = re.split(r'[.!?]+', text)
        seen_claims = {}

        for stmt in statements:
            stmt = stmt.strip().lower()
            if len(stmt) < 10:
                continue

            # Check for "is" statements
            is_match = re.search(r'(\w+)\s+is\s+(.+?)(?:\sand\s|\s*$)', stmt)
            if is_match:
                subject, predicate = is_match.groups()
                key = subject.strip()

                if key in seen_claims:
                    if seen_claims[key] != predicate.strip():
                        contradictions.append(
                            f"Contradiction: '{key}' described as both '{seen_claims[key]}' and '{predicate.strip()}'"
                        )
                else:
                    seen_claims[key] = predicate.strip()

        return contradictions

    def _calculate_confidence(self, result: ValidationResult) -> float:
        """Calculate overall confidence based on scores and issues."""
        if result.issues:
            critical_count = len([i for i in result.issues if i.severity == "critical"])
            warning_count = len([i for i in result.issues if i.severity == "warning"])

            confidence = 1.0
            confidence -= critical_count * 0.3
            confidence -= warning_count * 0.1

            return max(confidence, 0.0)

        # If no issues, average all scores
        if result.scores:
            return sum(result.scores.values()) / len(result.scores)

        return 0.95

    def _confidence_to_level(self, confidence: float) -> ConfidenceLevel:
        """Convert numeric confidence to confidence level."""
        if confidence >= 0.9:
            return ConfidenceLevel.CERTAIN
        elif confidence >= 0.7:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif confidence >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW


class FactChecker:
    """Fact-checking using meta-evaluation (LLM evaluates LLM output)."""

    def __init__(self, llm_client=None):
        """Initialize fact checker.

        Args:
            llm_client: Optional OpenRouterClient for fact-checking calls
        """
        self.llm_client = llm_client

    def extract_claims(self, text: str) -> List[Claim]:
        """Extract factual claims from text.

        Args:
            text: Text to extract claims from

        Returns:
            List of Claims found
        """
        claims = []

        # Pattern 1: "X is Y" statements
        for match in re.finditer(r'(\w+(?:\s+\w+)?)\s+is\s+([^.!?]+)', text):
            claim_text = match.group(0)
            position = match.start()
            claims.append(Claim(text=claim_text, position=position))

        # Pattern 2: "According to / Studies show" statements
        for match in re.finditer(r'(?:According to|Studies show|Research indicates|Evidence suggests)\s+([^.!?]+)', text):
            claim_text = match.group(0)
            position = match.start()
            claims.append(Claim(text=claim_text, position=position))

        # Pattern 3: Quantitative claims (numbers/percentages)
        for match in re.finditer(r'(\d+(?:%|percent|percentage)?)\s+([^.!?]+)', text):
            claim_text = match.group(0)
            position = match.start()
            claims.append(Claim(text=claim_text, position=position))

        logger.debug(f"Extracted {len(claims)} claims from text")
        return claims

    def verify_claim(self, claim: Claim, section: str = "BRAIN") -> FactCheckResult:
        """Verify a single claim.

        Args:
            claim: Claim to verify
            section: Vault section for context

        Returns:
            FactCheckResult with verification
        """
        # For now, implement basic fact-checking without LLM
        # If LLM client available, could make API call
        is_verifiable = self._assess_verifiability(claim.text)
        confidence = 0.6 if is_verifiable else 0.3

        reasoning = (
            "Claim appears to be a factual assertion that could be verified"
            if is_verifiable
            else "Claim is subjective or opinions-based"
        )

        return FactCheckResult(
            claim=claim,
            is_verifiable=is_verifiable,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _assess_verifiability(self, claim_text: str) -> bool:
        """Quick assessment of whether claim is verifiable."""
        # Verifiable claims usually contain:
        # - Concrete nouns (people, places, things)
        # - Numbers or quantitative markers
        # - Action verbs
        # - Avoid purely subjective words

        subjective_words = {"think", "feel", "believe", "like", "prefer", "beautiful", "ugly", "good", "bad"}
        lowercase_claim = claim_text.lower()

        # If contains subjective words, likely not verifiable
        if any(word in lowercase_claim for word in subjective_words):
            return False

        # If contains numbers or comparisons, likely verifiable
        if re.search(r'\d+|more|less|greater|fewer', lowercase_claim):
            return True

        # If contains action verbs, likely verifiable
        action_verbs = {"found", "discovered", "showed", "demonstrated", "proved"}
        if any(verb in lowercase_claim for verb in action_verbs):
            return True

        return True  # Default to verifiable

    def score_factuality(self, text: str, section: str = "BRAIN") -> float:
        """Score overall factuality of response.

        Args:
            text: Text to evaluate
            section: Vault section for context

        Returns:
            Factuality score 0.0-1.0
        """
        claims = self.extract_claims(text)
        if not claims:
            return 0.5  # Neutral if no claims found

        verifiable_count = sum(
            1 for claim in claims
            if self._assess_verifiability(claim.text)
        )

        return verifiable_count / len(claims)

    def generate_fact_check_report(self, text: str, section: str = "BRAIN") -> Dict:
        """Generate comprehensive fact-check report.

        Args:
            text: Text to fact-check
            section: Vault section for context

        Returns:
            Dictionary with fact-check results
        """
        claims = self.extract_claims(text)
        verifications = [self.verify_claim(claim, section) for claim in claims]

        report = {
            "total_claims": len(claims),
            "verifiable_claims": sum(1 for v in verifications if v.is_verifiable),
            "factuality_score": self.score_factuality(text, section),
            "verifications": [
                {
                    "claim": v.claim.text,
                    "is_verifiable": v.is_verifiable,
                    "confidence": v.confidence,
                    "reasoning": v.reasoning,
                }
                for v in verifications
            ],
            "timestamp": datetime.now().isoformat(),
        }

        return report


class AutoCorrector:
    """Auto-correction for common response issues."""

    def __init__(self, llm_client=None):
        """Initialize auto-corrector.

        Args:
            llm_client: Optional OpenRouterClient for continuation requests
        """
        self.llm_client = llm_client

    def detect_truncation(self, text: str) -> Tuple[bool, float]:
        """Detect if response appears truncated.

        Args:
            text: Text to check

        Returns:
            Tuple of (is_truncated, confidence)
        """
        if not text:
            return False, 0.0

        # Pattern 1: Ends with ellipsis
        if re.search(r'\.{2,}\s*$', text):
            return True, 0.9

        # Pattern 2: Ends with incomplete list
        if re.search(r'^\s*[-*]\s+[^.!?]*$', text.strip().split('\n')[-1]):
            return True, 0.8

        # Pattern 3: Ends mid-sentence (no terminal punctuation on last line)
        last_line = text.strip().split('\n')[-1]
        if last_line and not re.search(r'[.!?:)\]}\'"]\s*$', last_line):
            return True, 0.6

        # Pattern 4: Incomplete sentence structure (too many open brackets)
        open_count = text.count('(') + text.count('[') + text.count('{')
        close_count = text.count(')') + text.count(']') + text.count('}')
        if open_count > close_count:
            return True, 0.7

        return False, 0.0

    def request_continuation(
        self,
        original_response: str,
        original_prompt: str,
        llm_client=None,
    ) -> str:
        """Request continuation of truncated response.

        Args:
            original_response: The incomplete response
            original_prompt: Original prompt that generated response
            llm_client: OpenRouterClient to use (uses self.llm_client if None)

        Returns:
            Continuation text (or original if cannot continue)
        """
        if not self.llm_client and not llm_client:
            logger.warning("No LLM client available for continuation")
            return original_response

        client = llm_client or self.llm_client

        # Build continuation prompt
        continuation_prompt = (
            f"The following response was cut off. Please continue and complete it:\n\n"
            f"Original question: {original_prompt}\n\n"
            f"Incomplete response:\n{original_response}\n\n"
            f"Please continue the response, completing all thoughts and sections."
        )

        try:
            # This would call the LLM client
            # For now, just return original (would be implemented when integrated with vault_sync)
            logger.info("Would request continuation from LLM")
            return original_response
        except Exception as e:
            logger.error(f"Error requesting continuation: {e}")
            return original_response

    def fix_obvious_errors(self, text: str) -> str:
        """Fix obvious errors in text.

        Args:
            text: Text to fix

        Returns:
            Corrected text
        """
        corrected = text

        # Fix double spaces
        corrected = re.sub(r'\s{2,}', ' ', corrected)

        # Fix duplicate punctuation
        corrected = re.sub(r'([.!?]){2,}', r'\1', corrected)

        # Fix space before punctuation
        corrected = re.sub(r'\s+([.!?:,;])', r'\1', corrected)

        # Fix quotes
        corrected = re.sub(r'"\s+', '" ', corrected)
        corrected = re.sub(r'\s+"', ' "', corrected)

        return corrected.strip()

    def enhance_incomplete_sections(self, text: str) -> str:
        """Enhance incomplete sections with placeholder suggestions.

        Args:
            text: Text with potentially incomplete sections

        Returns:
            Enhanced text with suggestions
        """
        # This is a simple version; would be enhanced with LLM
        sections = re.split(r'\n(?:##|###)\s+', text)

        if len(sections) > 1:
            # Check if last section is incomplete
            last_section = sections[-1]
            if len(last_section.split()) < 50:
                # Add note that section needs expansion
                text += "\n\n*[Note: This section needs further development]*"

        return text


class BlindValidationEngine:
    """Triple blind validation with consensus scoring."""

    def __init__(self, validator: ResponseValidator = None, llm_client=None):
        """Initialize blind validation engine.

        Args:
            validator: ResponseValidator to use
            llm_client: Optional OpenRouterClient for LLM-based validation
        """
        self.validator = validator or ResponseValidator()
        self.llm_client = llm_client
        self.round_results: List[ValidationResult] = []

    def validate_blind_round1(self, text: str, section: str = "BRAIN") -> ValidationResult:
        """First validation round (basic structure check)."""
        return self.validator.validate_response(text, section)

    def validate_blind_round2(self, text: str, section: str = "BRAIN") -> ValidationResult:
        """Second validation round (content depth check)."""
        result = ValidationResult(is_valid=True, confidence=1.0, confidence_level=ConfidenceLevel.CERTAIN)

        word_count = len(text.split())
        sentence_count = len(re.split(r'[.!?]+', text.strip()))
        paragraph_count = len([p for p in text.split('\n\n') if p.strip()])

        # Check for sufficient detail
        if word_count > 500 and sentence_count > 10:
            result.scores["depth"] = 0.9
        elif word_count > 300 and sentence_count > 5:
            result.scores["depth"] = 0.7
        else:
            result.scores["depth"] = 0.5

        if paragraph_count < 2:
            result.add_issue(ValidationIssue(
                issue_type=ValidationIssueType.POOR_STRUCTURE,
                severity="info",
                message="Response lacks multiple paragraphs",
            ))

        result.confidence = sum(result.scores.values()) / len(result.scores) if result.scores else 0.5
        result.confidence_level = self.validator._confidence_to_level(result.confidence)

        return result

    def validate_blind_round3(self, text: str, section: str = "BRAIN") -> ValidationResult:
        """Third validation round (coherence check)."""
        result = ValidationResult(is_valid=True, confidence=1.0, confidence_level=ConfidenceLevel.CERTAIN)

        # Check for coherence patterns
        sentences = re.split(r'[.!?]+', text)
        coherence_score = self._assess_coherence(sentences)

        result.scores["coherence"] = coherence_score
        if coherence_score < 0.5:
            result.add_issue(ValidationIssue(
                issue_type=ValidationIssueType.INCOHERENT,
                severity="warning",
                message="Response coherence is low",
            ))

        result.confidence = coherence_score
        result.confidence_level = self.validator._confidence_to_level(result.confidence)

        return result

    def consensus_score(self, scores: List[float]) -> Tuple[float, str, float]:
        """Calculate consensus score from multiple validation rounds.

        Args:
            scores: List of validation confidence scores

        Returns:
            Tuple of (final_score, confidence_level, confidence_interval)
        """
        if not scores:
            return 0.5, "medium", 0.0

        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5

        # Confidence interval (95%)
        confidence_interval = 1.96 * std_dev

        # Determine confidence level
        confidence_level = self.validator._confidence_to_level(mean_score)

        return mean_score, confidence_level.value, confidence_interval

    def _assess_coherence(self, sentences: List[str]) -> float:
        """Assess coherence of text sentences."""
        if len(sentences) < 2:
            return 0.5

        # Check for coherence patterns
        # - Do sentences reference previous content?
        # - Is there logical flow?
        coherence_count = 0

        for i in range(1, len(sentences)):
            curr = sentences[i].strip().lower()
            prev = sentences[i-1].strip().lower()

            if not curr or not prev:
                continue

            # Check for pronouns (indicate reference to previous content)
            if re.search(r'\b(this|that|these|those|it|they|he|she)\b', curr):
                coherence_count += 1

            # Check for causal markers
            if re.search(r'\b(because|therefore|thus|so|however|furthermore|moreover)\b', curr):
                coherence_count += 1

        coherence_score = min(coherence_count / (len(sentences) - 1), 1.0)
        return coherence_score

    def full_blind_validation(self, text: str, section: str = "BRAIN") -> Dict:
        """Execute full triple-blind validation.

        Args:
            text: Text to validate
            section: Vault section for context

        Returns:
            Dictionary with all validation results and consensus
        """
        # Run three rounds
        round1 = self.validate_blind_round1(text, section)
        round2 = self.validate_blind_round2(text, section)
        round3 = self.validate_blind_round3(text, section)

        self.round_results = [round1, round2, round3]

        # Calculate consensus
        scores = [round1.confidence, round2.confidence, round3.confidence]
        final_score, confidence_level, confidence_interval = self.consensus_score(scores)

        return {
            "round1": {
                "score": round1.confidence,
                "is_valid": round1.is_valid,
                "issues": [str(i) for i in round1.issues],
            },
            "round2": {
                "score": round2.confidence,
                "is_valid": round2.is_valid,
                "issues": [str(i) for i in round2.issues],
            },
            "round3": {
                "score": round3.confidence,
                "is_valid": round3.is_valid,
                "issues": [str(i) for i in round3.issues],
            },
            "consensus": {
                "final_score": final_score,
                "confidence_level": confidence_level,
                "confidence_interval": confidence_interval,
                "overall_valid": final_score >= 0.6,
                "requires_review": final_score < 0.5,
            },
            "timestamp": datetime.now().isoformat(),
        }

    def generate_validation_report(self) -> str:
        """Generate human-readable validation report.

        Returns:
            Formatted report as string
        """
        if not self.round_results:
            return "No validation results available"

        report_lines = [
            "=" * 60,
            "BLIND VALIDATION REPORT",
            "=" * 60,
            "",
        ]

        for i, result in enumerate(self.round_results, 1):
            report_lines.extend([
                f"Round {i}: {result.get_summary()}",
                f"Issues: {len(result.issues)}",
            ])
            for issue in result.issues:
                report_lines.append(f"  - {issue}")
            report_lines.append("")

        return "\n".join(report_lines)
