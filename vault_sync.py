#!/usr/bin/env python3
"""
vault_sync.py — Tree of Thoughts → Obsidian Vault CLI

Orchestrates a complete ToT session or periodic report generation,
writing results directly into the Obsidian vault.

Usage
-----
# Run a ToT session and write notes to the vault
python vault_sync.py --prompt "Quelle est ma prochaine étape spirituelle?" --algorithm BFS

# Generate a daily report
python vault_sync.py --report daily

# Override vault root (default: $VAULT_ROOT or /vault)
python vault_sync.py --prompt "..." --vault-root /path/to/vault

# Dry run — print output without writing to vault
python vault_sync.py --prompt "..." --dry-run
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("vault_sync")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    """Return env var value or exit with a clear message."""
    value = os.environ.get(name, "")
    if not value:
        logger.error(
            f"Environment variable {name!r} is not set. "
            f"Copy .env.example → .env and fill in your values."
        )
        sys.exit(1)
    return value


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vault_sync",
        description="Tree of Thoughts → Obsidian Vault synchroniser",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # --- Session mode ---
    session = parser.add_argument_group("Session mode (ToT reasoning)")
    session.add_argument(
        "--prompt", "-p",
        metavar="TEXT",
        help="The question or reflection to explore with Tree of Thoughts.",
    )
    session.add_argument(
        "--algorithm", "-a",
        choices=["BFS", "DFS", "MCTS", "BEST", "ASTAR"],
        default="BFS",
        help="Search algorithm (default: BFS).",
    )
    session.add_argument(
        "--section",
        choices=["PSYCHE", "BRAIN", "KNOWLEDGE", "RAPPORT"],
        default=None,
        help="Target vault section. Auto-detected from prompt if omitted.",
    )
    session.add_argument(
        "--num-thoughts", "-k",
        type=int,
        default=3,
        metavar="N",
        help="Thoughts generated per state per step (default: 3).",
    )
    session.add_argument(
        "--max-steps",
        type=int,
        default=3,
        metavar="N",
        help="Maximum reasoning depth / steps (default: 3).",
    )
    session.add_argument(
        "--max-states",
        type=int,
        default=5,
        metavar="N",
        help="Maximum states kept per step — BFS/MCTS only (default: 5).",
    )
    session.add_argument(
        "--value-threshold",
        type=float,
        default=0.5,
        metavar="F",
        help="Minimum score to keep a state — BFS/DFS (default: 0.5).",
    )
    session.add_argument(
        "--pruning-threshold",
        type=float,
        default=0.5,
        metavar="F",
        help="Pruning threshold for all algorithms (default: 0.5).",
    )

    # --- Report mode ---
    report = parser.add_argument_group("Report mode")
    report.add_argument(
        "--report",
        choices=["daily", "weekly", "monthly", "annual"],
        metavar="TYPE",
        help="Generate a vault report instead of a ToT session.",
    )
    report.add_argument(
        "--report-date",
        metavar="YYYY-MM-DD",
        help="Target date for daily report (default: today).",
    )
    report.add_argument(
        "--report-year",
        type=int,
        metavar="YYYY",
        help="Year for monthly/annual reports.",
    )
    report.add_argument(
        "--report-month",
        type=int,
        metavar="MM",
        help="Month number for monthly reports.",
    )
    report.add_argument(
        "--prompt-summary",
        metavar="TEXT",
        help="Personal reflections included verbatim in the daily report.",
    )

    # --- Infrastructure ---
    infra = parser.add_argument_group("Infrastructure")
    infra.add_argument(
        "--vault-root",
        metavar="PATH",
        default=os.environ.get("VAULT_ROOT", "/vault"),
        help="Vault root directory (default: $VAULT_ROOT or /vault).",
    )

    # Explicit section paths — prevent notes from mixing across sections.
    # In Docker: set via docker-compose volume targets.
    # Locally: set VAULT_*_PATH env vars or pass --*-path flags.
    infra.add_argument(
        "--psyche-path",
        metavar="PATH",
        default=os.environ.get("VAULT_PSYCHE_PATH"),
        help=(
            "Absolute path to _PSYCHE vault section. "
            "Default: $VAULT_PSYCHE_PATH or <vault-root>/_PSYCHE"
        ),
    )
    infra.add_argument(
        "--brain-path",
        metavar="PATH",
        default=os.environ.get("VAULT_BRAIN_PATH"),
        help=(
            "Absolute path to _BRAIN vault section. "
            "Default: $VAULT_BRAIN_PATH or <vault-root>/_BRAIN"
        ),
    )
    infra.add_argument(
        "--knowledge-path",
        metavar="PATH",
        default=os.environ.get("VAULT_KNOWLEDGE_PATH"),
        help=(
            "Absolute path to KNOWLEDGE vault section. "
            "Default: $VAULT_KNOWLEDGE_PATH or <vault-root>/KNOWLEDGE"
        ),
    )
    infra.add_argument(
        "--rapport-path",
        metavar="PATH",
        default=os.environ.get("VAULT_RAPPORT_PATH"),
        help=(
            "Absolute path to RAPPORT vault section. "
            "Default: $VAULT_RAPPORT_PATH or "
            "<vault-root>/RAPPORT QUOTIDIEN, HEBDOMADAIRE,MENSUEL & ANNUEL"
        ),
    )
    infra.add_argument(
        "--logs-dir",
        metavar="PATH",
        default="./logs",
        help="Directory for ToT session JSON files (default: ./logs).",
    )
    infra.add_argument(
        "--language",
        choices=["fr", "en"],
        default=os.environ.get("TOT_LANGUAGE", "fr"),
        help="Report/prompt language: fr (default) or en.",
    )
    infra.add_argument(
        "--model",
        default=os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-6"),
        help="Anthropic model ID (default: claude-opus-4-6).",
    )
    infra.add_argument(
        "--max-tokens",
        type=int,
        default=int(os.environ.get("TOT_MAX_TOKENS", "1500")),
        help="Max tokens per Claude response (default: 1500).",
    )
    infra.add_argument(
        "--temperature",
        type=float,
        default=float(os.environ.get("TOT_TEMPERATURE", "0.7")),
        help="Sampling temperature 0.0–1.0 (default: 0.7).",
    )
    infra.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be written without touching the vault.",
    )
    infra.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG logging.",
    )

    return parser


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _build_section_paths(args: argparse.Namespace) -> Optional[Dict[str, str]]:
    """
    Build an explicit section_paths dict from CLI args / env vars.

    If none of the --*-path flags are supplied the function returns None,
    which causes ObsidianVaultIntegration to derive paths from vault_root
    using the standard VAULT_SECTIONS mapping.

    When at least one explicit path is provided every section is pinned to
    prevent notes from drifting into the wrong directory.
    """
    from pathlib import Path as _Path

    vault_root = _Path(args.vault_root)

    # Windows → container path mapping (Docker Desktop WSL2 convention):
    #   D:/Vault/Vault/_PSYCHE  →  /vault/_PSYCHE  (via docker-compose bind mount)
    # When running locally the user can set VAULT_*_PATH directly.
    explicit = {
        "PSYCHE":    args.psyche_path,
        "BRAIN":     args.brain_path,
        "KNOWLEDGE": args.knowledge_path,
        "RAPPORT":   args.rapport_path,
    }

    # Defaults derived from vault_root (mirrors VAULT_SECTIONS constants)
    defaults = {
        "PSYCHE":    str(vault_root / "_PSYCHE"),
        "BRAIN":     str(vault_root / "_BRAIN"),
        "KNOWLEDGE": str(vault_root / "KNOWLEDGE"),
        "RAPPORT":   str(vault_root / "RAPPORT QUOTIDIEN, HEBDOMADAIRE,MENSUEL & ANNUEL"),
    }

    # Merge: explicit overrides default, both are always returned so every
    # section resolves to a deterministic, non-overlapping path.
    merged = {
        key: (explicit[key] if explicit[key] else defaults[key])
        for key in defaults
    }
    return merged


def run_report(args: argparse.Namespace) -> None:
    """Generate a periodic vault report."""
    from tree_of_thoughts.report_generator import VaultReportGenerator

    # VaultReportGenerator derives the RAPPORT section path from vault_root.
    # If the user supplied an explicit --rapport-path, use its parent as the
    # vault_root so the subdirectory logic resolves correctly.
    section_paths = _build_section_paths(args)
    rapport_path = section_paths["RAPPORT"] if section_paths else None

    if rapport_path and args.rapport_path:
        # Explicit RAPPORT path provided → pass its parent as vault_root so
        # VaultReportGenerator writes to the exact directory.
        from pathlib import Path as _P
        vault_root_for_report = str(_P(rapport_path).parent)
    else:
        vault_root_for_report = args.vault_root

    generator = VaultReportGenerator(
        vault_root=vault_root_for_report,
        logs_dir=args.logs_dir,
        language=args.language,
    )

    if args.dry_run:
        logger.info("[DRY RUN] Report would be generated but not written.")
        return

    report_type = args.report

    if report_type == "daily":
        target = (
            date.fromisoformat(args.report_date)
            if args.report_date
            else date.today()
        )
        path = generator.generate_daily_report(
            target_date=target,
            prompt_summary=args.prompt_summary,
        )
    elif report_type == "weekly":
        target = (
            date.fromisoformat(args.report_date)
            if args.report_date
            else date.today()
        )
        path = generator.generate_weekly_report(week_end_date=target)
    elif report_type == "monthly":
        path = generator.generate_monthly_report(
            year=args.report_year,
            month=args.report_month,
        )
    elif report_type == "annual":
        path = generator.generate_annual_report(year=args.report_year)
    else:
        logger.error(f"Unknown report type: {report_type}")
        sys.exit(1)

    print(f"\n✓ Report written: {path}\n")


# ---------------------------------------------------------------------------
# Session mode — ToT reasoning + vault write
# ---------------------------------------------------------------------------

def run_session(args: argparse.Namespace) -> None:
    """Run a Tree of Thoughts session and write results to the Obsidian vault."""
    # Validate API key early
    api_key = _require_env("ANTHROPIC_API_KEY")
    os.environ.setdefault("ANTHROPIC_API_KEY", api_key)

    from tree_of_thoughts.obsidian_vault_integration import ObsidianVaultIntegration
    from tree_of_thoughts.models.vault_aware_model import VaultAwareModel

    # --- Build vault integration with explicit section paths ---
    # Each section maps to its own isolated directory so notes never mix.
    section_paths = _build_section_paths(args)
    logger.info(f"Vault root  : {args.vault_root}")
    for sec, path in (section_paths or {}).items():
        logger.info(f"  [{sec}] → {path}")

    vault = ObsidianVaultIntegration(
        vault_root=args.vault_root,
        section_paths=section_paths,
        language=args.language,
    )

    # --- Determine target section ---
    if args.section:
        section = args.section
    else:
        section = vault.detect_vault_section(args.prompt)
        logger.info(f"Auto-detected vault section: {section}")

    # --- Build LLM ---
    logger.info(f"Loading VaultAwareModel ({args.model})…")
    model = VaultAwareModel(
        vault_integration=vault,
        model=args.model,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        language=args.language,
    )

    # --- Build solver ---
    logger.info(f"Building ToT solver: {args.algorithm}")
    solver = _build_solver(args.algorithm, model)

    # --- Run solve() ---
    logger.info(f"Starting ToT session — algorithm={args.algorithm}, k={args.num_thoughts}, steps={args.max_steps}")
    print(f"\n{'='*60}")
    print(f"  Tree of Thoughts — {args.algorithm}")
    print(f"  Prompt : {args.prompt[:80]}{'…' if len(args.prompt) > 80 else ''}")
    print(f"  Section: {section}")
    print(f"{'='*60}\n")

    solution = _run_solver(solver, args)

    if solution:
        print(f"\n{'='*60}")
        print("  SOLUTION SYNTHÉTISÉE / SYNTHESISED SOLUTION")
        print(f"{'='*60}")
        print(solution)
        print(f"{'='*60}\n")
    else:
        logger.warning("No solution was produced by the solver.")

    # --- Save tree JSON ---
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logs_path = Path(args.logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)
    json_filename = f"{logs_path}/session_{session_id}_{args.algorithm.lower()}.json"

    if hasattr(solver, "save_tree_to_json"):
        if args.dry_run:
            logger.info(f"[DRY RUN] Would save tree JSON to: {json_filename}")
        else:
            solver.save_tree_to_json(json_filename)
            logger.info(f"Tree JSON saved: {json_filename}")
    else:
        logger.warning(f"{args.algorithm} solver has no save_tree_to_json — skipping JSON export.")

    # --- Convert to Obsidian markdown ---
    if args.dry_run:
        logger.info("[DRY RUN] Would write vault notes. No files created.")
        return

    if not Path(json_filename).exists():
        logger.warning("JSON file not found — skipping vault write.")
        return

    vault_context = vault.read_vault_context()
    logger.info("Converting ToT tree to Obsidian notes…")
    written_paths = vault.convert_tree_to_markdown(
        tree_json_path=json_filename,
        prompt=args.prompt,
        algorithm=args.algorithm,
        session_id=session_id,
        target_section=section,
        vault_context=vault_context,
    )

    print(f"\n✓ {len(written_paths)} note(s) written to vault section [{section}]:")
    for p in written_paths:
        print(f"   {p}")
    print()

    # Refresh model context after writing so next call sees new notes
    model.refresh_vault_context()


def _build_solver(algorithm: str, model):
    """Instantiate the correct ToT solver class."""
    from tree_of_thoughts.treeofthoughts import (
        TreeofThoughtsBFS,
        TreeofThoughtsDFS,
        MonteCarloTreeofThoughts,
        TreeofThoughtsBEST,
        TreeofThoughtsASearch,
    )

    mapping = {
        "BFS": TreeofThoughtsBFS,
        "DFS": TreeofThoughtsDFS,
        "MCTS": MonteCarloTreeofThoughts,
        "BEST": TreeofThoughtsBEST,
        "ASTAR": TreeofThoughtsASearch,
    }
    cls = mapping[algorithm]
    return cls(model)


def _run_solver(solver, args: argparse.Namespace):
    """
    Call solver.solve() with the right signature for each algorithm.

    BFS  : initial_prompt, num_thoughts, max_steps, max_states, value_threshold, pruning_threshold
    DFS  : initial_prompt, num_thoughts, max_steps, value_threshold, pruning_threshold
    MCTS : initial_prompt, num_thoughts, max_steps, max_states, pruning_threshold
    BEST : initial_prompt, num_thoughts, max_steps, pruning_threshold
    ASTAR: initial_prompt, num_thoughts, max_steps, pruning_threshold
    """
    p = args.prompt
    k = args.num_thoughts
    steps = args.max_steps
    states = args.max_states
    vth = args.value_threshold
    pth = args.pruning_threshold
    alg = args.algorithm

    try:
        if alg == "BFS":
            return solver.solve(p, k, steps, states, vth, pth)
        elif alg == "DFS":
            return solver.solve(p, k, steps, vth, pth)
        elif alg == "MCTS":
            return solver.solve(p, k, steps, states, pth)
        elif alg in ("BEST", "ASTAR"):
            return solver.solve(p, k, steps, pth)
        else:
            logger.error(f"Unknown algorithm: {alg}")
            return None
    except Exception as exc:
        logger.error(f"Solver error ({alg}): {exc}", exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate: must specify --prompt or --report
    if not args.prompt and not args.report:
        parser.print_help()
        print("\nError: specify --prompt for a ToT session or --report for report generation.\n")
        sys.exit(1)

    if args.report:
        run_report(args)
    else:
        run_session(args)


if __name__ == "__main__":
    main()
