"""Unit tests for Obsidian exporters."""

import tempfile
import unittest
from pathlib import Path
from datetime import datetime

from tree_of_thoughts.exporters.obsidian_adapter import ObsidianAdapter
from tree_of_thoughts.exporters.markdown_exporter import MarkdownExporter
from tree_of_thoughts.sync.conflict_resolver import ConflictResolver


class TestMarkdownExporter(unittest.TestCase):
    """Test MarkdownExporter functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.exporter = MarkdownExporter(self.temp_dir.name)

        self.sample_tot_data = {
            "nodes": {
                "initial": {"thoughts": [0.8, 0.75], "depth": 0},
                "initial | branch1": {"thoughts": [0.9, 0.85], "depth": 1},
                "initial | branch2": {"thoughts": [0.6], "depth": 1},
            }
        }

        self.sample_metadata = {
            "algorithm": "TreeofThoughtsBFS",
            "model": "GPT-4",
            "timestamp": datetime.now().isoformat(),
            "best_value": 0.95,
        }

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_export_creates_file(self):
        """Test that export creates a file."""
        output_path = self.exporter.export(
            self.sample_tot_data, self.sample_metadata, "Test Export"
        )
        self.assertTrue(Path(output_path).exists())

    def test_export_contains_title(self):
        """Test that exported file contains title."""
        output_path = self.exporter.export(
            self.sample_tot_data, self.sample_metadata, "Test Export"
        )
        content = Path(output_path).read_text(encoding="utf-8")
        self.assertIn("# Test Export", content)

    def test_export_contains_metadata(self):
        """Test that exported file contains metadata."""
        output_path = self.exporter.export(
            self.sample_tot_data, self.sample_metadata, "Test Export"
        )
        content = Path(output_path).read_text(encoding="utf-8")
        self.assertIn("TreeofThoughtsBFS", content)
        self.assertIn("GPT-4", content)

    def test_export_contains_nodes(self):
        """Test that exported file contains tree nodes."""
        output_path = self.exporter.export(
            self.sample_tot_data, self.sample_metadata, "Test Export"
        )
        content = Path(output_path).read_text(encoding="utf-8")
        self.assertIn("initial", content)
        self.assertIn("branch1", content)


class TestObsidianAdapter(unittest.TestCase):
    """Test ObsidianAdapter functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.adapter = ObsidianAdapter(output_dir=self.temp_dir.name, vault_path=None)

        self.sample_tot_data = {
            "nodes": {
                "problem": {"thoughts": [0.7], "depth": 0},
                "problem | solution": {"thoughts": [0.95], "depth": 1},
            }
        }

        self.sample_metadata = {
            "algorithm": "MonteCarloTreeofThoughts",
            "model": "Claude",
            "timestamp": datetime.now().isoformat(),
        }

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_export_creates_file(self):
        """Test that export creates a file."""
        output_path = self.adapter.export(
            self.sample_tot_data, self.sample_metadata, "Obsidian Test"
        )
        self.assertTrue(Path(output_path).exists())

    def test_frontmatter_contains_required_fields(self):
        """Test that frontmatter contains required fields."""
        output_path = self.adapter.export(
            self.sample_tot_data, self.sample_metadata, "Obsidian Test"
        )
        content = Path(output_path).read_text(encoding="utf-8")

        # Check for YAML frontmatter fields
        self.assertIn("title:", content)
        self.assertIn("type:", content)
        self.assertIn("uuid:", content)
        self.assertIn("timestamp:", content)
        self.assertIn("algorithm:", content)
        self.assertIn("model:", content)

    def test_tags_generation(self):
        """Test that tags are generated from metadata."""
        tags = self.adapter._generate_tags(self.sample_metadata)
        self.assertIn("tree-of-thoughts", tags)
        self.assertIn("reasoning", tags)
        self.assertIn("tot", tags)
        # MonteCarloTreeofThoughts lowercased becomes montecarlotreeofthoughts
        self.assertIn("montecarlotreeofthoughts", tags)
        self.assertIn("claude", tags)

    def test_wiki_link_creation(self):
        """Test wiki-link creation."""
        link = self.adapter.create_wiki_link("target-note")
        self.assertEqual(link, "[[target-note]]")

        link_with_text = self.adapter.create_wiki_link("target", "Display Text")
        self.assertEqual(link_with_text, "[[target|Display Text]]")


class TestConflictResolver(unittest.TestCase):
    """Test ConflictResolver functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.resolver = ConflictResolver(
            vault_path=Path(self.temp_dir.name) / "vault",
            local_path=Path(self.temp_dir.name) / "local",
        )
        (Path(self.temp_dir.name) / "vault").mkdir(exist_ok=True)
        (Path(self.temp_dir.name) / "local").mkdir(exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_identical_files_detected(self):
        """Test that identical files are detected."""
        content = "test content"
        local_file = Path(self.temp_dir.name) / "local" / "test.md"
        vault_file = Path(self.temp_dir.name) / "vault" / "test.md"

        local_file.write_text(content, encoding="utf-8")
        vault_file.write_text(content, encoding="utf-8")

        result = self.resolver.resolve_conflict(local_file, vault_file)
        self.assertEqual(result["status"], "identical")

    def test_ignore_patterns(self):
        """Test that ignore patterns work."""
        self.assertTrue(self.resolver.should_ignore_file(".conflict-test.md"))
        self.assertTrue(self.resolver.should_ignore_file("file.metadata-.md"))
        self.assertFalse(self.resolver.should_ignore_file("regular.md"))

    def test_hash_computation(self):
        """Test hash computation."""
        content1 = "test content 1"
        content2 = "test content 2"

        hash1 = self.resolver._compute_hash(content1)
        hash2 = self.resolver._compute_hash(content2)

        self.assertNotEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA256 hex string length

    def test_debounce_prevents_duplicate_syncs(self):
        """Test debouncing prevents duplicate syncs."""
        filepath = "test.md"

        # First call should not debounce
        self.assertFalse(self.resolver.should_debounce(filepath, sync_timeout=1.0))

        # Second call should debounce (within timeout)
        self.assertTrue(self.resolver.should_debounce(filepath, sync_timeout=1.0))


class TestObsidianAdapterIntegration(unittest.TestCase):
    """Integration tests for Obsidian adapter."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.adapter = ObsidianAdapter(output_dir=self.temp_dir.name, vault_path=None)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_full_export_workflow(self):
        """Test complete export workflow."""
        tot_data = {
            "nodes": {
                "start": {"thoughts": [0.5]},
                "start | branch": {"thoughts": [0.9]},
            }
        }

        metadata = {
            "algorithm": "TreeofThoughtsDFS",
            "model": "GPT-4",
            "timestamp": datetime.now().isoformat(),
            "problem": "Solve math problem",
        }

        output_path = self.adapter.export(tot_data, metadata, "Math Problem")

        # Verify file exists and contains expected content
        self.assertTrue(Path(output_path).exists())

        content = Path(output_path).read_text(encoding="utf-8")
        self.assertIn("tree-of-thoughts", content)
        self.assertIn("TreeofThoughtsDFS", content)
        self.assertIn("Math Problem", content)
        self.assertIn("start", content)


if __name__ == "__main__":
    unittest.main()
