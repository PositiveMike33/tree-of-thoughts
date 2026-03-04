"""Tests for monitoring_persistence module."""

import unittest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from ..monitoring_persistence import (
    SearchMetrics,
    SearchAuditEntry,
    SearchHistory,
    SearchMonitor,
    PersistenceManager,
)
from ..tot_integration import ToTSearchResult, ConfidenceLevel


class TestSearchMetrics(unittest.TestCase):
    """Test SearchMetrics dataclass."""

    def setUp(self):
        """Set up test fixtures."""
        self.metrics = SearchMetrics(search_id="test-search-001")

    def test_create_metrics(self):
        """Test creating metrics object."""
        self.assertEqual(self.metrics.search_id, "test-search-001")
        self.assertEqual(self.metrics.nodes_explored, 0)
        self.assertEqual(self.metrics.thoughts_generated, 0)
        self.assertTrue(self.metrics.search_success)

    def test_efficiency_score_zero(self):
        """Test efficiency when no tokens used."""
        score = self.metrics.get_efficiency_score()
        self.assertEqual(score, 0.0)

    def test_efficiency_score_calculation(self):
        """Test efficiency score calculation."""
        self.metrics.nodes_explored = 10
        self.metrics.total_tokens_used = 100
        score = self.metrics.get_efficiency_score()
        expected = min(1.0, (10 * 100) / 100)
        self.assertEqual(score, expected)

    def test_cache_efficiency_no_accesses(self):
        """Test cache efficiency with no accesses."""
        efficiency = self.metrics.get_cache_efficiency()
        self.assertEqual(efficiency, 0.0)

    def test_cache_efficiency_calculation(self):
        """Test cache efficiency calculation."""
        self.metrics.cache_hits = 8
        self.metrics.cache_misses = 2
        efficiency = self.metrics.get_cache_efficiency()
        self.assertEqual(efficiency, 0.8)  # 8/(8+2) = 0.8


class TestSearchAuditEntry(unittest.TestCase):
    """Test SearchAuditEntry dataclass."""

    def test_create_audit_entry(self):
        """Test creating audit entry."""
        entry = SearchAuditEntry(
            timestamp=datetime.now().isoformat(),
            step="thought_generation",
            action="generated_3_thoughts",
            result="Generated 3 candidate thoughts",
            confidence=0.8,
            tokens_used=150,
        )
        self.assertEqual(entry.step, "thought_generation")
        self.assertEqual(entry.confidence, 0.8)

    def test_audit_entry_to_dict(self):
        """Test converting audit entry to dict."""
        entry = SearchAuditEntry(
            timestamp=datetime.now().isoformat(),
            step="evaluation",
            action="evaluated_3_states",
            result="Average score: 0.75",
            confidence=0.75,
        )
        entry_dict = entry.to_dict()
        self.assertIn("timestamp", entry_dict)
        self.assertEqual(entry_dict["step"], "evaluation")
        self.assertEqual(entry_dict["confidence"], 0.75)

    def test_audit_entry_result_truncation(self):
        """Test that long results are truncated."""
        long_result = "x" * 200
        entry = SearchAuditEntry(
            timestamp=datetime.now().isoformat(),
            step="test",
            action="test",
            result=long_result,
        )
        entry_dict = entry.to_dict()
        self.assertEqual(len(entry_dict["result"]), 100)


class TestSearchHistory(unittest.TestCase):
    """Test SearchHistory dataclass."""

    def setUp(self):
        """Set up test fixtures."""
        self.metrics = SearchMetrics(search_id="test-001")
        self.history = SearchHistory(
            search_id="test-001",
            initial_prompt="What is X?",
            metrics=self.metrics,
        )

    def test_create_history(self):
        """Test creating search history."""
        self.assertEqual(self.history.search_id, "test-001")
        self.assertEqual(self.history.status, "in_progress")
        self.assertIsNone(self.history.result)

    def test_add_audit_entry(self):
        """Test adding audit entries."""
        self.history.add_audit_entry(
            step="thought_generation",
            action="generated_3",
            result="Success",
            confidence=0.8,
        )
        self.assertEqual(len(self.history.audit_trail), 1)
        self.assertEqual(self.history.audit_trail[0].step, "thought_generation")

    def test_mark_completed(self):
        """Test marking search as completed."""
        result = ToTSearchResult(
            solution="The answer is 42",
            best_state="reasoning",
            confidence_score=0.85,
            confidence_level=ConfidenceLevel.HIGH,
            search_depth=3,
            nodes_explored=12,
            validation_report={},
            fact_check_report={},
            blind_validation_report={},
        )
        self.history.mark_completed(result)

        self.assertEqual(self.history.status, "completed")
        self.assertEqual(self.history.result, result)
        self.assertIsNotNone(self.history.completed_at)

    def test_mark_failed(self):
        """Test marking search as failed."""
        error_msg = "LLM timeout"
        self.history.mark_failed(error_msg)

        self.assertEqual(self.history.status, "failed")
        self.assertIsNotNone(self.history.completed_at)
        self.assertEqual(len(self.history.audit_trail), 1)

    def test_to_dict(self):
        """Test converting history to dict."""
        self.history.add_audit_entry("test", "test", "test result")
        hist_dict = self.history.to_dict()

        self.assertEqual(hist_dict["search_id"], "test-001")
        self.assertEqual(hist_dict["status"], "in_progress")
        self.assertIsNotNone(hist_dict["metrics"])
        self.assertIsNotNone(hist_dict["audit_trail"])


class TestSearchMonitor(unittest.TestCase):
    """Test SearchMonitor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.monitor = SearchMonitor()

    def test_initialization(self):
        """Test monitor initialization."""
        self.assertEqual(len(self.monitor.active_searches), 0)
        self.assertEqual(len(self.monitor.completed_searches), 0)
        self.assertEqual(self.monitor.total_metrics["total_searches"], 0)

    def test_start_search(self):
        """Test starting a new search."""
        history = self.monitor.start_search("search-001", "What is AI?")

        self.assertEqual(history.search_id, "search-001")
        self.assertEqual(history.initial_prompt, "What is AI?")
        self.assertIn("search-001", self.monitor.active_searches)
        self.assertEqual(self.monitor.total_metrics["total_searches"], 1)

    def test_record_thought_generation(self):
        """Test recording thought generation."""
        self.monitor.start_search("search-001", "Test")
        self.monitor.record_thought_generation("search-001", 3, tokens_used=150)

        history = self.monitor.active_searches["search-001"]
        self.assertEqual(history.metrics.thoughts_generated, 3)
        self.assertEqual(history.metrics.prompt_tokens_used, 150)
        self.assertEqual(len(history.audit_trail), 1)

    def test_record_evaluation(self):
        """Test recording state evaluation."""
        self.monitor.start_search("search-001", "Test")
        self.monitor.record_evaluation(
            "search-001",
            count=3,
            avg_score=0.8,
            cache_hit=False,
            tokens_used=200,
        )

        history = self.monitor.active_searches["search-001"]
        self.assertEqual(history.metrics.states_evaluated, 3)
        self.assertEqual(history.metrics.cache_misses, 1)
        self.assertEqual(history.metrics.completion_tokens_used, 200)

    def test_record_evaluation_cache_hit(self):
        """Test recording cache hits."""
        self.monitor.start_search("search-001", "Test")
        self.monitor.record_evaluation(
            "search-001",
            count=1,
            avg_score=0.7,
            cache_hit=True,
            tokens_used=0,
        )

        history = self.monitor.active_searches["search-001"]
        self.assertEqual(history.metrics.cache_hits, 1)
        self.assertEqual(history.metrics.cache_misses, 0)

    def test_record_validation(self):
        """Test recording validation."""
        self.monitor.start_search("search-001", "Test")
        self.monitor.record_validation(
            "search-001",
            is_valid=True,
            confidence=0.9,
            tokens_used=100,
        )

        history = self.monitor.active_searches["search-001"]
        self.assertEqual(history.metrics.validation_checks, 1)
        self.assertEqual(history.metrics.completion_tokens_used, 100)

    def test_record_fact_check(self):
        """Test recording fact-checking."""
        self.monitor.start_search("search-001", "Test")
        self.monitor.record_fact_check(
            "search-001",
            total_claims=5,
            verifiable_claims=4,
            factuality_score=0.85,
            tokens_used=80,
        )

        history = self.monitor.active_searches["search-001"]
        self.assertEqual(history.metrics.fact_checks, 1)
        self.assertEqual(history.metrics.completion_tokens_used, 80)

    def test_complete_search(self):
        """Test completing a search."""
        self.monitor.start_search("search-001", "Test question")
        result = ToTSearchResult(
            solution="Test solution",
            best_state="best reasoning",
            confidence_score=0.88,
            confidence_level=ConfidenceLevel.HIGH,
            search_depth=3,
            nodes_explored=15,
            validation_report={},
            fact_check_report={},
            blind_validation_report={},
        )

        history = self.monitor.complete_search("search-001", result, 5.2)

        self.assertEqual(history.status, "completed")
        self.assertEqual(history.metrics.final_confidence, 0.88)
        self.assertAlmostEqual(history.metrics.total_time_seconds, 5.2)
        self.assertEqual(self.monitor.total_metrics["successful_searches"], 1)
        self.assertNotIn("search-001", self.monitor.active_searches)
        self.assertIn(history, self.monitor.completed_searches)

    def test_fail_search(self):
        """Test failing a search."""
        self.monitor.start_search("search-001", "Test")
        history = self.monitor.fail_search("search-001", "Connection timeout", 2.5)

        self.assertEqual(history.status, "failed")
        self.assertEqual(self.monitor.total_metrics["failed_searches"], 1)
        self.assertNotIn("search-001", self.monitor.active_searches)

    def test_get_search_statistics(self):
        """Test getting search statistics."""
        # Start and complete a search
        self.monitor.start_search("search-001", "Test")
        result = ToTSearchResult(
            solution="Solution",
            best_state="state",
            confidence_score=0.9,
            confidence_level=ConfidenceLevel.HIGH,
            search_depth=2,
            nodes_explored=10,
            validation_report={},
            fact_check_report={},
            blind_validation_report={},
        )
        self.monitor.complete_search("search-001", result, 3.0)

        stats = self.monitor.get_search_statistics()

        self.assertEqual(stats["total_searches"], 1)
        self.assertEqual(stats["successful_searches"], 1)
        self.assertEqual(stats["failed_searches"], 0)
        self.assertEqual(stats["success_rate"], 1.0)

    def test_inactive_search_recording(self):
        """Test recording to non-existent search is ignored."""
        # Should not raise error
        self.monitor.record_thought_generation("non-existent", 3, tokens_used=100)
        self.monitor.record_evaluation("non-existent", 1, 0.5)


class TestPersistenceManager(unittest.TestCase):
    """Test PersistenceManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = PersistenceManager(Path(self.temp_dir))

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test manager initialization."""
        self.assertTrue(self.manager.base_path.exists())
        self.assertTrue(self.manager.history_dir.exists())
        self.assertTrue(self.manager.results_dir.exists())
        self.assertTrue(self.manager.recovery_dir.exists())

    def test_save_and_load_search_history(self):
        """Test saving and loading search history."""
        metrics = SearchMetrics(search_id="test-001")
        history = SearchHistory(
            search_id="test-001",
            initial_prompt="Test prompt",
            metrics=metrics,
        )
        history.add_audit_entry("test", "test_action", "test result")

        # Save
        saved_path = self.manager.save_search_history(history)
        self.assertTrue(saved_path.exists())

        # Load
        loaded = self.manager.load_search_history("test-001")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["search_id"], "test-001")

    def test_save_search_result(self):
        """Test saving search result."""
        result = ToTSearchResult(
            solution="Test solution",
            best_state="test state",
            confidence_score=0.85,
            confidence_level=ConfidenceLevel.HIGH,
            search_depth=3,
            nodes_explored=10,
            validation_report={},
            fact_check_report={},
            blind_validation_report={},
        )

        saved_path = self.manager.save_search_result("test-001", result)
        self.assertTrue(saved_path.exists())

    def test_save_and_load_recovery_checkpoint(self):
        """Test saving and loading recovery checkpoints."""
        state = {
            "best_score": 0.8,
            "nodes_explored": 5,
            "last_state": "test state",
        }

        saved_path = self.manager.save_recovery_checkpoint("test-001", state)
        self.assertTrue(saved_path.exists())

        loaded = self.manager.load_recovery_checkpoint("test-001")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["best_score"], 0.8)

    def test_load_nonexistent_checkpoint(self):
        """Test loading non-existent checkpoint returns None."""
        loaded = self.manager.load_recovery_checkpoint("non-existent")
        self.assertIsNone(loaded)

    def test_list_all_searches(self):
        """Test listing all saved searches."""
        metrics1 = SearchMetrics(search_id="search-001")
        history1 = SearchHistory(
            search_id="search-001",
            initial_prompt="Test 1",
            metrics=metrics1,
        )
        self.manager.save_search_history(history1)

        metrics2 = SearchMetrics(search_id="search-002")
        history2 = SearchHistory(
            search_id="search-002",
            initial_prompt="Test 2",
            metrics=metrics2,
        )
        self.manager.save_search_history(history2)

        searches = self.manager.list_all_searches()
        self.assertEqual(len(searches), 2)
        self.assertEqual(searches[0]["search_id"], "search-001")

    def test_cleanup_old_searches(self):
        """Test cleanup of old searches."""
        # Save a search
        metrics = SearchMetrics(search_id="old-search")
        history = SearchHistory(
            search_id="old-search",
            initial_prompt="Test",
            metrics=metrics,
        )
        self.manager.save_search_history(history)

        # Cleanup with days=0 should delete everything
        deleted = self.manager.cleanup_old_searches(days=0)
        self.assertGreater(deleted, 0)


class TestMonitoringIntegration(unittest.TestCase):
    """Integration tests for monitoring and persistence."""

    def setUp(self):
        """Set up test fixtures."""
        self.monitor = SearchMonitor()
        self.temp_dir = tempfile.mkdtemp()
        self.persistence = PersistenceManager(Path(self.temp_dir))

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_monitoring_workflow(self):
        """Test complete monitoring and persistence workflow."""
        # Start search
        search_id = "complete-test"
        history = self.monitor.start_search(search_id, "Test question")

        # Simulate search steps
        self.monitor.record_thought_generation(search_id, 3, tokens_used=100)
        self.monitor.record_evaluation(search_id, 3, 0.8, tokens_used=150)
        self.monitor.record_validation(search_id, True, 0.9, tokens_used=80)
        self.monitor.record_fact_check(search_id, 5, 4, 0.85, tokens_used=90)

        # Complete search
        result = ToTSearchResult(
            solution="Complete solution",
            best_state="final state",
            confidence_score=0.87,
            confidence_level=ConfidenceLevel.HIGH,
            search_depth=3,
            nodes_explored=12,
            validation_report={"is_valid": True},
            fact_check_report={"factuality_score": 0.85},
            blind_validation_report={},
        )

        completed = self.monitor.complete_search(search_id, result, 5.5)

        # Persist
        self.persistence.save_search_history(completed)
        self.persistence.save_search_result(search_id, result)

        # Verify persistence
        loaded_history = self.persistence.load_search_history(search_id)
        self.assertIsNotNone(loaded_history)
        self.assertEqual(loaded_history["search_id"], search_id)
        self.assertEqual(loaded_history["status"], "completed")

        # Verify statistics
        stats = self.monitor.get_search_statistics()
        self.assertEqual(stats["total_searches"], 1)
        self.assertEqual(stats["successful_searches"], 1)


if __name__ == "__main__":
    unittest.main()
