"""Research Analyst skill for comprehensive research and analysis tasks."""

import logging
import time
from typing import Dict, Optional, Tuple

from .skill_config import SkillConfig, SkillType, AlgorithmType
from .base_skill import BaseSkill, SkillResult
from .skill_utils import merge_confidence_scores, apply_confidence_penalty
from ..tot_integration import VaultAwareLanguageModel
from ..tree_of_thoughts_vault_integration import ObsidianVaultIntegration

logger = logging.getLogger(__name__)


class ResearchAnalyst(BaseSkill):
    """
    Research Analyst skill for conducting deep research and analysis.

    Specializes in:
    - Comprehensive topic analysis
    - Source validation and fact-checking
    - Pattern identification across sources
    - Synthesis of complex information
    - Confidence calibration through multi-source validation

    Uses A* algorithm by default for optimal path finding through research space.
    """

    def __init__(
        self,
        config: Optional[SkillConfig] = None,
        llm_model: Optional[VaultAwareLanguageModel] = None,
        vault: Optional[ObsidianVaultIntegration] = None,
    ):
        """Initialize Research Analyst skill.

        Args:
            config: Skill configuration (uses research defaults if not provided)
            llm_model: Language model for research generation
            vault: Vault integration for persistence
        """
        if config is None:
            config = SkillConfig(
                skill_type=SkillType.RESEARCH,
                algorithm=AlgorithmType.A_STAR,
                name="Research Analyst",
                description="Conduct comprehensive research and analysis",
                num_thoughts=8,
                max_steps=7,
                confidence_threshold=0.75,
            )

        super().__init__(config, llm_model, vault)

        # Research-specific state
        self.sources_consulted = []
        self.key_findings = []
        self.contradictions_found = []

    def validate_input(self, prompt: str) -> Tuple[bool, str]:
        """Validate research query input.

        Args:
            prompt: Research query to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not prompt or not isinstance(prompt, str):
            return False, "Research prompt must be a non-empty string"

        if len(prompt) < 10:
            return False, "Research prompt should be at least 10 characters"

        if len(prompt) > 2000:
            return False, "Research prompt exceeds maximum length (2000 chars)"

        # Check for basic research keywords
        research_keywords = [
            "research", "analyze", "investigate", "study", "examine",
            "evaluate", "assess", "review", "investigate", "explore",
            "understand", "explain", "why", "how", "what"
        ]
        has_research_intent = any(
            keyword in prompt.lower() for keyword in research_keywords
        )

        if not has_research_intent:
            return False, "Prompt should contain research-oriented language"

        return True, ""

    def build_system_prompt(self) -> str:
        """Build system prompt for research analyst.

        Returns:
            System prompt for research tasks
        """
        return """You are a Research Analyst specializing in comprehensive analysis.

Your responsibilities:
1. Conduct thorough research on the given topic
2. Identify credible sources and validate information
3. Synthesize findings from multiple perspectives
4. Identify contradictions and areas of uncertainty
5. Provide confidence assessments for each finding
6. Recommend further research directions

Approach:
- Start broad, then narrow to specific aspects
- Cross-reference information from multiple sources
- Highlight areas of consensus and disagreement
- Note limitations and areas requiring further study
- Provide actionable insights based on findings

Format findings clearly with source attribution and confidence levels."""

    def execute(self, prompt: str, context: Optional[Dict] = None) -> SkillResult:
        """Execute research analysis on given prompt.

        Args:
            prompt: Research query
            context: Optional context for research (e.g., domain, sources)

        Returns:
            SkillResult with research findings
        """
        is_valid, error_msg = self.validate_input(prompt)
        if not is_valid:
            return self._handle_execution_error(ValueError(error_msg))

        start_time = time.time()

        try:
            # Extract context if provided
            domain = context.get("domain", "general") if context else "general"
            sources = context.get("sources", []) if context else []

            # Build research prompt
            research_context = self._build_research_context(prompt, domain, sources)

            # Run ToT search for research
            tot_result = self._run_tot_search(research_context)

            # Convert to skill result
            execution_time = time.time() - start_time
            result = self._convert_tot_result_to_skill_result(tot_result, execution_time)

            # Store execution history
            self.execution_history.append({
                "timestamp": time.time(),
                "prompt": prompt,
                "domain": domain,
                "result_confidence": result.confidence_score,
            })

            self.current_result = result

            # Persist if enabled
            if self.config.persist_results:
                self._persist_result(result)

            return result

        except Exception as e:
            logger.error(f"Error in research execution: {e}")
            return self._handle_execution_error(e)

    def _build_research_context(
        self, prompt: str, domain: str, sources: list
    ) -> str:
        """Build research context with domain information.

        Args:
            prompt: Original research query
            domain: Research domain/field
            sources: List of suggested sources

        Returns:
            Enhanced research prompt with context
        """
        context = f"""Research Domain: {domain}
Research Query: {prompt}"""

        if sources:
            context += f"\nSuggested Sources/References:\n"
            for source in sources[:5]:  # Limit to 5 sources
                context += f"- {source}\n"

        return context

    def _validate_research_findings(self, findings: str) -> Dict:
        """Validate research findings.

        Args:
            findings: Research findings text

        Returns:
            Validation results dictionary
        """
        issues = []
        confidence_adjustments = []

        # Check for citation count
        citation_count = findings.count("[") + findings.count("(source:")
        if citation_count == 0:
            issues.append("No citations found in research")
            confidence_adjustments.append(-0.1)

        # Check for contradiction markers
        contradiction_markers = [
            "contradicts", "conflicts with", "contrasts with",
            "however", "on the other hand", "conversely"
        ]
        has_contradictions = any(
            marker in findings.lower() for marker in contradiction_markers
        )
        if has_contradictions:
            self.contradictions_found.append(findings[:100])

        # Check for evidence of multiple perspectives
        perspective_markers = ["research shows", "studies indicate", "experts argue"]
        has_multiple_perspectives = sum(
            findings.lower().count(marker) for marker in perspective_markers
        ) >= 2

        if not has_multiple_perspectives:
            issues.append("Limited evidence of multiple perspectives")
            confidence_adjustments.append(-0.05)

        # Compile validation result
        base_confidence = 0.80
        for adjustment in confidence_adjustments:
            base_confidence += adjustment

        base_confidence = max(0.0, min(1.0, base_confidence))

        return {
            "is_valid": len(issues) <= 2,
            "confidence": base_confidence,
            "issues": issues,
            "has_contradictions": has_contradictions,
            "perspective_count": sum(
                findings.lower().count(marker) for marker in perspective_markers
            ),
        }

    def _extract_key_findings(self, research_output: str) -> list:
        """Extract key findings from research output.

        Args:
            research_output: Full research text

        Returns:
            List of key findings
        """
        findings = []

        # Split by common finding markers
        markers = ["finding:", "result:", "key insight:", "-"]
        lines = research_output.split("\n")

        for line in lines:
            line = line.strip()
            if any(marker in line.lower() for marker in markers) and len(line) > 10:
                findings.append(line)

        return findings[:5]  # Return top 5 findings

    def get_research_summary(self) -> Dict:
        """Get summary of research findings.

        Returns:
            Dictionary with research summary
        """
        return {
            "sources_consulted": len(self.sources_consulted),
            "key_findings_count": len(self.key_findings),
            "contradictions_found": len(self.contradictions_found),
            "execution_history": len(self.execution_history),
            "last_result": self.current_result.to_dict() if self.current_result else None,
        }
