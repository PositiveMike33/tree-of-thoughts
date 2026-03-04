"""Expert Simulator skill for domain-expert reasoning and high-confidence recommendations."""

import logging
import time
from typing import Dict, Optional, Tuple, List

from .skill_config import SkillConfig, SkillType, AlgorithmType
from .base_skill import BaseSkill, SkillResult
from ..tot_integration import VaultAwareLanguageModel
from ..tree_of_thoughts_vault_integration import ObsidianVaultIntegration

logger = logging.getLogger(__name__)


class ExpertSimulator(BaseSkill):
    """
    Expert Simulator skill for domain-expert reasoning with high confidence.

    Specializes in:
    - Expert reasoning simulation
    - Domain knowledge application
    - Best practices validation
    - Expert-level recommendations
    - Domain-specific analysis
    - Confidence-based expert consensus

    Uses DFS with domain context for deep expert reasoning paths.
    """

    def __init__(
        self,
        config: Optional[SkillConfig] = None,
        llm_model: Optional[VaultAwareLanguageModel] = None,
        vault: Optional[ObsidianVaultIntegration] = None,
    ):
        """Initialize Expert Simulator skill.

        Args:
            config: Skill configuration (uses expert defaults if not provided)
            llm_model: Language model for expert reasoning
            vault: Vault integration for persistence
        """
        if config is None:
            config = SkillConfig(
                skill_type=SkillType.EXPERT,
                algorithm=AlgorithmType.DFS,
                name="Expert Simulator",
                description="Simulate expert reasoning with domain-specific knowledge",
                num_thoughts=8,
                max_steps=10,
                confidence_threshold=0.85,
            )

        super().__init__(config, llm_model, vault)

        # Expert-specific state
        self.expert_analyses_performed = []
        self.domain_insights = []
        self.expert_recommendations = []
        self.best_practices_applied = []

    def validate_input(self, prompt: str) -> Tuple[bool, str]:
        """Validate expert reasoning request.

        Args:
            prompt: Request for expert analysis

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not prompt or not isinstance(prompt, str):
            return False, "Expert request must be a non-empty string"

        if len(prompt) < 20:
            return False, "Expert request must be at least 20 characters"

        if len(prompt) > 3000:
            return False, "Expert request exceeds maximum length (3000 chars)"

        # Check for expert-oriented language
        expert_keywords = [
            "expert", "professional", "best practice", "industry",
            "standard", "recommendation", "advise", "guidance",
            "opinion", "perspective", "analysis", "how should",
            "what is the best", "what would", "technical expertise"
        ]
        has_expert_intent = any(
            keyword in prompt.lower() for keyword in expert_keywords
        )

        if not has_expert_intent:
            return False, "Request should seek expert advice or analysis"

        return True, ""

    def build_system_prompt(self) -> str:
        """Build system prompt for expert simulator.

        Returns:
            System prompt for expert reasoning
        """
        return """You are an expert reasoning system with deep domain knowledge.

Your expertise includes:
1. Industry best practices and standards
2. Domain-specific problem-solving approaches
3. Professional recommendations based on experience
4. Risk assessment and mitigation strategies
5. Competitive analysis and market insights
6. Technical depth and architectural understanding
7. Mentoring and guidance provision

Expert Analysis Framework:
- Problem understanding and domain context
- Best practice identification
- Industry standard application
- Risk and benefit analysis
- Strategic recommendations
- Implementation guidance
- Success factor identification

Expert Reasoning Process:
- Deep domain knowledge application
- Multiple perspective analysis
- Best practice validation
- Industry standard adherence
- Risk-aware recommendation
- Confidence assessment
- Clear reasoning explanation

Output Structure:
- Executive summary
- Domain analysis and insights
- Best practices applicable
- Expert recommendation with rationale
- Alternative approaches and trade-offs
- Risk factors and mitigation
- Success metrics and KPIs
- Confidence level and reasoning basis"""

    def execute(self, prompt: str, context: Optional[Dict] = None) -> SkillResult:
        """Execute expert reasoning on given request.

        Args:
            prompt: Request for expert analysis
            context: Optional context (domain, expertise_area, industry)

        Returns:
            SkillResult with expert analysis
        """
        is_valid, error_msg = self.validate_input(prompt)
        if not is_valid:
            return self._handle_execution_error(ValueError(error_msg))

        start_time = time.time()

        try:
            # Extract context if provided
            domain = context.get("domain", "general") if context else "general"
            expertise_area = context.get("expertise_area", "general") if context else "general"
            industry = context.get("industry", "general") if context else "general"

            # Build expert reasoning context
            expert_prompt = self._build_expert_context(
                prompt, domain, expertise_area, industry
            )

            # Run ToT search for expert reasoning
            tot_result = self._run_tot_search(expert_prompt)

            # Convert to skill result
            execution_time = time.time() - start_time
            result = self._convert_tot_result_to_skill_result(tot_result, execution_time)

            # Extract expert insights
            insights = self._extract_expert_insights(result.output)
            self.domain_insights.extend(insights)

            # Extract recommendations
            recommendation = self._extract_expert_recommendation(result.output)
            if recommendation:
                self.expert_recommendations.append(recommendation)

            # Store execution history
            self.execution_history.append({
                "timestamp": time.time(),
                "domain": domain,
                "expertise_area": expertise_area,
                "industry": industry,
                "result_confidence": result.confidence_score,
            })

            self.current_result = result

            # Persist if enabled
            if self.config.persist_results:
                self._persist_result(result)

            return result

        except Exception as e:
            logger.error(f"Error in expert reasoning: {e}")
            return self._handle_execution_error(e)

    def _build_expert_context(
        self, prompt: str, domain: str, expertise_area: str, industry: str
    ) -> str:
        """Build expert reasoning context.

        Args:
            prompt: Expert question or request
            domain: Domain of expertise
            expertise_area: Specific area of expertise
            industry: Industry context

        Returns:
            Enhanced expert prompt with context
        """
        context = f"""Domain: {domain}
Expertise Area: {expertise_area}
Industry: {industry}

Expert Question:
{prompt}
"""
        return context

    def _extract_expert_insights(self, analysis: str) -> List[str]:
        """Extract expert insights from analysis.

        Args:
            analysis: Expert analysis text

        Returns:
            List of key insights
        """
        insights = []

        insight_keywords = ["insight", "finding", "discovery", "pattern", "trend", "observation"]

        lines = analysis.split("\n")

        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in insight_keywords):
                if len(line.strip()) > 10:
                    insights.append(line.strip())

        return insights[:5]

    def _extract_expert_recommendation(self, analysis: str) -> Optional[str]:
        """Extract expert recommendation from analysis.

        Args:
            analysis: Expert analysis text

        Returns:
            Expert recommendation or None
        """
        recommendation_keywords = ["recommend", "advise", "suggest", "should", "best practice"]

        lines = analysis.split("\n")

        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in recommendation_keywords):
                if len(line.strip()) > 20:
                    return line.strip()

        return None

    def _validate_best_practices(self, analysis: str) -> Dict:
        """Validate best practices mentioned in analysis.

        Args:
            analysis: Expert analysis text

        Returns:
            Best practices validation result
        """
        validation = {
            "best_practices_identified": 0,
            "compliance_level": "unknown",
            "industry_standards_met": False,
        }

        practice_keywords = ["best practice", "standard", "guideline", "convention", "pattern"]

        practice_count = sum(
            1 for keyword in practice_keywords if keyword in analysis.lower()
        )

        validation["best_practices_identified"] = practice_count

        if "industry standard" in analysis.lower() or "follows best practice" in analysis.lower():
            validation["industry_standards_met"] = True
            validation["compliance_level"] = "high"
        elif practice_count > 0:
            validation["compliance_level"] = "medium"
        else:
            validation["compliance_level"] = "low"

        return validation

    def _assess_expert_confidence(self, analysis: str) -> float:
        """Assess confidence level of expert recommendation.

        Args:
            analysis: Expert analysis text

        Returns:
            Confidence score from 0.0 to 1.0
        """
        confidence = 0.5

        confidence_keywords = {
            "certain": 0.95,
            "confident": 0.90,
            "strong": 0.85,
            "recommend": 0.80,
            "likely": 0.70,
            "possible": 0.50,
            "uncertain": 0.30,
            "risky": 0.20,
        }

        analysis_lower = analysis.lower()

        for keyword, score in confidence_keywords.items():
            if keyword in analysis_lower:
                confidence = max(confidence, score)

        return max(0.0, min(1.0, confidence))

    def _identify_domain_expertise(self, analysis: str) -> Dict:
        """Identify domain expertise areas from analysis.

        Args:
            analysis: Expert analysis text

        Returns:
            Domain expertise assessment
        """
        expertise = {
            "expertise_areas": [],
            "depth_level": "general",
            "experience_indicators": 0,
        }

        experience_keywords = ["experience", "years of", "proven", "track record", "established"]

        experience_count = sum(
            1 for keyword in experience_keywords if keyword in analysis.lower()
        )

        expertise["experience_indicators"] = experience_count

        if experience_count > 2:
            expertise["depth_level"] = "deep"
        elif experience_count > 0:
            expertise["depth_level"] = "intermediate"

        return expertise

    def get_expert_summary(self) -> Dict:
        """Get summary of expert analyses.

        Returns:
            Dictionary with expert summary
        """
        return {
            "expert_analyses_performed": len(self.expert_analyses_performed),
            "domain_insights": len(self.domain_insights),
            "expert_recommendations": len(self.expert_recommendations),
            "best_practices_applied": len(self.best_practices_applied),
            "analyses_completed": len(self.execution_history),
            "last_expert_analysis": self.current_result.to_dict() if self.current_result else None,
        }
