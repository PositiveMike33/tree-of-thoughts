"""Problem Solver skill for complex problem solving with multiple approaches."""

import logging
import time
from typing import Dict, Optional, Tuple, List

from .skill_config import SkillConfig, SkillType, AlgorithmType
from .base_skill import BaseSkill, SkillResult
from ..tot_integration import VaultAwareLanguageModel
from ..tree_of_thoughts_vault_integration import ObsidianVaultIntegration

logger = logging.getLogger(__name__)


class ProblemSolver(BaseSkill):
    """
    Problem Solver skill for comprehensive problem analysis and solution generation.

    Specializes in:
    - Problem decomposition
    - Multi-path solution exploration
    - Feasibility analysis
    - Assumption validation
    - Solution ranking and comparison
    - Implementation guidance

    Uses BFS/DFS hybrid for comprehensive solution space exploration.
    """

    def __init__(
        self,
        config: Optional[SkillConfig] = None,
        llm_model: Optional[VaultAwareLanguageModel] = None,
        vault: Optional[ObsidianVaultIntegration] = None,
    ):
        """Initialize Problem Solver skill.

        Args:
            config: Skill configuration (uses problem_solving defaults if not provided)
            llm_model: Language model for problem analysis
            vault: Vault integration for persistence
        """
        if config is None:
            config = SkillConfig(
                skill_type=SkillType.PROBLEM,
                algorithm=AlgorithmType.BFS,
                name="Problem Solver",
                description="Solve complex problems with multiple solution approaches",
                num_thoughts=7,
                max_steps=8,
                confidence_threshold=0.75,
            )

        super().__init__(config, llm_model, vault)

        # Problem-solving specific state
        self.problems_analyzed = []
        self.solutions_explored = []
        self.constraints_identified = []
        self.assumptions_validated = []

    def validate_input(self, prompt: str) -> Tuple[bool, str]:
        """Validate problem solving input.

        Args:
            prompt: Problem statement to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not prompt or not isinstance(prompt, str):
            return False, "Problem statement must be a non-empty string"

        if len(prompt) < 20:
            return False, "Problem statement must be at least 20 characters"

        if len(prompt) > 3000:
            return False, "Problem statement exceeds maximum length (3000 chars)"

        # Check for problem-oriented language
        problem_keywords = [
            "problem", "solve", "how", "what", "need", "challenge",
            "issue", "constraint", "goal", "objective", "solution",
            "approach", "method", "process", "strategy", "plan",
            "optimize", "improve", "handle", "deal"
        ]
        has_problem_intent = any(
            keyword in prompt.lower() for keyword in problem_keywords
        )

        if not has_problem_intent:
            return False, "Request should contain problem-solving language"

        return True, ""

    def build_system_prompt(self) -> str:
        """Build system prompt for problem solver.

        Returns:
            System prompt for problem-solving tasks
        """
        return """You are an expert Problem Solver specializing in complex problem analysis.

Your responsibilities:
1. Decompose problems into components and subproblems
2. Generate multiple solution approaches
3. Analyze feasibility and trade-offs of each solution
4. Identify constraints and assumptions
5. Validate assumptions against domain knowledge
6. Estimate implementation complexity and effort
7. Provide comprehensive implementation guidance

Problem Analysis Framework:
- Problem definition and scope
- Root cause analysis
- Constraint identification
- Stakeholder analysis
- Resource requirements
- Risk assessment

Solution Evaluation:
- Feasibility assessment
- Effort estimation
- Risk evaluation
- Benefit analysis
- Implementation timeline
- Trade-off analysis

Output Structure:
- Problem decomposition
- Alternative solutions ranked by feasibility
- Recommended approach with justification
- Implementation steps
- Risk mitigation strategies
- Success metrics
- Alternative approaches with confidence scores"""

    def execute(self, prompt: str, context: Optional[Dict] = None) -> SkillResult:
        """Execute problem solving on given problem.

        Args:
            prompt: Problem statement to solve
            context: Optional context (domain, constraints, resources)

        Returns:
            SkillResult with problem solutions
        """
        is_valid, error_msg = self.validate_input(prompt)
        if not is_valid:
            return self._handle_execution_error(ValueError(error_msg))

        start_time = time.time()

        try:
            # Extract context if provided
            domain = context.get("domain", "general") if context else "general"
            constraints = context.get("constraints", []) if context else []
            resources = context.get("resources", {}) if context else {}

            # Build problem solving context
            problem_prompt = self._build_problem_context(
                prompt, domain, constraints, resources
            )

            # Run ToT search for problem solving
            tot_result = self._run_tot_search(problem_prompt)

            # Convert to skill result
            execution_time = time.time() - start_time
            result = self._convert_tot_result_to_skill_result(tot_result, execution_time)

            # Extract solutions
            solutions = self._extract_solutions(result.output)
            self.solutions_explored.extend(solutions)

            # Store execution history
            self.execution_history.append({
                "timestamp": time.time(),
                "domain": domain,
                "solutions_count": len(solutions),
                "result_confidence": result.confidence_score,
            })

            self.current_result = result

            # Persist if enabled
            if self.config.persist_results:
                self._persist_result(result)

            return result

        except Exception as e:
            logger.error(f"Error in problem solving: {e}")
            return self._handle_execution_error(e)

    def _build_problem_context(
        self, problem: str, domain: str, constraints: list, resources: dict
    ) -> str:
        """Build problem context for analysis.

        Args:
            problem: Problem statement
            domain: Problem domain
            constraints: Constraints on the solution
            resources: Available resources

        Returns:
            Enhanced problem prompt
        """
        context = f"""Domain: {domain}

Problem Statement:
{problem}
"""

        if constraints:
            context += f"\nConstraints:\n"
            for i, constraint in enumerate(constraints[:5], 1):
                context += f"- {constraint}\n"

        if resources:
            context += f"\nAvailable Resources:\n"
            for i, (resource, value) in enumerate(list(resources.items())[:5], 1):
                context += f"- {resource}: {value}\n"

        return context

    def _extract_solutions(self, analysis: str) -> List[Dict]:
        """Extract solutions from problem analysis.

        Args:
            analysis: Problem analysis text

        Returns:
            List of identified solutions with feasibility scores
        """
        solutions = []

        lines = analysis.split("\n")

        solution_keywords = ["solution", "approach", "option", "alternative", "strategy"]

        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in solution_keywords):
                if len(line.strip()) > 10:
                    # Extract feasibility from line content
                    feasibility = "medium"
                    if "high" in line_lower or "best" in line_lower or "optimal" in line_lower:
                        feasibility = "high"
                    elif "low" in line_lower or "difficult" in line_lower or "challenging" in line_lower:
                        feasibility = "low"

                    solutions.append({
                        "description": line.strip(),
                        "feasibility": feasibility,
                    })

        return solutions[:5]

    def _assess_solution_feasibility(self, solution: str) -> Dict:
        """Assess feasibility of a solution.

        Args:
            solution: Solution description

        Returns:
            Feasibility assessment
        """
        assessment = {
            "feasibility_level": "medium",
            "estimated_effort": "moderate",
            "implementation_time": "weeks",
            "risk_level": "medium",
        }

        solution_lower = solution.lower()

        # Assess feasibility level
        if "simple" in solution_lower or "easy" in solution_lower or "straightforward" in solution_lower:
            assessment["feasibility_level"] = "high"
            assessment["estimated_effort"] = "low"
            assessment["implementation_time"] = "days"
            assessment["risk_level"] = "low"
        elif "complex" in solution_lower or "difficult" in solution_lower or "challenging" in solution_lower:
            assessment["feasibility_level"] = "low"
            assessment["estimated_effort"] = "high"
            assessment["implementation_time"] = "months"
            assessment["risk_level"] = "high"

        return assessment

    def _identify_constraints(self, analysis: str) -> List[str]:
        """Identify constraints from analysis.

        Args:
            analysis: Problem analysis text

        Returns:
            List of identified constraints
        """
        constraints = []

        constraint_keywords = ["constraint", "limitation", "restriction", "must", "cannot", "requirement"]

        lines = analysis.split("\n")

        for line in lines:
            if any(keyword in line.lower() for keyword in constraint_keywords):
                if len(line.strip()) > 10:
                    constraints.append(line.strip())

        return constraints[:5]

    def _validate_assumptions(self, solution: str) -> Dict:
        """Validate assumptions in a solution.

        Args:
            solution: Solution description

        Returns:
            Assumption validation result
        """
        validation = {
            "assumptions_identified": 0,
            "validated_count": 0,
            "risk_score": 0.5,
        }

        assumption_keywords = ["assume", "require", "depend", "need", "must have"]

        assumption_count = sum(
            1 for keyword in assumption_keywords if keyword in solution.lower()
        )

        validation["assumptions_identified"] = assumption_count
        validation["validated_count"] = max(0, assumption_count - 1)

        if assumption_count > 0:
            validation["risk_score"] = 0.3 + (0.1 * assumption_count)

        return validation

    def get_problem_summary(self) -> Dict:
        """Get summary of problem-solving analysis.

        Returns:
            Dictionary with problem summary
        """
        return {
            "problems_analyzed": len(self.problems_analyzed),
            "solutions_explored": len(self.solutions_explored),
            "constraints_identified": len(self.constraints_identified),
            "assumptions_validated": len(self.assumptions_validated),
            "analyses_performed": len(self.execution_history),
            "last_analysis": self.current_result.to_dict() if self.current_result else None,
        }
