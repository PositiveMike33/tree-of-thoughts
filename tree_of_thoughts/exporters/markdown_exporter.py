"""Markdown exporter for Tree of Thoughts results."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from tree_of_thoughts.exporters.base_exporter import BaseExporter


class MarkdownExporter(BaseExporter):
    """Export Tree of Thoughts results to Markdown format."""

    def export(
        self,
        tot_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
    ) -> str:
        """Export ToT data to Markdown format.

        Args:
            tot_data: Tree of Thoughts data structure.
            metadata: Execution metadata (algorithm, model, timestamp, etc).
            title: Title for the Markdown document.

        Returns:
            Path to exported Markdown file.
        """
        self._ensure_output_dir()

        # Default title and metadata
        if title is None:
            algo = (
                metadata.get("algorithm", "Tree of Thoughts")
                if metadata
                else "Tree of Thoughts"
            )
            title = f"{algo} - Execution Results"

        if metadata is None:
            metadata = {}

        # Generate Markdown content
        markdown_content = self._generate_markdown(tot_data, metadata, title)

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tot_result_{timestamp}.md"
        output_path = self._get_output_path(filename)

        # Write to file
        output_path.write_text(markdown_content, encoding="utf-8")

        return str(output_path)

    def _generate_markdown(
        self, tot_data: Dict[str, Any], metadata: Dict[str, Any], title: str
    ) -> str:
        """Generate Markdown content from ToT data.

        Args:
            tot_data: Tree of Thoughts data.
            metadata: Execution metadata.
            title: Document title.

        Returns:
            Markdown formatted string.
        """
        lines = [f"# {title}\n"]

        # Add metadata section
        if metadata:
            lines.append("## Metadata\n")
            lines.append("| Property | Value |")
            lines.append("|----------|-------|")
            for key, value in metadata.items():
                if key not in ["nodes", "tree"]:
                    lines.append(f"| {key} | {value} |")
            lines.append("")

        # Add tree structure section
        lines.append("## Thinking Tree\n")

        if "nodes" in tot_data:
            nodes = tot_data["nodes"]
            if nodes:
                # Build tree hierarchy from node keys
                lines.extend(self._format_tree_nodes(nodes))
            else:
                lines.append("No nodes in tree.\n")
        else:
            lines.append("No tree data available.\n")

        # Add raw JSON section for reference
        lines.append("\n## Raw JSON Data\n")
        lines.append("```json")
        lines.append(json.dumps(tot_data, indent=2))
        lines.append("```")

        return "\n".join(lines)

    def _format_tree_nodes(self, nodes: Dict[str, Any]) -> List[str]:
        """Format tree nodes as hierarchical Markdown.

        Args:
            nodes: Dictionary of nodes from ToT execution.

        Returns:
            List of formatted Markdown lines.
        """
        lines = []

        # Sort nodes by depth if available, otherwise by key
        sorted_nodes = sorted(
            nodes.items(),
            key=lambda x: (
                len(x[0].split(" | ")) if isinstance(x[0], str) else 0,
                x[0],
            ),
        )

        for state_key, node_data in sorted_nodes:
            # Calculate depth from pipe-separated state representation
            depth = len(state_key.split(" | ")) - 1 if isinstance(state_key, str) else 0
            indent = "  " * depth

            # Format state key
            if isinstance(state_key, str):
                parts = state_key.split(" | ")
                display_text = parts[-1] if parts else state_key
            else:
                display_text = str(state_key)

            # Add node to output
            thoughts = node_data.get("thoughts", [])
            avg_score = (
                sum(thoughts) / len(thoughts)
                if isinstance(thoughts, list) and thoughts
                else 0
            )

            lines.append(f"{indent}- **{display_text}** (score: {avg_score:.2f})")

            # Add thoughts as sub-items
            if isinstance(thoughts, list):
                for thought in thoughts:
                    lines.append(f"{indent}  - {thought}")

        return lines

    def export_with_frontmatter(
        self,
        tot_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
        custom_frontmatter: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """Export ToT data with optional YAML frontmatter.

        Args:
            tot_data: Tree of Thoughts data.
            metadata: Execution metadata.
            title: Document title.
            custom_frontmatter: Custom YAML frontmatter fields.

        Returns:
            Tuple of (markdown_content, output_path).
        """
        self._ensure_output_dir()

        if title is None:
            algo = (
                metadata.get("algorithm", "Tree of Thoughts")
                if metadata
                else "Tree of Thoughts"
            )
            title = f"{algo} - Results"

        # Generate markdown without frontmatter
        markdown_content = self._generate_markdown(tot_data, metadata or {}, title)

        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tot_result_{timestamp}.md"
        output_path = self._get_output_path(filename)

        # Write to file
        output_path.write_text(markdown_content, encoding="utf-8")

        return markdown_content, str(output_path)
