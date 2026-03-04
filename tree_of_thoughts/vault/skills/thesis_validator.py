"""Thesis Validator skill for comprehensive argument and thesis analysis."""

import logging
import time
from typing import Dict, Optional, Tuple, List

from .skill_config import SkillConfig, SkillType, AlgorithmType
from .base_skill import BaseSkill, SkillResult
from ..tot_integration import VaultAwareLanguageModel
from ..tree_of_thoughts_vault_integration import ObsidianVaultIntegration

logger = logging.getLogger(__name__)


class ThesisValidator(BaseSkill):
    """
    Thesis Validator skill for argument and thesis analysis.

    Specializes in:
    - Thesis statement validation
    - Argument structure analysis
    - Logical fallacy detection
    - Evidence quality assessment
    - Counter-argument identification
    - Conclusion strength evaluation

    Uses MCTS (Monte Carlo Tree Search) for exploring argument spaces.
    """

    def __init__(
        self,
        config: Optional[SkillConfig] = None,
        llm_model: Optional[VaultAwareLanguageModel] = None,
        vault: Optional[ObsidianVaultIntegration] = None,
    ):
        """Initialize Thesis Validator skill.

        Args:
            config: Skill configuration (uses thesis defaults if not provided)
            llm_model: Language model for thesis analysis
            vault: Vault integration for persistence
        """
        if config is None:
            config = SkillConfig(
                skill_type=SkillType.THESIS,
                algorithm=AlgorithmType.MCTS,
                name="Thesis Validator",
                description="Validate and analyze theses and arguments",
                num_thoughts=7,
                max_steps=8,
                confidence_threshold=0.80,
            )

        super().__init__(config, llm_model, vault)

        # Thesis-specific state
        self.theses_analyzed = []
        self.fallacies_detected = []
        self.arguments_evaluated = []
        self.counter_arguments = []

    def validate_input(self, prompt: str) -> Tuple[bool, str]:
        """Validate thesis analysis input.

        Args:
            prompt: Thesis or argument to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not prompt or not isinstance(prompt, str):
            return False, "Thesis prompt must be a non-empty string"

        if len(prompt) < 20:
            return False, "Thesis must be at least 20 characters"

        if len(prompt) > 3000:
            return False, "Thesis exceeds maximum length (3000 chars)"

        # Check for thesis-oriented language
        thesis_keywords = [
            "thesis", "argument", "claim", "propose", "assert",
            "demonstrate", "show", "prove", "contend", "hypothesis",
            "conclusion", "therefore", "thus", "so", "suggest",
            "support", "evidence", "because", "reason"
        ]
        has_thesis_intent = any(
            keyword in prompt.lower() for keyword in thesis_keywords
        )

        if not has_thesis_intent:
            return False, "Request should contain thesis or argument language"

        return True, ""

    def build_system_prompt(self) -> str:
        """Build system prompt for thesis validator.

        Returns:
            System prompt for thesis validation tasks
        """
        return """You are a Thesis Validator specializing in argument analysis.

Your responsibilities:
1. Analyze and evaluate thesis statements
2. Structure the main arguments and supporting points
3. Identify logical fallacies and weak reasoning
4. Assess quality and relevance of evidence
5. Identify counter-arguments and rebuttals
6. Evaluate overall argument strength
7. Provide constructive feedback for improvement

Analysis Framework:
- Thesis clarity and specificity
- Argument validity and soundness
- Evidence relevance and strength
- Logical coherence and flow
- Counter-argument handling
- Conclusion support

Fallacy Detection:
- Ad hominem attacks
- Straw man arguments
- False dilemmas
- Begging the question
- Hasty generalizations
- Appeal to authority

Output Format:
- Thesis summary and strength
- Main argument structure
- Evidence quality assessment
- Identified fallacies
- Counter-arguments analysis
- Overall validity score
- Improvement recommendations"""

    def execute(self, prompt: str, context: Optional[Dict] = None) -> SkillResult:
        """Execute thesis validation on given prompt.

        Args:
            prompt: Thesis or argument to validate
            context: Optional context (subject area, audience, etc.)

        Returns:
            SkillResult with thesis analysis
        """
        is_valid, error_msg = self.validate_input(prompt)
        if not is_valid:
            return self._handle_execution_error(ValueError(error_msg))

        start_time = time.time()

        try:
            # Extract context if provided
            subject_area = context.get("subject", "general") if context else "general"
            audience_level = context.get("audience", "academic") if context else "academic"

            # Build thesis validation prompt
            analysis_prompt = self._build_validation_context(
                prompt, subject_area, audience_level
            )

            # Run ToT search for thesis validation
            tot_result = self._run_tot_search(analysis_prompt)

            # Convert to skill result
            execution_time = time.time() - start_time
            result = self._convert_tot_result_to_skill_result(tot_result, execution_time)

            # Extract analysis details
            fallacies = self._detect_fallacies(result.output)
            self.fallacies_detected.extend(fallacies)

            # Store execution history
            self.execution_history.append({
                "timestamp": time.time(),
                "subject": subject_area,
                "fallacies_count": len(fallacies),
                "result_confidence": result.confidence_score,
            })

            self.current_result = result

            # Persist if enabled
            if self.config.persist_results:
                self._persist_result(result)

            return result

        except Exception as e:
            logger.error(f"Error in thesis validation: {e}")
            return self._handle_execution_error(e)

    def _build_validation_context(
        self, thesis: str, subject_area: str, audience_level: str
    ) -> str:
        """Build thesis validation context.

        Args:
            thesis: Thesis statement to validate
            subject_area: Subject area for the thesis
            audience_level: Target audience level

        Returns:
            Enhanced validation prompt
        """
        context = f"""Subject Area: {subject_area}
Target Audience: {audience_level}

Thesis to Validate:
{thesis}
"""
        return context

    def _detect_fallacies(self, analysis: str) -> List[str]:
        """Detect logical fallacies in thesis analysis.

        Args:
            analysis: Thesis analysis text

        Returns:
            List of detected fallacies
        """
        fallacies = []

        fallacy_patterns = {
            "ad_hominem": ["attacks the person", "character assassination", "personal attack"],
            "straw_man": ["misrepresents", "distorts", "exaggerates claim"],
            "false_dilemma": ["either or", "only two options", "false choice"],
            "begging_question": ["assumes the conclusion", "circular reasoning"],
            "hasty_generalization": ["generalizes too quickly", "stereotypes", "insufficient evidence"],
            "appeal_to_authority": ["appeals to authority", "relies on celebrity"],
            "false_cause": ["correlation implies causation", "post hoc"],
        }

        analysis_lower = analysis.lower()

        for fallacy, indicators in fallacy_patterns.items():
            if any(indicator in analysis_lower for indicator in indicators):
                fallacies.append(fallacy)

        return list(set(fallacies))[:10]

    def _assess_argument_strength(self, analysis: str) -> float:
        """Assess overall argument strength.

        Args:
            analysis: Thesis analysis text

        Returns:
            Strength score from 0.0 to 1.0
        """
        strength = 0.5  # Default middle score

        # Strength indicators
        strong_indicators = [
            "strong argument", "well-supported", "clear evidence",
            "logical flow", "coherent", "compelling"
        ]
        weak_indicators = [
            "weak argument", "lacks support", "insufficient evidence",
            "logical flaw", "incoherent", "unconvincing"
        ]

        analysis_lower = analysis.lower()

        strong_count = sum(
            1 for indicator in strong_indicators if indicator in analysis_lower
        )
        weak_count = sum(
            1 for indicator in weak_indicators if indicator in analysis_lower
        )

        # Adjust score based on indicators
        if strong_count > weak_count:
            strength = 0.7 + (0.2 * min(strong_count, 5) / 5)
        elif weak_count > strong_count:
            strength = 0.3 - (0.2 * min(weak_count, 5) / 5)

        return max(0.0, min(1.0, strength))

    def _extract_counter_arguments(self, analysis: str) -> List[str]:
        """Extract counter-arguments from analysis.

        Args:
            analysis: Thesis analysis text

        Returns:
            List of counter-arguments
        """
        counter_arguments = []

        lines = analysis.split("\n")

        counter_keywords = ["counter-argument", "objection", "counterpoint", "however", "on the other hand"]

        for line in lines:
            if any(keyword in line.lower() for keyword in counter_keywords):
                if len(line.strip()) > 10:
                    counter_arguments.append(line.strip())

        return counter_arguments[:5]

    def _evaluate_evidence_quality(self, analysis: str) -> Dict:
        """Evaluate quality of evidence in thesis.

        Args:
            analysis: Thesis analysis text

        Returns:
            Evidence quality assessment
        """
        assessment = {
            "evidence_quality": "unknown",
            "source_credibility": 0.5,
            "evidence_count": 0,
        }

        analysis_lower = analysis.lower()

        # Quality indicators
        if "primary sources" in analysis_lower:
            assessment["evidence_quality"] = "high"
            assessment["source_credibility"] = 0.85
        elif "peer-reviewed" in analysis_lower or "academic" in analysis_lower:
            assessment["evidence_quality"] = "high"
            assessment["source_credibility"] = 0.80
        elif "secondary sources" in analysis_lower or "reputable" in analysis_lower:
            assessment["evidence_quality"] = "medium"
            assessment["source_credibility"] = 0.70
        elif "unreliable" in analysis_lower or "weak" in analysis_lower:
            assessment["evidence_quality"] = "low"
            assessment["source_credibility"] = 0.30

        # Count evidence references
        evidence_markers = ["evidence:", "example:", "case:", "study:"]
        assessment["evidence_count"] = sum(
            analysis_lower.count(marker) for marker in evidence_markers
        )

        return assessment

    def get_validation_summary(self) -> Dict:
        """Get summary of thesis validations.

        Returns:
            Dictionary with validation summary
        """
        return {
            "theses_analyzed": len(self.theses_analyzed),
            "fallacies_detected_total": len(self.fallacies_detected),
            "arguments_evaluated": len(self.arguments_evaluated),
            "counter_arguments_identified": len(self.counter_arguments),
            "validations_performed": len(self.execution_history),
            "last_validation": self.current_result.to_dict() if self.current_result else None,
        }
