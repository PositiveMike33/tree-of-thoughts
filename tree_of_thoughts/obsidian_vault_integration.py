"""
Obsidian Vault Integration for Tree of Thoughts.

Converts ToT reasoning trees into interconnected Obsidian markdown notes
with YAML frontmatter, wikilinks, Mermaid diagrams, and cross-section routing.
"""

import hashlib
import json
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Section constants — match the vault directory names exactly
# ---------------------------------------------------------------------------

VAULT_SECTIONS = {
    "PSYCHE":    "_PSYCHE",
    "BRAIN":     "_BRAIN",
    "KNOWLEDGE": "KNOWLEDGE",
    "RAPPORT":   "RAPPORT QUOTIDIEN, HEBDOMADAIRE,MENSUEL & ANNUEL",
}

# Keywords (French + English) used to route thoughts to the right section
SECTION_ROUTING_KEYWORDS: Dict[str, List[str]] = {
    "PSYCHE": [
        "âme", "spirit", "méditation", "émotion", "moi", "identité",
        "conscience", "intuition", "rêve", "symbole", "archétype",
        "soul", "meditation", "emotion", "identity", "consciousness",
        "shadow", "anima", "persona", "self", "psyché", "psyche",
        "spirituel", "spiritual", "intérieur", "inner", "ombre",
        "transformation", "éveil", "awakening", "transcendance",
    ],
    "BRAIN": [
        "cognition", "mémoire", "apprentissage", "neurone", "cerveau",
        "réflexion", "logique", "raisonnement", "analyse", "stratégie",
        "memory", "learning", "brain", "logic", "reasoning", "analysis",
        "focus", "concentration", "habitude", "habit", "mental",
        "pensée", "thought", "décision", "decision", "productivité",
        "productivity", "attention", "perception",
    ],
    "KNOWLEDGE": [
        "concept", "théorie", "recherche", "définition", "science",
        "philosophie", "histoire", "technologie", "référence",
        "theory", "research", "definition", "philosophy", "history",
        "technology", "reference", "framework", "modèle", "model",
        "connaissance", "knowledge", "étude", "study", "livre", "book",
        "lecture", "reading", "apprentissage", "savoir",
    ],
    "RAPPORT": [
        "quotidien", "journal", "bilan", "rapport", "semaine", "mois",
        "résumé", "synthèse", "daily", "weekly", "monthly", "annual",
        "report", "summary", "review", "today", "aujourd", "hier",
        "tomorrow", "demain", "hebdomadaire", "mensuel", "annuel",
        "progression", "progress", "suivi", "tracking",
    ],
}


class ObsidianVaultIntegration:
    """
    Bridges Tree of Thoughts reasoning trees with an Obsidian vault.

    Reads existing notes for context, converts ToT JSON tree output into
    interconnected markdown files with YAML frontmatter, wikilinks, and
    Mermaid diagrams routed to the appropriate vault section.
    """

    def __init__(
        self,
        vault_root: str,
        section_paths: Optional[Dict[str, str]] = None,
        language: str = "fr",
    ):
        """
        Parameters
        ----------
        vault_root:
            Absolute path to vault root as seen from the container (e.g. '/vault').
        section_paths:
            Override mapping of section keys to subdirectory paths relative to
            vault_root. Defaults to the four standard sections.
        language:
            Primary language for generated content ('fr' or 'en').
        """
        self.vault_root = Path(vault_root)
        self.language = language

        if section_paths is None:
            self.section_paths: Dict[str, Path] = {
                key: self.vault_root / dirname
                for key, dirname in VAULT_SECTIONS.items()
            }
        else:
            self.section_paths = {
                key: self.vault_root / rel
                for key, rel in section_paths.items()
            }

    # -----------------------------------------------------------------------
    # Vault Reading
    # -----------------------------------------------------------------------

    def read_vault_context(
        self,
        sections: Optional[List[str]] = None,
        max_notes: int = 50,
        tag_filter: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Scan the vault and extract context from existing notes.

        Returns
        -------
        dict with keys:
            - notes: list of parsed note dicts
            - tags: {tag_name: count}
            - wikilinks_index: {NoteTitle: relative_path}
            - recent_themes: [top tag names]
        """
        if sections is None:
            sections = list(self.section_paths.keys())

        result: Dict[str, Any] = {
            "notes": [],
            "tags": {},
            "wikilinks_index": {},
            "recent_themes": [],
        }

        for section in sections:
            section_path = self.section_paths.get(section)
            if section_path is None or not section_path.exists():
                logger.debug(f"Vault section not found: {section_path}")
                continue

            md_files = list(section_path.rglob("*.md"))
            md_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            for md_file in md_files[:max_notes]:
                note_data = self._parse_note(md_file)
                if note_data is None:
                    continue

                if tag_filter:
                    note_tags = note_data["frontmatter"].get("tags", [])
                    if not any(t in note_tags for t in tag_filter):
                        continue

                result["notes"].append(note_data)

                for tag in note_data["frontmatter"].get("tags", []):
                    result["tags"][tag] = result["tags"].get(tag, 0) + 1

                title = note_data["frontmatter"].get("title", md_file.stem)
                rel_path = str(md_file.relative_to(self.vault_root))
                result["wikilinks_index"][title] = rel_path

        sorted_tags = sorted(
            result["tags"].items(), key=lambda x: x[1], reverse=True
        )
        result["recent_themes"] = [t for t, _ in sorted_tags[:10]]
        return result

    def _parse_note(self, path: Path) -> Optional[Dict]:
        """Parse a markdown file and return frontmatter + excerpt, or None."""
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.debug(f"Cannot read {path}: {exc}")
            return None

        frontmatter: Dict = {}
        body = raw

        if raw.startswith("---"):
            end = raw.find("\n---", 3)
            if end != -1:
                yaml_block = raw[3:end].strip()
                body = raw[end + 4:].strip()
                try:
                    frontmatter = yaml.safe_load(yaml_block) or {}
                except yaml.YAMLError:
                    pass

        clean_body = re.sub(r"\[\[.*?\]\]", "", body)
        clean_body = re.sub(r"#+\s", "", clean_body)
        excerpt = clean_body[:200].strip()

        return {
            "path": str(path),
            "relative_path": str(path.relative_to(self.vault_root)),
            "frontmatter": frontmatter,
            "excerpt": excerpt,
        }

    def extract_existing_wikilinks(self, note_path: Path) -> List[str]:
        """Return all [[wikilink]] targets found in a note."""
        try:
            raw = note_path.read_text(encoding="utf-8")
        except OSError:
            return []
        return re.findall(r"\[\[([^\]]+)\]\]", raw)

    # -----------------------------------------------------------------------
    # Section Routing
    # -----------------------------------------------------------------------

    def detect_vault_section(
        self, text: str, fallback: str = "KNOWLEDGE"
    ) -> str:
        """
        Classify text to the most appropriate vault section via keyword scoring.

        Returns one of: 'PSYCHE', 'BRAIN', 'KNOWLEDGE', 'RAPPORT'.
        """
        scores: Dict[str, int] = {key: 0 for key in SECTION_ROUTING_KEYWORDS}
        lower_text = text.lower()

        for section, keywords in SECTION_ROUTING_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in lower_text:
                    scores[section] += 1

        best_section = max(scores, key=lambda s: scores[s])
        if scores[best_section] == 0:
            return fallback
        return best_section

    # -----------------------------------------------------------------------
    # Markdown / Obsidian Generation
    # -----------------------------------------------------------------------

    def convert_tree_to_markdown(
        self,
        tree_json_path: str,
        prompt: str,
        algorithm: str = "BFS",
        session_id: Optional[str] = None,
        target_section: Optional[str] = None,
        vault_context: Optional[Dict] = None,
    ) -> List[str]:
        """
        Read the JSON tree produced by save_tree_to_json() and generate
        one Obsidian note per top thought node plus one neural-map overview.

        Returns a list of absolute file paths written.
        """
        with open(tree_json_path, "r", encoding="utf-8") as f:
            tree_data = json.load(f)

        if session_id is None:
            session_id = hashlib.md5(
                (prompt + str(datetime.now())).encode()
            ).hexdigest()[:8]

        today = date.today().isoformat()
        nodes = tree_data.get("nodes", {})
        written_paths: List[str] = []

        def best_score(node_value: Dict) -> float:
            thoughts = node_value.get("thoughts", [0])
            return max(thoughts) if thoughts else 0.0

        ranked_nodes = sorted(
            nodes.items(), key=lambda x: best_score(x[1]), reverse=True
        )

        node_titles: List[str] = []
        for i, (state_str, node_data) in enumerate(ranked_nodes[:20]):
            section = target_section or self.detect_vault_section(state_str)
            title = self._make_note_title(state_str, session_id, i)
            node_titles.append(title)

            related = self._find_related_notes(state_str, vault_context or {})

            md_content = self._render_thought_node(
                title=title,
                state_str=state_str,
                node_data=node_data,
                prompt=prompt,
                algorithm=algorithm,
                session_id=session_id,
                date_str=today,
                section=section,
                related_notes=related,
                node_index=i,
            )

            out_path = self._resolve_output_path(section, title + ".md")
            self._write_note(out_path, md_content)
            written_paths.append(str(out_path))

        # Neural-map overview note
        map_section = target_section or self.detect_vault_section(prompt)
        map_path = self._generate_neural_map(
            session_id=session_id,
            prompt=prompt,
            algorithm=algorithm,
            tree_data=tree_data,
            node_titles=node_titles,
            date_str=today,
            section=map_section,
        )
        written_paths.append(str(map_path))

        # Backlinks index note
        index_content = self.generate_backlinks_index(session_id, written_paths)
        index_path = self._resolve_output_path(
            map_section, f"Index ToT - {session_id}.md"
        )
        self._write_note(index_path, index_content)
        written_paths.append(str(index_path))

        return written_paths

    def _make_note_title(
        self, state_str: str, session_id: str, index: int
    ) -> str:
        """Derive a safe, unique Obsidian note title from a state string."""
        truncated = state_str.split(".")[0][:60].strip()
        safe = re.sub(r'[\\/:*?"<>|#^[\]]', "", truncated)
        safe = safe.strip() or f"Thought-{session_id}-{index}"
        return safe

    def _find_related_notes(
        self, text: str, vault_context: Dict
    ) -> List[str]:
        """Simple token-overlap search to find related existing notes."""
        if not vault_context:
            return []

        words = set(re.sub(r"[^\w\s]", "", text.lower()).split())
        related: List[Tuple[int, str]] = []

        for title in vault_context.get("wikilinks_index", {}):
            title_words = set(title.lower().split())
            overlap = len(words & title_words)
            if overlap >= 2:
                related.append((overlap, title))

        related.sort(reverse=True)
        return [t for _, t in related[:5]]

    def _render_thought_node(
        self,
        title: str,
        state_str: str,
        node_data: Dict,
        prompt: str,
        algorithm: str,
        session_id: str,
        date_str: str,
        section: str,
        related_notes: List[str],
        node_index: int,
    ) -> str:
        """Produce full markdown content for a single thought-node note."""
        thoughts_scores = node_data.get("thoughts", [])
        best_score = max(thoughts_scores) if thoughts_scores else 0.0
        avg_score = (
            sum(thoughts_scores) / len(thoughts_scores)
            if thoughts_scores
            else 0.0
        )

        related_links = "\n".join(f"- [[{n}]]" for n in related_notes)
        if not related_links:
            if self.language == "fr":
                related_links = "_Aucune connexion détectée_"
            else:
                related_links = "_No connections detected_"

        tags = [
            "tree-of-thoughts",
            section.lower(),
            algorithm.lower(),
            f"session-{session_id}",
        ]

        frontmatter = {
            "title": title,
            "date": date_str,
            "tags": tags,
            "section": section,
            "tot_algorithm": algorithm,
            "session_id": session_id,
            "score_best": round(best_score, 4),
            "score_avg": round(avg_score, 4),
            "node_index": node_index,
            "related_notes": related_notes,
        }

        fm_str = yaml.dump(
            frontmatter,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )

        filled = int(best_score * 5)
        score_bar = "█" * filled + "░" * (5 - filled)

        if self.language == "fr":
            content = f"""---
{fm_str}---

# {title}

> **Contexte** : [[Session ToT {session_id}]] | Algorithme : `{algorithm}` | Score : `{score_bar}` ({best_score:.2f})

## Pensée / Thought

{state_str}

## Évaluation ToT

| Métrique | Valeur |
|---|---|
| Meilleur score | `{best_score:.4f}` |
| Score moyen | `{avg_score:.4f}` |
| Nombre d'évaluations | `{len(thoughts_scores)}` |

## Connexions

### Notes liées dans le vault
{related_links}

### Réseau de session
- [[Carte Neurale - {session_id}]]
- [[Index ToT - {session_id}]]

## Prompt initial

> {prompt[:500]}{"..." if len(prompt) > 500 else ""}

---
_Généré automatiquement par Tree of Thoughts · {date_str}_
"""
        else:
            content = f"""---
{fm_str}---

# {title}

> **Context** : [[Session ToT {session_id}]] | Algorithm : `{algorithm}` | Score : `{score_bar}` ({best_score:.2f})

## Thought

{state_str}

## ToT Evaluation

| Metric | Value |
|---|---|
| Best score | `{best_score:.4f}` |
| Average score | `{avg_score:.4f}` |
| Evaluations | `{len(thoughts_scores)}` |

## Connections

### Related vault notes
{related_links}

### Session network
- [[Neural Map - {session_id}]]
- [[ToT Index - {session_id}]]

## Initial prompt

> {prompt[:500]}{"..." if len(prompt) > 500 else ""}

---
_Auto-generated by Tree of Thoughts · {date_str}_
"""
        return content

    def _generate_neural_map(
        self,
        session_id: str,
        prompt: str,
        algorithm: str,
        tree_data: Dict,
        node_titles: List[str],
        date_str: str,
        section: str,
    ) -> Path:
        """Create a neural-map overview note with a Mermaid graph diagram."""
        nodes = tree_data.get("nodes", {})

        if self.language == "fr":
            map_title = f"Carte Neurale - {session_id}"
            tags = ["neural-map", "tree-of-thoughts", section.lower(), f"session-{session_id}"]
        else:
            map_title = f"Neural Map - {session_id}"
            tags = ["neural-map", "tree-of-thoughts", section.lower(), f"session-{session_id}"]

        frontmatter = {
            "title": map_title,
            "date": date_str,
            "tags": tags,
            "section": section,
            "tot_algorithm": algorithm,
            "session_id": session_id,
            "node_count": len(nodes),
        }
        fm_str = yaml.dump(
            frontmatter,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )

        # Build Mermaid graph
        mermaid_lines = ["graph TD"]
        prompt_label = prompt[:40].replace('"', "'").replace("\n", " ")
        mermaid_lines.append(f'    ROOT["\U0001f331 {prompt_label}"]')

        for i, (state_str, node_data) in enumerate(list(nodes.items())[:20]):
            thoughts = node_data.get("thoughts", [0])
            score = max(thoughts) if thoughts else 0.0
            node_id = f"N{i}"
            label = state_str[:35].replace('"', "'").replace("\n", " ")
            mermaid_lines.append(f'    {node_id}["{label}\\n({score:.2f})"]')
            mermaid_lines.append(f"    ROOT --> {node_id}")
            if score >= 0.7:
                mermaid_lines.append(f"    style {node_id} fill:#4CAF50,color:#fff")
            elif score >= 0.4:
                mermaid_lines.append(f"    style {node_id} fill:#FF9800,color:#fff")
            else:
                mermaid_lines.append(f"    style {node_id} fill:#F44336,color:#fff")

        mermaid_block = "\n".join(mermaid_lines)
        node_links = "\n".join(f"- [[{t}]]" for t in node_titles)

        if self.language == "fr":
            content = f"""---
{fm_str}---

# Carte Neurale — Session `{session_id}`

> Algorithme : `{algorithm}` · Date : {date_str} · Nœuds : {len(nodes)}

## Réseau de Pensées

```mermaid
{mermaid_block}
```

## Nœuds du réseau

{node_links}

## Prompt source

> {prompt[:500]}{"..." if len(prompt) > 500 else ""}

---
_Généré automatiquement par Tree of Thoughts · {date_str}_
"""
        else:
            content = f"""---
{fm_str}---

# Neural Map — Session `{session_id}`

> Algorithm : `{algorithm}` · Date : {date_str} · Nodes : {len(nodes)}

## Thought Network

```mermaid
{mermaid_block}
```

## Network Nodes

{node_links}

## Source Prompt

> {prompt[:500]}{"..." if len(prompt) > 500 else ""}

---
_Auto-generated by Tree of Thoughts · {date_str}_
"""

        out_path = self._resolve_output_path(section, f"{map_title}.md")
        self._write_note(out_path, content)
        return out_path

    # -----------------------------------------------------------------------
    # File I/O Helpers
    # -----------------------------------------------------------------------

    def _resolve_output_path(self, section: str, filename: str) -> Path:
        """Build the absolute output path, creating a ToT/ subdirectory."""
        section_dir = self.section_paths.get(section, self.vault_root)
        tot_dir = section_dir / "ToT"
        tot_dir.mkdir(parents=True, exist_ok=True)
        return tot_dir / filename

    def _write_note(self, path: Path, content: str) -> None:
        """Write a note, adding a timestamp suffix if the file already exists."""
        if path.exists():
            ts = datetime.now().strftime("%H%M%S")
            path = path.with_stem(path.stem + f"_{ts}")
            logger.info(f"Note exists, writing versioned copy: {path}")
        path.write_text(content, encoding="utf-8")
        logger.info(f"Written: {path}")

    def generate_backlinks_index(
        self, session_id: str, written_paths: List[str]
    ) -> str:
        """Generate a markdown backlinks index note for the session."""
        today = date.today().isoformat()
        links = "\n".join(f"- [[{Path(p).stem}]]" for p in written_paths)

        if self.language == "fr":
            return f"""---
title: "Index ToT - {session_id}"
date: {today}
tags: [index, tree-of-thoughts, session-{session_id}]
---

# Index de session ToT — `{session_id}`

Notes générées lors de cette session :

{links}

---
_Index auto-généré · {today}_
"""
        return f"""---
title: "ToT Index - {session_id}"
date: {today}
tags: [index, tree-of-thoughts, session-{session_id}]
---

# ToT Session Index — `{session_id}`

Notes generated in this session:

{links}

---
_Auto-generated index · {today}_
"""
