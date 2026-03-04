"""
Simplified Vault Sync CLI

Main command-line interface for running thought node sessions
and managing vault operations through OpenRouter LLM.
"""

import argparse
import json
import re
import logging
import sys
import uuid
from typing import List, Optional, Tuple
from pathlib import Path

from .openrouter_config import LLMConfig, OpenRouterConfigManager
from .tree_of_thoughts_vault_integration import (
    VaultSection,
    ThoughtNode,
    ObsidianVaultIntegration,
    VaultAwareLLMContext,
    ReportGenerator,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class SimplifiedVaultSync:
    """Simplified CLI wrapper for vault sync operations."""

    def __init__(self, vault_root: Optional[str] = None):
        """Initialize vault sync with configuration.

        Args:
            vault_root: Optional vault root path

        Raises:
            ValueError: If configuration cannot be loaded
        """
        try:
            self.config = OpenRouterConfigManager.load_from_env()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            raise

        self.vault = ObsidianVaultIntegration(vault_root)
        self.llm_context = VaultAwareLLMContext()
        self.llm_client = OpenRouterConfigManager.create_llm_client(self.config)
        self.reports = ReportGenerator(self.vault)

        logger.info(f"✓ LLM Provider: {self.config.provider}")
        logger.info(f"✓ Model: {self.config.model}")

    def session(
        self,
        prompt: str,
        section: str = "BRAIN",
        language: str = "english",
        depth: int = 0,
        parent_id: Optional[str] = None,
        verbose: bool = False
    ) -> dict:
        """Run a single session and create nodes from response.

        Args:
            prompt: User prompt/question
            section: Vault section name
            language: Response language ("english" or "french")
            depth: Tree depth for evaluation
            parent_id: Parent node ID for relationships
            verbose: Enable verbose logging

        Returns:
            Dictionary with created nodes and response metadata
        """
        # Validate section
        try:
            vault_section = VaultSection[section.upper()]
        except KeyError:
            raise ValueError(
                f"Invalid section: {section}. "
                f"Choose: {', '.join([s.name for s in VaultSection])}"
            )

        logger.info(f"[STARTING SESSION]")
        logger.info(f"Section: {vault_section.value}")
        logger.info(f"Depth: {depth}")
        logger.info(f"Language: {language}")
        logger.info(f"Prompt: {prompt[:100]}...")

        # Get system prompt
        system_prompt = self.llm_context.get_system_prompt(
            vault_section,
            language
        )

        if verbose:
            logger.info(f"\n[SYSTEM PROMPT]\n{system_prompt}\n")

        # Call LLM with focus on completeness
        logger.info("[CALLING LLM]")
        try:
            response = self.llm_client.call(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.8,
                max_tokens=5000
            )
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

        logger.info(f"[RESPONSE RECEIVED] ({len(response)} characters)")

        # Check completeness
        is_complete = self._is_response_complete(response)
        if not is_complete:
            logger.warning("Response may be incomplete")

        # Parse response into thought nodes
        nodes = self._parse_response_to_nodes(
            response,
            vault_section,
            language,
            depth,
            parent_id
        )

        logger.info(f"[CREATED NODES] {len(nodes)} nodes")

        # Create vault notes
        created_nodes = []
        for node in nodes:
            try:
                path = self.vault.create_note(node)
                created_nodes.append({
                    "id": node.id,
                    "section": vault_section.value,
                    "path": str(path),
                    "words": node.get_word_count(),
                    "complete": node.is_complete(),
                    "evaluation": node.evaluation,
                    "confidence": node.confidence,
                })
                logger.info(f"✓ Node: {node.id} ({node.get_word_count()} words)")
            except Exception as e:
                logger.error(f"Failed to create node: {e}")

        # Generate synthesis
        logger.info("[GENERATING SYNTHESIS]")
        try:
            synthesis_path = self.vault.create_synthesis_note(
                nodes,
                vault_section,
                "Tree of Thoughts",
                prompt
            )
            synthesis_file = str(synthesis_path)
            logger.info(f"✓ Synthesis: {synthesis_path.name}")
        except Exception as e:
            logger.error(f"Synthesis generation failed: {e}")
            synthesis_file = ""

        # Generate neural map
        logger.info("[GENERATING NEURAL MAP]")
        try:
            neural_map_path = self.vault.create_neural_map(vault_section)
            neural_map_file = str(neural_map_path)
            logger.info(f"✓ Neural Map: {neural_map_path.name}")
        except Exception as e:
            logger.error(f"Neural map generation failed: {e}")
            neural_map_file = ""

        # Summary
        logger.info(f"\n[SUCCESS]")
        logger.info(f"Nodes created: {len(created_nodes)}")
        logger.info(f"Location: {self.vault.get_section_path(vault_section)}")

        return {
            "status": "success",
            "section": vault_section.value,
            "nodes_created": len(created_nodes),
            "nodes": created_nodes,
            "response_length": len(response),
            "tokens_used": self._estimate_tokens(response),
            "synthesis": synthesis_file,
            "neural_map": neural_map_file,
        }

    def _is_response_complete(self, response: str) -> bool:
        """Check if response appears complete (not truncated).

        Args:
            response: Response text to validate

        Returns:
            True if response appears complete
        """
        response = response.strip()

        # Check for incomplete trailing patterns
        incomplete_patterns = [
            r'\.\.\.$',  # Ellipsis at end
            r'[,;\(\[]$',  # Hanging punctuation
            r'(?:as mentioned|as discussed)$',  # Incomplete references
            r'(?:for example|such as)$',  # Unfinished lists
        ]

        # If response is very short, likely incomplete
        if len(response) < 200:
            logger.warning(f"Response very short ({len(response)} chars)")
            return False

        # Check for incomplete patterns
        for pattern in incomplete_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                logger.warning(f"Found incomplete pattern: {pattern}")
                return False

        return True

    def _parse_response_to_nodes(
        self,
        response: str,
        section: VaultSection,
        language: str,
        depth: int,
        parent_id: Optional[str]
    ) -> List[ThoughtNode]:
        """Parse response into multiple thought nodes.

        Strategy hierarchy:
        1. Split by markdown headers (## or ###)
        2. If no headers, split by numbered sections
        3. If no sections, split by paragraphs
        4. Validate each node has minimum content

        Args:
            response: Full LLM response
            section: VaultSection enum
            language: Response language
            depth: Tree depth
            parent_id: Parent node ID

        Returns:
            List of ThoughtNode objects
        """
        nodes = []
        segments = []

        logger.info("[PARSING RESPONSE]")

        # Strategy 1: Split by markdown headers
        header_pattern = r'^#{2,3}\s+(.+?)$'
        headers = list(re.finditer(header_pattern, response, re.MULTILINE))

        if len(headers) >= 2:
            segments = self._split_by_headers(response, headers)
            logger.info(f"Using header-based splitting: {len(segments)} segments")
        else:
            # Strategy 2: Split by numbered sections
            numbered_pattern = r'^\d+[\.\)]\s+(.+?)$'
            numbered = list(re.finditer(numbered_pattern, response, re.MULTILINE))

            if len(numbered) >= 2:
                segments = self._split_by_numbered(response, numbered)
                logger.info(f"Using numbered-based splitting: {len(segments)} segments")
            else:
                # Strategy 3: Split by paragraphs
                segments = self._split_by_paragraphs(response)
                logger.info(f"Using paragraph-based splitting: {len(segments)} segments")

        # Create ThoughtNode for each segment
        for idx, (title, content) in enumerate(segments):
            word_count = len(content.split())

            if word_count < 300:
                logger.debug(f"Skipping segment {idx}: too short ({word_count} words)")
                continue

            node = ThoughtNode(
                id=self._generate_node_id(section),
                text=content.strip(),
                section=section,
                depth=depth,
                evaluation=self._calculate_evaluation(idx, len(segments), depth),
                confidence=0.85,
                tags=[title] if title else [],
                parent_id=parent_id,
                language=language
            )
            nodes.append(node)
            logger.debug(f"Created node: {node.id} ({word_count} words)")

        # Fallback: treat entire response as single node if no segments
        if not nodes and len(response) >= 300:
            logger.warning("No segments found, treating entire response as single node")
            node = ThoughtNode(
                id=self._generate_node_id(section),
                text=response.strip(),
                section=section,
                depth=depth,
                evaluation=0.85,
                confidence=0.8,
                parent_id=parent_id,
                language=language
            )
            nodes.append(node)

        return nodes

    def _split_by_headers(
        self,
        response: str,
        headers: list
    ) -> List[Tuple[str, str]]:
        """Split response by markdown headers.

        Returns:
            List of (title, content) tuples
        """
        segments = []
        for i, header_match in enumerate(headers):
            title = header_match.group(1).strip()
            start = header_match.end()

            # End at next header or end of string
            if i < len(headers) - 1:
                end = headers[i + 1].start()
            else:
                end = len(response)

            content = response[start:end].strip()
            segments.append((title, content))

        return segments

    def _split_by_numbered(
        self,
        response: str,
        numbered: list
    ) -> List[Tuple[str, str]]:
        """Split response by numbered sections.

        Returns:
            List of (title, content) tuples
        """
        segments = []
        for i, match in enumerate(numbered):
            title = match.group(1).strip()
            start = match.end()

            if i < len(numbered) - 1:
                end = numbered[i + 1].start()
            else:
                end = len(response)

            content = response[start:end].strip()
            segments.append((title, content))

        return segments

    def _split_by_paragraphs(
        self,
        response: str,
        max_segments: int = 5
    ) -> List[Tuple[str, str]]:
        """Split response by paragraphs, limiting segments.

        Returns:
            List of (title, content) tuples
        """
        paragraphs = response.split('\n\n')
        segments = []

        # Filter out empty paragraphs
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        # Group paragraphs if too many
        if len(paragraphs) > max_segments:
            chunk_size = len(paragraphs) // max_segments
            for i in range(0, len(paragraphs), chunk_size):
                chunk = '\n\n'.join(paragraphs[i:i+chunk_size])
                title = f"Section {len(segments) + 1}"
                segments.append((title, chunk))
        else:
            for i, para in enumerate(paragraphs, 1):
                title = f"Section {i}"
                segments.append((title, para))

        return segments

    def _generate_node_id(self, section: VaultSection) -> str:
        """Generate unique node ID with section name.

        Format: {section_prefix}_{uuid_short}
        """
        short_uuid = str(uuid.uuid4())[:8]
        return f"{short_uuid}"

    def _calculate_evaluation(
        self,
        position: int,
        total: int,
        depth: int
    ) -> float:
        """Calculate evaluation score based on position and depth.

        Args:
            position: Position in segments (0-indexed)
            total: Total number of segments
            depth: Tree depth

        Returns:
            Evaluation score between 0.0 and 1.0
        """
        # Root nodes score higher
        depth_factor = 1.0 - (depth * 0.1)

        # Earlier segments score slightly higher
        position_factor = 1.0 - (position / (total * 2))

        return min(1.0, max(0.0, depth_factor * position_factor))

    def _estimate_tokens(self, response: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters).

        Args:
            response: Response text

        Returns:
            Estimated token count
        """
        return len(response) // 4

    def report(
        self,
        section: str = "BRAIN",
        report_type: str = "daily"
    ) -> dict:
        """Generate synthesis report for a section.

        Args:
            section: Vault section to report on
            report_type: Type of report (daily, weekly, monthly)

        Returns:
            Dictionary with report metadata
        """
        try:
            vault_section = VaultSection[section.upper()]
        except KeyError:
            raise ValueError(f"Invalid section: {section}")

        logger.info(f"[GENERATING {report_type.upper()} REPORT]")
        logger.info(f"Section: {vault_section.value}")

        # Generate report
        if report_type == "daily":
            report_path = self.reports.generate_daily_report()
        elif report_type == "weekly":
            report_path = self.reports.generate_weekly_report()
        elif report_type == "monthly":
            report_path = self.reports.generate_monthly_report()
        else:
            raise ValueError(f"Invalid report type: {report_type}")

        logger.info(f"✓ Report generated: {report_path.name}")

        return {
            "status": "success",
            "report_type": report_type,
            "section": vault_section.value,
            "path": str(report_path),
        }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Vault Sync - LLM-powered thought node creation for Obsidian",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a PSYCHE session in French
  python -m tree_of_thoughts.vault.vault_sync_simple session \\
    --prompt "Comment comprendre mes traumas complexes?" \\
    --section PSYCHE --language french

  # Run BRAIN session in English
  python -m tree_of_thoughts.vault.vault_sync_simple session \\
    --prompt "What is consciousness?" --section BRAIN

  # Generate daily report
  python -m tree_of_thoughts.vault.vault_sync_simple report --type daily
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Session command
    session_parser = subparsers.add_parser(
        "session",
        help="Run a session and create thought nodes"
    )
    session_parser.add_argument(
        "prompt",
        help="The prompt/question to explore"
    )
    session_parser.add_argument(
        "--section",
        choices=["PSYCHE", "BRAIN", "KNOWLEDGE", "PLANNING", "RAPPORT"],
        default="BRAIN",
        help="Vault section (default: BRAIN)"
    )
    session_parser.add_argument(
        "--language",
        choices=["english", "french"],
        default="english",
        help="Response language (default: english)"
    )
    session_parser.add_argument(
        "--depth",
        type=int,
        default=0,
        help="Tree depth for evaluation (default: 0)"
    )
    session_parser.add_argument(
        "--parent",
        help="Parent node ID for relationships"
    )
    session_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    # Report command
    report_parser = subparsers.add_parser(
        "report",
        help="Generate synthesis report"
    )
    report_parser.add_argument(
        "--section",
        choices=["PSYCHE", "BRAIN", "KNOWLEDGE", "PLANNING", "RAPPORT"],
        default="BRAIN",
        help="Section to report on (default: BRAIN)"
    )
    report_parser.add_argument(
        "--type",
        choices=["daily", "weekly", "monthly"],
        default="daily",
        help="Report type (default: daily)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        sync = SimplifiedVaultSync()

        if args.command == "session":
            result = sync.session(
                prompt=args.prompt,
                section=args.section,
                language=args.language,
                depth=args.depth,
                parent_id=args.parent,
                verbose=args.verbose
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0

        elif args.command == "report":
            result = sync.report(
                section=args.section,
                report_type=args.type
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        if "--verbose" in sys.argv or "-v" in sys.argv:
            import traceback
            traceback.print_exc()
        return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
