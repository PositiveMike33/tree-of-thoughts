"""
Claude Code Skill Wrapper for Tree of Thoughts Skills.

Exposes Tree of Thoughts skills as CLI commands with real-time optimization.
"""

import logging
import json
from typing import Dict, Optional, Any, Type
from pathlib import Path

from .skills_manager import SkillsManagementSystem
from .skill_config import SkillConfig, SkillType, AlgorithmType, get_default_config
from .base_skill import BaseSkill, SkillResult
from .code_reviewer import CodeReviewer
from .decision_maker import DecisionMaker
from .expert_simulator import ExpertSimulator
from .problem_solver import ProblemSolver
from .research_analyst import ResearchAnalyst
from .thesis_validator import ThesisValidator

logger = logging.getLogger(__name__)


class SkillWrapper:
    """Wrapper for exposing ToT skills as Claude Code skills."""

    # Mapping of skill types to skill classes
    SKILL_CLASSES: Dict[SkillType, Type[BaseSkill]] = {
        SkillType.CODE_REVIEW: CodeReviewer,
        SkillType.DECISION: DecisionMaker,
        SkillType.EXPERT: ExpertSimulator,
        SkillType.PROBLEM: ProblemSolver,
        SkillType.RESEARCH: ResearchAnalyst,
        SkillType.THESIS: ThesisValidator,
    }

    def __init__(
        self,
        user_id: str = "default",
        config_dir: Optional[Path] = None,
        llm_model: Optional[Any] = None,
    ):
        """Initialize skill wrapper.

        Args:
            user_id: User identifier
            config_dir: Configuration directory
            llm_model: LLM model instance
        """
        self.user_id = user_id
        self.llm_model = llm_model
        self.skills_manager = SkillsManagementSystem(
            user_id=user_id,
            config_dir=config_dir,
            enable_persistence=True,
        )

        # Initialize default skills
        self._initialize_default_skills()

    def _initialize_default_skills(self) -> None:
        """Initialize all default skills with their configurations."""
        for skill_type, skill_class in self.SKILL_CLASSES.items():
            config = get_default_config(skill_type)
            self.skills_manager.register_skill(skill_type, config, force=True)
            logger.info(f"Initialized skill: {skill_type.value}")

    # ========================================================================
    # SKILL EXECUTION
    # ========================================================================

    def execute_skill(
        self,
        skill_type: SkillType,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        apply_optimizations: bool = True,
    ) -> Dict[str, Any]:
        """Execute a skill with real-time optimization.

        Args:
            skill_type: Type of skill to execute
            prompt: Input prompt/question
            context: Optional execution context
            apply_optimizations: Whether to apply pending optimizations

        Returns:
            Dictionary with result and metadata
        """
        config = self.skills_manager.get_skill_config(skill_type)
        if not config:
            return {
                "success": False,
                "error": f"Skill {skill_type.value} not initialized",
            }

        try:
            # Apply pending optimizations
            if apply_optimizations:
                recommendations = self.skills_manager.process_real_time_data()
                self._apply_recommendations(recommendations)

            # Create skill instance
            skill_class = self.SKILL_CLASSES.get(skill_type)
            if not skill_class:
                return {
                    "success": False,
                    "error": f"Skill class not found for {skill_type.value}",
                }

            skill = skill_class(config=config, llm_model=self.llm_model)

            # Execute skill
            result = skill.execute(prompt=prompt, context=context)

            # Record execution
            self.skills_manager.record_execution(skill_type, result, context)

            # Get optimization recommendations
            recommendations = self.skills_manager.process_real_time_data()

            return {
                "success": True,
                "result": result.to_dict(),
                "metrics": self.skills_manager.get_skill_metrics(skill_type).to_dict(),
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"Error executing skill {skill_type.value}: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # ========================================================================
    # SKILL MANAGEMENT
    # ========================================================================

    def get_skill_status(self, skill_type: Optional[SkillType] = None) -> Dict[str, Any]:
        """Get status of skill(s).

        Args:
            skill_type: Specific skill type, or None for all skills

        Returns:
            Dictionary with skill status and metrics
        """
        if skill_type:
            skill_types = [skill_type]
        else:
            skill_types = list(SkillType)

        status = {}
        for st in skill_types:
            config = self.skills_manager.get_skill_config(st)
            metrics = self.skills_manager.get_skill_metrics(st)

            status[st.value] = {
                "name": config.name if config else "Not initialized",
                "algorithm": config.algorithm.value if config else None,
                "status": "initialized" if config else "not_initialized",
                "metrics": metrics.to_dict() if metrics else None,
            }

        return status

    def update_skill_config(
        self,
        skill_type: SkillType,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update skill configuration.

        Args:
            skill_type: Type of skill
            updates: Configuration updates

        Returns:
            Status dictionary
        """
        success, msg = self.skills_manager.update_skill_config(skill_type, updates)
        return {
            "success": success,
            "message": msg,
            "updated_config": self.skills_manager.get_skill_config(skill_type).to_dict() if success else None,
        }

    def switch_algorithm(
        self,
        skill_type: SkillType,
        algorithm: AlgorithmType,
    ) -> Dict[str, Any]:
        """Switch algorithm for a skill.

        Args:
            skill_type: Type of skill
            algorithm: New algorithm type

        Returns:
            Status dictionary
        """
        return self.update_skill_config(skill_type, {"algorithm": algorithm})

    # ========================================================================
    # OPTIMIZATION & RECOMMENDATIONS
    # ========================================================================

    def get_optimization_status(self) -> Dict[str, Any]:
        """Get optimization status and recommendations.

        Returns:
            Dictionary with optimization data
        """
        recommendations = self.skills_manager.process_real_time_data()
        summary = self.skills_manager.get_optimization_summary()

        return {
            "pending_recommendations": recommendations,
            "optimization_summary": summary,
            "skills_optimized": len(summary["skills_optimized"]),
            "total_optimizations": summary["total_optimizations"],
        }

    def apply_recommendations(self, apply_all: bool = False) -> Dict[str, Any]:
        """Apply optimization recommendations.

        Args:
            apply_all: Whether to apply all recommendations

        Returns:
            Status dictionary
        """
        recommendations = self.skills_manager.process_real_time_data()
        applied = []
        failed = []

        for rec in recommendations:
            if not apply_all:
                # Only apply automatic recommendations
                if not rec.get("action"):
                    continue

            try:
                skill_type = SkillType(rec["skill_type"])
                action = rec.get("action", {})
                parameter = action.get("parameter")
                new_value = action.get("new_value")

                if parameter and new_value is not None:
                    success, msg = self.skills_manager.apply_optimization(
                        skill_type, parameter, new_value
                    )
                    if success:
                        applied.append(rec)
                    else:
                        failed.append((rec, msg))

            except Exception as e:
                logger.error(f"Failed to apply recommendation: {e}")
                failed.append((rec, str(e)))

        return {
            "applied": len(applied),
            "failed": len(failed),
            "applied_recommendations": applied,
            "failed_recommendations": failed,
        }

    def _apply_recommendations(self, recommendations: list) -> None:
        """Automatically apply safe recommendations.

        Args:
            recommendations: List of optimization recommendations
        """
        for rec in recommendations:
            try:
                # Only apply low-risk optimizations automatically
                if rec.get("type") not in ["low_confidence", "slow_execution"]:
                    continue

                skill_type = SkillType(rec["skill_type"])
                action = rec.get("action", {})
                parameter = action.get("parameter")
                new_value = action.get("new_value")

                if parameter and new_value is not None:
                    self.skills_manager.apply_optimization(
                        skill_type, parameter, new_value
                    )

            except Exception as e:
                logger.debug(f"Failed to apply auto-optimization: {e}")

    # ========================================================================
    # PERSISTENCE
    # ========================================================================

    def export_state(self) -> Dict[str, Any]:
        """Export complete system state."""
        return self.skills_manager.export_system_state()

    def import_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Import system state.

        Args:
            state: System state dictionary

        Returns:
            Status dictionary
        """
        success, msg = self.skills_manager.import_system_state(state)
        return {
            "success": success,
            "message": msg,
        }

    def save_state(self) -> None:
        """Save system state to disk."""
        self.skills_manager.save_profile()

    # ========================================================================
    # CLI INTERFACE
    # ========================================================================

    def cli_list_skills(self) -> str:
        """CLI: List all available skills."""
        status = self.get_skill_status()
        lines = ["Available Skills:\n"]
        for skill_name, skill_info in status.items():
            lines.append(f"  • {skill_info['name']} ({skill_name})")
            if skill_info["metrics"]:
                metrics = skill_info["metrics"]
                lines.append(f"    - Algorithm: {skill_info['algorithm']}")
                lines.append(f"    - Avg Confidence: {metrics['avg_confidence']:.2%}")
                lines.append(f"    - Executions: {metrics['total_executions']}")
        return "\n".join(lines)

    def cli_optimize(self) -> str:
        """CLI: Get and apply optimizations."""
        opt_status = self.get_optimization_status()
        lines = ["Optimization Status:\n"]

        if not opt_status["pending_recommendations"]:
            lines.append("✓ All skills performing optimally")
        else:
            lines.append(f"Found {len(opt_status['pending_recommendations'])} optimization opportunities:\n")
            for rec in opt_status["pending_recommendations"]:
                lines.append(f"  • {rec['skill_type']}: {rec['type']}")
                lines.append(f"    Suggestion: {rec['suggestion']}")

        lines.append(f"\nTotal optimizations applied: {opt_status['total_optimizations']}")
        return "\n".join(lines)

    def cli_skill_metrics(self, skill_name: str) -> str:
        """CLI: Get metrics for a specific skill."""
        try:
            skill_type = SkillType(skill_name.lower())
            metrics = self.skills_manager.get_skill_metrics(skill_type)

            if not metrics:
                return f"No metrics available for {skill_name}"

            lines = [f"Metrics for {skill_name}:\n"]
            lines.append(f"  • Executions: {metrics.total_executions}")
            lines.append(f"  • Avg Time: {metrics.avg_execution_time:.2f}s")
            lines.append(f"  • Avg Confidence: {metrics.avg_confidence:.2%}")
            lines.append(f"  • Trending Confidence: {metrics.trending_confidence:.2%}")
            lines.append(f"  • Human Review Rate: {metrics.human_review_rate:.2%}")
            lines.append(f"  • Last Updated: {metrics.last_updated}")

            return "\n".join(lines)

        except ValueError:
            return f"Unknown skill: {skill_name}"

    def cli_execute(
        self,
        skill_name: str,
        prompt: str,
    ) -> str:
        """CLI: Execute a skill.

        Args:
            skill_name: Name of skill to execute
            prompt: Input prompt

        Returns:
            Formatted result string
        """
        try:
            skill_type = SkillType(skill_name.lower())
            result = self.execute_skill(skill_type, prompt)

            if not result["success"]:
                return f"Error: {result.get('error', 'Unknown error')}"

            skill_result = result["result"]
            lines = [
                f"Result from {skill_name}:\n",
                f"Output:\n{skill_result['output']}\n",
                f"Confidence: {skill_result['confidence_level']} ({skill_result['confidence_score']:.2%})",
                f"Execution Time: {skill_result['execution_time']:.2f}s",
            ]

            if result["recommendations"]:
                lines.append("\nOptimization Suggestions:")
                for rec in result["recommendations"]:
                    lines.append(f"  • {rec['suggestion']}")

            return "\n".join(lines)

        except ValueError:
            return f"Unknown skill: {skill_name}"
        except Exception as e:
            return f"Error executing skill: {e}"
