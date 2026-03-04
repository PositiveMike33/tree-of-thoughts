"""
Vault Integration Package for Tree of Thoughts

Provides Obsidian Vault integration with OpenRouter LLM for creating
and organizing thought nodes across multiple sections.

Main Classes:
- SimplifiedVaultSync: CLI interface for vault operations
- ObsidianVaultIntegration: Vault file operations
- VaultSection: Enum of vault sections
- ThoughtNode: Dataclass for thought nodes
"""

from .tree_of_thoughts_vault_integration import (
    VaultSection,
    ThoughtNode,
    ObsidianVaultIntegration,
    VaultAwareLLMContext,
    ReportGenerator,
)
from .openrouter_config import LLMConfig, OpenRouterConfigManager
from .vault_sync_simple import SimplifiedVaultSync

__all__ = [
    "VaultSection",
    "ThoughtNode",
    "ObsidianVaultIntegration",
    "VaultAwareLLMContext",
    "ReportGenerator",
    "LLMConfig",
    "OpenRouterConfigManager",
    "SimplifiedVaultSync",
]

__version__ = "0.1.0"
