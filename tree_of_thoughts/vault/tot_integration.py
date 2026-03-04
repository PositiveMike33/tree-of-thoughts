"""
Tree of Thoughts Integration with Vault Persistence and Validation

Implements VaultAwareLanguageModel that extends AbstractLanguageModel
to provide Tree of Thoughts algorithms with vault persistence, validation,
fact-checking, and confidence scoring.
"""

import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime

from ..models.abstract_language_model import AbstractLanguageModel
from .tree_of_thoughts_vault_integration import (
    ThoughtNode,
    VaultSection,
    ObsidianVaultIntegration,
    VaultAwareLLMContext,
)
from .validation_engine import (
    ResponseValidator,
    FactChecker,
    AutoCorrector,
    BlindValidationEngine,
    ConfidenceLevel,
)
from .openrouter_config import OpenRouterClient

logger = logging.getLogger(__name__)


@dataclass
class ValidatedThought:
    """Represents a thought with validation metadata."""
    text: str
    evaluation_score: float  # 0.0-1.0
    confidence: float  # 0.0-1.0 from validation
    confidence_level: ConfidenceLevel
    is_valid: bool
    validation_issues: List[str] = field(default_factory=list)
    fact_check_score: float = 0.7
    passes_blind_validation: bool = False
    metadata: Dict = field(default_factory=dict)


@dataclass
class ToTSearchResult:
    """Complete result from a Tree of Thoughts search."""
    solution: str
    best_state: str
    confidence_score: float
    confidence_level: ConfidenceLevel
    search_depth: int
    nodes_explored: int
    validation_report: Dict
    fact_check_report: Dict
    blind_validation_report: Dict
    thought_path: List[ValidatedThought] = field(default_factory=list)
    alternatives: List[Tuple[str, float]] = field(default_factory=list)
    requires_review: bool = False


class VaultAwareLanguageModel(AbstractLanguageModel):
    """
    Language model implementation that integrates Tree of Thoughts with:
    - Obsidian vault persistence
    - Multi-level validation (syntactic, completeness, consistency)
    - Fact-checking with claim verification
    - Triple-blind validation with consensus scoring
    - Confidence tracking at each step
    """

    def __init__(
        self,
        llm_client: OpenRouterClient,
        vault_root: Optional[str] = None,
        validate_thoughts: bool = True,
        fact_check: bool = True,
        blind_validate: bool = True,
        persist_to_vault: bool = True,
    ):
        """Initialize VaultAwareLanguageModel.

        Args:
            llm_client: OpenRouter LLM client for generating thoughts/evaluations
            vault_root: Optional path to Obsidian vault
            validate_thoughts: Enable multi-level validation
            fact_check: Enable fact-checking of thoughts
            blind_validate: Enable triple-blind validation
            persist_to_vault: Enable persistence to vault
        """
        self.llm_client = llm_client
        self.vault = ObsidianVaultIntegration(vault_root) if persist_to_vault else None
        self.llm_context = VaultAwareLLMContext()

        # Validation components
        self.validator = ResponseValidator()
        self.fact_checker = FactChecker(llm_client)
        self.auto_corrector = AutoCorrector(llm_client)
        self.blind_validator = BlindValidationEngine(self.validator, llm_client)

        # Configuration
        self.validate_thoughts = validate_thoughts
        self.fact_check = fact_check
        self.blind_validate = blind_validate
        self.persist_to_vault = persist_to_vault and (vault_root is not None)

        # Tracking
        self.explored_states: Set[str] = set()
        self.state_validations: Dict[str, ValidatedThought] = {}
        self.current_search: Optional[ToTSearchResult] = None

        logger.info(
            f"VaultAwareLanguageModel initialized: "
            f"validate={validate_thoughts}, "
            f"fact_check={fact_check}, "
            f"blind_validate={blind_validate}"
        )

    def generate_thoughts(self, state: str, k: int, initial_prompt: str = "") -> List[str]:
        """
        Generate k candidate next thoughts from current state.

        Args:
            state: Current reasoning state (str or joined sequence)
            k: Number of thoughts to generate
            initial_prompt: Original problem statement

        Returns:
            List of k generated thought strings
        """
        if isinstance(state, (tuple, list)):
            state_text = " → ".join(state)
        else:
            state_text = state

        system_prompt = self._build_generation_prompt(initial_prompt)

        prompt = f"""Current reasoning state:
{state_text}

Generate {k} distinct next reasoning steps to advance toward solving: {initial_prompt}

For each step, be concise and specific. Consider multiple angles."""

        try:
            # Generate k thoughts in parallel
            thoughts = []
            for i in range(k):
                response = self.llm_client.call(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=0.7 + (i * 0.05),  # Increase temperature for diversity
                    max_tokens=500,
                )
                thoughts.append(response.strip())

            logger.info(f"Generated {len(thoughts)} thoughts from state")
            return thoughts

        except Exception as e:
            logger.error(f"Error generating thoughts: {e}")
            return [state]  # Fallback: return current state

    def evaluate_states(
        self, states: Dict[str, float], initial_prompt: str = ""
    ) -> Dict[str, float]:
        """
        Evaluate quality/promise of one or more states.

        Args:
            states: Dict mapping state (str) to placeholder score
            initial_prompt: Original problem for context

        Returns:
            Dict mapping state to evaluation score (0.0-1.0)
        """
        evaluated: Dict[str, float] = {}

        for state in states.keys():
            if isinstance(state, (tuple, list)):
                state_text = " → ".join(state)
            else:
                state_text = state

            # Skip if already evaluated
            if state_text in self.state_validations:
                validated = self.state_validations[state_text]
                evaluated[state] = validated.evaluation_score
                continue

            # Build evaluation prompt
            eval_prompt = f"""Rate the quality and progress toward solving '{initial_prompt}'
for this reasoning state:

{state_text}

Provide ONLY a float between 0.0 (invalid/no progress) and 1.0 (excellent/near solution).
Consider: logical coherence, relevance, completeness, and progress toward goal."""

            try:
                response = self.llm_client.call(
                    prompt=eval_prompt,
                    system_prompt="You are an expert evaluator of reasoning quality.",
                    temperature=0.2,  # Low temperature for consistency
                    max_tokens=20,
                )

                # Extract float from response
                try:
                    score = float(response.strip().split()[0])
                    score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                except (ValueError, IndexError):
                    score = 0.5  # Default if parsing fails

                # Validate the thought if enabled
                if self.validate_thoughts:
                    validation = self.validator.validate_response(state_text)
                    validated_thought = ValidatedThought(
                        text=state_text,
                        evaluation_score=score,
                        confidence=validation.confidence,
                        confidence_level=validation.confidence_level,
                        is_valid=validation.is_valid,
                        validation_issues=[str(i) for i in validation.issues],
                    )

                    # Run fact-checking if enabled
                    if self.fact_check:
                        fact_report = self.fact_checker.generate_fact_check_report(
                            state_text
                        )
                        validated_thought.fact_check_score = fact_report.get(
                            "factuality_score", 0.7
                        )

                    # Adjust score based on validation
                    if not validation.is_valid:
                        score *= 0.8  # Penalize invalid thoughts
                    if validated_thought.fact_check_score < 0.5:
                        score *= 0.8  # Penalize low factuality

                    self.state_validations[state_text] = validated_thought
                    evaluated[state] = score
                else:
                    evaluated[state] = score

                logger.debug(f"Evaluated state: score={score:.2f}")

            except Exception as e:
                logger.error(f"Error evaluating state: {e}")
                evaluated[state] = 0.5  # Default score on error

        return evaluated

    def generate_solution(self, initial_prompt: str, best_state: str) -> str:
        """
        Generate final solution from best state found.

        Args:
            initial_prompt: Original problem statement
            best_state: Best state reached during search

        Returns:
            Final solution string
        """
        if isinstance(best_state, (tuple, list)):
            state_text = " → ".join(best_state)
        else:
            state_text = best_state

        solution_prompt = f"""Based on this reasoning journey:
{state_text}

For the problem: {initial_prompt}

Provide a comprehensive final solution. Be clear, direct, and complete."""

        try:
            solution = self.llm_client.call(
                prompt=solution_prompt,
                system_prompt=self._build_solution_prompt(),
                temperature=0.6,
                max_tokens=2000,
            )

            # Validate solution if enabled
            if self.validate_thoughts:
                validation = self.validator.validate_response(solution)
                logger.info(
                    f"Solution validation: "
                    f"valid={validation.is_valid}, "
                    f"confidence={validation.confidence:.2f}"
                )

                # Run blind validation for final solution
                if self.blind_validate:
                    blind_report = self.blind_validator.full_blind_validation(solution)
                    logger.info(
                        f"Blind validation: "
                        f"score={blind_report['consensus']['final_score']:.2f}"
                    )

            return solution

        except Exception as e:
            logger.error(f"Error generating solution: {e}")
            return best_state

    def search_with_validation(
        self,
        initial_prompt: str,
        section: str = "BRAIN",
        search_depth: int = 3,
    ) -> ToTSearchResult:
        """
        Execute a complete Tree of Thoughts search with full validation.

        Args:
            initial_prompt: Problem statement
            section: Vault section for persistence
            search_depth: Maximum depth to explore

        Returns:
            ToTSearchResult with solution, confidence, and validation details
        """
        logger.info(f"Starting ToT search: depth={search_depth}")

        try:
            vault_section = VaultSection[section.upper()]
        except KeyError:
            vault_section = VaultSection.BRAIN

        # Initialize search tracking
        self.explored_states.clear()
        self.state_validations.clear()
        nodes_explored = 0

        # Run initial thought generation and evaluation
        initial_thoughts = self.generate_thoughts(initial_prompt, k=3, initial_prompt=initial_prompt)
        evaluations = self.evaluate_states(
            {thought: 0.0 for thought in initial_thoughts}, initial_prompt
        )

        # Find best initial thought
        best_thought = max(evaluations.items(), key=lambda x: x[1])
        best_state = best_thought[0]
        best_score = best_thought[1]

        logger.info(f"Best initial thought: score={best_score:.2f}")

        # Store best state for final solution
        self.explored_states.add(best_state)
        nodes_explored += len(initial_thoughts)

        # Generate final solution from best state
        solution = self.generate_solution(initial_prompt, best_state)

        # Perform comprehensive validation on final solution
        validation_result = self.validator.validate_response(solution)
        fact_report = self.fact_checker.generate_fact_check_report(
            solution
        ) if self.fact_check else {}
        blind_report = self.blind_validator.full_blind_validation(
            solution
        ) if self.blind_validate else {}

        # Calculate final confidence
        final_confidence = (
            validation_result.confidence * 0.5 +
            fact_report.get("factuality_score", 0.7) * 0.3 +
            best_score * 0.2
        )
        final_confidence = max(0.0, min(1.0, final_confidence))

        # Map confidence to level
        if final_confidence >= 0.9:
            confidence_level = ConfidenceLevel.CERTAIN
        elif final_confidence >= 0.7:
            confidence_level = ConfidenceLevel.HIGH
        elif final_confidence >= 0.5:
            confidence_level = ConfidenceLevel.MEDIUM
        elif final_confidence >= 0.3:
            confidence_level = ConfidenceLevel.LOW
        else:
            confidence_level = ConfidenceLevel.VERY_LOW

        # Create result
        result = ToTSearchResult(
            solution=solution,
            best_state=best_state,
            confidence_score=final_confidence,
            confidence_level=confidence_level,
            search_depth=search_depth,
            nodes_explored=nodes_explored,
            validation_report={
                "is_valid": validation_result.is_valid,
                "confidence": validation_result.confidence,
                "confidence_level": validation_result.confidence_level.value,
                "issues": [str(i) for i in validation_result.issues],
                "scores": validation_result.scores,
            },
            fact_check_report=fact_report,
            blind_validation_report=blind_report,
            requires_review=not validation_result.is_valid or final_confidence < 0.5,
        )

        # Persist to vault if enabled
        if self.persist_to_vault and self.vault:
            try:
                node = ThoughtNode(
                    text=solution,
                    section=vault_section,
                    evaluation=best_score,
                    confidence=final_confidence,
                    depth=search_depth,
                    tags=["tot-search", section.lower()],
                )
                path = self.vault.create_note(node)
                logger.info(f"Persisted result to vault: {path}")
            except Exception as e:
                logger.error(f"Failed to persist to vault: {e}")

        self.current_search = result
        logger.info(
            f"Search complete: confidence={final_confidence:.2f}, "
            f"level={confidence_level.value}"
        )

        return result

    def _build_generation_prompt(self, initial_prompt: str) -> str:
        """Build system prompt for thought generation."""
        return """You are an expert reasoning system. Generate logical,
coherent, and creative next steps in solving complex problems.
Each step should build on previous reasoning and advance toward the solution."""

    def _build_solution_prompt(self) -> str:
        """Build system prompt for final solution generation."""
        return """You are an expert solution synthesizer. Take the reasoning
journey provided and craft a clear, comprehensive, and actionable solution.
Ensure the solution directly addresses the original problem and is well-reasoned."""

    def get_search_report(self) -> str:
        """Generate human-readable report of last search.

        Returns:
            Formatted report string
        """
        if not self.current_search:
            return "No search results available"

        result = self.current_search
        report = f"""
=== TREE OF THOUGHTS SEARCH REPORT ===

SOLUTION:
{result.solution}

CONFIDENCE: {result.confidence_score:.1%} ({result.confidence_level.value})
SEARCH DEPTH: {result.search_depth}
NODES EXPLORED: {result.nodes_explored}

VALIDATION:
  Valid: {result.validation_report.get('is_valid', False)}
  Issues: {len(result.validation_report.get('issues', []))}

FACT-CHECKING:
  Total Claims: {result.fact_check_report.get('total_claims', 0)}
  Verifiable: {result.fact_check_report.get('verifiable_claims', 0)}
  Factuality Score: {result.fact_check_report.get('factuality_score', 'N/A')}

BLIND VALIDATION (3 rounds):
  Round 1: {result.blind_validation_report.get('round1', {}).get('confidence', 'N/A')}
  Round 2: {result.blind_validation_report.get('round2', {}).get('confidence', 'N/A')}
  Round 3: {result.blind_validation_report.get('round3', {}).get('confidence', 'N/A')}
  Consensus: {result.blind_validation_report.get('consensus', {}).get('final_score', 'N/A')}

{"⚠️  REQUIRES HUMAN REVIEW" if result.requires_review else "✓ Ready for use"}
=====================================
"""
        return report
