"""
Configuration and enums for Tree of Thoughts skills.

Defines skill types, algorithm choices, confidence thresholds, and configuration dataclasses.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, Tuple


class SkillType(Enum):
    """Types of available skills."""
    RESEARCH = "research"              # Research analyst skill
    DECISION = "decision"              # Decision maker skill
    CODE_REVIEW = "code_review"        # Code reviewer skill
    THESIS = "thesis"                  # Thesis validator skill
    PROBLEM = "problem"                # Problem solver skill
    EXPERT = "expert"                  # Expert simulator skill


class AlgorithmType(Enum):
    """Tree of Thoughts algorithms available for skills."""
    BFS = "bfs"                        # Breadth-first search
    DFS = "dfs"                        # Depth-first search
    BEST = "best"                      # Best-first search
    A_STAR = "a_star"                  # A* search with heuristic
    MCTS = "mcts"                      # Monte Carlo Tree Search


class ConfidenceThresholdType(Enum):
    """Confidence level thresholds."""
    MINIMUM = 0.3                      # Minimum acceptable confidence
    LOW = 0.5                          # Low confidence threshold
    MEDIUM = 0.7                       # Medium confidence threshold
    HIGH = 0.85                        # High confidence threshold
    VERY_HIGH = 0.95                   # Very high confidence threshold


class VaultSection(Enum):
    """Vault sections for persisting skill results."""
    PSYCHE = "PSYCHE"                  # Psychological/reasoning insights
    BRAIN = "BRAIN"                    # Logical/analytical findings
    KNOWLEDGE = "KNOWLEDGE"            # Domain knowledge
    PLANNING = "PLANNING"              # Plans and decisions
    RAPPORT = "RAPPORT"                # Relationships and synthesis


@dataclass
class SkillConfig:
    """Configuration for a skill instance."""

    # Basic settings
    skill_type: SkillType
    algorithm: AlgorithmType
    name: str = ""                     # Display name
    description: str = ""              # Skill description

    # ToT parameters
    num_thoughts: int = 5              # Number of thoughts to generate per step
    max_steps: int = 5                 # Maximum depth of reasoning

    # Confidence settings
    confidence_threshold: float = 0.75 # Minimum confidence for accepting result
    require_fact_check: bool = True    # Whether to fact-check claims
    require_blind_validation: bool = True  # Whether to use blind validation

    # Vault settings
    vault_section: VaultSection = VaultSection.BRAIN
    persist_results: bool = True       # Whether to save results to vault

    # Performance settings
    timeout_seconds: int = 30          # Maximum execution time
    max_tokens: int = 5000             # Token budget for LLM

    # Domain-specific settings
    extra_config: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> Tuple[bool, str]:
        """Validate that configuration is valid.

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if self.num_thoughts < 1:
            return False, "num_thoughts must be >= 1"
        if self.max_steps < 1:
            return False, "max_steps must be >= 1"
        if not (0.0 <= self.confidence_threshold <= 1.0):
            return False, "confidence_threshold must be between 0.0 and 1.0"
        if self.timeout_seconds < 1:
            return False, "timeout_seconds must be >= 1"
        if self.max_tokens < 100:
            return False, "max_tokens must be >= 100"
        return True, ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "skill_type": self.skill_type.value,
            "algorithm": self.algorithm.value,
            "name": self.name,
            "description": self.description,
            "num_thoughts": self.num_thoughts,
            "max_steps": self.max_steps,
            "confidence_threshold": self.confidence_threshold,
            "require_fact_check": self.require_fact_check,
            "require_blind_validation": self.require_blind_validation,
            "vault_section": self.vault_section.value,
            "persist_results": self.persist_results,
            "timeout_seconds": self.timeout_seconds,
            "max_tokens": self.max_tokens,
            "extra_config": self.extra_config,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillConfig':
        """Create config from dictionary."""
        return cls(
            skill_type=SkillType(data.get("skill_type", "problem")),
            algorithm=AlgorithmType(data.get("algorithm", "bfs")),
            name=data.get("name", ""),
            description=data.get("description", ""),
            num_thoughts=data.get("num_thoughts", 5),
            max_steps=data.get("max_steps", 5),
            confidence_threshold=data.get("confidence_threshold", 0.75),
            require_fact_check=data.get("require_fact_check", True),
            require_blind_validation=data.get("require_blind_validation", True),
            vault_section=VaultSection(data.get("vault_section", "BRAIN")),
            persist_results=data.get("persist_results", True),
            timeout_seconds=data.get("timeout_seconds", 30),
            max_tokens=data.get("max_tokens", 5000),
            extra_config=data.get("extra_config", {}),
        )


# Default skill configurations
DEFAULT_CONFIGS = {
    SkillType.RESEARCH: SkillConfig(
        skill_type=SkillType.RESEARCH,
        algorithm=AlgorithmType.A_STAR,
        name="Research Analyst",
        description="Comprehensive research with verified sources",
        num_thoughts=8,
        max_steps=7,
        confidence_threshold=0.75,
        vault_section=VaultSection.KNOWLEDGE,
    ),
    SkillType.DECISION: SkillConfig(
        skill_type=SkillType.DECISION,
        algorithm=AlgorithmType.BEST,
        name="Decision Maker",
        description="Multi-option evaluation and recommendation",
        num_thoughts=6,
        max_steps=5,
        confidence_threshold=0.80,
        vault_section=VaultSection.PLANNING,
    ),
    SkillType.CODE_REVIEW: SkillConfig(
        skill_type=SkillType.CODE_REVIEW,
        algorithm=AlgorithmType.BFS,
        name="Code Reviewer",
        description="Code quality and security analysis",
        num_thoughts=5,
        max_steps=6,
        confidence_threshold=0.75,
        vault_section=VaultSection.BRAIN,
    ),
    SkillType.THESIS: SkillConfig(
        skill_type=SkillType.THESIS,
        algorithm=AlgorithmType.MCTS,
        name="Thesis Validator",
        description="Academic claim validation",
        num_thoughts=7,
        max_steps=8,
        confidence_threshold=0.80,
        vault_section=VaultSection.KNOWLEDGE,
    ),
    SkillType.PROBLEM: SkillConfig(
        skill_type=SkillType.PROBLEM,
        algorithm=AlgorithmType.BFS,
        name="Problem Solver",
        description="Multi-solution path exploration",
        num_thoughts=6,
        max_steps=7,
        confidence_threshold=0.75,
        vault_section=VaultSection.PLANNING,
    ),
    SkillType.EXPERT: SkillConfig(
        skill_type=SkillType.EXPERT,
        algorithm=AlgorithmType.DFS,
        name="Expert Simulator",
        description="Domain expertise simulation",
        num_thoughts=5,
        max_steps=8,
        confidence_threshold=0.80,
        vault_section=VaultSection.BRAIN,
    ),
}


def get_default_config(skill_type: SkillType) -> SkillConfig:
    """Get default configuration for a skill type."""
    return DEFAULT_CONFIGS.get(skill_type, DEFAULT_CONFIGS[SkillType.PROBLEM])
