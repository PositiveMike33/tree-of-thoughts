"""
Tree of Thoughts Monitoring and Persistence

Provides comprehensive monitoring, metrics collection, and persistence
for Tree of Thoughts searches with audit trails and recovery capabilities.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
import time

from .tot_integration import (
    ToTSearchResult,
    VaultAwareLanguageModel,
    ValidatedThought,
)
from .tree_of_thoughts_vault_integration import ObsidianVaultIntegration

logger = logging.getLogger(__name__)


@dataclass
class SearchMetrics:
    """Metrics collected during a Tree of Thoughts search."""
    search_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    total_time_seconds: float = 0.0
    nodes_explored: int = 0
    thoughts_generated: int = 0
    states_evaluated: int = 0
    validation_checks: int = 0
    fact_checks: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    average_confidence: float = 0.0
    final_confidence: float = 0.0
    solution_length: int = 0
    prompt_tokens_used: int = 0
    completion_tokens_used: int = 0
    total_tokens_used: int = 0
    errors_encountered: int = 0
    warnings_encountered: int = 0
    search_depth: int = 0
    search_success: bool = True

    def get_efficiency_score(self) -> float:
        """Calculate efficiency metric (0.0-1.0).

        Returns:
            Score based on tokens used vs nodes explored
        """
        if self.total_tokens_used == 0:
            return 0.0
        efficiency = (self.nodes_explored * 100) / self.total_tokens_used
        return min(1.0, efficiency)

    def get_cache_efficiency(self) -> float:
        """Calculate cache hit rate.

        Returns:
            Ratio of cache hits to total cache accesses
        """
        total_accesses = self.cache_hits + self.cache_misses
        if total_accesses == 0:
            return 0.0
        return self.cache_hits / total_accesses


@dataclass
class SearchAuditEntry:
    """Single entry in the search audit trail."""
    timestamp: str
    step: str  # "thought_generation", "evaluation", "validation", "solution"
    action: str
    result: str
    confidence: Optional[float] = None
    tokens_used: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "step": self.step,
            "action": self.action,
            "result": self.result[:100] if self.result else "",  # Truncate for readability
            "confidence": self.confidence,
            "tokens_used": self.tokens_used,
            "error": self.error,
        }


@dataclass
class SearchHistory:
    """Complete history of a Tree of Thoughts search."""
    search_id: str
    initial_prompt: str
    metrics: SearchMetrics
    result: Optional[ToTSearchResult] = None
    audit_trail: List[SearchAuditEntry] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    status: str = "in_progress"  # in_progress, completed, failed

    def add_audit_entry(
        self,
        step: str,
        action: str,
        result: str,
        confidence: Optional[float] = None,
        tokens_used: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """Add entry to audit trail."""
        entry = SearchAuditEntry(
            timestamp=datetime.now().isoformat(),
            step=step,
            action=action,
            result=result,
            confidence=confidence,
            tokens_used=tokens_used,
            error=error,
        )
        self.audit_trail.append(entry)

    def mark_completed(self, result: ToTSearchResult) -> None:
        """Mark search as completed with result."""
        self.result = result
        self.completed_at = datetime.now().isoformat()
        self.status = "completed"

    def mark_failed(self, error: str) -> None:
        """Mark search as failed."""
        self.completed_at = datetime.now().isoformat()
        self.status = "failed"
        self.add_audit_entry("error", "search_failed", error, error=error)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result_dict = None
        if self.result:
            result_dict = asdict(self.result)
            # Convert enum to string for JSON serialization
            if "confidence_level" in result_dict:
                result_dict["confidence_level"] = result_dict["confidence_level"].value

        return {
            "search_id": self.search_id,
            "initial_prompt": self.initial_prompt,
            "metrics": asdict(self.metrics),
            "result": result_dict,
            "audit_trail": [entry.to_dict() for entry in self.audit_trail],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "status": self.status,
        }


class SearchMonitor:
    """Monitors and tracks Tree of Thoughts search execution."""

    def __init__(self):
        """Initialize search monitor."""
        self.active_searches: Dict[str, SearchHistory] = {}
        self.completed_searches: List[SearchHistory] = []
        self.total_metrics: Dict[str, Any] = {
            "total_searches": 0,
            "successful_searches": 0,
            "failed_searches": 0,
            "total_time_seconds": 0.0,
            "total_tokens_used": 0,
            "average_confidence": 0.0,
        }

    def start_search(self, search_id: str, initial_prompt: str) -> SearchHistory:
        """Start monitoring a new search.

        Args:
            search_id: Unique identifier for search
            initial_prompt: The problem to solve

        Returns:
            SearchHistory object for tracking
        """
        metrics = SearchMetrics(search_id=search_id)
        history = SearchHistory(
            search_id=search_id,
            initial_prompt=initial_prompt,
            metrics=metrics,
        )
        self.active_searches[search_id] = history
        self.total_metrics["total_searches"] += 1
        logger.info(f"Started monitoring search: {search_id}")
        return history

    def record_thought_generation(
        self,
        search_id: str,
        count: int,
        tokens_used: int = 0,
    ) -> None:
        """Record thought generation step.

        Args:
            search_id: Search identifier
            count: Number of thoughts generated
            tokens_used: Tokens consumed
        """
        if search_id not in self.active_searches:
            return

        history = self.active_searches[search_id]
        history.metrics.thoughts_generated += count
        history.metrics.prompt_tokens_used += tokens_used
        history.add_audit_entry(
            step="thought_generation",
            action=f"generated_{count}_thoughts",
            result=f"Generated {count} candidate thoughts",
            tokens_used=tokens_used,
        )

    def record_evaluation(
        self,
        search_id: str,
        count: int,
        avg_score: float,
        cache_hit: bool = False,
        tokens_used: int = 0,
    ) -> None:
        """Record state evaluation step.

        Args:
            search_id: Search identifier
            count: Number of states evaluated
            avg_score: Average evaluation score
            cache_hit: Whether cache was used
            tokens_used: Tokens consumed
        """
        if search_id not in self.active_searches:
            return

        history = self.active_searches[search_id]
        history.metrics.states_evaluated += count
        history.metrics.completion_tokens_used += tokens_used

        if cache_hit:
            history.metrics.cache_hits += 1
        else:
            history.metrics.cache_misses += 1

        history.add_audit_entry(
            step="evaluation",
            action=f"evaluated_{count}_states",
            result=f"Average score: {avg_score:.2f}",
            confidence=avg_score,
            tokens_used=tokens_used,
        )

    def record_validation(
        self,
        search_id: str,
        is_valid: bool,
        confidence: float,
        tokens_used: int = 0,
    ) -> None:
        """Record validation check.

        Args:
            search_id: Search identifier
            is_valid: Whether validation passed
            confidence: Validation confidence score
            tokens_used: Tokens consumed
        """
        if search_id not in self.active_searches:
            return

        history = self.active_searches[search_id]
        history.metrics.validation_checks += 1
        history.metrics.completion_tokens_used += tokens_used

        history.add_audit_entry(
            step="validation",
            action=f"validation_{'passed' if is_valid else 'failed'}",
            result=f"Valid: {is_valid}, Confidence: {confidence:.2f}",
            confidence=confidence,
            tokens_used=tokens_used,
        )

    def record_fact_check(
        self,
        search_id: str,
        total_claims: int,
        verifiable_claims: int,
        factuality_score: float,
        tokens_used: int = 0,
    ) -> None:
        """Record fact-checking step.

        Args:
            search_id: Search identifier
            total_claims: Total claims found
            verifiable_claims: Claims that are verifiable
            factuality_score: Factuality confidence
            tokens_used: Tokens consumed
        """
        if search_id not in self.active_searches:
            return

        history = self.active_searches[search_id]
        history.metrics.fact_checks += 1
        history.metrics.completion_tokens_used += tokens_used

        history.add_audit_entry(
            step="fact_check",
            action=f"fact_checked_{total_claims}_claims",
            result=f"Verifiable: {verifiable_claims}/{total_claims}, Score: {factuality_score:.2f}",
            confidence=factuality_score,
            tokens_used=tokens_used,
        )

    def complete_search(
        self,
        search_id: str,
        result: ToTSearchResult,
        elapsed_time: float,
    ) -> SearchHistory:
        """Mark search as completed.

        Args:
            search_id: Search identifier
            result: Final ToT search result
            elapsed_time: Total search time in seconds

        Returns:
            Completed SearchHistory
        """
        if search_id not in self.active_searches:
            logger.warning(f"Search {search_id} not found in active searches")
            return None

        history = self.active_searches.pop(search_id)
        history.metrics.total_time_seconds = elapsed_time
        history.metrics.final_confidence = result.confidence_score
        history.metrics.solution_length = len(result.solution)
        history.metrics.search_depth = result.search_depth
        history.metrics.nodes_explored = result.nodes_explored
        history.metrics.total_tokens_used = (
            history.metrics.prompt_tokens_used
            + history.metrics.completion_tokens_used
        )

        history.mark_completed(result)
        self.completed_searches.append(history)
        self.total_metrics["successful_searches"] += 1
        self.total_metrics["total_time_seconds"] += elapsed_time
        self.total_metrics["total_tokens_used"] += history.metrics.total_tokens_used

        logger.info(
            f"Completed search {search_id}: "
            f"confidence={result.confidence_score:.2f}, "
            f"time={elapsed_time:.2f}s, "
            f"tokens={history.metrics.total_tokens_used}"
        )
        return history

    def fail_search(
        self,
        search_id: str,
        error: str,
        elapsed_time: float,
    ) -> SearchHistory:
        """Mark search as failed.

        Args:
            search_id: Search identifier
            error: Error message
            elapsed_time: Time before failure

        Returns:
            Failed SearchHistory
        """
        if search_id not in self.active_searches:
            return None

        history = self.active_searches.pop(search_id)
        history.metrics.total_time_seconds = elapsed_time
        history.mark_failed(error)
        self.completed_searches.append(history)
        self.total_metrics["failed_searches"] += 1
        self.total_metrics["total_time_seconds"] += elapsed_time

        logger.error(f"Search {search_id} failed: {error}")
        return history

    def get_search_statistics(self) -> Dict[str, Any]:
        """Get overall search statistics.

        Returns:
            Dictionary with aggregated metrics
        """
        if self.total_metrics["successful_searches"] == 0:
            avg_confidence = 0.0
        else:
            avg_confidence = sum(
                s.metrics.final_confidence
                for s in self.completed_searches
                if s.status == "completed"
            ) / self.total_metrics["successful_searches"]

        return {
            **self.total_metrics,
            "average_confidence": avg_confidence,
            "success_rate": (
                self.total_metrics["successful_searches"]
                / self.total_metrics["total_searches"]
                if self.total_metrics["total_searches"] > 0
                else 0.0
            ),
            "active_searches": len(self.active_searches),
            "completed_searches": len(self.completed_searches),
        }


class PersistenceManager:
    """Manages persistence of searches and results to disk."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize persistence manager.

        Args:
            base_path: Base directory for storing search data
        """
        if base_path is None:
            base_path = Path.home() / ".tree_of_thoughts" / "searches"
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.history_dir = self.base_path / "history"
        self.results_dir = self.base_path / "results"
        self.recovery_dir = self.base_path / "recovery"
        self.history_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
        self.recovery_dir.mkdir(exist_ok=True)
        logger.info(f"PersistenceManager initialized at: {self.base_path}")

    def save_search_history(self, history: SearchHistory) -> Path:
        """Save search history to disk.

        Args:
            history: SearchHistory to save

        Returns:
            Path to saved file
        """
        file_path = self.history_dir / f"{history.search_id}.json"
        try:
            with open(file_path, "w") as f:
                json.dump(history.to_dict(), f, indent=2, default=str)
            logger.info(f"Saved search history: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save search history: {e}")
            return None

    def load_search_history(self, search_id: str) -> Optional[SearchHistory]:
        """Load search history from disk.

        Args:
            search_id: ID of search to load

        Returns:
            Loaded SearchHistory or None
        """
        file_path = self.history_dir / f"{search_id}.json"
        try:
            if not file_path.exists():
                return None
            with open(file_path, "r") as f:
                data = json.load(f)
            logger.info(f"Loaded search history: {file_path}")
            return data  # Return raw dict for flexibility
        except Exception as e:
            logger.error(f"Failed to load search history: {e}")
            return None

    def save_search_result(self, search_id: str, result: ToTSearchResult) -> Path:
        """Save search result separately.

        Args:
            search_id: Search identifier
            result: ToTSearchResult to save

        Returns:
            Path to saved file
        """
        file_path = self.results_dir / f"{search_id}.json"
        try:
            with open(file_path, "w") as f:
                json.dump(asdict(result), f, indent=2, default=str)
            logger.info(f"Saved search result: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save search result: {e}")
            return None

    def save_recovery_checkpoint(
        self,
        search_id: str,
        state: Dict[str, Any],
    ) -> Path:
        """Save recovery checkpoint for in-progress search.

        Args:
            search_id: Search identifier
            state: State to save for recovery

        Returns:
            Path to saved checkpoint
        """
        file_path = self.recovery_dir / f"{search_id}.json"
        try:
            checkpoint = {
                "search_id": search_id,
                "timestamp": datetime.now().isoformat(),
                "state": state,
            }
            with open(file_path, "w") as f:
                json.dump(checkpoint, f, indent=2, default=str)
            logger.info(f"Saved recovery checkpoint: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save recovery checkpoint: {e}")
            return None

    def load_recovery_checkpoint(self, search_id: str) -> Optional[Dict[str, Any]]:
        """Load recovery checkpoint for in-progress search.

        Args:
            search_id: Search identifier

        Returns:
            Saved checkpoint state or None
        """
        file_path = self.recovery_dir / f"{search_id}.json"
        try:
            if not file_path.exists():
                return None
            with open(file_path, "r") as f:
                checkpoint = json.load(f)
            logger.info(f"Loaded recovery checkpoint: {file_path}")
            return checkpoint.get("state")
        except Exception as e:
            logger.error(f"Failed to load recovery checkpoint: {e}")
            return None

    def list_all_searches(self) -> List[Dict[str, Any]]:
        """List all saved searches.

        Returns:
            List of search metadata
        """
        searches = []
        try:
            for file_path in sorted(self.history_dir.glob("*.json")):
                with open(file_path, "r") as f:
                    data = json.load(f)
                searches.append({
                    "search_id": data["search_id"],
                    "created_at": data["created_at"],
                    "status": data["status"],
                    "confidence": data.get("metrics", {}).get("final_confidence", 0.0),
                })
        except Exception as e:
            logger.error(f"Failed to list searches: {e}")
        return searches

    def cleanup_old_searches(self, days: int = 30) -> int:
        """Clean up search records older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of deleted files
        """
        import time
        cutoff_time = time.time() - (days * 86400)
        deleted_count = 0

        for dir_path in [self.history_dir, self.results_dir]:
            try:
                for file_path in dir_path.glob("*.json"):
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
            except Exception as e:
                logger.error(f"Error cleaning up {dir_path}: {e}")

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old search files")
        return deleted_count
