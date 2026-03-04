"""Obsidian-specific adapter for Tree of Thoughts results."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from tree_of_thoughts.exporters.markdown_exporter import MarkdownExporter


class ObsidianAdapter(MarkdownExporter):
    """Export Tree of Thoughts results in Obsidian-compatible format."""

    def __init__(
        self, output_dir: Optional[str] = None, vault_path: Optional[str] = None
    ):
        """Initialize Obsidian adapter.

        Args:
            output_dir: Local directory for exports.
            vault_path: Path to Obsidian vault (D:/Vault/Vault/).
        """
        super().__init__(output_dir)
        self.vault_path = Path(vault_path) if vault_path else None
        self._setup_vault_structure()

    def _setup_vault_structure(self) -> None:
        """Setup required Obsidian vault directories."""
        if not self.vault_path or not self.vault_path.exists():
            return

        required_dirs = [
            "00-Index",
            "thinking",
            "states",
            "analysis",
            "exports",
            ".vault-metadata",
        ]

        for dir_name in required_dirs:
            (self.vault_path / dir_name).mkdir(parents=True, exist_ok=True)

    def export(
        self,
        tot_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
    ) -> str:
        """Export ToT data in Obsidian format with YAML frontmatter.

        Args:
            tot_data: Tree of Thoughts data.
            metadata: Execution metadata.
            title: Note title.

        Returns:
            Path to exported Obsidian note.
        """
        if metadata is None:
            metadata = {}

        # Add execution timestamp if not present
        if "timestamp" not in metadata:
            metadata["timestamp"] = datetime.now().isoformat()

        # Generate Obsidian note
        note_content = self._generate_obsidian_note(tot_data, metadata, title)
        output_path = self._save_obsidian_note(note_content, metadata)

        # Sync to vault if configured
        if self.vault_path:
            self._sync_to_vault(output_path, metadata)

        return output_path

    def _generate_obsidian_note(
        self,
        tot_data: Dict[str, Any],
        metadata: Dict[str, Any],
        title: Optional[str] = None,
    ) -> str:
        """Generate Obsidian-formatted note with YAML frontmatter.

        Args:
            tot_data: Tree of Thoughts data.
            metadata: Execution metadata.
            title: Note title.

        Returns:
            Complete Obsidian note content.
        """
        if title is None:
            title = f"Tree of Thoughts - {metadata.get('algorithm', 'Execution')}"

        # Build YAML frontmatter
        frontmatter = self._build_frontmatter(title, metadata)

        # Build Markdown content
        markdown = self._generate_markdown(tot_data, metadata, title)

        # Combine frontmatter and markdown
        if yaml:
            return f"---\n{frontmatter}---\n\n{markdown}"
        else:
            # Fallback if PyYAML not available
            return f"---\n{self._dict_to_yaml_string(frontmatter)}---\n\n{markdown}"

    def _build_frontmatter(self, title: str, metadata: Dict[str, Any]) -> str:
        """Build YAML frontmatter for Obsidian note.

        Args:
            title: Note title.
            metadata: Execution metadata.

        Returns:
            YAML frontmatter string.
        """
        frontmatter_dict = {
            "title": title,
            "type": "thought",
            "uuid": str(uuid.uuid4()),
            "timestamp": metadata.get("timestamp", datetime.now().isoformat()),
            "algorithm": metadata.get("algorithm", "tree-of-thoughts"),
            "model": metadata.get("model", "unknown"),
            "tags": self._generate_tags(metadata),
            "status": metadata.get("status", "completed"),
        }

        # Add custom metadata
        for key, value in metadata.items():
            if key not in frontmatter_dict and not isinstance(value, (dict, list)):
                frontmatter_dict[key] = value

        if yaml:
            return yaml.dump(
                frontmatter_dict, default_flow_style=False, sort_keys=False
            )
        else:
            return self._dict_to_yaml_string(frontmatter_dict)

    def _dict_to_yaml_string(self, data: Dict[str, Any], indent: int = 0) -> str:
        """Convert dict to YAML string (fallback if PyYAML not available).

        Args:
            data: Dictionary to convert.
            indent: Current indentation level.

        Returns:
            YAML formatted string.
        """
        lines = []
        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"{'  ' * indent}{key}:")
                for item in value:
                    lines.append(f"{'  ' * (indent + 1)}- {item}")
            elif isinstance(value, dict):
                lines.append(f"{'  ' * indent}{key}:")
                lines.append(self._dict_to_yaml_string(value, indent + 1))
            else:
                # Quote strings that contain special characters
                if isinstance(value, str) and any(c in value for c in ['"', "'", ":"]):
                    value = f'"{value}"'
                lines.append(f"{'  ' * indent}{key}: {value}")
        return "\n".join(lines)

    def _generate_tags(self, metadata: Dict[str, Any]) -> List[str]:
        """Generate Obsidian tags from metadata.

        Args:
            metadata: Execution metadata.

        Returns:
            List of tags.
        """
        tags = ["tree-of-thoughts", "reasoning", "tot"]

        # Add algorithm tag
        algo = metadata.get("algorithm", "").lower()
        if algo:
            tags.append(algo.replace(" ", "-"))

        # Add model tag
        model = metadata.get("model", "").lower()
        if model:
            tags.append(model.split("-")[0])  # e.g., 'gpt' from 'gpt-4'

        # Add custom tags from metadata if present
        if "tags" in metadata:
            custom_tags = metadata["tags"]
            if isinstance(custom_tags, list):
                tags.extend(custom_tags)
            elif isinstance(custom_tags, str):
                tags.extend(custom_tags.split(","))

        return list(set(tags))  # Remove duplicates

    def _save_obsidian_note(self, content: str, metadata: Dict[str, Any]) -> str:
        """Save Obsidian note to local directory.

        Args:
            content: Note content with frontmatter.
            metadata: Execution metadata.

        Returns:
            Path to saved file.
        """
        self._ensure_output_dir()

        # Create filename from timestamp
        timestamp = metadata.get("timestamp", datetime.now().isoformat())
        date_str = timestamp.split("T")[0]

        # Organize by date subdirectory
        date_dir = self.output_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)

        # Create filename
        algo = metadata.get("algorithm", "tot").lower().replace(" ", "-")
        filename = f"{algo}_{datetime.now().strftime('%H%M%S')}.md"
        output_path = date_dir / filename

        # Write file
        output_path.write_text(content, encoding="utf-8")

        return str(output_path)

    def _sync_to_vault(self, local_path: str, metadata: Dict[str, Any]) -> None:
        """Sync exported note to Obsidian vault.

        Args:
            local_path: Path to local exported file.
            metadata: Execution metadata.
        """
        if not self.vault_path or not self.vault_path.exists():
            return

        # Copy to vault thinking directory
        vault_date_dir = (
            self.vault_path / "thinking" / metadata.get("timestamp", "").split("T")[0]
        )
        vault_date_dir.mkdir(parents=True, exist_ok=True)

        # Copy file
        local_file = Path(local_path)
        if local_file.exists():
            vault_file = vault_date_dir / local_file.name
            vault_file.write_text(
                local_file.read_text(encoding="utf-8"), encoding="utf-8"
            )

    def create_wiki_link(self, target: str, display_text: Optional[str] = None) -> str:
        """Create Obsidian wiki-link.

        Args:
            target: Target file or note name.
            display_text: Optional display text.

        Returns:
            Obsidian wiki-link string.
        """
        if display_text:
            return f"[[{target}|{display_text}]]"
        return f"[[{target}]]"

    def create_backlink_reference(self, state_id: str, note_id: str) -> Dict[str, Any]:
        """Create backlink reference between states.

        Args:
            state_id: ID of the state node.
            note_id: ID of the related note.

        Returns:
            Backlink reference dictionary.
        """
        return {
            "source": state_id,
            "target": note_id,
            "type": "references",
            "timestamp": datetime.now().isoformat(),
        }
