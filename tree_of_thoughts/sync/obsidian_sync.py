"""Bidirectional synchronization manager for Obsidian vault."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent

    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

from tree_of_thoughts.sync.conflict_resolver import ConflictResolver

logger = logging.getLogger(__name__)


class ObsidianSync:
    """Manages bidirectional synchronization with Obsidian vault."""

    def __init__(
        self,
        vault_path: Optional[str] = None,
        local_path: Optional[str] = None,
        enable_watcher: bool = True,
    ):
        """Initialize Obsidian sync manager.

        Args:
            vault_path: Path to Obsidian vault (D:/Vault/Vault/).
            local_path: Path to local exports directory.
            enable_watcher: Enable file watcher for continuous sync.
        """
        self.vault_path = Path(vault_path) if vault_path else None
        self.local_path = Path(local_path) if local_path else None
        self.conflict_resolver = ConflictResolver(vault_path, local_path)
        self.sync_log = []
        self.observer = None

        if enable_watcher and HAS_WATCHDOG and self.vault_path:
            self._setup_watcher()

    def _setup_watcher(self) -> None:
        """Setup file system watcher for vault directory."""
        if not HAS_WATCHDOG or not self.vault_path:
            logger.warning("watchdog not installed. File watching disabled.")
            return

        handler = VaultFileHandler(self)
        self.observer = Observer()
        self.observer.schedule(handler, str(self.vault_path), recursive=True)
        self.observer.start()
        logger.info(f"Started watching vault directory: {self.vault_path}")

    def sync_to_vault(self, local_file: Path, force: bool = False) -> Dict[str, Any]:
        """Sync local file to Obsidian vault.

        Args:
            local_file: Path to local file to sync.
            force: Force sync even if debounced.

        Returns:
            Sync result dictionary.
        """
        if not local_file.exists():
            return {"status": "error", "message": "Local file does not exist"}

        if not force and self.conflict_resolver.should_debounce(str(local_file)):
            return {"status": "debounced", "message": "File sync debounced"}

        if not self.vault_path:
            return {"status": "error", "message": "Vault path not configured"}

        # Determine vault file path (mirror structure)
        vault_file = self._get_vault_file_path(local_file)

        if self.conflict_resolver.should_ignore_file(str(vault_file)):
            return {"status": "ignored", "message": "File ignored by sync rules"}

        # Resolve conflicts if vault file exists
        if vault_file.exists():
            resolution = self.conflict_resolver.resolve_conflict(local_file, vault_file)
            applied = self.conflict_resolver.apply_resolution(
                resolution, local_file, vault_file
            )
        else:
            # New file - just copy
            vault_file.parent.mkdir(parents=True, exist_ok=True)
            vault_file.write_text(
                local_file.read_text(encoding="utf-8"), encoding="utf-8"
            )
            applied = True
            resolution = {"status": "created", "action": "copy_local_to_vault"}

        # Log sync event
        log_entry = self.conflict_resolver.log_sync_event(
            "synced", str(local_file), resolution
        )
        self.sync_log.append(log_entry)

        return {
            "status": "success" if applied else "failed",
            "vault_file": str(vault_file),
            "resolution": resolution,
        }

    def sync_from_vault(self, vault_file: Path, force: bool = False) -> Dict[str, Any]:
        """Sync file from Obsidian vault to local directory.

        Args:
            vault_file: Path to vault file to sync.
            force: Force sync even if debounced.

        Returns:
            Sync result dictionary.
        """
        if not vault_file.exists():
            return {"status": "error", "message": "Vault file does not exist"}

        if not force and self.conflict_resolver.should_debounce(str(vault_file)):
            return {"status": "debounced", "message": "File sync debounced"}

        if not self.local_path:
            return {"status": "error", "message": "Local path not configured"}

        # Determine local file path
        local_file = self._get_local_file_path(vault_file)

        if self.conflict_resolver.should_ignore_file(str(local_file)):
            return {"status": "ignored", "message": "File ignored by sync rules"}

        # Resolve conflicts if local file exists
        if local_file.exists():
            resolution = self.conflict_resolver.resolve_conflict(local_file, vault_file)
            applied = self.conflict_resolver.apply_resolution(
                resolution, local_file, vault_file
            )
        else:
            # New file - just copy
            local_file.parent.mkdir(parents=True, exist_ok=True)
            local_file.write_text(
                vault_file.read_text(encoding="utf-8"), encoding="utf-8"
            )
            applied = True
            resolution = {"status": "created", "action": "copy_vault_to_local"}

        # Log sync event
        log_entry = self.conflict_resolver.log_sync_event(
            "synced", str(vault_file), resolution
        )
        self.sync_log.append(log_entry)

        return {
            "status": "success" if applied else "failed",
            "local_file": str(local_file),
            "resolution": resolution,
        }

    def _get_vault_file_path(self, local_file: Path) -> Path:
        """Map local file to vault file path.

        Args:
            local_file: Local file path.

        Returns:
            Corresponding vault file path.
        """
        if not self.vault_path or not self.local_path:
            return Path()

        # Try to preserve relative path structure
        try:
            relative_path = local_file.relative_to(self.local_path)
            return self.vault_path / "thinking" / relative_path
        except ValueError:
            # If not relative, use filename in thinking directory
            return self.vault_path / "thinking" / local_file.name

    def _get_local_file_path(self, vault_file: Path) -> Path:
        """Map vault file to local file path.

        Args:
            vault_file: Vault file path.

        Returns:
            Corresponding local file path.
        """
        if not self.vault_path or not self.local_path:
            return Path()

        # Extract filename and date if in thinking directory
        try:
            relative_path = vault_file.relative_to(self.vault_path / "thinking")
            return self.local_path / relative_path
        except ValueError:
            # If not in thinking directory, use filename in local path
            return self.local_path / vault_file.name

    def save_sync_log(self, log_file: Optional[Path] = None) -> str:
        """Save synchronization log to file.

        Args:
            log_file: Path to log file (default: .vault-metadata/sync-log.json).

        Returns:
            Path to saved log file.
        """
        if log_file is None:
            if not self.vault_path:
                return ""
            log_file = self.vault_path / ".vault-metadata" / "sync-log.json"

        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Prepare log data
        log_data = {
            "last_sync": datetime.now().isoformat(),
            "total_events": len(self.sync_log),
            "events": self.sync_log,
        }

        log_file.write_text(json.dumps(log_data, indent=2), encoding="utf-8")
        return str(log_file)

    def start_continuous_sync(self) -> None:
        """Start continuous file watching for sync."""
        if self.observer:
            logger.info("Continuous sync watcher already running")
        elif HAS_WATCHDOG:
            self._setup_watcher()
        else:
            logger.warning("watchdog not installed. Cannot start continuous sync.")

    def stop_continuous_sync(self) -> None:
        """Stop continuous file watching."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Stopped continuous sync watcher")


class VaultFileHandler(FileSystemEventHandler):
    """Handles file system events for vault directory."""

    def __init__(self, sync_manager: ObsidianSync):
        """Initialize vault file handler.

        Args:
            sync_manager: ObsidianSync instance.
        """
        self.sync_manager = sync_manager

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events.

        Args:
            event: File system event.
        """
        if event.is_directory:
            return

        filepath = Path(event.src_path)

        # Ignore certain files
        if self.sync_manager.conflict_resolver.should_ignore_file(str(filepath)):
            return

        # Only handle markdown files
        if filepath.suffix != ".md":
            return

        logger.debug(f"Vault file modified: {filepath}")

        # Sync from vault to local
        result = self.sync_manager.sync_from_vault(filepath)
        logger.info(f"Sync result: {result.get('status')}")
