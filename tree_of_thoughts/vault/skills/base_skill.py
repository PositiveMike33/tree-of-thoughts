"""
Abstract base class for Tree of Thoughts skills.

Provides common interface and implementation for domain-specific skills that
leverage full ToT + validation pipeline for high-confidence reasoning.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

from .skill_config import SkillConfig, SkillType, AlgorithmType
from .skill_utils import (
    format_state,
    merge_confidence_scores,
    apply_confidence_penalty,
    calculate_overall_confidence,
    format_skill_result,
    create_skill_metadata,
)
from ..tot_integration import ToTSearchResult, VaultAwareLanguageModel
from ..tree_of_thoughts_vault_integration import ObsidianVaultIntegration, ThoughtNode
from ..validation_engine import ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class SkillResult:
    """Result from executing a skill."""

    # Core output
    skill_name: str
    skill_type: SkillType
    output: str                        # Primary answer/recommendation
    confidence_score: float            # 0.0-1.0
    confidence_level: str              # CERTAIN/HIGH/MEDIUM/LOW/VERY_LOW

    # Detailed results
    reasoning_path: List[str] = field(default_factory=list)
    validation_results: Dict = field(default_factory=dict)
    fact_check_report: Dict = field(default_factory=dict)
    blind_validation_report: Dict = field(default_factory=dict)

    # Alternatives and recommendations
    alternatives: List[Tuple[str, float]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Audit trail
    audit_trail: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)

    # Flags
    requires_human_review: bool = False
    confidence_interval: float = 0.05
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "skill_name": self.skill_name,
            "skill_type": self.skill_type.value,
            "output": self.output,
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level,
            "reasoning_path": self.reasoning_path,
            "validation_results": self.validation_results,
            "fact_check_report": self.fact_check_report,
            "blind_validation_report": self.blind_validation_report,
            "alternatives": [(alt, score) for alt, score in self.alternatives],
            "recommendations": self.recommendations,
            "audit_trail": self.audit_trail,
            "metadata": self.metadata,
            "requires_human_review": self.requires_human_review,
            "confidence_interval": self.confidence_interval,
            "execution_time": self.execution_time,
        }


class BaseSkill(ABC):
    """Abstract base class for all domain-specific skills."""

    def __init__(
        self,
        config: SkillConfig,
        llm_model: VaultAwareLanguageModel,
        vault: Optional[ObsidianVaultIntegration] = None,
    ):
        """Initialize skill with configuration and dependencies.

        Args:
            config: Skill configuration
            llm_model: VaultAwareLanguageModel instance for ToT execution
            vault: Optional vault integration for persistence
        """
        self.config = config
        self.llm_model = llm_model
        self.vault = vault
        self.execution_history: List[Dict] = []
        self.current_result: Optional[SkillResult] = None

        # Validate configuration
        is_valid, error_msg = config.validate()
        if not is_valid:
            raise ValueError(f"Invalid skill configuration: {error_msg}")

        logger.info(f"Initialized {self.config.name} skill with {config.algorithm.value} algorithm")

    @abstractmethod
    def execute(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SkillResult:
        """Execute the skill with given prompt and optional context.

        Args:
            prompt: Input prompt/question for the skill
            context: Optional additional context for the skill

        Returns:
            SkillResult with output, confidence, and audit trail
        """
        pass

    @abstractmethod
    def validate_input(self, prompt: str) -> Tuple[bool, str]:
        """Validate that input is appropriate for this skill.

        Args:
            prompt: Input to validate

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        pass

    @abstractmethod
    def build_system_prompt(self) -> str:
        """Build specialized system prompt for this skill.

        Should emphasize domain-specific concerns and reasoning patterns.

        Returns:
            System prompt string
        """
        pass

    # ========================================================================
    # PROTECTED METHODS FOR SKILL IMPLEMENTATION
    # ========================================================================

    def _run_tot_search(
        self,
        prompt: str,
        initial_state: str = ""
    ) -> ToTSearchResult:
        """Execute Tree of Thoughts search with configured algorithm.

        Args:
            prompt: Problem statement/prompt
            initial_state: Optional initial state for search

        Returns:
            ToTSearchResult with solution and validation reports
        """
        start_time = time.time()
        algorithm = self.config.algorithm

        try:
            # Dispatch to appropriate algorithm
            if algorithm == AlgorithmType.BFS:
                result = self._tot_bfs_search(prompt, initial_state)
            elif algorithm == AlgorithmType.DFS:
                result = self._tot_dfs_search(prompt, initial_state)
            elif algorithm == AlgorithmType.BEST:
                result = self._tot_best_search(prompt, initial_state)
            elif algorithm == AlgorithmType.A_STAR:
                result = self._tot_a_star_search(prompt, initial_state)
            elif algorithm == AlgorithmType.MCTS:
                result = self._tot_mcts_search(prompt, initial_state)
            else:
                raise ValueError(f"Unknown algorithm: {algorithm}")

            elapsed = time.time() - start_time
            logger.info(
                f"ToT search completed in {elapsed:.2f}s, "
                f"explored {result.nodes_explored} nodes, "
                f"confidence: {result.confidence_level}"
            )

            return result

        except Exception as e:
            logger.error(f"Error during ToT search: {e}")
            raise

    def _tot_bfs_search(self, prompt: str, initial_state: str = "") -> ToTSearchResult:
        """Execute BFS Tree of Thoughts algorithm."""
        # TODO: Implement BFS via VaultAwareLanguageModel
        # For now, return placeholder
        return ToTSearchResult(
            solution="BFS search not yet implemented",
            best_state=initial_state or prompt,
            confidence_score=0.0,
            confidence_level="VERY_LOW",
            search_depth=0,
            nodes_explored=0,
            validation_report={},
            fact_check_report={},
            blind_validation_report={},
        )

    def _tot_dfs_search(self, prompt: str, initial_state: str = "") -> ToTSearchResult:
        """Execute DFS Tree of Thoughts algorithm."""
        # TODO: Implement DFS via VaultAwareLanguageModel
        return ToTSearchResult(
            solution="DFS search not yet implemented",
            best_state=initial_state or prompt,
            confidence_score=0.0,
            confidence_level="VERY_LOW",
            search_depth=0,
            nodes_explored=0,
            validation_report={},
            fact_check_report={},
            blind_validation_report={},
        )

    def _tot_best_search(self, prompt: str, initial_state: str = "") -> ToTSearchResult:
        """Execute BEST Tree of Thoughts algorithm."""
        # TODO: Implement BEST via VaultAwareLanguageModel
        return ToTSearchResult(
            solution="BEST search not yet implemented",
            best_state=initial_state or prompt,
            confidence_score=0.0,
            confidence_level="VERY_LOW",
            search_depth=0,
            nodes_explored=0,
            validation_report={},
            fact_check_report={},
            blind_validation_report={},
        )

    def _tot_a_star_search(self, prompt: str, initial_state: str = "") -> ToTSearchResult:
        """Execute A* Tree of Thoughts algorithm."""
        # TODO: Implement A* via VaultAwareLanguageModel
        return ToTSearchResult(
            solution="A* search not yet implemented",
            best_state=initial_state or prompt,
            confidence_score=0.0,
            confidence_level="VERY_LOW",
            search_depth=0,
            nodes_explored=0,
            validation_report={},
            fact_check_report={},
            blind_validation_report={},
        )

    def _tot_mcts_search(self, prompt: str, initial_state: str = "") -> ToTSearchResult:
        """Execute MCTS Tree of Thoughts algorithm."""
        # TODO: Implement MCTS via VaultAwareLanguageModel
        return ToTSearchResult(
            solution="MCTS search not yet implemented",
            best_state=initial_state or prompt,
            confidence_score=0.0,
            confidence_level="VERY_LOW",
            search_depth=0,
            nodes_explored=0,
            validation_report={},
            fact_check_report={},
            blind_validation_report={},
        )

    def _convert_tot_result_to_skill_result(
        self,
        tot_result: ToTSearchResult,
        execution_time: float
    ) -> SkillResult:
        """Convert ToTSearchResult to SkillResult with confidence calculation.

        Args:
            tot_result: Result from ToT search
            execution_time: Execution time in seconds

        Returns:
            SkillResult with comprehensive metadata
        """
        # Calculate overall confidence from three validation layers
        validation_score = tot_result.validation_report.get("confidence", 0.7)
        factuality_score = tot_result.fact_check_report.get("factuality_score", 0.7)
        blind_score = tot_result.blind_validation_report.get("consensus_score", 0.7)

        overall_confidence = calculate_overall_confidence(
            validation_score=validation_score,
            factuality_score=factuality_score,
            blind_score=blind_score
        )

        # Determine if human review is needed
        requires_review = (
            overall_confidence < self.config.confidence_threshold or
            tot_result.requires_review or
            len(tot_result.validation_report.get("issues", [])) > 0
        )

        return SkillResult(
            skill_name=self.config.name,
            skill_type=self.config.skill_type,
            output=tot_result.solution,
            confidence_score=overall_confidence,
            confidence_level=tot_result.confidence_level,
            reasoning_path=[t.text for t in tot_result.thought_path],
            validation_results=tot_result.validation_report,
            fact_check_report=tot_result.fact_check_report,
            blind_validation_report=tot_result.blind_validation_report,
            alternatives=tot_result.alternatives,
            audit_trail={
                "algorithm": self.config.algorithm.value,
                "search_depth": tot_result.search_depth,
                "nodes_explored": tot_result.nodes_explored,
                "best_state": format_state(tot_result.best_state),
            },
            metadata=create_skill_metadata(
                skill_name=self.config.name,
                algorithm=self.config.algorithm.value,
                confidence_score=overall_confidence,
                execution_time=execution_time
            ),
            requires_human_review=requires_review,
            execution_time=execution_time,
        )

    def _persist_result(self, result: SkillResult) -> None:
        """Persist skill result to vault if enabled.

        Args:
            result: SkillResult to persist
        """
        if not self.config.persist_results or not self.vault:
            return

        try:
            # Persist to vault
            self.vault.create_note(
                filename=f"{self.config.skill_type.value}_{int(time.time())}",
                content=result.output,
                section=self.config.vault_section
            )

            logger.info(f"Result persisted to vault: {self.config.skill_type.value}")

        except Exception as e:
            logger.error(f"Error persisting result to vault: {e}")

    def _handle_execution_error(self, error: Exception) -> SkillResult:
        """Handle execution errors gracefully.

        Args:
            error: Exception that occurred during execution

        Returns:
            SkillResult with error information
        """
        logger.error(f"Skill execution failed: {error}")

        return SkillResult(
            skill_name=self.config.name,
            skill_type=self.config.skill_type,
            output=f"Error: {str(error)}",
            confidence_score=0.0,
            confidence_level="VERY_LOW",
            requires_human_review=True,
            metadata={
                "error": str(error),
                "error_type": type(error).__name__,
            }
        )

    # ========================================================================
    # PUBLIC METHODS FOR INSPECTION
    # ========================================================================

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of last skill execution.

        Returns:
            Dictionary with execution metrics
        """
        if not self.current_result:
            return {}

        return {
            "skill_name": self.current_result.skill_name,
            "execution_time": self.current_result.execution_time,
            "confidence_score": self.current_result.confidence_score,
            "confidence_level": self.current_result.confidence_level,
            "nodes_explored": self.current_result.audit_trail.get("nodes_explored", 0),
            "requires_review": self.current_result.requires_human_review,
        }

    def get_config(self) -> Dict[str, Any]:
        """Get skill configuration as dictionary.

        Returns:
            Configuration dictionary
        """
        return self.config.to_dict()
