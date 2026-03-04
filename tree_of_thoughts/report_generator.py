"""
Vault Report Generator for Tree of Thoughts.

Aggregates ToT sessions and vault notes into structured periodic reports
(daily, weekly, monthly, annual) written to the Obsidian vault RAPPORT section.
"""

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


class VaultReportGenerator:
    """
    Generates structured periodic reports aggregating Tree of Thoughts sessions
    and vault notes, written to the RAPPORT section of the Obsidian vault.

    Report types:
        - daily:   Single day summary
        - weekly:  7-day synthesis
        - monthly: Full month review
        - annual:  Year-end review
    """

    REPORT_TYPES = {
        "daily":   {"label_fr": "Rapport Quotidien",    "label_en": "Daily Report",      "dir": "DAILY"},
        "weekly":  {"label_fr": "Synthèse Hebdomadaire","label_en": "Weekly Synthesis",   "dir": "WEEKLY"},
        "monthly": {"label_fr": "Bilan Mensuel",         "label_en": "Monthly Review",     "dir": "MONTHLY"},
        "annual":  {"label_fr": "Bilan Annuel",          "label_en": "Annual Review",      "dir": "ANNUAL"},
    }

    def __init__(
        self,
        vault_root: str,
        logs_dir: str = "./logs",
        language: str = "fr",
    ):
        """
        Parameters
        ----------
        vault_root:
            Absolute path to vault root (e.g. '/vault').
        logs_dir:
            Directory containing ToT session JSON files.
        language:
            'fr' or 'en'. Controls report language.
        """
        self.vault_root = Path(vault_root)
        self.logs_dir = Path(logs_dir)
        self.language = language
        self.rapport_dir = (
            self.vault_root
            / "RAPPORT QUOTIDIEN, HEBDOMADAIRE,MENSUEL & ANNUEL"
        )

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def generate_daily_report(
        self,
        target_date: Optional[date] = None,
        prompt_summary: Optional[str] = None,
    ) -> str:
        """
        Generate a daily report note.

        Parameters
        ----------
        target_date:
            Date to generate report for. Defaults to today.
        prompt_summary:
            Optional human-written intentions/reflections included verbatim.

        Returns the absolute path of the written file.
        """
        target_date = target_date or date.today()
        sessions = self._collect_sessions_for_range(target_date, target_date)
        vault_notes = self._collect_vault_notes_for_range(target_date, target_date)
        return self._write_report(
            report_type="daily",
            start_date=target_date,
            end_date=target_date,
            sessions=sessions,
            vault_notes=vault_notes,
            prompt_summary=prompt_summary,
        )

    def generate_weekly_report(
        self,
        week_end_date: Optional[date] = None,
    ) -> str:
        """
        Generate a weekly synthesis for the 7 days ending on week_end_date.
        """
        end = week_end_date or date.today()
        start = end - timedelta(days=6)
        sessions = self._collect_sessions_for_range(start, end)
        vault_notes = self._collect_vault_notes_for_range(start, end)
        return self._write_report(
            report_type="weekly",
            start_date=start,
            end_date=end,
            sessions=sessions,
            vault_notes=vault_notes,
        )

    def generate_monthly_report(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> str:
        """Generate a monthly review note."""
        import calendar
        today = date.today()
        year = year or today.year
        month = month or today.month
        _, last_day = calendar.monthrange(year, month)
        start = date(year, month, 1)
        end = date(year, month, last_day)
        sessions = self._collect_sessions_for_range(start, end)
        vault_notes = self._collect_vault_notes_for_range(start, end)
        return self._write_report(
            report_type="monthly",
            start_date=start,
            end_date=end,
            sessions=sessions,
            vault_notes=vault_notes,
        )

    def generate_annual_report(self, year: Optional[int] = None) -> str:
        """Generate an annual review note."""
        year = year or date.today().year
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        sessions = self._collect_sessions_for_range(start, end)
        vault_notes = self._collect_vault_notes_for_range(start, end)
        return self._write_report(
            report_type="annual",
            start_date=start,
            end_date=end,
            sessions=sessions,
            vault_notes=vault_notes,
        )

    # -----------------------------------------------------------------------
    # Data Collection
    # -----------------------------------------------------------------------

    def _collect_sessions_for_range(
        self, start: date, end: date
    ) -> List[Dict]:
        """
        Find all JSON tree files in logs/ whose modification date
        falls within [start, end].
        """
        sessions = []
        if not self.logs_dir.exists():
            return sessions

        for json_path in self.logs_dir.glob("*.json"):
            try:
                mtime = date.fromtimestamp(json_path.stat().st_mtime)
            except OSError:
                continue
            if start <= mtime <= end:
                try:
                    with open(json_path, encoding="utf-8") as f:
                        data = json.load(f)
                    data["_source_file"] = str(json_path)
                    data["_date"] = mtime.isoformat()
                    sessions.append(data)
                except (json.JSONDecodeError, OSError):
                    pass
        return sessions

    def _collect_vault_notes_for_range(
        self, start: date, end: date
    ) -> List[Dict]:
        """
        Walk the vault for notes tagged 'tree-of-thoughts' whose
        frontmatter date falls within [start, end].
        """
        notes = []
        for md_path in self.vault_root.rglob("*.md"):
            try:
                raw = md_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if not raw.startswith("---"):
                continue
            end_fm = raw.find("\n---", 3)
            if end_fm == -1:
                continue
            try:
                fm = yaml.safe_load(raw[3:end_fm]) or {}
            except yaml.YAMLError:
                continue
            tags = fm.get("tags", [])
            if "tree-of-thoughts" not in tags:
                continue
            note_date_str = fm.get("date", "")
            try:
                note_date = date.fromisoformat(str(note_date_str))
            except (ValueError, TypeError):
                continue
            if start <= note_date <= end:
                notes.append({
                    "path": str(md_path),
                    "frontmatter": fm,
                })
        return notes

    # -----------------------------------------------------------------------
    # Report Rendering
    # -----------------------------------------------------------------------

    def _write_report(
        self,
        report_type: str,
        start_date: date,
        end_date: date,
        sessions: List[Dict],
        vault_notes: List[Dict],
        prompt_summary: Optional[str] = None,
    ) -> str:
        """Build and write a report markdown file. Returns the written path."""
        labels = self.REPORT_TYPES[report_type]
        label = labels["label_fr"] if self.language == "fr" else labels["label_en"]
        subdir = labels["dir"]

        today = date.today().isoformat()
        date_range_str = (
            start_date.isoformat()
            if start_date == end_date
            else f"{start_date.isoformat()} au {end_date.isoformat()}"
        )

        # Aggregate stats
        total_nodes = sum(len(s.get("nodes", {})) for s in sessions)
        all_scores: List[float] = []
        for s in sessions:
            for node_data in s.get("nodes", {}).values():
                all_scores.extend(node_data.get("thoughts", []))
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
        best_score = max(all_scores) if all_scores else 0.0

        # Group notes by section
        section_note_links: Dict[str, List[str]] = {}
        for note in vault_notes:
            section = note["frontmatter"].get("section", "KNOWLEDGE")
            title = note["frontmatter"].get("title", Path(note["path"]).stem)
            section_note_links.setdefault(section, []).append(f"[[{title}]]")

        section_block = self._render_section_links(section_note_links)
        sessions_table = self._render_sessions_table(sessions)
        timeline_links = self._render_timeline_links(start_date, end_date, report_type, label)

        # Frontmatter
        frontmatter = {
            "title": f"{label} — {date_range_str}",
            "date": today,
            "tags": ["rapport", report_type, "tree-of-thoughts"],
            "section": "RAPPORT",
            "tot_sessions": len(sessions),
            "tot_nodes_total": total_nodes,
            "score_moyen": round(avg_score, 4),
            "score_meilleur": round(best_score, 4),
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
        }
        fm_str = yaml.dump(
            frontmatter,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )

        prompt_block = (
            f"\n## Intentions & Réflexions personnelles\n\n{prompt_summary}\n"
            if prompt_summary and self.language == "fr"
            else (
                f"\n## Personal Intentions & Reflections\n\n{prompt_summary}\n"
                if prompt_summary
                else ""
            )
        )

        if self.language == "fr":
            content = f"""---
{fm_str}---

# {label} — {date_range_str}
{prompt_block}
## Statistiques Tree of Thoughts

| Indicateur | Valeur |
|---|---|
| Sessions | `{len(sessions)}` |
| Nœuds totaux | `{total_nodes}` |
| Score moyen | `{avg_score:.4f}` |
| Meilleur score | `{best_score:.4f}` |
| Notes générées | `{len(vault_notes)}` |

## Notes générées par section
{section_block}

## Résumé des sessions
{sessions_table}

## Navigation temporelle
{timeline_links}

---
_Rapport généré automatiquement par Tree of Thoughts · {today}_
"""
        else:
            content = f"""---
{fm_str}---

# {label} — {date_range_str}
{prompt_block}
## Tree of Thoughts Statistics

| Indicator | Value |
|---|---|
| Sessions | `{len(sessions)}` |
| Total nodes | `{total_nodes}` |
| Average score | `{avg_score:.4f}` |
| Best score | `{best_score:.4f}` |
| Notes generated | `{len(vault_notes)}` |

## Notes by section
{section_block}

## Sessions summary
{sessions_table}

## Timeline navigation
{timeline_links}

---
_Report auto-generated by Tree of Thoughts · {today}_
"""

        # Write to RAPPORT section
        out_dir = self.rapport_dir / subdir
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{label} {date_range_str}.md".replace("/", "-")
        out_path = out_dir / filename

        # Avoid overwrite — add timestamp suffix if exists
        if out_path.exists():
            from datetime import datetime
            ts = datetime.now().strftime("%H%M%S")
            out_path = out_dir / f"{label} {date_range_str}_{ts}.md"

        out_path.write_text(content, encoding="utf-8")
        logger.info(f"Report written: {out_path}")
        return str(out_path)

    def _render_section_links(
        self, section_note_links: Dict[str, List[str]]
    ) -> str:
        if not section_note_links:
            return "_Aucune note générée sur cette période._" if self.language == "fr" else "_No notes generated for this period._"
        block = ""
        for section, links in section_note_links.items():
            block += f"\n### {section}\n" + "\n".join(f"- {l}" for l in links)
        return block

    def _render_sessions_table(self, sessions: List[Dict]) -> str:
        if not sessions:
            return (
                "_Aucune session Tree of Thoughts sur cette période._"
                if self.language == "fr"
                else "_No Tree of Thoughts sessions for this period._"
            )
        header = (
            "| Date | Fichier | Nœuds | Meilleur score |\n|---|---|---|---|"
            if self.language == "fr"
            else "| Date | File | Nodes | Best score |\n|---|---|---|---|"
        )
        rows = [header]
        for s in sessions:
            nodes = s.get("nodes", {})
            all_s = [v for nd in nodes.values() for v in nd.get("thoughts", [])]
            best = max(all_s) if all_s else 0.0
            rows.append(
                f"| {s.get('_date', '?')} "
                f"| `{Path(s.get('_source_file', '?')).name}` "
                f"| {len(nodes)} "
                f"| {best:.4f} |"
            )
        return "\n".join(rows)

    def _render_timeline_links(
        self,
        start: date,
        end: date,
        report_type: str,
        label: str,
    ) -> str:
        """Generate navigation wikilinks to adjacent periods."""
        sep = "au" if self.language == "fr" else "to"

        if report_type == "daily":
            prev = (start - timedelta(days=1)).isoformat()
            nxt = (end + timedelta(days=1)).isoformat()
            prev_label = "Rapport Quotidien" if self.language == "fr" else "Daily Report"
            return (
                f"- Précédent : [[{prev_label} — {prev}]]\n"
                f"- Suivant : [[{prev_label} — {nxt}]]"
                if self.language == "fr"
                else f"- Previous: [[{prev_label} — {prev}]]\n- Next: [[{prev_label} — {nxt}]]"
            )
        elif report_type == "weekly":
            prev_end = start - timedelta(days=1)
            prev_start = prev_end - timedelta(days=6)
            prev_label = "Synthèse Hebdomadaire" if self.language == "fr" else "Weekly Synthesis"
            return (
                f"- Semaine précédente : [[{prev_label} — {prev_start.isoformat()} {sep} {prev_end.isoformat()}]]"
                if self.language == "fr"
                else f"- Previous week: [[{prev_label} — {prev_start.isoformat()} {sep} {prev_end.isoformat()}]]"
            )
        elif report_type == "monthly":
            prev_month = start.replace(day=1) - timedelta(days=1)
            prev_label = "Bilan Mensuel" if self.language == "fr" else "Monthly Review"
            return (
                f"- Mois précédent : [[{prev_label} — {prev_month.year}-{prev_month.month:02d}-01 {sep} {prev_month.isoformat()}]]"
                if self.language == "fr"
                else f"- Previous month: [[{prev_label} — {prev_month.year}-{prev_month.month:02d}-01 {sep} {prev_month.isoformat()}]]"
            )
        else:
            prev_year = start.year - 1
            prev_label = "Bilan Annuel" if self.language == "fr" else "Annual Review"
            return (
                f"- Année précédente : [[{prev_label} — {prev_year}]]"
                if self.language == "fr"
                else f"- Previous year: [[{prev_label} — {prev_year}]]"
            )
