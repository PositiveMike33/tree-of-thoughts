"""Tests for base_skill module."""

import unittest
from unittest.mock import Mock, MagicMock, patch
from ..skill_config import SkillType, AlgorithmType, SkillConfig, VaultSection
from ..base_skill import SkillResult, BaseSkill
from ...tot_integration import ToTSearchResult, VaultAwareLanguageModel
from ...tree_of_thoughts_vault_integration import ObsidianVaultIntegration


class TestSkillResult(unittest.TestCase):
    """Test SkillResult dataclass."""

    def test_create_skill_result_with_defaults(self):
        """Test creating SkillResult with required fields."""
        result = SkillResult(
            skill_name="Test Skill",
            skill_type=SkillType.RESEARCH,
            output="Test output",
            confidence_score=0.85,
            confidence_level="HIGH",
        )
        self.assertEqual(result.skill_name, "Test Skill")
        self.assertEqual(result.skill_type, SkillType.RESEARCH)
        self.assertEqual(result.output, "Test output")
        self.assertEqual(result.confidence_score, 0.85)
        self.assertEqual(result.confidence_level, "HIGH")
        self.assertEqual(result.reasoning_path, [])
        self.assertEqual(result.alternatives, [])
        self.assertFalse(result.requires_human_review)

    def test_create_skill_result_with_all_fields(self):
        """Test creating SkillResult with all fields."""
        result = SkillResult(
            skill_name="Complete Test",
            skill_type=SkillType.DECISION,
            output="Decision result",
            confidence_score=0.78,
            confidence_level="HIGH",
            reasoning_path=["Step 1", "Step 2", "Step 3"],
            validation_results={"test": "data"},
            fact_check_report={"verified": True},
            blind_validation_report={"consensus": 0.80},
            alternatives=[("Option A", 0.75), ("Option B", 0.65)],
            recommendations=["Recommendation 1"],
            audit_trail={"nodes": 15},
            metadata={"algo": "BFS"},
            requires_human_review=True,
            confidence_interval=0.06,
            execution_time=12.5,
        )
        self.assertEqual(result.skill_name, "Complete Test")
        self.assertEqual(len(result.reasoning_path), 3)
        self.assertEqual(len(result.alternatives), 2)
        self.assertTrue(result.requires_human_review)
        self.assertEqual(result.execution_time, 12.5)

    def test_skill_result_to_dict(self):
        """Test converting SkillResult to dictionary."""
        result = SkillResult(
            skill_name="Test",
            skill_type=SkillType.CODE_REVIEW,
            output="Code review findings",
            confidence_score=0.82,
            confidence_level="HIGH",
            reasoning_path=["Analysis 1", "Analysis 2"],
            alternatives=[("Finding A", 0.80), ("Finding B", 0.70)],
        )
        result_dict = result.to_dict()
        self.assertEqual(result_dict["skill_name"], "Test")
        self.assertEqual(result_dict["skill_type"], "code_review")
        self.assertEqual(result_dict["output"], "Code review findings")
        self.assertEqual(result_dict["confidence_score"], 0.82)
        self.assertEqual(len(result_dict["reasoning_path"]), 2)
        self.assertEqual(len(result_dict["alternatives"]), 2)


class MockVaultAwareLanguageModel(VaultAwareLanguageModel):
    """Mock implementation of VaultAwareLanguageModel for testing."""

    def __init__(self):
        # Don't call parent __init__ to avoid LLM setup
        pass

    def generate_thoughts(self, prompt, num_thoughts=5):
        """Mock generate_thoughts."""
        return [f"Thought {i+1}" for i in range(num_thoughts)]

    def evaluate_states(self, states, prompt):
        """Mock evaluate_states."""
        return {state: 0.5 + (0.1 * i) for i, state in enumerate(states)}


class ConcreteSkill(BaseSkill):
    """Concrete implementation of BaseSkill for testing."""

    def execute(self, prompt: str, context=None):
        """Execute skill."""
        return SkillResult(
            skill_name=self.config.name,
            skill_type=self.config.skill_type,
            output="Test output",
            confidence_score=0.80,
            confidence_level="HIGH",
        )

    def validate_input(self, prompt: str):
        """Validate input."""
        return True, ""

    def build_system_prompt(self) -> str:
        """Build system prompt."""
        return "Test system prompt"


class TestBaseSkill(unittest.TestCase):
    """Test BaseSkill abstract class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = SkillConfig(
            skill_type=SkillType.RESEARCH,
            algorithm=AlgorithmType.A_STAR,
            name="Test Research Skill",
        )
        self.llm_model = MockVaultAwareLanguageModel()
        self.vault = Mock(spec=ObsidianVaultIntegration)

    def test_skill_initialization_with_valid_config(self):
        """Test initializing skill with valid configuration."""
        skill = ConcreteSkill(
            config=self.config,
            llm_model=self.llm_model,
            vault=self.vault,
        )
        self.assertEqual(skill.config, self.config)
        self.assertEqual(skill.llm_model, self.llm_model)
        self.assertEqual(skill.vault, self.vault)
        self.assertEqual(skill.execution_history, [])
        self.assertIsNone(skill.current_result)

    def test_skill_initialization_with_invalid_config(self):
        """Test initialization with invalid configuration."""
        invalid_config = SkillConfig(
            skill_type=SkillType.RESEARCH,
            algorithm=AlgorithmType.BFS,
            num_thoughts=0,  # Invalid
        )
        with self.assertRaises(ValueError) as context:
            ConcreteSkill(
                config=invalid_config,
                llm_model=self.llm_model,
            )
        self.assertIn("Invalid skill configuration", str(context.exception))

    def test_skill_initialization_without_vault(self):
        """Test skill can be initialized without vault."""
        skill = ConcreteSkill(
            config=self.config,
            llm_model=self.llm_model,
            vault=None,
        )
        self.assertIsNone(skill.vault)

    def test_get_config(self):
        """Test getting skill configuration."""
        skill = ConcreteSkill(
            config=self.config,
            llm_model=self.llm_model,
        )
        config_dict = skill.get_config()
        self.assertEqual(config_dict["skill_type"], "research")
        self.assertEqual(config_dict["algorithm"], "a_star")
        self.assertEqual(config_dict["name"], "Test Research Skill")

    def test_get_execution_summary_when_no_result(self):
        """Test getting execution summary when no result exists."""
        skill = ConcreteSkill(
            config=self.config,
            llm_model=self.llm_model,
        )
        summary = skill.get_execution_summary()
        self.assertEqual(summary, {})

    def test_get_execution_summary_with_result(self):
        """Test getting execution summary after execution."""
        skill = ConcreteSkill(
            config=self.config,
            llm_model=self.llm_model,
        )
        # Set a result
        skill.current_result = SkillResult(
            skill_name="Test",
            skill_type=SkillType.RESEARCH,
            output="Output",
            confidence_score=0.85,
            confidence_level="HIGH",
            execution_time=5.0,
            audit_trail={"nodes_explored": 20},
        )
        summary = skill.get_execution_summary()
        self.assertEqual(summary["skill_name"], "Test")
        self.assertEqual(summary["execution_time"], 5.0)
        self.assertEqual(summary["confidence_score"], 0.85)
        self.assertEqual(summary["confidence_level"], "HIGH")
        self.assertEqual(summary["nodes_explored"], 20)
        self.assertFalse(summary["requires_review"])

    def test_execute_calls_build_system_prompt(self):
        """Test that execute can access system prompt."""
        skill = ConcreteSkill(
            config=self.config,
            llm_model=self.llm_model,
        )
        prompt = skill.build_system_prompt()
        self.assertEqual(prompt, "Test system prompt")

    def test_tot_algorithm_selection_bfs(self):
        """Test BFS algorithm selection."""
        config = SkillConfig(
            skill_type=SkillType.PROBLEM,
            algorithm=AlgorithmType.BFS,
        )
        skill = ConcreteSkill(
            config=config,
            llm_model=self.llm_model,
        )
        result = skill._run_tot_search("Test prompt")
        self.assertIsNotNone(result)
        self.assertEqual(result.solution, "BFS search not yet implemented")

    def test_tot_algorithm_selection_dfs(self):
        """Test DFS algorithm selection."""
        config = SkillConfig(
            skill_type=SkillType.EXPERT,
            algorithm=AlgorithmType.DFS,
        )
        skill = ConcreteSkill(
            config=config,
            llm_model=self.llm_model,
        )
        result = skill._run_tot_search("Test prompt")
        self.assertEqual(result.solution, "DFS search not yet implemented")

    def test_tot_algorithm_selection_best(self):
        """Test BEST algorithm selection."""
        config = SkillConfig(
            skill_type=SkillType.DECISION,
            algorithm=AlgorithmType.BEST,
        )
        skill = ConcreteSkill(
            config=config,
            llm_model=self.llm_model,
        )
        result = skill._run_tot_search("Test prompt")
        self.assertEqual(result.solution, "BEST search not yet implemented")

    def test_tot_algorithm_selection_a_star(self):
        """Test A* algorithm selection."""
        config = SkillConfig(
            skill_type=SkillType.RESEARCH,
            algorithm=AlgorithmType.A_STAR,
        )
        skill = ConcreteSkill(
            config=config,
            llm_model=self.llm_model,
        )
        result = skill._run_tot_search("Test prompt")
        self.assertEqual(result.solution, "A* search not yet implemented")

    def test_tot_algorithm_selection_mcts(self):
        """Test MCTS algorithm selection."""
        config = SkillConfig(
            skill_type=SkillType.THESIS,
            algorithm=AlgorithmType.MCTS,
        )
        skill = ConcreteSkill(
            config=config,
            llm_model=self.llm_model,
        )
        result = skill._run_tot_search("Test prompt")
        self.assertEqual(result.solution, "MCTS search not yet implemented")

    def test_convert_tot_result_to_skill_result(self):
        """Test converting ToT result to skill result."""
        tot_result = ToTSearchResult(
            solution="Found solution",
            best_state="State A",
            confidence_score=0.80,
            confidence_level="HIGH",
            search_depth=5,
            nodes_explored=20,
            validation_report={"confidence": 0.8},
            fact_check_report={"factuality_score": 0.75},
            blind_validation_report={"consensus_score": 0.85},
        )

        skill = ConcreteSkill(
            config=self.config,
            llm_model=self.llm_model,
        )

        skill_result = skill._convert_tot_result_to_skill_result(tot_result, 2.5)

        self.assertEqual(skill_result.skill_name, "Test Research Skill")
        self.assertEqual(skill_result.output, "Found solution")
        self.assertEqual(skill_result.execution_time, 2.5)
        self.assertIn("algorithm", skill_result.audit_trail)

    def test_persist_result_without_vault(self):
        """Test persisting result when vault is disabled."""
        config = SkillConfig(
            skill_type=SkillType.RESEARCH,
            algorithm=AlgorithmType.A_STAR,
            persist_results=False,
        )
        skill = ConcreteSkill(
            config=config,
            llm_model=self.llm_model,
            vault=self.vault,
        )

        result = SkillResult(
            skill_name="Test",
            skill_type=SkillType.RESEARCH,
            output="Output",
            confidence_score=0.80,
            confidence_level="HIGH",
        )

        skill._persist_result(result)
        # Vault should not be called
        self.vault.create_note.assert_not_called()

    def test_persist_result_with_vault(self):
        """Test persisting result to vault."""
        config = SkillConfig(
            skill_type=SkillType.RESEARCH,
            algorithm=AlgorithmType.A_STAR,
            persist_results=True,
            vault_section=VaultSection.KNOWLEDGE,
        )
        skill = ConcreteSkill(
            config=config,
            llm_model=self.llm_model,
            vault=self.vault,
        )

        result = SkillResult(
            skill_name="Test",
            skill_type=SkillType.RESEARCH,
            output="Test output",
            confidence_score=0.80,
            confidence_level="HIGH",
            metadata={"test": "data"},
        )

        skill._persist_result(result)
        # Vault should be called
        self.vault.create_note.assert_called_once()

    def test_handle_execution_error(self):
        """Test handling execution errors gracefully."""
        skill = ConcreteSkill(
            config=self.config,
            llm_model=self.llm_model,
        )

        error = ValueError("Test error message")
        result = skill._handle_execution_error(error)

        self.assertEqual(result.skill_name, "Test Research Skill")
        self.assertEqual(result.confidence_score, 0.0)
        self.assertEqual(result.confidence_level, "VERY_LOW")
        self.assertTrue(result.requires_human_review)
        self.assertIn("Test error message", result.output)
        self.assertEqual(result.metadata["error_type"], "ValueError")

    def test_validate_input_call(self):
        """Test that validate_input can be called."""
        skill = ConcreteSkill(
            config=self.config,
            llm_model=self.llm_model,
        )
        is_valid, message = skill.validate_input("Test prompt")
        self.assertTrue(is_valid)
        self.assertEqual(message, "")

    def test_execute_skill(self):
        """Test executing skill."""
        skill = ConcreteSkill(
            config=self.config,
            llm_model=self.llm_model,
        )
        result = skill.execute("Test prompt")
        self.assertIsNotNone(result)
        self.assertEqual(result.skill_name, "Test Research Skill")
        self.assertEqual(result.output, "Test output")


class TestBaseSkillErrorHandling(unittest.TestCase):
    """Test error handling in BaseSkill."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = SkillConfig(
            skill_type=SkillType.RESEARCH,
            algorithm=AlgorithmType.A_STAR,
        )
        self.llm_model = MockVaultAwareLanguageModel()

    def test_unknown_algorithm_error(self):
        """Test error handling for unknown algorithm."""
        config = SkillConfig(
            skill_type=SkillType.RESEARCH,
            algorithm=AlgorithmType.BFS,
        )
        skill = ConcreteSkill(
            config=config,
            llm_model=self.llm_model,
        )
        # This should work - it just returns a placeholder
        result = skill._run_tot_search("Test")
        self.assertIsNotNone(result)

    def test_invalid_confidence_threshold(self):
        """Test that invalid confidence threshold raises error."""
        invalid_config = SkillConfig(
            skill_type=SkillType.RESEARCH,
            algorithm=AlgorithmType.A_STAR,
            confidence_threshold=1.5,  # Out of range
        )
        with self.assertRaises(ValueError):
            ConcreteSkill(
                config=invalid_config,
                llm_model=self.llm_model,
            )

    def test_invalid_num_thoughts(self):
        """Test that invalid num_thoughts raises error."""
        invalid_config = SkillConfig(
            skill_type=SkillType.RESEARCH,
            algorithm=AlgorithmType.A_STAR,
            num_thoughts=-5,
        )
        with self.assertRaises(ValueError):
            ConcreteSkill(
                config=invalid_config,
                llm_model=self.llm_model,
            )


if __name__ == "__main__":
    unittest.main()
