"""Conflict resolution for bidirectional synchronization.

Uses Last Write Wins (LWWM) strategy for conflict resolution.
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class ConflictResolver:
    """Resolve conflicts using Last Write Wins (LWWM) merge strategy."""

    # Debounce settings to prevent sync loops
    MIN_SYNC_INTERVAL_SECONDS = 0.5
    IGNORE_PATTERNS = [".conflict-", ".metadata-"]

    def __init__(
        self, vault_path: Optional[Path] = None, local_path: Optional[Path] = None
    ):
        """Initialize conflict resolver.

        Args:
            vault_path: Path to Obsidian vault (D:/Vault/Vault/).
            local_path: Path to local exports directory.
        """
        self.vault_path = Path(vault_path) if vault_path else None
        self.local_path = Path(local_path) if local_path else None
        self.last_sync_times = {}  # Track last sync time per file

    def should_ignore_file(self, filepath: str) -> bool:
        """Check if file should be ignored in sync.

        Args:
            filepath: Path to file to check.

        Returns:
            True if file should be ignored, False otherwise.
        """
        filename = Path(filepath).name
        for pattern in self.IGNORE_PATTERNS:
            if pattern in filename:
                return True
        return False

    def resolve_conflict(self, local_file: Path, vault_file: Path) -> Dict[str, Any]:
        """Resolve conflict between local and vault versions using LWWM.

        Args:
            local_file: Path to local file.
            vault_file: Path to vault file.

        Returns:
            Dict with resolution decision and metadata.
        """
        # Get file modification times and checksums
        local_mtime = local_file.stat().st_mtime if local_file.exists() else 0
        vault_mtime = vault_file.stat().st_mtime if vault_file.exists() else 0

        local_content = (
            local_file.read_text(encoding="utf-8") if local_file.exists() else ""
        )
        vault_content = (
            vault_file.read_text(encoding="utf-8") if vault_file.exists() else ""
        )

        local_hash = self._compute_hash(local_content)
        vault_hash = self._compute_hash(vault_content)

        # Determine action based on timestamps and hashes
        if local_hash == vault_hash:
            # Content identical, no action needed
            return {
                "status": "identical",
                "action": "none",
                "winner": None,
                "message": "Files are identical, no sync needed.",
            }

        elif local_mtime > vault_mtime:
            # Local is newer
            return {
                "status": "conflict",
                "action": "copy_local_to_vault",
                "winner": "local",
                "message": (
                    f"Local file is newer ({local_mtime} > {vault_mtime}). "
                    "Copying to vault."
                ),
                "local_mtime": local_mtime,
                "vault_mtime": vault_mtime,
            }

        elif vault_mtime > local_mtime:
            # Vault is newer
            return {
                "status": "conflict",
                "action": "copy_vault_to_local",
                "winner": "vault",
                "message": (
                    f"Vault file is newer ({vault_mtime} > {local_mtime}). "
                    "Copying to local."
                ),
                "local_mtime": local_mtime,
                "vault_mtime": vault_mtime,
            }

        else:
            # Same mtime but different content - create conflict file
            return {
                "status": "genuine_conflict",
                "action": "create_conflict_file",
                "winner": None,
                "message": (
                    "Same timestamp but different content. " "Creating conflict file."
                ),
                "local_hash": local_hash,
                "vault_hash": vault_hash,
            }

    def apply_resolution(
        self, resolution: Dict[str, Any], local_file: Path, vault_file: Path
    ) -> bool:
        """Apply the resolved action.

        Args:
            resolution: Resolution decision from resolve_conflict().
            local_file: Path to local file.
            vault_file: Path to vault file.

        Returns:
            True if action applied successfully, False otherwise.
        """
        action = resolution.get("action")

        try:
            if action == "none":
                return True

            elif action == "copy_local_to_vault":
                if local_file.exists() and vault_file.parent.exists():
                    vault_file.write_text(
                        local_file.read_text(encoding="utf-8"), encoding="utf-8"
                    )
                    return True

            elif action == "copy_vault_to_local":
                if vault_file.exists() and local_file.parent.exists():
                    local_file.write_text(
                        vault_file.read_text(encoding="utf-8"), encoding="utf-8"
                    )
                    return True

            elif action == "create_conflict_file":
                return self._create_conflict_file(local_file, vault_file)

            return False

        except Exception as e:
            print(f"Error applying resolution: {e}")
            return False

    def _create_conflict_file(self, local_file: Path, vault_file: Path) -> bool:
        """Create a conflict marker file with both versions.

        Args:
            local_file: Path to local file.
            vault_file: Path to vault file.

        Returns:
            True if conflict file created successfully.
        """
        conflict_filename = (
            f"{vault_file.stem}.conflict-{datetime.now().isoformat()}.md"
        )
        conflict_path = vault_file.parent / conflict_filename

        local_content = (
            local_file.read_text(encoding="utf-8") if local_file.exists() else ""
        )
        vault_content = (
            vault_file.read_text(encoding="utf-8") if vault_file.exists() else ""
        )

        conflict_content = f"""# ⚠️ CONFLICT: {vault_file.name}

**Generated**: {datetime.now().isoformat()}

## LOCAL VERSION (Tree of Thoughts)
```
{local_content}
```

## VAULT VERSION (Obsidian)
```
{vault_content}
```

## Resolution Instructions
1. Review both versions above
2. Merge the changes manually if needed
3. Delete this conflict file once resolved
4. Rename the final version back to the original filename
"""

        try:
            conflict_path.write_text(conflict_content, encoding="utf-8")
            return True
        except Exception as e:
            print(f"Error creating conflict file: {e}")
            return False

    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content.

        Args:
            content: Content to hash.

        Returns:
            Hex hash string.
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def log_sync_event(
        self,
        event_type: str,
        filename: str,
        resolution: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log a synchronization event.

        Args:
            event_type: Type of event (created, modified, deleted, conflicted).
            filename: File that was synced.
            resolution: Optional resolution data.

        Returns:
            Event log entry.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "filename": filename,
            "resolution": resolution or {},
        }
        return entry

    def should_debounce(self, filepath: str, sync_timeout: float = None) -> bool:
        """Check if file should be debounced (avoid re-sync).

        Args:
            filepath: Path to file.
            sync_timeout: Timeout in seconds (default: MIN_SYNC_INTERVAL_SECONDS).

        Returns:
            True if file should be debounced, False otherwise.
        """
        if sync_timeout is None:
            sync_timeout = self.MIN_SYNC_INTERVAL_SECONDS

        if filepath not in self.last_sync_times:
            self.last_sync_times[filepath] = datetime.now().timestamp()
            return False

        elapsed = datetime.now().timestamp() - self.last_sync_times[filepath]
        if elapsed < sync_timeout:
            return True

        self.last_sync_times[filepath] = datetime.now().timestamp()
        return False
