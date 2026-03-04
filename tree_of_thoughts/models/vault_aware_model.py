"""
Vault-Aware Language Model for Tree of Thoughts.

Extends AbstractLanguageModel using Anthropic Claude as the LLM backend,
enriched with context from the user's Obsidian vault. Includes a configurable
system prompt for personalised reasoning (e.g. psychology / HR expert mode).
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import anthropic as anthropic_sdk

from tree_of_thoughts.models.abstract_language_model import AbstractLanguageModel
from tree_of_thoughts.obsidian_vault_integration import ObsidianVaultIntegration

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default system prompt (French) — psychology + personal development expert
# Matches the user's requested prompt style
# ---------------------------------------------------------------------------
DEFAULT_SYSTEM_PROMPT_FR = """AGISSEZ comme un psychologue et un expert en ressources humaines et développement personnel, votre tâche est d'aider l'utilisateur à explorer et résoudre des problèmes complexes liés à son développement spirituel et personnel. Reconnaissez-le en répondant "OUI"!

Pour chaque question ou état de réflexion, vous devez :
1. Reconnaître la profondeur émotionnelle et psychologique de la situation
2. Proposer des pensées distinctes qui tiennent compte de facteurs tels que l'expérience, le timing, la préparation, le professionnalisme et la proposition de valeur personnelle
3. Évaluer chaque pensée selon son potentiel, ses avantages/inconvénients, l'effort nécessaire, les défis potentiels et les résultats attendus
4. Approfondir les processus de réflexion avec des stratégies de scénarios, les ressources nécessaires et comment surmonter les obstacles
5. Considérer les résultats inattendus et comment les gérer

Vous travaillez dans le cadre de la méthode Tree of Thoughts (ToT) — un réseau neuronal virtuel de réflexion personnelle connecté au vault Obsidian de l'utilisateur.

Répondez toujours en français sauf indication contraire. Utilisez la syntaxe [[Lien]] pour référencer des concepts importants qui pourraient exister comme notes dans le vault."""

DEFAULT_SYSTEM_PROMPT_EN = """ACT as a psychologist and expert in human resources and personal development. Your task is to help the user explore and resolve complex issues related to their spiritual and personal growth. Acknowledge this by responding "YES"!

For each question or reflective state, you must:
1. Acknowledge the emotional and psychological depth of the situation
2. Propose distinct thoughts considering factors such as experience, timing, preparation, professionalism, and personal value proposition
3. Evaluate each thought by its potential, pros/cons, effort required, potential challenges, and expected outcomes
4. Deepen the reflection process with scenario strategies, required resources, and how to overcome obstacles
5. Consider unexpected outcomes and how to manage them

You are working within the Tree of Thoughts (ToT) framework — a virtual neural network of personal reflection connected to the user's Obsidian vault.

Always respond in English unless otherwise specified. Use [[Link]] syntax to reference important concepts that may exist as notes in the vault."""


class VaultAwareModel(AbstractLanguageModel):
    """
    AbstractLanguageModel implementation using Anthropic Claude,
    enriched with Obsidian vault context for personalised ToT reasoning.

    Vault context is loaded once at construction and cached, avoiding
    repeated filesystem scans during solve() loops.
    """

    def __init__(
        self,
        vault_integration: ObsidianVaultIntegration,
        model: str = "claude-opus-4-6",
        max_tokens: int = 1500,
        temperature: float = 0.7,
        evaluation_strategy: str = "value",
        vault_context_sections: Optional[List[str]] = None,
        language: str = "fr",
        system_prompt: Optional[str] = None,
    ):
        """
        Parameters
        ----------
        vault_integration:
            Already-constructed ObsidianVaultIntegration instance.
        model:
            Anthropic model identifier (default: claude-opus-4-6).
        max_tokens:
            Max tokens per API response.
        temperature:
            Sampling temperature (0.0–1.0).
        evaluation_strategy:
            'value' (float score per state) or 'vote' (comparative).
        vault_context_sections:
            Which vault sections to load context from. Defaults to all four.
        language:
            'fr' or 'en'. Controls prompt and output language.
        system_prompt:
            Custom system prompt. Defaults to the psychology/HR expert prompt.
        """
        self.vault = vault_integration
        self.model_name = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.evaluation_strategy = evaluation_strategy
        self.language = language

        # System prompt — use custom or language-appropriate default
        if system_prompt is not None:
            self.system_prompt = system_prompt
        elif language == "fr":
            self.system_prompt = DEFAULT_SYSTEM_PROMPT_FR
        else:
            self.system_prompt = DEFAULT_SYSTEM_PROMPT_EN

        # Anthropic SDK client (reads ANTHROPIC_API_KEY from env)
        self.client = anthropic_sdk.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )

        # Load vault context once and cache
        logger.info("Loading Obsidian vault context...")
        self._vault_context = self.vault.read_vault_context(
            sections=vault_context_sections
        )
        self._context_summary = self._build_context_summary()
        logger.info(
            f"Vault context loaded: {len(self._vault_context['notes'])} notes, "
            f"themes: {self._vault_context['recent_themes'][:5]}"
        )

    # -----------------------------------------------------------------------
    # Context Building
    # -----------------------------------------------------------------------

    def _build_context_summary(self) -> str:
        """Produce a condensed textual summary of the vault context for prompt injection."""
        themes = self._vault_context.get("recent_themes", [])
        top_notes = self._vault_context.get("notes", [])[:5]

        theme_str = (
            ", ".join(themes[:8]) if themes
            else ("aucun thème détecté" if self.language == "fr" else "no themes detected")
        )

        notes_str = "\n".join(
            f"- [[{n['frontmatter'].get('title', Path(n['path']).stem)}]]: "
            f"{n['excerpt'][:80]}..."
            for n in top_notes
        )

        if self.language == "fr":
            return (
                f"Thèmes principaux du vault : {theme_str}\n\n"
                f"Notes récentes pertinentes :\n{notes_str}"
                if notes_str
                else f"Thèmes principaux du vault : {theme_str}"
            )
        return (
            f"Main vault themes: {theme_str}\n\n"
            f"Recent relevant notes:\n{notes_str}"
            if notes_str
            else f"Main vault themes: {theme_str}"
        )

    # -----------------------------------------------------------------------
    # Claude API
    # -----------------------------------------------------------------------

    def _call_claude(self, prompt: str, system: Optional[str] = None) -> str:
        """Send a prompt to Claude with the configured system prompt."""
        system_content = system or self.system_prompt
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_content,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as exc:
            logger.error(f"Anthropic API error: {exc}")
            return ""

    # -----------------------------------------------------------------------
    # AbstractLanguageModel interface
    # -----------------------------------------------------------------------

    def generate_thoughts(
        self,
        state: Union[str, tuple],
        k: int,
        initial_prompt: str = "",
        rejected_solutions: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Generate k next-step thoughts from the current state,
        enriched with vault context and the psychology/HR system prompt.

        The approach mirrors the user's requested structure:
        - Propose k distinct thoughts
        - Consider experience, timing, preparation, professionalism, value
        - Connect to vault themes where relevant
        """
        if isinstance(state, str):
            state_text = state
        else:
            state_text = "\n".join(str(s) for s in state)

        rejected_str = (
            "\n".join(f"- {r}" for r in rejected_solutions)
            if rejected_solutions
            else ("Aucune" if self.language == "fr" else "None")
        )

        if self.language == "fr":
            prompt = f"""## Contexte de ton vault personnel
{self._context_summary}

## État de raisonnement actuel
{state_text}

## Tâche principale
{initial_prompt}

## Solutions déjà rejetées
{rejected_str}

---

Génère exactement {k} pensées distinctes, cohérentes et approfondies pour avancer vers la solution.
Chaque pensée doit tenir compte de facteurs tels que : l'expérience, le calendrier, la préparation, le professionnalisme et la proposition de valeur personnelle.
Pour chaque pensée, évalue également son potentiel et ses défis.

Format requis — chaque pensée sur une ligne, numérotée :
1. [Ta première pensée approfondie]
2. [Ta deuxième pensée approfondie]
...

Connecte tes pensées aux thèmes du vault quand c'est pertinent (utilise la syntaxe [[Concept]]).
Réponds uniquement avec les pensées numérotées."""
        else:
            prompt = f"""## Your personal vault context
{self._context_summary}

## Current reasoning state
{state_text}

## Main task
{initial_prompt}

## Already rejected solutions
{rejected_str}

---

Generate exactly {k} distinct, coherent, and deep thoughts to progress toward the solution.
Each thought must consider factors such as: experience, timing, preparation, professionalism, and personal value proposition.
For each thought, also assess its potential and challenges.

Required format — each thought on a numbered line:
1. [Your first deep thought]
2. [Your second deep thought]
...

Connect thoughts to vault themes where relevant (use [[Concept]] syntax).
Respond only with the numbered thoughts."""

        raw = self._call_claude(prompt)
        return self._parse_numbered_list(raw, k)

    def evaluate_states(
        self,
        states: Union[Dict, List, set, str],
        initial_prompt: str = "",
    ) -> Dict[str, float]:
        """
        Evaluate each state and return a float score in [0, 1].

        Handles the three calling conventions used by ToT algorithms:
        dict (BFS), set/list (DFS), string (generic).
        """
        # Normalise to list
        if isinstance(states, dict):
            state_list = list(states.keys())
        elif isinstance(states, (list, set)):
            state_list = list(states)
        elif isinstance(states, str):
            state_list = [states]
        else:
            state_list = [str(states)]

        if not state_list:
            return {}

        results: Dict[str, float] = {}
        for state in state_list:
            state_text = (
                state if isinstance(state, str)
                else "\n".join(str(s) for s in state)
            )

            if self.language == "fr":
                prompt = f"""Évalue la qualité de cette pensée pour atteindre l'objectif de développement personnel.

Objectif : {initial_prompt}

Pensée à évaluer :
{state_text}

Critères d'évaluation :
- Pertinence par rapport à l'objectif (0–1)
- Profondeur psychologique et personnelle
- Praticabilité et réalisme
- Alignement avec les valeurs et le développement intérieur

Donne UNIQUEMENT un nombre flottant entre 0.0 et 1.0.
Exemple de réponses valides : 0.75, 0.4, 0.9
Réponds avec le nombre uniquement, sans texte."""
            else:
                prompt = f"""Evaluate how well this thought progresses toward the personal development goal.

Goal: {initial_prompt}

Thought to evaluate:
{state_text}

Evaluation criteria:
- Relevance to the goal (0–1)
- Psychological and personal depth
- Practicability and realism
- Alignment with values and inner development

Respond with ONLY a float between 0.0 and 1.0.
Valid response examples: 0.75, 0.4, 0.9
Number only, no text."""

            raw = self._call_claude(prompt)
            try:
                match = re.search(r"[0-9]*\.?[0-9]+", raw)
                value = float(match.group()) if match else 0.0
                value = max(0.0, min(1.0, value))
            except (AttributeError, ValueError):
                logger.warning(f"Could not parse score from: '{raw}', defaulting to 0.0")
                value = 0.0

            results[state] = value

        return results

    def generate_solution(
        self,
        initial_prompt: str,
        state: Union[str, tuple, list],
        rejected_solutions: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Generate the final solution synthesis from the best reasoning state.

        Follows the user's requested structure:
        - 3 distinct solutions with pros/cons and probability of success
        - Deep scenario strategies for each
        - Ranked recommendations with justification
        """
        if isinstance(state, (list, tuple)):
            state_text = "\n".join(str(s) for s in state)
        else:
            state_text = str(state)

        if self.language == "fr":
            prompt = f"""## Contexte vault personnel
{self._context_summary}

## Meilleur raisonnement développé (Tree of Thoughts)
{state_text}

## Question / problème initial
{initial_prompt}

---

Sur la base de ce raisonnement approfondi, rédige une synthèse finale structurée en markdown.

**Structure requise :**

### Reconnaissance de la situation
[Reconnaître la profondeur émotionnelle et psychologique]

### 3 Solutions distinctes

Pour chaque solution :
**Solution 1 : [Nom]**
- Description
- Avantages et inconvénients
- Effort initial et difficulté de mise en œuvre
- Défis potentiels et résultats attendus
- Probabilité de succès : X% | Niveau de confiance : X%

**Scénario approfondi :**
- Stratégie de mise en œuvre
- Ressources et partenariats nécessaires
- Comment surmonter les obstacles
- Résultats inattendus potentiels

(Répéter pour Solutions 2 et 3)

### Classement final et recommandations
[Classement des solutions avec justification et réflexions finales]

### Connexions au vault
[Notes et concepts liés avec syntaxe [[Lien]]]

---
Réponds en français avec des sections markdown claires."""
        else:
            prompt = f"""## Personal vault context
{self._context_summary}

## Best reasoning developed (Tree of Thoughts)
{state_text}

## Initial question / problem
{initial_prompt}

---

Based on this deep reasoning, write a structured final synthesis in markdown.

**Required structure:**

### Situation Recognition
[Acknowledge the emotional and psychological depth]

### 3 Distinct Solutions

For each solution:
**Solution 1: [Name]**
- Description
- Pros and cons
- Initial effort and implementation difficulty
- Potential challenges and expected outcomes
- Probability of success: X% | Confidence level: X%

**Deep Scenario:**
- Implementation strategy
- Required resources and partnerships
- How to overcome obstacles
- Potential unexpected outcomes

(Repeat for Solutions 2 and 3)

### Final Ranking and Recommendations
[Solution ranking with justification and final thoughts]

### Vault Connections
[Related notes and concepts using [[Link]] syntax]

---
Respond in English with clear markdown sections."""

        result = self._call_claude(prompt)
        return result or None

    def route_thought_to_section(self, thought: str) -> str:
        """Convenience wrapper around section routing."""
        return self.vault.detect_vault_section(thought)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _parse_numbered_list(raw: str, expected_k: int) -> List[str]:
        """Parse a numbered list LLM response into a Python list."""
        lines = [
            re.sub(r"^\d+\.\s*", "", line).strip()
            for line in raw.splitlines()
            if re.match(r"^\d+\.", line.strip())
        ]
        if lines:
            return lines[:expected_k]
        # Fallback: split by blank lines
        paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
        return paragraphs[:expected_k] if paragraphs else [raw]

    def refresh_vault_context(
        self, sections: Optional[List[str]] = None
    ) -> None:
        """Reload vault context (call after new notes are written)."""
        logger.info("Refreshing vault context...")
        self._vault_context = self.vault.read_vault_context(sections=sections)
        self._context_summary = self._build_context_summary()
        logger.info("Vault context refreshed.")
