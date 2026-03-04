"""
Centralized Skills Management System for Tree of Thoughts.

Orchestrates skill execution, optimization, real-time updates, and user evolution tracking.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime

from .skill_config import SkillConfig, SkillType, AlgorithmType
from .base_skill import SkillResult

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """Tracks user skill evolution and preferences."""

    user_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    skill_preferences: Dict[SkillType, Dict[str, Any]] = field(default_factory=dict)
    skill_performance: Dict[SkillType, List[float]] = field(default_factory=dict)
    algorithm_preferences: Dict[SkillType, AlgorithmType] = field(default_factory=dict)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    optimization_metrics: Dict[str, float] = field(default_factory=dict)
    confidence_trends: Dict[SkillType, List[float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            "user_id": self.user_id,
            "created_at": self.created_at,
            "skill_preferences": {k.value: v for k, v in self.skill_preferences.items()},
            "skill_performance": {k.value: v for k, v in self.skill_performance.items()},
            "algorithm_preferences": {k.value: v.value for k, v in self.algorithm_preferences.items()},
            "execution_history": self.execution_history,
            "optimization_metrics": self.optimization_metrics,
            "confidence_trends": {k.value: v for k, v in self.confidence_trends.items()},
        }


@dataclass
class SkillMetrics:
    """Real-time metrics for a skill."""

    skill_type: SkillType
    avg_execution_time: float = 0.0
    avg_confidence: float = 0.0
    total_executions: int = 0
    success_rate: float = 0.0
    human_review_rate: float = 0.0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    trending_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return asdict(self)


class SkillsManagementSystem:
    """Central system for managing all Tree of Thoughts skills."""

    def __init__(
        self,
        user_id: str,
        config_dir: Optional[Path] = None,
        enable_persistence: bool = True,
    ):
        """Initialize Skills Management System.

        Args:
            user_id: Unique user identifier
            config_dir: Directory for storing configurations and metrics
            enable_persistence: Whether to persist data to disk
        """
        self.user_id = user_id
        self.config_dir = config_dir or Path.home() / ".tot" / "skills"
        self.enable_persistence = enable_persistence

        # Create directories
        if self.enable_persistence:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.metrics_dir = self.config_dir / "metrics"
            self.metrics_dir.mkdir(exist_ok=True)

        # Initialize storage
        self.user_profile = self._load_or_create_profile()
        self.skill_metrics: Dict[SkillType, SkillMetrics] = {}
        self.skill_configs: Dict[SkillType, SkillConfig] = {}
        self.optimization_history: List[Dict[str, Any]] = []

        # Real-time data queue
        self.data_queue: List[Dict[str, Any]] = []
        self.processing_interval = 5  # seconds

        logger.info(f"Initialized SkillsManagementSystem for user: {user_id}")

    # ========================================================================
    # PROFILE MANAGEMENT
    # ========================================================================

    def _load_or_create_profile(self) -> UserProfile:
        """Load user profile or create new one."""
        if not self.enable_persistence:
            return UserProfile(user_id=self.user_id)

        profile_path = self.config_dir / f"{self.user_id}_profile.json"
        if profile_path.exists():
            try:
                data = json.loads(profile_path.read_text())
                return UserProfile(
                    user_id=data["user_id"],
                    created_at=data.get("created_at"),
                    skill_preferences={
                        SkillType(k): v for k, v in data.get("skill_preferences", {}).items()
                    },
                    execution_history=data.get("execution_history", []),
                )
            except Exception as e:
                logger.warning(f"Failed to load profile: {e}")

        return UserProfile(user_id=self.user_id)

    def save_profile(self) -> None:
        """Persist user profile to disk."""
        if not self.enable_persistence:
            return

        profile_path = self.config_dir / f"{self.user_id}_profile.json"
        try:
            profile_path.write_text(json.dumps(self.user_profile.to_dict(), indent=2))
            logger.debug(f"Profile saved: {profile_path}")
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")

    # ========================================================================
    # SKILL CONFIGURATION
    # ========================================================================

    def register_skill(
        self,
        skill_type: SkillType,
        config: SkillConfig,
        force: bool = False
    ) -> Tuple[bool, str]:
        """Register a skill with its configuration.

        Args:
            skill_type: Type of skill
            config: Skill configuration
            force: Whether to overwrite existing config

        Returns:
            Tuple of (success: bool, message: str)
        """
        if skill_type in self.skill_configs and not force:
            return False, f"Skill {skill_type.value} already registered"

        # Validate configuration
        is_valid, error = config.validate()
        if not is_valid:
            return False, f"Invalid config: {error}"

        self.skill_configs[skill_type] = config
        self.skill_metrics[skill_type] = SkillMetrics(skill_type=skill_type)

        logger.info(f"Registered skill: {skill_type.value}")
        return True, "Skill registered successfully"

    def get_skill_config(self, skill_type: SkillType) -> Optional[SkillConfig]:
        """Get configuration for a skill."""
        return self.skill_configs.get(skill_type)

    def update_skill_config(
        self,
        skill_type: SkillType,
        updates: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Update skill configuration with new parameters.

        Args:
            skill_type: Type of skill to update
            updates: Dictionary of parameters to update

        Returns:
            Tuple of (success: bool, message: str)
        """
        if skill_type not in self.skill_configs:
            return False, f"Skill {skill_type.value} not registered"

        config = self.skill_configs[skill_type]

        # Apply updates
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)

        # Validate
        is_valid, error = config.validate()
        if not is_valid:
            return False, f"Invalid config after update: {error}"

        logger.info(f"Updated config for {skill_type.value}: {updates}")
        return True, "Configuration updated successfully"

    # ========================================================================
    # SKILL EXECUTION TRACKING
    # ========================================================================

    def record_execution(
        self,
        skill_type: SkillType,
        result: SkillResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record skill execution for analysis and optimization.

        Args:
            skill_type: Type of skill executed
            result: SkillResult from execution
            context: Optional execution context
        """
        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "skill_type": skill_type.value,
            "execution_time": result.execution_time,
            "confidence_score": result.confidence_score,
            "confidence_level": result.confidence_level,
            "requires_review": result.requires_human_review,
            "context": context or {},
        }

        # Add to profile history
        self.user_profile.execution_history.append(execution_record)

        # Add to real-time queue for processing
        self.data_queue.append(execution_record)

        # Update metrics
        self._update_skill_metrics(skill_type, result)

        logger.debug(f"Recorded execution for {skill_type.value}")

    def _update_skill_metrics(
        self,
        skill_type: SkillType,
        result: SkillResult
    ) -> None:
        """Update real-time metrics for a skill."""
        if skill_type not in self.skill_metrics:
            self.skill_metrics[skill_type] = SkillMetrics(skill_type=skill_type)

        metrics = self.skill_metrics[skill_type]

        # Update metrics
        n = metrics.total_executions
        metrics.avg_execution_time = (
            (metrics.avg_execution_time * n + result.execution_time) / (n + 1)
        )
        metrics.avg_confidence = (
            (metrics.avg_confidence * n + result.confidence_score) / (n + 1)
        )
        metrics.total_executions += 1

        # Track confidence trends
        if skill_type not in self.user_profile.confidence_trends:
            self.user_profile.confidence_trends[skill_type] = []
        self.user_profile.confidence_trends[skill_type].append(result.confidence_score)

        # Calculate trending confidence (last 10 executions)
        trend_values = self.user_profile.confidence_trends[skill_type][-10:]
        metrics.trending_confidence = sum(trend_values) / len(trend_values)

        # Calculate success rate
        if result.requires_human_review:
            metrics.human_review_rate = (
                (metrics.human_review_rate * (n) + 1) / (n + 1)
            )

        metrics.last_updated = datetime.now().isoformat()

    # ========================================================================
    # REAL-TIME OPTIMIZATION
    # ========================================================================

    def process_real_time_data(self) -> List[Dict[str, Any]]:
        """Process accumulated real-time data for optimization.

        Returns:
            List of optimization recommendations
        """
        if not self.data_queue:
            return []

        recommendations = []

        # Analyze each skill's performance
        for skill_type in SkillType:
            skill_data = [
                d for d in self.data_queue
                if d["skill_type"] == skill_type.value
            ]

            if not skill_data:
                continue

            # Generate optimization recommendations
            recs = self._analyze_skill_performance(skill_type, skill_data)
            recommendations.extend(recs)

        # Clear processed data
        self.data_queue.clear()

        return recommendations

    def _analyze_skill_performance(
        self,
        skill_type: SkillType,
        executions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze skill performance and generate recommendations.

        Args:
            skill_type: Type of skill
            executions: List of execution records

        Returns:
            List of optimization recommendations
        """
        recommendations = []
        metrics = self.skill_metrics.get(skill_type)
        config = self.skill_configs.get(skill_type)

        if not metrics or not config:
            return recommendations

        # Analyze confidence trend
        confidence_scores = [e["confidence_score"] for e in executions]
        avg_confidence = sum(confidence_scores) / len(confidence_scores)

        if avg_confidence < 0.6:
            recommendations.append({
                "skill_type": skill_type.value,
                "type": "low_confidence",
                "current_value": avg_confidence,
                "suggestion": "Consider increasing max_steps or num_thoughts",
                "action": {
                    "parameter": "max_steps",
                    "new_value": min(config.max_steps + 2, 10)
                }
            })

        # Analyze execution time
        exec_times = [e["execution_time"] for e in executions]
        avg_time = sum(exec_times) / len(exec_times)

        if avg_time > config.timeout_seconds * 0.8:
            recommendations.append({
                "skill_type": skill_type.value,
                "type": "slow_execution",
                "current_value": avg_time,
                "suggestion": "Execution near timeout limit",
                "action": {
                    "parameter": "num_thoughts",
                    "new_value": max(config.num_thoughts - 1, 1)
                }
            })

        # Analyze review rate
        review_count = sum(1 for e in executions if e["requires_review"])
        review_rate = review_count / len(executions)

        if review_rate > 0.3:
            recommendations.append({
                "skill_type": skill_type.value,
                "type": "high_review_rate",
                "current_value": review_rate,
                "suggestion": "Many results need human review",
                "action": {
                    "parameter": "confidence_threshold",
                    "new_value": max(config.confidence_threshold - 0.1, 0.5)
                }
            })

        return recommendations

    def apply_optimization(
        self,
        skill_type: SkillType,
        parameter: str,
        new_value: Any
    ) -> Tuple[bool, str]:
        """Apply optimization to a skill.

        Args:
            skill_type: Type of skill
            parameter: Parameter to optimize
            new_value: New value for parameter

        Returns:
            Tuple of (success: bool, message: str)
        """
        success, msg = self.update_skill_config(
            skill_type,
            {parameter: new_value}
        )

        if success:
            # Record optimization
            opt_record = {
                "timestamp": datetime.now().isoformat(),
                "skill_type": skill_type.value,
                "parameter": parameter,
                "new_value": new_value,
            }
            self.optimization_history.append(opt_record)

            if self.enable_persistence:
                self._save_metrics()

        return success, msg

    # ========================================================================
    # METRICS & REPORTING
    # ========================================================================

    def get_skill_metrics(self, skill_type: SkillType) -> Optional[SkillMetrics]:
        """Get metrics for a specific skill."""
        return self.skill_metrics.get(skill_type)

    def get_all_metrics(self) -> Dict[SkillType, SkillMetrics]:
        """Get metrics for all registered skills."""
        return self.skill_metrics.copy()

    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of optimizations applied."""
        return {
            "total_optimizations": len(self.optimization_history),
            "history": self.optimization_history[-10:],  # Last 10
            "skills_optimized": list(set(
                h["skill_type"] for h in self.optimization_history
            )),
        }

    def _save_metrics(self) -> None:
        """Persist metrics to disk."""
        if not self.enable_persistence:
            return

        for skill_type, metrics in self.skill_metrics.items():
            metrics_path = self.metrics_dir / f"{skill_type.value}_metrics.json"
            try:
                metrics_path.write_text(json.dumps(metrics.to_dict(), indent=2))
            except Exception as e:
                logger.error(f"Failed to save metrics: {e}")

    # ========================================================================
    # EXPORT & IMPORT
    # ========================================================================

    def export_system_state(self) -> Dict[str, Any]:
        """Export complete system state."""
        return {
            "user_profile": self.user_profile.to_dict(),
            "skill_configs": {
                k.value: v.to_dict()
                for k, v in self.skill_configs.items()
            },
            "skill_metrics": {
                k.value: v.to_dict()
                for k, v in self.skill_metrics.items()
            },
            "optimization_history": self.optimization_history,
            "export_timestamp": datetime.now().isoformat(),
        }

    def import_system_state(self, state: Dict[str, Any]) -> Tuple[bool, str]:
        """Import system state from exported data."""
        try:
            # Import user profile
            profile_data = state.get("user_profile", {})
            self.user_profile = UserProfile(
                user_id=profile_data.get("user_id", self.user_id),
                created_at=profile_data.get("created_at"),
            )

            # Import configs
            configs_data = state.get("skill_configs", {})
            for skill_key, config_data in configs_data.items():
                try:
                    skill_type = SkillType(skill_key)
                    config = SkillConfig.from_dict(config_data)
                    self.skill_configs[skill_type] = config
                except Exception as e:
                    logger.warning(f"Failed to import config for {skill_key}: {e}")

            # Import metrics
            metrics_data = state.get("skill_metrics", {})
            for skill_key, metric_data in metrics_data.items():
                try:
                    skill_type = SkillType(skill_key)
                    metrics = SkillMetrics(
                        skill_type=skill_type,
                        **{k: v for k, v in metric_data.items() if k != "skill_type"}
                    )
                    self.skill_metrics[skill_type] = metrics
                except Exception as e:
                    logger.warning(f"Failed to import metrics for {skill_key}: {e}")

            self.optimization_history = state.get("optimization_history", [])

            logger.info("System state imported successfully")
            return True, "State imported successfully"

        except Exception as e:
            logger.error(f"Failed to import state: {e}")
            return False, f"Import failed: {e}"
