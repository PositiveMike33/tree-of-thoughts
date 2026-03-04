"""Tests for skill_config module."""

import unittest
from ..skill_config import (
    SkillType,
    AlgorithmType,
    ConfidenceThresholdType,
    VaultSection,
    SkillConfig,
    get_default_config,
)


class TestSkillType(unittest.TestCase):
    """Test SkillType enum."""

    def test_all_skill_types_exist(self):
        """Test that all expected skill types are defined."""
        expected_skills = {
            "RESEARCH", "DECISION", "CODE_REVIEW", "THESIS", "PROBLEM", "EXPERT"
        }
        actual_skills = {s.name for s in SkillType}
        self.assertEqual(actual_skills, expected_skills)

    def test_skill_type_values(self):
        """Test that skill type values are correct."""
        self.assertEqual(SkillType.RESEARCH.value, "research")
        self.assertEqual(SkillType.DECISION.value, "decision")
        self.assertEqual(SkillType.CODE_REVIEW.value, "code_review")


class TestAlgorithmType(unittest.TestCase):
    """Test AlgorithmType enum."""

    def test_all_algorithms_exist(self):
        """Test that all expected algorithms are defined."""
        expected_algorithms = {"BFS", "DFS", "BEST", "A_STAR", "MCTS"}
        actual_algorithms = {a.name for a in AlgorithmType}
        self.assertEqual(actual_algorithms, expected_algorithms)

    def test_algorithm_values(self):
        """Test that algorithm values are correct."""
        self.assertEqual(AlgorithmType.BFS.value, "bfs")
        self.assertEqual(AlgorithmType.A_STAR.value, "a_star")
        self.assertEqual(AlgorithmType.MCTS.value, "mcts")


class TestConfidenceThresholdType(unittest.TestCase):
    """Test ConfidenceThresholdType enum."""

    def test_threshold_values(self):
        """Test that threshold values are correct."""
        self.assertEqual(ConfidenceThresholdType.MINIMUM.value, 0.3)
        self.assertEqual(ConfidenceThresholdType.LOW.value, 0.5)
        self.assertEqual(ConfidenceThresholdType.MEDIUM.value, 0.7)
        self.assertEqual(ConfidenceThresholdType.HIGH.value, 0.85)
        self.assertEqual(ConfidenceThresholdType.VERY_HIGH.value, 0.95)


class TestVaultSection(unittest.TestCase):
    """Test VaultSection enum."""

    def test_all_vault_sections_exist(self):
        """Test that all expected vault sections are defined."""
        expected_sections = {"PSYCHE", "BRAIN", "KNOWLEDGE", "PLANNING", "RAPPORT"}
        actual_sections = {s.name for s in VaultSection}
        self.assertEqual(actual_sections, expected_sections)


class TestSkillConfig(unittest.TestCase):
    """Test SkillConfig dataclass."""

    def test_create_config_with_defaults(self):
        """Test creating config with default values."""
        config = SkillConfig(
            skill_type=SkillType.RESEARCH,
            algorithm=AlgorithmType.A_STAR,
        )
        self.assertEqual(config.skill_type, SkillType.RESEARCH)
        self.assertEqual(config.algorithm, AlgorithmType.A_STAR)
        self.assertEqual(config.num_thoughts, 5)
        self.assertEqual(config.max_steps, 5)
        self.assertEqual(config.confidence_threshold, 0.75)
        self.assertTrue(config.require_fact_check)
        self.assertTrue(config.require_blind_validation)
        self.assertEqual(config.timeout_seconds, 30)
        self.assertEqual(config.max_tokens, 5000)

    def test_create_config_with_custom_values(self):
        """Test creating config with custom values."""
        config = SkillConfig(
            skill_type=SkillType.CODE_REVIEW,
            algorithm=AlgorithmType.BFS,
            name="Custom Code Reviewer",
            num_thoughts=10,
            max_steps=7,
            confidence_threshold=0.85,
            timeout_seconds=60,
        )
        self.assertEqual(config.name, "Custom Code Reviewer")
        self.assertEqual(config.num_thoughts, 10)
        self.assertEqual(config.max_steps, 7)
        self.assertEqual(config.confidence_threshold, 0.85)
        self.assertEqual(config.timeout_seconds, 60)

    def test_validate_config_valid(self):
        """Test validation of valid config."""
        config = SkillConfig(
            skill_type=SkillType.RESEARCH,
            algorithm=AlgorithmType.A_STAR,
        )
        is_valid, message = config.validate()
        self.assertTrue(is_valid)
        self.assertEqual(message, "")

    def test_validate_config_invalid_num_thoughts(self):
        """Test validation rejects invalid num_thoughts."""
        config = SkillConfig(
            skill_type=SkillType.RESEARCH,
            algorithm=AlgorithmType.A_STAR,
            num_thoughts=0,
        )
        is_valid, message = config.validate()
        self.assertFalse(is_valid)
        self.assertIn("num_thoughts", message)

    def test_validate_config_invalid_max_steps(self):
        """Test validation rejects invalid max_steps."""
        config = SkillConfig(
            skill_type=SkillType.RESEARCH,
            algorithm=AlgorithmType.A_STAR,
            max_steps=-1,
        )
        is_valid, message = config.validate()
        self.assertFalse(is_valid)
        self.assertIn("max_steps", message)

    def test_validate_config_invalid_confidence_threshold(self):
        """Test validation rejects invalid confidence_threshold."""
        config = SkillConfig(
            skill_type=SkillType.RESEARCH,
            algorithm=AlgorithmType.A_STAR,
            confidence_threshold=1.5,
        )
        is_valid, message = config.validate()
        self.assertFalse(is_valid)
        self.assertIn("confidence_threshold", message)

    def test_validate_config_invalid_timeout(self):
        """Test validation rejects invalid timeout."""
        config = SkillConfig(
            skill_type=SkillType.RESEARCH,
            algorithm=AlgorithmType.A_STAR,
            timeout_seconds=0,
        )
        is_valid, message = config.validate()
        self.assertFalse(is_valid)

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = SkillConfig(
            skill_type=SkillType.DECISION,
            algorithm=AlgorithmType.BEST,
            name="Test Decision Maker",
            num_thoughts=6,
        )
        result_dict = config.to_dict()
        self.assertEqual(result_dict["skill_type"], "decision")
        self.assertEqual(result_dict["algorithm"], "best")
        self.assertEqual(result_dict["name"], "Test Decision Maker")
        self.assertEqual(result_dict["num_thoughts"], 6)

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "skill_type": "research",
            "algorithm": "a_star",
            "name": "Research from Dict",
            "num_thoughts": 8,
            "max_steps": 7,
            "confidence_threshold": 0.80,
        }
        config = SkillConfig.from_dict(data)
        self.assertEqual(config.skill_type, SkillType.RESEARCH)
        self.assertEqual(config.algorithm, AlgorithmType.A_STAR)
        self.assertEqual(config.name, "Research from Dict")
        self.assertEqual(config.num_thoughts, 8)
        self.assertEqual(config.confidence_threshold, 0.80)

    def test_roundtrip_serialization(self):
        """Test dict conversion roundtrip."""
        original = SkillConfig(
            skill_type=SkillType.CODE_REVIEW,
            algorithm=AlgorithmType.BFS,
            name="Original Config",
            num_thoughts=5,
        )
        as_dict = original.to_dict()
        reconstructed = SkillConfig.from_dict(as_dict)
        self.assertEqual(original.skill_type, reconstructed.skill_type)
        self.assertEqual(original.algorithm, reconstructed.algorithm)
        self.assertEqual(original.name, reconstructed.name)
        self.assertEqual(original.num_thoughts, reconstructed.num_thoughts)


class TestDefaultConfigs(unittest.TestCase):
    """Test default skill configurations."""

    def test_all_default_configs_exist(self):
        """Test that default configs exist for all skill types."""
        for skill_type in SkillType:
            config = get_default_config(skill_type)
            self.assertIsNotNone(config)
            self.assertEqual(config.skill_type, skill_type)

    def test_research_default_config(self):
        """Test Research Analyst default config."""
        config = get_default_config(SkillType.RESEARCH)
        self.assertEqual(config.algorithm, AlgorithmType.A_STAR)
        self.assertEqual(config.num_thoughts, 8)
        self.assertEqual(config.max_steps, 7)

    def test_decision_default_config(self):
        """Test Decision Maker default config."""
        config = get_default_config(SkillType.DECISION)
        self.assertEqual(config.algorithm, AlgorithmType.BEST)
        self.assertEqual(config.num_thoughts, 6)

    def test_code_review_default_config(self):
        """Test Code Reviewer default config."""
        config = get_default_config(SkillType.CODE_REVIEW)
        self.assertEqual(config.algorithm, AlgorithmType.BFS)

    def test_all_default_configs_valid(self):
        """Test that all default configs are valid."""
        for skill_type in SkillType:
            config = get_default_config(skill_type)
            is_valid, message = config.validate()
            self.assertTrue(is_valid, f"Config for {skill_type} is invalid: {message}")


if __name__ == "__main__":
    unittest.main()
