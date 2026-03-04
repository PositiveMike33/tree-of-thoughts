"""
CLI Handlers for Tree of Thoughts Skills.

Individual CLI commands for each skill with Claude Code integration.
"""

import logging
import json
import sys
from typing import Optional, Dict, Any
from pathlib import Path

from .skill_wrapper import SkillWrapper
from .skill_config import SkillType, AlgorithmType

logger = logging.getLogger(__name__)


class SkillCLIHandler:
    """Handler for skill CLI commands."""

    def __init__(self, skill_type: SkillType):
        """Initialize CLI handler for a skill.

        Args:
            skill_type: Type of skill to handle
        """
        self.skill_type = skill_type
        self.wrapper = SkillWrapper(user_id="claude-code")

    def execute(
        self,
        prompt: str,
        context: Optional[str] = None,
        algorithm: Optional[str] = None,
    ) -> str:
        """Execute the skill.

        Args:
            prompt: Input prompt/question
            context: Optional context as JSON string
            algorithm: Optional algorithm override

        Returns:
            Formatted result string
        """
        try:
            # Parse context if provided
            ctx = {}
            if context:
                try:
                    ctx = json.loads(context)
                except json.JSONDecodeError:
                    ctx = {"raw_context": context}

            # Override algorithm if specified
            if algorithm:
                try:
                    algo = AlgorithmType(algorithm.lower())
                    self.wrapper.switch_algorithm(self.skill_type, algo)
                except ValueError:
                    return f"Invalid algorithm: {algorithm}"

            # Execute skill
            result = self.wrapper.execute_skill(self.skill_type, prompt, ctx)

            if not result["success"]:
                return f"❌ Error: {result.get('error', 'Unknown error')}"

            # Format output
            return self._format_result(result)

        except Exception as e:
            logger.error(f"Error executing {self.skill_type.value}: {e}")
            return f"❌ Execution failed: {e}"

    def status(self) -> str:
        """Get skill status."""
        try:
            status = self.wrapper.get_skill_status(self.skill_type)
            skill_status = status.get(self.skill_type.value, {})

            lines = [f"📊 Status: {skill_status['name']}\n"]
            lines.append(f"  Algorithm: {skill_status.get('algorithm', 'N/A')}")

            if skill_status.get("metrics"):
                metrics = skill_status["metrics"]
                lines.append(f"  Executions: {metrics['total_executions']}")
                lines.append(f"  Avg Confidence: {metrics['avg_confidence']:.1%}")
                lines.append(f"  Avg Time: {metrics['avg_execution_time']:.2f}s")
                lines.append(f"  Trending: {metrics['trending_confidence']:.1%}")

            return "\n".join(lines)

        except Exception as e:
            return f"❌ Failed to get status: {e}"

    def optimize(self) -> str:
        """Get optimization status and suggestions."""
        try:
            opt_status = self.wrapper.get_optimization_status()
            relevant_recs = [
                r for r in opt_status["pending_recommendations"]
                if r["skill_type"] == self.skill_type.value
            ]

            if not relevant_recs:
                return f"✓ {self.skill_type.value} is performing optimally"

            lines = [f"🔧 Optimization Suggestions for {self.skill_type.value}:\n"]
            for rec in relevant_recs:
                lines.append(f"  • {rec['type']}: {rec['suggestion']}")

            return "\n".join(lines)

        except Exception as e:
            return f"❌ Failed to get optimizations: {e}"

    def config(self, parameter: Optional[str] = None, value: Optional[str] = None) -> str:
        """Get or update configuration.

        Args:
            parameter: Config parameter to update
            value: New value for parameter

        Returns:
            Formatted config string
        """
        try:
            if parameter and value is not None:
                # Update config
                result = self.wrapper.update_skill_config(
                    self.skill_type,
                    {parameter: json.loads(value) if value.startswith("[{") else value}
                )

                if result["success"]:
                    return f"✓ Updated {parameter} = {value}"
                else:
                    return f"❌ {result['message']}"

            # Show current config
            config = self.wrapper.skills_manager.get_skill_config(self.skill_type)
            lines = [f"⚙️  Configuration for {self.skill_type.value}:\n"]

            if config:
                config_dict = config.to_dict()
                for key, val in config_dict.items():
                    if not key.startswith("_"):
                        lines.append(f"  {key}: {val}")

            return "\n".join(lines)

        except Exception as e:
            return f"❌ Failed to manage config: {e}"

    def _format_result(self, result: Dict[str, Any]) -> str:
        """Format execution result for display.

        Args:
            result: Skill execution result

        Returns:
            Formatted string
        """
        skill_result = result.get("result", {})
        recommendations = result.get("recommendations", [])

        lines = [
            f"✨ {self.skill_type.value.upper()} Result:\n",
            f"{skill_result.get('output', 'N/A')}\n",
        ]

        # Add confidence info
        confidence = skill_result.get("confidence_score", 0)
        level = skill_result.get("confidence_level", "UNKNOWN")
        lines.append(f"📈 Confidence: {level} ({confidence:.1%})")
        lines.append(f"⏱️  Execution Time: {skill_result.get('execution_time', 0):.2f}s")

        # Add recommendations
        if recommendations:
            lines.append("\n🔧 Optimization Opportunities:")
            for rec in recommendations:
                lines.append(f"  • {rec.get('type', 'unknown')}: {rec.get('suggestion', 'N/A')}")

        # Add review flag
        if skill_result.get("requires_human_review"):
            lines.append("\n⚠️  Requires human review")

        return "\n".join(lines)


# ============================================================================
# Individual Skill Handlers
# ============================================================================

class CodeReviewerCLI(SkillCLIHandler):
    """CLI for Code Reviewer skill."""

    def __init__(self):
        super().__init__(SkillType.CODE_REVIEW)

    def execute(
        self,
        prompt: str,
        file_path: Optional[str] = None,
        algorithm: Optional[str] = None,
    ) -> str:
        """Execute code review.

        Args:
            prompt: Review prompt
            file_path: Optional file to review
            algorithm: Optional algorithm override

        Returns:
            Formatted result
        """
        context = {}
        if file_path:
            try:
                context["file_path"] = file_path
                context["file_content"] = Path(file_path).read_text()
            except Exception as e:
                return f"❌ Failed to read file: {e}"

        return super().execute(prompt, json.dumps(context), algorithm)


class DecisionMakerCLI(SkillCLIHandler):
    """CLI for Decision Maker skill."""

    def __init__(self):
        super().__init__(SkillType.DECISION)

    def execute(
        self,
        prompt: str,
        options: Optional[str] = None,
        algorithm: Optional[str] = None,
    ) -> str:
        """Execute decision analysis.

        Args:
            prompt: Decision prompt
            options: Decision options as JSON array
            algorithm: Optional algorithm override

        Returns:
            Formatted result
        """
        context = {}
        if options:
            try:
                context["options"] = json.loads(options)
            except json.JSONDecodeError:
                return f"❌ Invalid options JSON: {options}"

        return super().execute(prompt, json.dumps(context), algorithm)


class ResearchAnalystCLI(SkillCLIHandler):
    """CLI for Research Analyst skill."""

    def __init__(self):
        super().__init__(SkillType.RESEARCH)

    def execute(
        self,
        prompt: str,
        sources: Optional[str] = None,
        algorithm: Optional[str] = None,
    ) -> str:
        """Execute research analysis.

        Args:
            prompt: Research prompt
            sources: Known sources as JSON array
            algorithm: Optional algorithm override

        Returns:
            Formatted result
        """
        context = {}
        if sources:
            try:
                context["known_sources"] = json.loads(sources)
            except json.JSONDecodeError:
                return f"❌ Invalid sources JSON: {sources}"

        return super().execute(prompt, json.dumps(context), algorithm)


class ProblemSolverCLI(SkillCLIHandler):
    """CLI for Problem Solver skill."""

    def __init__(self):
        super().__init__(SkillType.PROBLEM)

    def execute(
        self,
        prompt: str,
        constraints: Optional[str] = None,
        algorithm: Optional[str] = None,
    ) -> str:
        """Execute problem solving.

        Args:
            prompt: Problem statement
            constraints: Problem constraints as JSON
            algorithm: Optional algorithm override

        Returns:
            Formatted result
        """
        context = {}
        if constraints:
            try:
                context["constraints"] = json.loads(constraints)
            except json.JSONDecodeError:
                return f"❌ Invalid constraints JSON: {constraints}"

        return super().execute(prompt, json.dumps(context), algorithm)


class ThesisValidatorCLI(SkillCLIHandler):
    """CLI for Thesis Validator skill."""

    def __init__(self):
        super().__init__(SkillType.THESIS)

    def execute(
        self,
        prompt: str,
        evidence: Optional[str] = None,
        algorithm: Optional[str] = None,
    ) -> str:
        """Execute thesis validation.

        Args:
            prompt: Thesis statement
            evidence: Supporting evidence as JSON
            algorithm: Optional algorithm override

        Returns:
            Formatted result
        """
        context = {}
        if evidence:
            try:
                context["evidence"] = json.loads(evidence)
            except json.JSONDecodeError:
                return f"❌ Invalid evidence JSON: {evidence}"

        return super().execute(prompt, json.dumps(context), algorithm)


class ExpertSimulatorCLI(SkillCLIHandler):
    """CLI for Expert Simulator skill."""

    def __init__(self):
        super().__init__(SkillType.EXPERT)

    def execute(
        self,
        prompt: str,
        expertise: Optional[str] = None,
        algorithm: Optional[str] = None,
    ) -> str:
        """Execute expert simulation.

        Args:
            prompt: Question for expert
            expertise: Domain of expertise
            algorithm: Optional algorithm override

        Returns:
            Formatted result
        """
        context = {}
        if expertise:
            context["expertise_domain"] = expertise

        return super().execute(prompt, json.dumps(context), algorithm)


# ============================================================================
# Factory
# ============================================================================

def get_cli_handler(skill_type: SkillType) -> SkillCLIHandler:
    """Factory function to get appropriate CLI handler.

    Args:
        skill_type: Type of skill

    Returns:
        Appropriate CLI handler instance
    """
    handlers = {
        SkillType.CODE_REVIEW: CodeReviewerCLI,
        SkillType.DECISION: DecisionMakerCLI,
        SkillType.RESEARCH: ResearchAnalystCLI,
        SkillType.PROBLEM: ProblemSolverCLI,
        SkillType.THESIS: ThesisValidatorCLI,
        SkillType.EXPERT: ExpertSimulatorCLI,
    }

    handler_class = handlers.get(skill_type, SkillCLIHandler)
    return handler_class()
