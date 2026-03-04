"""Base exporter abstract class for Tree of Thoughts results."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pathlib import Path


class BaseExporter(ABC):
    """Abstract base class for exporting Tree of Thoughts results."""

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize base exporter.

        Args:
            output_dir: Directory to save exported files.
                If None, uses current directory.
        """
        self.output_dir = Path(output_dir) if output_dir else Path(".")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def export(
        self, tot_data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Export Tree of Thoughts data to a specific format.

        Args:
            tot_data: Tree of Thoughts data containing nodes and structure.
            metadata: Optional metadata about the execution (algorithm, model, etc).

        Returns:
            Path to the exported file.
        """
        pass

    def _ensure_output_dir(self) -> Path:
        """Ensure output directory exists."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir

    def _get_output_path(self, filename: str) -> Path:
        """Get full path for output file."""
        return self.output_dir / filename
