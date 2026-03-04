"""Code Reviewer skill for comprehensive code analysis and improvement suggestions."""

import logging
import time
from typing import Dict, Optional, Tuple, List

from .skill_config import SkillConfig, SkillType, AlgorithmType
from .base_skill import BaseSkill, SkillResult
from ..tot_integration import VaultAwareLanguageModel
from ..tree_of_thoughts_vault_integration import ObsidianVaultIntegration

logger = logging.getLogger(__name__)


class CodeReviewer(BaseSkill):
    """
    Code Reviewer skill for comprehensive code analysis.

    Specializes in:
    - Code quality assessment
    - Performance optimization
    - Security vulnerability detection
    - Best practices validation
    - Maintainability analysis
    - Refactoring suggestions

    Uses BFS algorithm for comprehensive code path exploration.
    """

    def __init__(
        self,
        config: Optional[SkillConfig] = None,
        llm_model: Optional[VaultAwareLanguageModel] = None,
        vault: Optional[ObsidianVaultIntegration] = None,
    ):
        """Initialize Code Reviewer skill.

        Args:
            config: Skill configuration (uses code_review defaults if not provided)
            llm_model: Language model for code analysis
            vault: Vault integration for persistence
        """
        if config is None:
            config = SkillConfig(
                skill_type=SkillType.CODE_REVIEW,
                algorithm=AlgorithmType.BFS,
                name="Code Reviewer",
                description="Review code and suggest improvements",
                num_thoughts=5,
                max_steps=6,
                confidence_threshold=0.75,
            )

        super().__init__(config, llm_model, vault)

        # Code review-specific state
        self.issues_found = []
        self.recommendations = []
        self.complexity_scores = {}
        self.security_issues = []

    def validate_input(self, prompt: str) -> Tuple[bool, str]:
        """Validate code review request.

        Args:
            prompt: Code review request to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not prompt or not isinstance(prompt, str):
            return False, "Code review request must be a non-empty string"

        if len(prompt) < 20:
            return False, "Code review request must be at least 20 characters"

        if len(prompt) > 5000:
            return False, "Code exceeds maximum length (5000 chars)"

        # Check for code-related keywords
        code_keywords = [
            "code", "function", "class", "method", "review",
            "improve", "bug", "performance", "security",
            "refactor", "quality", "best practice", "test",
            "algorithm", "optimization", "structure"
        ]
        has_code_intent = any(
            keyword in prompt.lower() for keyword in code_keywords
        )

        if not has_code_intent:
            return False, "Request should mention code review or related concepts"

        return True, ""

    def build_system_prompt(self) -> str:
        """Build system prompt for code reviewer.

        Returns:
            System prompt for code review tasks
        """
        return """You are an expert Code Reviewer with deep expertise in software quality.

Your responsibilities:
1. Analyze code for correctness and functionality
2. Identify performance bottlenecks and optimization opportunities
3. Detect security vulnerabilities and risks
4. Evaluate code maintainability and readability
5. Check adherence to best practices and standards
6. Provide specific, actionable recommendations
7. Estimate complexity and technical debt

Review Categories:
- Functionality: Does code work correctly?
- Performance: Is it efficient?
- Security: Are there vulnerabilities?
- Maintainability: Is it understandable?
- Testing: Is it testable?
- Standards: Does it follow best practices?

Output Structure:
- Summary of overall code quality
- Issues by category (critical, major, minor)
- Refactoring suggestions with priority
- Performance improvement opportunities
- Security recommendations
- Code quality metrics
- Confidence level for assessment"""

    def execute(self, prompt: str, context: Optional[Dict] = None) -> SkillResult:
        """Execute code review on provided code.

        Args:
            prompt: Code to review or review request with code
            context: Optional context (language, frameworks, standards)

        Returns:
            SkillResult with code review findings
        """
        is_valid, error_msg = self.validate_input(prompt)
        if not is_valid:
            return self._handle_execution_error(ValueError(error_msg))

        start_time = time.time()

        try:
            # Extract context if provided
            language = context.get("language", "unknown") if context else "unknown"
            frameworks = context.get("frameworks", []) if context else []
            standards = context.get("standards", []) if context else []

            # Build code review context
            review_prompt = self._build_review_context(
                prompt, language, frameworks, standards
            )

            # Run ToT search for code review
            tot_result = self._run_tot_search(review_prompt)

            # Convert to skill result
            execution_time = time.time() - start_time
            result = self._convert_tot_result_to_skill_result(tot_result, execution_time)

            # Extract and store issues
            issues = self._extract_issues(result.output)
            self.issues_found.extend(issues)

            # Store execution history
            self.execution_history.append({
                "timestamp": time.time(),
                "language": language,
                "issues_count": len(issues),
                "result_confidence": result.confidence_score,
            })

            self.current_result = result

            # Persist if enabled
            if self.config.persist_results:
                self._persist_result(result)

            return result

        except Exception as e:
            logger.error(f"Error in code review: {e}")
            return self._handle_execution_error(e)

    def _build_review_context(
        self, code: str, language: str, frameworks: list, standards: list
    ) -> str:
        """Build code review context.

        Args:
            code: Code to review
            language: Programming language
            frameworks: Used frameworks/libraries
            standards: Code standards to check

        Returns:
            Enhanced review prompt with context
        """
        context = f"""Programming Language: {language}
Code to Review:
{code}
"""

        if frameworks:
            context += f"\nFrameworks/Libraries: {', '.join(frameworks)}\n"

        if standards:
            context += f"Code Standards: {', '.join(standards)}\n"

        return context

    def _extract_issues(self, review_output: str) -> List[Dict]:
        """Extract issues from code review output.

        Args:
            review_output: Code review analysis text

        Returns:
            List of identified issues
        """
        issues = []

        # Define issue severity patterns
        critical_patterns = ["critical", "security", "vulnerability", "crash"]
        major_patterns = ["bug", "error", "incorrect", "major issue"]
        minor_patterns = ["minor", "nitpick", "style", "convention"]

        lines = review_output.split("\n")

        for line in lines:
            line_lower = line.lower()

            if any(pattern in line_lower for pattern in critical_patterns):
                issues.append({"severity": "critical", "description": line.strip()})
            elif any(pattern in line_lower for pattern in major_patterns):
                issues.append({"severity": "major", "description": line.strip()})
            elif any(pattern in line_lower for pattern in minor_patterns):
                issues.append({"severity": "minor", "description": line.strip()})

        return issues[:20]  # Limit to 20 issues

    def _assess_code_complexity(self, code: str) -> Dict:
        """Assess code complexity metrics.

        Args:
            code: Code to analyze

        Returns:
            Complexity assessment dictionary
        """
        assessment = {
            "cyclomatic_complexity": 1,
            "nesting_depth": 0,
            "function_count": 0,
            "complexity_level": "low",
        }

        lines = code.split("\n")

        # Estimate nesting depth by counting indentation
        max_indent = 0
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                max_indent = max(max_indent, indent // 4)

        assessment["nesting_depth"] = max_indent

        # Count functions/methods
        func_keywords = ["def ", "function ", "class "]
        func_count = sum(
            line.count(keyword) for line in lines
            for keyword in func_keywords
        )
        assessment["function_count"] = func_count

        # Estimate complexity level
        if max_indent > 5:
            assessment["complexity_level"] = "very_high"
            assessment["cyclomatic_complexity"] = 4
        elif max_indent > 3:
            assessment["complexity_level"] = "high"
            assessment["cyclomatic_complexity"] = 3
        elif max_indent > 1:
            assessment["complexity_level"] = "medium"
            assessment["cyclomatic_complexity"] = 2
        else:
            assessment["complexity_level"] = "low"
            assessment["cyclomatic_complexity"] = 1

        return assessment

    def _detect_security_issues(self, code: str) -> List[str]:
        """Detect potential security issues in code.

        Args:
            code: Code to analyze for security

        Returns:
            List of detected security issues
        """
        security_issues = []

        # Security patterns to detect
        patterns = {
            "sql_injection": ["execute(", "query(", "sql", "inject"],
            "xss_vulnerability": ["innerhtml", "eval", "script"],
            "hardcoded_secrets": ["password", "api_key", "secret", "token"],
            "unsafe_deserialization": ["pickle", "deserialize", "json.load"],
            "path_traversal": ["open(", "path.join", "file"],
        }

        code_lower = code.lower()

        for issue_type, keywords in patterns.items():
            if any(keyword.lower() in code_lower for keyword in keywords):
                security_issues.append(issue_type)

        return list(set(security_issues))[:10]

    def get_review_summary(self) -> Dict:
        """Get summary of code reviews.

        Returns:
            Dictionary with review summary
        """
        return {
            "total_issues": len(self.issues_found),
            "critical_issues": sum(
                1 for issue in self.issues_found
                if issue.get("severity") == "critical"
            ),
            "major_issues": sum(
                1 for issue in self.issues_found
                if issue.get("severity") == "major"
            ),
            "minor_issues": sum(
                1 for issue in self.issues_found
                if issue.get("severity") == "minor"
            ),
            "security_concerns": len(self.security_issues),
            "recommendations": len(self.recommendations),
            "reviews_performed": len(self.execution_history),
        }
