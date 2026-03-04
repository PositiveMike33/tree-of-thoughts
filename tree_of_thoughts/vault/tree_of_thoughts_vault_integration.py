"""
Tree of Thoughts Vault Integration

Core classes for managing Obsidian Vault structure, thought nodes,
and synthesis of information.
"""

import os
import uuid
import logging
import re
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple

logger = logging.getLogger(__name__)


class VaultSection(Enum):
    """Enumeration of vault sections for thought organization."""
    PSYCHE = "_PSYCHE"  # Inner thoughts, beliefs, reflections
    BRAIN = "_BRAIN"  # Reasoning, logic, analysis
    KNOWLEDGE = "KNOWLEDGE"  # Facts, information, learned concepts
    PLANNING = "PLANNING"  # Goals, strategies, action items
    RAPPORT = "RAPPORT"  # Relationships, connections, context


@dataclass
class ThoughtNode:
    """Represents a single thought node in the vault."""
    text: str  # Main content of the thought
    section: VaultSection  # Which section this belongs to
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    depth: int = 1  # Tree depth (0 = root)
    evaluation: float = 0.7  # Quality score (0-1)
    confidence: float = 0.8  # Confidence in this thought
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    tags: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None  # Reference to parent node
    language: str = "english"  # "english" or "french"
    metadata: Dict[str, str] = field(default_factory=dict)

    def get_word_count(self) -> int:
        """Return number of words in text."""
        return len(self.text.split())

    def is_complete(self, min_words: int = 300) -> bool:
        """Check if node has minimum content.

        Args:
            min_words: Minimum word count

        Returns:
            True if node meets minimum content requirement
        """
        return self.get_word_count() >= min_words


class ObsidianVaultIntegration:
    """Handles all file operations with Obsidian vault."""

    def __init__(self, vault_root: Optional[str] = None):
        """Initialize vault integration.

        Args:
            vault_root: Root path of vault. Loads from VAULT_ROOT env if None.

        Raises:
            ValueError: If vault_root cannot be determined
        """
        if vault_root is None:
            vault_root = os.getenv("VAULT_ROOT")
            if not vault_root:
                vault_root = "./vault"  # Default to ./vault

        self.vault_root = Path(vault_root).expanduser().resolve()
        self.vault_root.mkdir(parents=True, exist_ok=True)
        self._ensure_section_structure()
        logger.info(f"Vault initialized at: {self.vault_root}")

    def _ensure_section_structure(self):
        """Create directory structure for each section with ToT subfolder."""
        for section in VaultSection:
            section_dir = self.vault_root / section.value
            tot_dir = section_dir / "ToT"
            tot_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured section structure: {tot_dir}")

    def get_section_path(self, section: VaultSection, is_tot: bool = True) -> Path:
        """Get path to section directory.

        Args:
            section: The vault section
            is_tot: If True, returns path to ToT subfolder

        Returns:
            Path object to section directory
        """
        section_path = self.vault_root / section.value
        if is_tot:
            return section_path / "ToT"
        return section_path

    def create_note(self, node: ThoughtNode) -> Path:
        """Create markdown note file for thought node.

        Args:
            node: ThoughtNode to persist

        Returns:
            Path to created note file
        """
        section_path = self.get_section_path(node.section, is_tot=True)
        file_path = section_path / f"{node.id}.md"

        markdown_content = self._generate_markdown(node)
        file_path.write_text(markdown_content, encoding='utf-8')

        logger.info(f"Created note: {file_path}")
        return file_path

    def _generate_markdown(self, node: ThoughtNode) -> str:
        """Generate markdown content for thought node.

        Returns:
            Complete markdown string with frontmatter and content
        """
        # YAML frontmatter with metadata
        tags_str = ", ".join(node.tags) if node.tags else ""
        frontmatter = f"""---
id: {node.id}
section: {node.section.value}
depth: {node.depth}
evaluation: {node.evaluation:.2f}
confidence: {node.confidence:.2f}
timestamp: {node.timestamp}
tags: {tags_str}
language: {node.language}
type: thought_node
---

"""

        # Title
        title = f"# {node.id} — {node.section.value}\n\n"

        # Pensée/Thought section (main content)
        pensee_header = f"## Pensée / Thought\n\n{node.text}\n\n"

        # Context section (metadata and relationships)
        context = self._generate_context_section(node)

        return frontmatter + title + pensee_header + context

    def _generate_context_section(self, node: ThoughtNode) -> str:
        """Generate context section with metadata and wikilinks.

        Returns:
            Markdown string for context section
        """
        context = "## Contexte / Context\n\n"

        if node.parent_id:
            context += f"**Parent**: [[{node.parent_id}]]\n\n"

        context += f"**Section**: [[{node.section.value}]]\n"
        context += f"**Depth**: {node.depth}\n"
        context += f"**Evaluation**: {node.evaluation:.1%}\n"
        context += f"**Confidence**: {node.confidence:.1%}\n"
        context += f"**Language**: {node.language}\n"
        context += f"**Created**: {node.timestamp}\n\n"

        if node.tags:
            tags_md = ", ".join([f"`{tag}`" for tag in node.tags])
            context += f"**Tags**: {tags_md}\n\n"

        if node.metadata:
            context += "**Metadata**:\n"
            for key, value in node.metadata.items():
                context += f"- {key}: {value}\n"
            context += "\n"

        return context

    def create_synthesis_note(
        self,
        nodes: List[ThoughtNode],
        section: VaultSection,
        title: str,
        original_prompt: str
    ) -> Path:
        """Create synthesis note aggregating all nodes.

        Args:
            nodes: List of ThoughtNode objects
            section: The vault section
            title: Synthesis title
            original_prompt: Original question/prompt

        Returns:
            Path to created synthesis note
        """
        section_path = self.get_section_path(section, is_tot=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = section_path / f"synthesis_{title}_{timestamp}.md"

        # Sort nodes by evaluation
        sorted_nodes = sorted(nodes, key=lambda n: n.evaluation, reverse=True)

        content = f"""# Synthesis: {title}

**Generated**: {datetime.now().isoformat()}
**Section**: {section.value}
**Original Prompt**: {original_prompt}

## Summary

Total thought nodes created: {len(nodes)}

### Nodes by Evaluation Score

"""

        # Add node references with scores
        for i, node in enumerate(sorted_nodes, 1):
            content += f"{i}. [[{node.id}]] - {node.evaluation:.1%} confidence\n"

        content += "\n## Full Nodes\n\n"

        # Add full content of each node
        for node in sorted_nodes:
            content += f"### {node.id}\n\n"
            content += f"**Evaluation**: {node.evaluation:.1%}\n"
            content += f"**Confidence**: {node.confidence:.1%}\n"
            content += f"**Words**: {node.get_word_count()}\n\n"
            content += f"{node.text}\n\n"
            content += "---\n\n"

        file_path.write_text(content, encoding='utf-8')
        logger.info(f"Created synthesis: {file_path}")
        return file_path

    def create_neural_map(self, section: VaultSection) -> Path:
        """Create neural map with Mermaid diagram.

        Args:
            section: The vault section

        Returns:
            Path to neural_map file
        """
        section_path = self.get_section_path(section, is_tot=True)
        file_path = section_path / "neural_map.md"

        # Read all notes in section
        notes = list(section_path.glob("*.md"))
        notes = [n for n in notes if n.name != "neural_map.md" and not n.name.startswith("synthesis_")]

        content = f"""# Neural Map: {section.value}

**Generated**: {datetime.now().isoformat()}
**Total Nodes**: {len(notes)}

## Graph Structure

```mermaid
graph TD
    root["{section.value}"]
"""

        # Add nodes to graph
        for note_path in notes:
            node_id = note_path.stem
            content += f"    {node_id}[\"{node_id}\"]\n"
            content += f"    root --> {node_id}\n"

        content += """```

## Node Connections

"""

        # Add simple node listing
        for note_path in sorted(notes):
            content += f"- [[{note_path.stem}]]\n"

        file_path.write_text(content, encoding='utf-8')
        logger.info(f"Created neural map: {file_path}")
        return file_path


class VaultAwareLLMContext:
    """Manages system prompts aware of vault structure and language."""

    @staticmethod
    def get_system_prompt(
        section: VaultSection,
        language: str = "english",
        additional_context: str = ""
    ) -> str:
        """Get section-specific system prompt.

        Args:
            section: The vault section for context
            language: "english" or "french"
            additional_context: Extra context to include

        Returns:
            System prompt string for LLM
        """
        prompts = {
            VaultSection.PSYCHE: {
                "english": (
                    "You are a compassionate psychological guide exploring inner landscape. "
                    "Provide COMPLETE, DETAILED answers examining beliefs, emotions, and personal growth. "
                    "Structure your response in at least 3 DISTINCT COMPLETE sections, each examining "
                    "different psychological aspects. Each section should be 300+ words with:\n"
                    "- Deep introspection and nuanced analysis\n"
                    "- Concrete examples and personal applications\n"
                    "- Reflective questions for self-discovery\n"
                    "- Healing perspectives and growth insights\n"
                    "Be thorough, vulnerable, and transformative. Do NOT truncate or abbreviate."
                ),
                "french": (
                    "Vous êtes un guide psychologique bienveillant explorant le paysage intérieur. "
                    "Fournissez des réponses COMPLÈTES et DÉTAILLÉES examinant croyances, émotions, "
                    "et croissance personnelle. Structurez votre réponse en au moins 3 sections "
                    "DISTINCTES et COMPLÈTES, chacune examinant différents aspects psychologiques. "
                    "Chaque section doit faire 300+ mots avec:\n"
                    "- Introspection profonde et analyse nuancée\n"
                    "- Exemples concrets et applications personnelles\n"
                    "- Questions réflexives pour l'auto-découverte\n"
                    "- Perspectives curatives et insights de croissance\n"
                    "Soyez exhaustif, vulnérable, et transformateur. Ne tronquez pas."
                )
            },
            VaultSection.BRAIN: {
                "english": (
                    "You are operating in analytical reasoning mode. "
                    "Provide COMPLETE logical analysis with step-by-step reasoning. "
                    "Structure arguments in distinct sections (minimum 2). "
                    "Include:\n"
                    "- Clear assumptions and premises\n"
                    "- Logical deduction and evidence\n"
                    "- Multiple perspectives and counterarguments\n"
                    "- Synthesis and conclusions\n"
                    "Do NOT abbreviate or truncate reasoning."
                ),
                "french": (
                    "Vous êtes en mode raisonnement analytique. "
                    "Fournissez une analyse COMPLÈTE avec raisonnement étape par étape. "
                    "Structurez les arguments en sections distinctes (minimum 2). "
                    "Incluez:\n"
                    "- Hypothèses et prémisses claires\n"
                    "- Déduction logique et preuves\n"
                    "- Perspectives multiples et contre-arguments\n"
                    "- Synthèse et conclusions\n"
                    "Ne tronquez pas le raisonnement."
                )
            },
            VaultSection.KNOWLEDGE: {
                "english": (
                    "You are building a comprehensive knowledge base. "
                    "Present information systematically and COMPLETELY. "
                    "Be exhaustive and well-organized. "
                    "Do NOT abbreviate or omit important details. "
                    "Include:\n"
                    "- Definitions and core concepts\n"
                    "- Historical context and evolution\n"
                    "- Current understanding and research\n"
                    "- Practical applications"
                ),
                "french": (
                    "Vous construisez une base de connaissances complète. "
                    "Présentez les informations systématiquement et COMPLÈTEMENT. "
                    "Soyez exhaustif et bien organisé. "
                    "Ne tronquez pas les détails importants."
                )
            },
            VaultSection.PLANNING: {
                "english": (
                    "You are developing strategic plans. "
                    "Provide COMPLETE, detailed planning with actionable steps. "
                    "Structure with multiple sections covering:\n"
                    "- Goals and objectives\n"
                    "- Strategic approaches\n"
                    "- Specific action steps\n"
                    "- Timeline and milestones\n"
                    "- Resource requirements\n"
                    "Be thorough and practical."
                ),
                "french": (
                    "Vous développez des plans stratégiques. "
                    "Fournissez une planification COMPLÈTE avec étapes concrètes."
                )
            },
            VaultSection.RAPPORT: {
                "english": (
                    "You are fostering relationships and connections. "
                    "Provide COMPLETE analysis of relational aspects. "
                    "Include:\n"
                    "- Relationship dynamics\n"
                    "- Communication patterns\n"
                    "- Connection opportunities\n"
                    "- Conflict resolution approaches"
                ),
                "french": (
                    "Vous cultivez les relations et les connexions. "
                    "Fournissez une analyse COMPLÈTE des aspects relationnels."
                )
            }
        }

        base_prompt = prompts.get(section, {}).get(
            language,
            prompts.get(section, {}).get("english", "")
        )

        if additional_context:
            return f"{base_prompt}\n\n{additional_context}"
        return base_prompt


class ReportGenerator:
    """Synthesizes vault nodes into neural maps and summary reports."""

    def __init__(self, vault_integration: ObsidianVaultIntegration):
        """Initialize report generator with vault access.

        Args:
            vault_integration: ObsidianVaultIntegration instance
        """
        self.vault = vault_integration

    def generate_synthesis_report(
        self,
        section: VaultSection,
        min_evaluation: float = 0.6
    ) -> str:
        """Generate synthesis report for a section's thoughts.

        Args:
            section: The section to synthesize
            min_evaluation: Minimum evaluation score to include

        Returns:
            Markdown string with synthesis report
        """
        section_path = self.vault.get_section_path(section, is_tot=True)

        # Read all note files
        note_files = list(section_path.glob("*.md"))
        note_files = [n for n in note_files if not n.name.startswith("synthesis_")]

        # Parse evaluation from frontmatter if available
        high_eval_notes = []
        for note_file in note_files:
            # Simple heuristic: files with higher evaluation scores
            high_eval_notes.append(note_file.stem)

        report = f"# {section.value} Synthesis Report\n\n"
        report += f"**Generated**: {datetime.now().isoformat()}\n"
        report += f"**Section**: {section.value}\n"
        report += f"**Total Notes**: {len(note_files)}\n\n"
        report += "## Indexed Nodes\n\n"

        for note_stem in sorted(high_eval_notes)[:10]:  # Limit to 10
            report += f"- [[{note_stem}]]\n"

        return report

    def generate_daily_report(self) -> Path:
        """Generate daily report.

        Returns:
            Path to generated report file
        """
        timestamp = datetime.now().strftime("%Y-%m-%d")
        report_path = self.vault.vault_root / f"daily_report_{timestamp}.md"

        content = f"""# Daily Report: {timestamp}

Generated: {datetime.now().isoformat()}

## Sections Overview

"""

        for section in VaultSection:
            section_path = self.vault.get_section_path(section, is_tot=True)
            note_files = list(section_path.glob("*.md"))
            note_files = [n for n in note_files if not n.name.startswith("synthesis_") and n.name != "neural_map.md"]

            content += f"### {section.value}\n"
            content += f"- Total nodes: {len(note_files)}\n\n"

        report_path.write_text(content, encoding='utf-8')
        logger.info(f"Created daily report: {report_path}")
        return report_path

    def generate_weekly_report(self) -> Path:
        """Generate weekly report.

        Returns:
            Path to generated report file
        """
        timestamp = datetime.now().strftime("%Y-W%W")
        report_path = self.vault.vault_root / f"weekly_report_{timestamp}.md"

        content = f"""# Weekly Report: {timestamp}

Generated: {datetime.now().isoformat()}

## Summary

Weekly overview of vault activity across all sections.

"""

        report_path.write_text(content, encoding='utf-8')
        logger.info(f"Created weekly report: {report_path}")
        return report_path

    def generate_monthly_report(self) -> Path:
        """Generate monthly report.

        Returns:
            Path to generated report file
        """
        timestamp = datetime.now().strftime("%Y-%m")
        report_path = self.vault.vault_root / f"monthly_report_{timestamp}.md"

        content = f"""# Monthly Report: {timestamp}

Generated: {datetime.now().isoformat()}

## Summary

Monthly overview of vault activity and insights.

"""

        report_path.write_text(content, encoding='utf-8')
        logger.info(f"Created monthly report: {report_path}")
        return report_path
