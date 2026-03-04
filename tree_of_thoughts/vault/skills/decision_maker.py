"""Decision Maker skill for structured decision analysis and recommendations."""

import logging
import time
from typing import Dict, Optional, Tuple, List

from .skill_config import SkillConfig, SkillType, AlgorithmType
from .base_skill import BaseSkill, SkillResult
from ..tot_integration import VaultAwareLanguageModel
from ..tree_of_thoughts_vault_integration import ObsidianVaultIntegration

logger = logging.getLogger(__name__)


class DecisionMaker(BaseSkill):
    """
    Decision Maker skill for structured decision analysis.

    Specializes in:
    - Multi-criteria decision analysis
    - Risk assessment
    - Stakeholder consideration
    - Trade-off analysis
    - Recommendation generation

    Uses BEST (Beam Search) algorithm for exploring decision alternatives.
    """

    def __init__(
        self,
        config: Optional[SkillConfig] = None,
        llm_model: Optional[VaultAwareLanguageModel] = None,
        vault: Optional[ObsidianVaultIntegration] = None,
    ):
        """Initialize Decision Maker skill.

        Args:
            config: Skill configuration (uses decision defaults if not provided)
            llm_model: Language model for decision analysis
            vault: Vault integration for persistence
        """
        if config is None:
            config = SkillConfig(
                skill_type=SkillType.DECISION,
                algorithm=AlgorithmType.BEST,
                name="Decision Maker",
                description="Analyze decisions and provide recommendations",
                num_thoughts=6,
                max_steps=5,
                confidence_threshold=0.80,
            )

        super().__init__(config, llm_model, vault)

        # Decision-specific state
        self.criteria_analyzed = []
        self.risks_identified = []
        self.alternatives_evaluated = []
        self.recommendations = []

    def validate_input(self, prompt: str) -> Tuple[bool, str]:
        """Validate decision input.

        Args:
            prompt: Decision problem statement to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not prompt or not isinstance(prompt, str):
            return False, "Decision prompt must be a non-empty string"

        if len(prompt) < 15:
            return False, "Decision problem must be at least 15 characters"

        if len(prompt) > 1500:
            return False, "Decision prompt exceeds maximum length (1500 chars)"

        # Check for decision-oriented language
        decision_keywords = [
            "decide", "choice", "option", "alternative", "best",
            "should", "evaluate", "assess", "compare", "recommend",
            "decision", "trade-off", "pros", "cons", "better"
        ]
        has_decision_intent = any(
            keyword in prompt.lower() for keyword in decision_keywords
        )

        if not has_decision_intent:
            return False, "Prompt should contain decision-oriented language"

        return True, ""

    def build_system_prompt(self) -> str:
        """Build system prompt for decision maker.

        Returns:
            System prompt for decision tasks
        """
        return """You are a Decision Maker specializing in structured analysis.

Your responsibilities:
1. Identify all key decision criteria and constraints
2. Evaluate alternative options systematically
3. Assess risks and potential consequences
4. Consider stakeholder perspectives
5. Analyze trade-offs between alternatives
6. Provide clear, actionable recommendations
7. Rate confidence in recommendations

Methodology:
- Use multi-criteria decision analysis
- Compare alternatives against each criterion
- Quantify trade-offs where possible
- Identify hidden risks and opportunities
- Consider short and long-term impacts
- Provide clear decision rationale

Output Format:
- Decision criteria with importance weights
- Alternative evaluation matrix
- Risk assessment
- Recommendation with justification
- Confidence level for recommendation"""

    def execute(self, prompt: str, context: Optional[Dict] = None) -> SkillResult:
        """Execute decision analysis on given problem.

        Args:
            prompt: Decision problem statement
            context: Optional context (stakeholders, constraints, etc.)

        Returns:
            SkillResult with decision analysis
        """
        is_valid, error_msg = self.validate_input(prompt)
        if not is_valid:
            return self._handle_execution_error(ValueError(error_msg))

        start_time = time.time()

        try:
            # Extract context if provided
            stakeholders = context.get("stakeholders", []) if context else []
            constraints = context.get("constraints", []) if context else []

            # Build decision analysis prompt
            analysis_prompt = self._build_decision_context(
                prompt, stakeholders, constraints
            )

            # Run ToT search for decision analysis
            tot_result = self._run_tot_search(analysis_prompt)

            # Convert to skill result
            execution_time = time.time() - start_time
            result = self._convert_tot_result_to_skill_result(tot_result, execution_time)

            # Store execution history
            self.execution_history.append({
                "timestamp": time.time(),
                "decision_problem": prompt,
                "stakeholders_count": len(stakeholders),
                "recommendation": result.output[:100] if result.output else None,
            })

            self.current_result = result

            # Persist if enabled
            if self.config.persist_results:
                self._persist_result(result)

            return result

        except Exception as e:
            logger.error(f"Error in decision analysis: {e}")
            return self._handle_execution_error(e)

    def _build_decision_context(
        self, prompt: str, stakeholders: List[str], constraints: List[str]
    ) -> str:
        """Build decision analysis context.

        Args:
            prompt: Original decision problem
            stakeholders: List of stakeholders to consider
            constraints: List of constraints

        Returns:
            Enhanced decision analysis prompt
        """
        context = f"Decision Problem:\n{prompt}\n"

        if stakeholders:
            context += f"\nKey Stakeholders:\n"
            for stakeholder in stakeholders[:5]:
                context += f"- {stakeholder}\n"

        if constraints:
            context += f"\nConstraints:\n"
            for constraint in constraints[:5]:
                context += f"- {constraint}\n"

        return context

    def _identify_decision_criteria(self, analysis: str) -> Dict[str, float]:
        """Identify and extract decision criteria from analysis.

        Args:
            analysis: Decision analysis text

        Returns:
            Dictionary of criteria and weights
        """
        criteria = {}

        # Common decision criteria
        criterion_keywords = {
            "cost": 0.2,
            "risk": 0.2,
            "feasibility": 0.15,
            "impact": 0.15,
            "timeline": 0.1,
            "quality": 0.1,
            "sustainability": 0.1,
        }

        for criterion, default_weight in criterion_keywords.items():
            if criterion.lower() in analysis.lower():
                criteria[criterion] = default_weight

        # Normalize weights
        if criteria:
            total = sum(criteria.values())
            criteria = {k: v / total for k, v in criteria.items()}

        return criteria

    def _assess_decision_risks(self, analysis: str) -> Dict:
        """Assess risks in decision alternatives.

        Args:
            analysis: Decision analysis text

        Returns:
            Risk assessment dictionary
        """
        risks = {
            "identified_risks": [],
            "risk_level": "unknown",
            "confidence": 0.5,
        }

        # Risk level indicators
        high_risk_indicators = [
            "high risk", "dangerous", "critical", "severe",
            "catastrophic", "irreversible"
        ]
        medium_risk_indicators = [
            "moderate risk", "concern", "caution", "potential issue",
            "challenging", "significant"
        ]
        low_risk_indicators = [
            "low risk", "minimal", "manageable", "controllable"
        ]

        analysis_lower = analysis.lower()

        if any(indicator in analysis_lower for indicator in high_risk_indicators):
            risks["risk_level"] = "high"
            risks["confidence"] = 0.85
        elif any(indicator in analysis_lower for indicator in medium_risk_indicators):
            risks["risk_level"] = "medium"
            risks["confidence"] = 0.75
        elif any(indicator in analysis_lower for indicator in low_risk_indicators):
            risks["risk_level"] = "low"
            risks["confidence"] = 0.80

        return risks

    def _evaluate_alternatives(self, analysis: str) -> List[Tuple[str, float]]:
        """Extract and evaluate decision alternatives.

        Args:
            analysis: Decision analysis text

        Returns:
            List of (alternative, score) tuples
        """
        alternatives = []

        # Look for alternative indicators
        lines = analysis.split("\n")
        for line in lines:
            if any(
                marker in line.lower()
                for marker in ["option", "alternative", "choice"]
            ):
                alternatives.append((line.strip(), 0.5))

        return alternatives[:5]

    def _generate_recommendation(self, analysis: str) -> Tuple[str, float]:
        """Generate recommendation from analysis.

        Args:
            analysis: Decision analysis text

        Returns:
            Tuple of (recommendation, confidence)
        """
        # Look for recommendation indicators
        recommendation_indicators = [
            "recommend", "suggest", "best option", "best choice",
            "most suitable", "optimal", "preferable"
        ]

        recommendation = "Unable to generate clear recommendation"
        confidence = 0.5

        analysis_lower = analysis.lower()

        if any(indicator in analysis_lower for indicator in recommendation_indicators):
            recommendation = analysis[:200] if analysis else recommendation
            confidence = 0.75

        return recommendation, confidence

    def get_decision_summary(self) -> Dict:
        """Get summary of decision analysis.

        Returns:
            Dictionary with decision summary
        """
        return {
            "criteria_analyzed": len(self.criteria_analyzed),
            "risks_identified": len(self.risks_identified),
            "alternatives_evaluated": len(self.alternatives_evaluated),
            "recommendations_made": len(self.recommendations),
            "execution_history": len(self.execution_history),
            "last_decision": self.current_result.to_dict() if self.current_result else None,
        }
