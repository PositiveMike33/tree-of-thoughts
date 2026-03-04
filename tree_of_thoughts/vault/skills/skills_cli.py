"""Unified CLI tool for executing skills."""

import argparse
import json
import sys
from typing import Optional

from .skill_config import SkillType
from .research_analyst import ResearchAnalyst
from .decision_maker import DecisionMaker
from .code_reviewer import CodeReviewer
from .thesis_validator import ThesisValidator
from .problem_solver import ProblemSolver
from .expert_simulator import ExpertSimulator
from ..tot_integration import VaultAwareLanguageModel


class SkillsCLI:
    """Command-line interface for executing skills."""

    SKILLS_MAP = {
        "research": ResearchAnalyst,
        "decision": DecisionMaker,
        "code": CodeReviewer,
        "thesis": ThesisValidator,
        "problem": ProblemSolver,
        "expert": ExpertSimulator,
    }

    def __init__(self, llm_model=None):
        """Initialize CLI with LLM model.

        Args:
            llm_model: Optional LLM model instance (for testing)
        """
        self.llm_model = llm_model

    def get_skill(self, skill_name: str):
        """Get skill instance by name.

        Args:
            skill_name: Name of the skill (research, decision, code, thesis, problem, expert)

        Returns:
            Skill instance or None if not found
        """
        skill_class = self.SKILLS_MAP.get(skill_name)
        if skill_class is None:
            return None
        return skill_class(llm_model=self.llm_model)

    def execute_skill(
        self, skill_name: str, prompt: str, context: Optional[dict] = None
    ) -> dict:
        """Execute a skill with given input.

        Args:
            skill_name: Name of the skill to execute
            prompt: Input prompt for the skill
            context: Optional context dictionary

        Returns:
            Dictionary with skill result
        """
        # Lazily initialize LLM if not provided
        if self.llm_model is None:
            self.llm_model = VaultAwareLanguageModel(llm_client=None)

        skill = self.get_skill(skill_name)
        if skill is None:
            return {
                "error": f"Unknown skill: {skill_name}",
                "available_skills": list(self.SKILLS_MAP.keys()),
            }

        try:
            result = skill.execute(prompt, context=context)
            return {
                "success": True,
                "skill": skill_name,
                "output": result.output,
                "confidence_score": result.confidence_score,
                "confidence_level": result.confidence_level,
                "requires_human_review": result.requires_human_review,
                "execution_time": result.execution_time,
                "skill_type": result.skill_type.name if result.skill_type else None,
            }
        except Exception as e:
            return {"error": str(e), "skill": skill_name}

    def list_skills(self) -> dict:
        """List available skills with descriptions.

        Returns:
            Dictionary with skill information
        """
        return {
            "available_skills": {
                "research": "Research analysis with verified sources",
                "decision": "Complex decision analysis with multiple perspectives",
                "code": "Deep code analysis and security review",
                "thesis": "Thesis/paper validation with rigor",
                "problem": "Complex problem solving with multiple approaches",
                "expert": "Expert reasoning simulation with domain knowledge",
            }
        }

    def main(self, args: Optional[list] = None):
        """Main CLI entry point.

        Args:
            args: Command-line arguments (for testing)
        """
        parser = argparse.ArgumentParser(
            description="Execute advanced skills with Tree of Thoughts reasoning"
        )
        parser.add_argument(
            "skill",
            nargs="?",
            help="Skill to execute (research, decision, code, thesis, problem, expert)",
        )
        parser.add_argument(
            "--prompt", "-p", help="Input prompt for the skill"
        )
        parser.add_argument(
            "--context", "-c", type=json.loads, help="Context as JSON string"
        )
        parser.add_argument(
            "--list", "-l", action="store_true", help="List available skills"
        )
        parser.add_argument(
            "--json", "-j", action="store_true", help="Output as JSON"
        )

        parsed_args = parser.parse_args(args)

        # Handle list command
        if parsed_args.list:
            result = self.list_skills()
            if parsed_args.json:
                print(json.dumps(result, indent=2))
            else:
                print("\nAvailable Skills:")
                for name, desc in result["available_skills"].items():
                    print(f"  {name:12} - {desc}")
            return

        # Require skill and prompt
        if not parsed_args.skill:
            parser.print_help()
            return

        if not parsed_args.prompt:
            print("Error: --prompt/-p is required")
            parser.print_help()
            return

        # Execute skill
        result = self.execute_skill(
            parsed_args.skill, parsed_args.prompt, context=parsed_args.context
        )

        # Output result
        if parsed_args.json:
            print(json.dumps(result, indent=2))
        else:
            if "error" in result:
                print(f"Error: {result['error']}")
                if "available_skills" in result:
                    print(f"Available skills: {result['available_skills']}")
            else:
                print(f"\n{'='*60}")
                print(f"Skill: {result['skill'].upper()}")
                print(f"{'='*60}")
                print(f"Output:\n{result['output']}")
                print(f"\nConfidence: {result['confidence_level']} ({result['confidence_score']:.2f})")
                print(f"Execution Time: {result['execution_time']:.2f}s")
                if result["requires_human_review"]:
                    print("⚠️  Requires human review")
                print(f"{'='*60}\n")


def main():
    """Entry point for CLI."""
    cli = SkillsCLI()
    cli.main()


if __name__ == "__main__":
    main()
