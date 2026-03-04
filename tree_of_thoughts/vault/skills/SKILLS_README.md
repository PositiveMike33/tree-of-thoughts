# Advanced Skills System Documentation

This document provides comprehensive guidance on using the advanced skills system for Tree of Thoughts reasoning with integrated validation, fact-checking, and confidence scoring.

## Overview

The Advanced Skills System provides six domain-specific "skills" that leverage the complete Tree of Thoughts + validation stack for production-quality analysis and recommendations. Each skill uses a different Tree of Thoughts algorithm and is optimized for specific domains.

## Available Skills

| Skill | Algorithm | Domain | Use Case |
|-------|-----------|--------|----------|
| **Research Analyst** | A* | Research | Comprehensive research with verified sources |
| **Decision Maker** | BEST | Decision Analysis | Complex decisions with multiple perspectives |
| **Code Reviewer** | BFS | Software Engineering | Code analysis and security review |
| **Thesis Validator** | MCTS | Academic Research | Thesis validation with rigor |
| **Problem Solver** | BFS | Problem Solving | Complex problems with multiple approaches |
| **Expert Simulator** | DFS | Expert Reasoning | Expert recommendations with domain knowledge |

## Quick Start

### Via Command Line

```bash
# List available skills
python -m tree_of_thoughts.vault.skills.skills_cli --list

# Execute a skill
python -m tree_of_thoughts.vault.skills.skills_cli research \
  --prompt "What are recent quantum computing breakthroughs"

# Execute with context
python -m tree_of_thoughts.vault.skills.skills_cli decision \
  --prompt "Should we migrate to cloud infrastructure" \
  --context '{"domain": "software-engineering"}'

# Get JSON output
python -m tree_of_thoughts.vault.skills.skills_cli code \
  --prompt "Review this code for security issues" \
  --json
```

### Via Python API

```python
from tree_of_thoughts.vault.skills import ResearchAnalyst
from tree_of_thoughts.vault.tot_integration import VaultAwareLanguageModel

# Initialize skill
llm = VaultAwareLanguageModel(llm_client=your_client)
research = ResearchAnalyst(llm_model=llm)

# Execute
result = research.execute("What are latest AI breakthroughs")

# Access results
print(f"Output: {result.output}")
print(f"Confidence: {result.confidence_level} ({result.confidence_score:.2f})")
print(f"Requires Review: {result.requires_human_review}")
```

## Skill-Specific Guides

### 1. Research Analyst Skill

**Purpose**: Comprehensive research with verified sources and fact-checking.

**Algorithm**: A* (Optimal search for directed goals)

**Input Requirements**:
- Question should contain research-oriented keywords
- Minimum 20 characters, maximum 3000 characters
- Examples: "What are latest breakthroughs", "Analyze current trends"

**Output Includes**:
- Research findings with confidence scores
- Supporting evidence and sources
- Alternative perspectives
- Audit trail of reasoning

**Example**:
```python
research = ResearchAnalyst(llm_model=llm)
result = research.execute(
    "What are the latest developments in renewable energy technology?"
)
print(f"Findings: {result.output}")
print(f"Confidence: {result.confidence_level}")
```

**Context Options**:
- `domain`: Domain of research (e.g., "technology", "healthcare")
- `research_area`: Specific area (e.g., "renewable-energy")
- `audience`: Target audience level (e.g., "academic", "general")

### 2. Decision Maker Skill

**Purpose**: Complex decision analysis from multiple perspectives.

**Algorithm**: BEST (Explore best promising paths)

**Input Requirements**:
- Question should contain decision-making language
- Keywords: "should", "decide", "choose", "recommend"
- Minimum 20 characters, maximum 3000 characters

**Output Includes**:
- Recommendation with confidence score
- Pros/cons analysis from multiple angles
- Risk assessment
- Timeline and next steps

**Example**:
```python
decision = DecisionMaker(llm_model=llm)
result = decision.execute(
    "Should we invest in expanding our engineering team",
    context={
        "constraints": ["Budget limit: $500k", "Timeline: 6 months"],
        "stakeholders": ["CTO", "CFO", "HR"]
    }
)
```

**Context Options**:
- `domain`: Business domain
- `constraints`: List of constraints
- `resources`: Available resources
- `timeline`: Decision timeline

### 3. Code Reviewer Skill

**Purpose**: Deep code analysis and security review.

**Algorithm**: BFS (Systematic exploration)

**Input Requirements**:
- Code review request with code analysis keywords
- Keywords: "review", "analyze", "security", "bug", "performance"
- Minimum 20 characters, maximum 3000 characters

**Output Includes**:
- Issues ranked by severity
- Security vulnerabilities
- Performance problems
- Code quality recommendations

**Example**:
```python
reviewer = CodeReviewer(llm_model=llm)
result = reviewer.execute(
    "Review this code for security vulnerabilities and performance issues",
    context={
        "language": "python",
        "framework": "django",
        "version": "4.0"
    }
)
```

**Context Options**:
- `language`: Programming language
- `framework`: Framework or library used
- `version`: Technology version
- `focus_areas`: ["security", "performance", "maintainability"]

### 4. Thesis Validator Skill

**Purpose**: Validate academic/scientific claims with logical rigor.

**Algorithm**: MCTS (Monte Carlo Tree Search - sampling-based)

**Input Requirements**:
- Thesis or claim statement
- Keywords: "thesis", "claim", "argue", "propose", "demonstrate"
- Minimum 20 characters, maximum 3000 characters

**Output Includes**:
- Validity assessment
- Identified fallacies
- Counter-arguments
- Evidence quality evaluation
- Argument strength score

**Example**:
```python
validator = ThesisValidator(llm_model=llm)
result = validator.execute(
    "Thesis: Online education is as effective as traditional education",
    context={
        "subject": "education",
        "audience": "academic"
    }
)
```

**Context Options**:
- `subject`: Subject matter
- `audience`: Target audience level
- `knowledge_level`: Expected knowledge level
- `citation_style`: Citation format expected

### 5. Problem Solver Skill

**Purpose**: Solve complex problems with multiple solution approaches.

**Algorithm**: BFS (Breadth-first exploration of solution space)

**Input Requirements**:
- Problem statement with solution-seeking language
- Keywords: "solve", "problem", "challenge", "how", "approach"
- Minimum 20 characters, maximum 3000 characters

**Output Includes**:
- Multiple solution approaches ranked by feasibility
- Implementation complexity assessment
- Risk analysis per solution
- Constraint satisfaction analysis

**Example**:
```python
solver = ProblemSolver(llm_model=llm)
result = solver.execute(
    "How can we improve database performance under high load",
    context={
        "domain": "software-engineering",
        "constraints": ["Budget: $50k", "No downtime allowed"],
        "resources": {"team": 3, "timeline": "3 months"}
    }
)
```

**Context Options**:
- `domain`: Problem domain
- `constraints`: Hard constraints
- `resources`: Available resources
- `stakeholders`: Stakeholders involved

### 6. Expert Simulator Skill

**Purpose**: Simulate expert reasoning with domain-specific knowledge.

**Algorithm**: DFS (Depth-first domain-focused reasoning)

**Input Requirements**:
- Question seeking expert advice
- Keywords: "expert", "professional", "recommend", "best practice"
- Minimum 20 characters, maximum 3000 characters

**Output Includes**:
- Expert recommendation with high confidence
- Domain-specific insights
- Best practices identified
- Implementation guidance
- Confidence in expertise

**Example**:
```python
expert = ExpertSimulator(llm_model=llm)
result = expert.execute(
    "What is the expert recommendation for microservices architecture",
    context={
        "domain": "software-engineering",
        "expertise_area": "system-design",
        "industry": "fintech"
    }
)
```

**Context Options**:
- `domain`: Domain of expertise
- `expertise_area`: Specific area within domain
- `industry`: Industry context
- `experience_level`: Expected expertise level

## Understanding Output

### SkillResult Structure

Every skill execution returns a `SkillResult` with:

```python
class SkillResult:
    # Main output
    output: str                    # The primary answer/recommendation

    # Confidence metrics
    confidence_score: float        # 0.0 to 1.0
    confidence_level: str          # CERTAIN, HIGH, MEDIUM, LOW, VERY_LOW
    confidence_interval: float     # ±margin

    # Reasoning
    reasoning_paths: List[str]     # Paths explored by ToT
    execution_time: float          # Seconds to execute

    # Validation results
    validation_results: List[ValidationResult]
    fact_check_report: Dict
    blind_validation_report: Dict

    # Alternatives
    alternatives: List[Tuple[str, float]]  # (solution, confidence)
    recommendations: List[str]             # Next steps

    # Audit trail
    audit_trail: Dict              # Full reasoning chain

    # Metadata
    skill_type: SkillType
    requires_human_review: bool
```

### Confidence Levels

- **CERTAIN** (0.9-1.0): High confidence, validated thoroughly
- **HIGH** (0.7-0.9): Strong confidence, good validation
- **MEDIUM** (0.5-0.7): Moderate confidence, reasonable validation
- **LOW** (0.3-0.5): Lower confidence, may need review
- **VERY_LOW** (0.0-0.3): Low confidence, requires human review

## Configuration

### Algorithm Selection

Skills use different algorithms optimized for their domain:

```python
from tree_of_thoughts.vault.skills import ResearchAnalyst
from tree_of_thoughts.vault.skills.skill_config import AlgorithmType

# View default algorithm
research = ResearchAnalyst(llm_model=llm)
print(research.config.algorithm)  # AlgorithmType.A_STAR

# Custom configuration
from tree_of_thoughts.vault.skills.skill_config import SkillConfig

config = SkillConfig(
    skill_type=SkillType.RESEARCH,
    algorithm=AlgorithmType.A_STAR,
    name="Custom Research",
    num_thoughts=6,
    max_steps=8,
    confidence_threshold=0.80
)
research = ResearchAnalyst(config=config, llm_model=llm)
```

### Tuning Parameters

- `num_thoughts`: Number of reasoning paths to explore (5-10)
- `max_steps`: Maximum depth of reasoning (5-15)
- `confidence_threshold`: Minimum confidence to accept (0.5-0.95)
- `persist_results`: Save results to vault

## Advanced Usage

### Chaining Skills

Execute multiple skills in sequence:

```python
# Research a topic
research = ResearchAnalyst(llm_model=llm)
research_result = research.execute("What are latest AI trends")

# Make decision based on research
decision = DecisionMaker(llm_model=llm)
decision_result = decision.execute(
    "Should we invest in AI technology",
    context={"research_findings": research_result.output}
)

# Validate the decision
validator = ThesisValidator(llm_model=llm)
validation_result = validator.execute(
    f"Thesis: {decision_result.output}"
)
```

### Filtering by Confidence

```python
# Execute multiple skills and rank by confidence
skills = [
    ResearchAnalyst(llm_model=llm),
    ExpertSimulator(llm_model=llm),
    DecisionMaker(llm_model=llm)
]

prompt = "What is the best approach for system design"
results = []

for skill in skills:
    result = skill.execute(prompt)
    if result.confidence_score > 0.7:  # Filter by confidence
        results.append(result)

# Sort by confidence
results.sort(key=lambda r: r.confidence_score, reverse=True)
```

### Custom Context

Pass domain-specific context to enhance results:

```python
context = {
    "domain": "healthcare",
    "expertise_area": "patient-care",
    "constraints": ["HIPAA compliance required", "Budget: $1M"],
    "timeline": "6 months"
}

expert = ExpertSimulator(llm_model=llm)
result = expert.execute(
    "What is the expert recommendation for EMR implementation",
    context=context
)
```

## Performance Tuning

### Timeout Configuration

```python
config = SkillConfig(
    skill_type=SkillType.PROBLEM,
    timeout=30,  # 30 seconds max
    max_tokens=5000  # Token budget
)
solver = ProblemSolver(config=config, llm_model=llm)
```

### Parallel Execution

```python
import concurrent.futures

skills = [
    ResearchAnalyst(llm_model=llm),
    ExpertSimulator(llm_model=llm),
    ProblemSolver(llm_model=llm)
]

prompt = "What are the best practices for cloud migration"

with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [s.execute(prompt) for s in skills]
    results = [f.result() for f in concurrent.futures.as_completed(futures)]
```

## Testing

All skills come with comprehensive test suites:

```bash
# Test a specific skill
python -m unittest tree_of_thoughts.vault.skills.tests.test_research_analyst -v

# Test CLI
python -m unittest tree_of_thoughts.vault.skills.tests.test_skill_integration -v

# Test all skills
python -m unittest discover tree_of_thoughts/vault/skills/tests -v
```

## Troubleshooting

### Input Validation Errors

**Error**: "Request should contain problem-solving language"

**Solution**: Ensure your prompt includes domain-specific keywords:
- Research: "What are", "analyze", "investigate"
- Decision: "Should we", "decide", "recommend"
- Code: "Review", "analyze", "security", "bug"
- Thesis: "Thesis", "claim", "argue"
- Problem: "Solve", "problem", "challenge", "approach"
- Expert: "Expert", "recommend", "best practice"

### Low Confidence Scores

**Cause**: Input may be ambiguous or lack context

**Solution**:
1. Provide more specific prompt
2. Add relevant context
3. Consider using a skill with more permissive algorithm (e.g., BEST instead of A*)
4. Review confidence intervals

### Timeout Errors

**Cause**: Skill execution exceeds configured timeout

**Solution**:
1. Increase timeout in config
2. Reduce max_steps parameter
3. Use simpler prompt
4. Check LLM client performance

## API Reference

### Core Classes

#### SkillBase

Abstract base class for all skills.

**Methods**:
- `validate_input(prompt: str) -> Tuple[bool, str]`
- `build_system_prompt() -> str`
- `execute(prompt: str, context: Dict = None) -> SkillResult`
- `get_summary() -> Dict`

#### SkillResult

Result from skill execution.

**Attributes**:
- `output: str` - Main output
- `confidence_score: float` - 0.0-1.0
- `confidence_level: str` - CERTAIN/HIGH/MEDIUM/LOW/VERY_LOW
- `requires_human_review: bool`
- `execution_time: float`

### Skill Classes

All skills inherit from `SkillBase` and follow the same interface:

- `ResearchAnalyst`
- `DecisionMaker`
- `CodeReviewer`
- `ThesisValidator`
- `ProblemSolver`
- `ExpertSimulator`

### SkillsCLI

Command-line interface for skill execution.

**Methods**:
- `list_skills() -> dict` - List available skills
- `get_skill(skill_name: str) -> Skill | None`
- `execute_skill(skill_name: str, prompt: str, context: dict = None) -> dict`
- `main(args: list = None)` - CLI entry point

## Best Practices

1. **Always check confidence levels** - Lower confidence (< 0.6) may require human review
2. **Provide context** - More context generally improves results
3. **Use appropriate skill** - Match skill to your domain
4. **Monitor execution time** - Optimize if exceeding budgets
5. **Validate results** - Use `ThesisValidator` for critical decisions
6. **Chain skills** - Combine complementary skills for better results
7. **Review audit trails** - Understand reasoning paths

## Examples

See `/tree_of_thoughts/vault/skills/examples/` for complete working examples:
- research_example.py
- decision_example.py
- code_review_example.py
- thesis_validation_example.py
- problem_solving_example.py
- expert_simulation_example.py

## Support & Issues

For issues or questions:
1. Check the troubleshooting section above
2. Review test cases for usage patterns
3. Check validation messages in result output
4. Enable debug logging for detailed information

---

**Version**: 1.0.0
**Last Updated**: 2026-03-04
**Status**: Production Ready
