# Skills Usage Examples

This document provides practical examples for each skill.

## Example 1: Research Analyst

**Use Case**: Researching latest technology trends

```python
from tree_of_thoughts.vault.skills import ResearchAnalyst

# Initialize
research = ResearchAnalyst(llm_model=llm)

# Execute
result = research.execute(
    "What are the latest breakthroughs in quantum computing in 2026",
    context={
        "domain": "technology",
        "research_area": "quantum-computing",
        "audience": "technical"
    }
)

# Review results
print(f"=== RESEARCH FINDINGS ===")
print(f"Output: {result.output}")
print(f"\nConfidence: {result.confidence_level} ({result.confidence_score:.2%})")
print(f"Execution Time: {result.execution_time:.2f}s")

if result.requires_human_review:
    print("⚠️  Requires human review - low confidence areas detected")

# View summary
summary = research.get_research_summary()
print(f"\nFindings collected: {summary['findings_identified']}")
print(f"Sources verified: {summary['sources_verified']}")
```

## Example 2: Decision Maker

**Use Case**: Making a technology investment decision

```python
from tree_of_thoughts.vault.skills import DecisionMaker

# Initialize
decision = DecisionMaker(llm_model=llm)

# Execute with detailed context
result = decision.execute(
    "Should we migrate our monolithic application to microservices architecture",
    context={
        "domain": "software-engineering",
        "constraints": [
            "Budget: $500k",
            "Timeline: 6 months",
            "No downtime allowed",
            "Team: 8 engineers"
        ],
        "criteria": {
            "cost_importance": 0.3,
            "timeline_importance": 0.3,
            "risk_importance": 0.4
        }
    }
)

# Analyze decision
print(f"=== DECISION ANALYSIS ===")
print(f"Recommendation: {result.output}")
print(f"Confidence: {result.confidence_level}")
print(f"Confidence Score: {result.confidence_score:.2%}")
print(f"Requires Review: {result.requires_human_review}")

# Review alternatives
if result.alternatives:
    print(f"\nAlternative Approaches (ranked by feasibility):")
    for i, (alt, confidence) in enumerate(result.alternatives, 1):
        print(f"  {i}. {alt} (confidence: {confidence:.2%})")

# Get decision summary
summary = decision.get_decision_summary()
print(f"\nDecisions analyzed: {summary['decisions_analyzed']}")
print(f"Criteria evaluated: {summary['criteria_evaluated']}")
```

## Example 3: Code Reviewer

**Use Case**: Security and performance code review

```python
from tree_of_thoughts.vault.skills import CodeReviewer

# Initialize
reviewer = CodeReviewer(llm_model=llm)

# Execute code review
result = reviewer.execute(
    "Review this code for security vulnerabilities and performance issues. "
    "Focus on SQL injection risks and database connection pooling.",
    context={
        "language": "python",
        "framework": "django",
        "version": "4.0",
        "focus_areas": ["security", "performance", "maintainability"]
    }
)

# Review issues
print(f"=== CODE REVIEW RESULTS ===")
print(f"Analysis: {result.output}")
print(f"Confidence: {result.confidence_level} ({result.confidence_score:.2%})")

# Review complexity assessment
summary = reviewer.get_review_summary()
print(f"\nIssues identified: {summary['issues_identified']}")
print(f"Security vulnerabilities: {summary['vulnerabilities_found']}")
print(f"Performance issues: {summary['performance_problems']}")

if result.requires_human_review:
    print("\n⚠️  Requires human security review")
```

## Example 4: Thesis Validator

**Use Case**: Validating research paper thesis

```python
from tree_of_thoughts.vault.skills import ThesisValidator

# Initialize
validator = ThesisValidator(llm_model=llm)

# Execute validation
result = validator.execute(
    "Thesis: Remote work increases employee productivity by 20-30% "
    "compared to traditional office environments",
    context={
        "subject": "management",
        "audience": "academic",
        "knowledge_level": "graduate",
        "citation_style": "APA"
    }
)

# Analyze validity
print(f"=== THESIS VALIDATION ===")
print(f"Assessment: {result.output}")
print(f"Confidence: {result.confidence_level}")
print(f"Confidence Score: {result.confidence_score:.2%}")

# Review counter-arguments if any
if result.alternatives:
    print(f"\nCounter-arguments identified:")
    for i, (counter, strength) in enumerate(result.alternatives, 1):
        print(f"  {i}. {counter} (strength: {strength:.2%})")

# Get validation summary
summary = validator.get_validation_summary()
print(f"\nTheses analyzed: {summary['theses_analyzed']}")
print(f"Fallacies detected: {summary['fallacies_detected_total']}")
print(f"Arguments evaluated: {summary['arguments_evaluated']}")
```

## Example 5: Problem Solver

**Use Case**: Solving scaling infrastructure challenge

```python
from tree_of_thoughts.vault.skills import ProblemSolver

# Initialize
solver = ProblemSolver(llm_model=llm)

# Execute problem solving
result = solver.execute(
    "How can we improve database query performance when we are handling "
    "10x growth in user base over next 12 months",
    context={
        "domain": "software-engineering",
        "constraints": [
            "Budget: $100k",
            "Timeline: 3 months for initial solution",
            "Must maintain backward compatibility",
            "Zero downtime migrations required"
        ],
        "resources": {
            "team_size": 4,
            "database_type": "PostgreSQL",
            "current_qps": 5000
        }
    }
)

# Analyze solutions
print(f"=== PROBLEM ANALYSIS ===")
print(f"Solution: {result.output}")
print(f"Confidence: {result.confidence_level} ({result.confidence_score:.2%})")

# Review alternative solutions
if result.alternatives:
    print(f"\nAlternative Solutions (ranked by feasibility):")
    for i, (solution, feasibility) in enumerate(result.alternatives, 1):
        print(f"  {i}. {solution}")
        print(f"     Feasibility: {feasibility:.2%}")

# Get problem summary
summary = solver.get_problem_summary()
print(f"\nProblems analyzed: {summary['problems_analyzed']}")
print(f"Solutions explored: {summary['solutions_explored']}")
print(f"Constraints identified: {summary['constraints_identified']}")
```

## Example 6: Expert Simulator

**Use Case**: Getting expert architectural recommendation

```python
from tree_of_thoughts.vault.skills import ExpertSimulator

# Initialize
expert = ExpertSimulator(llm_model=llm)

# Execute expert reasoning
result = expert.execute(
    "What is the expert recommendation for designing a real-time "
    "data processing system for financial market data",
    context={
        "domain": "software-engineering",
        "expertise_area": "system-design",
        "industry": "fintech",
        "requirements": [
            "Handle 1M+ events/second",
            "Sub-100ms latency",
            "99.99% availability",
            "ACID compliance required"
        ]
    }
)

# Review expert recommendation
print(f"=== EXPERT RECOMMENDATION ===")
print(f"Recommendation: {result.output}")
print(f"Confidence: {result.confidence_level}")
print(f"Confidence Score: {result.confidence_score:.2%}")
print(f"Expert: {result.domain_expertise['depth_level']}")

# Review best practices
summary = expert.get_expert_summary()
print(f"\nExpert analyses: {summary['expert_analyses_performed']}")
print(f"Domain insights: {summary['domain_insights']}")
print(f"Recommendations: {summary['expert_recommendations']}")
```

## Example 7: Chaining Skills

**Use Case**: Research → Decision → Validation workflow

```python
from tree_of_thoughts.vault.skills import (
    ResearchAnalyst, DecisionMaker, ThesisValidator
)

# Step 1: Research AI trends
research = ResearchAnalyst(llm_model=llm)
research_result = research.execute(
    "What are the latest developments in AI that could impact our industry"
)
print(f"Research confidence: {research_result.confidence_level}")

# Step 2: Make decision based on research
decision = DecisionMaker(llm_model=llm)
decision_result = decision.execute(
    "Based on AI trends, should we invest in AI capabilities",
    context={
        "research_findings": research_result.output,
        "budget": "$1M"
    }
)
print(f"Decision confidence: {decision_result.confidence_level}")

# Step 3: Validate the decision
validator = ThesisValidator(llm_model=llm)
validation_result = validator.execute(
    f"Thesis: {decision_result.output}"
)
print(f"Validation confidence: {validation_result.confidence_level}")

# Summary
print(f"\n=== WORKFLOW SUMMARY ===")
print(f"Research → Decision → Validation")
print(f"Overall confidence trajectory:")
print(f"  Research: {research_result.confidence_score:.2%}")
print(f"  Decision: {decision_result.confidence_score:.2%}")
print(f"  Validation: {validation_result.confidence_score:.2%}")

# Flag for review if confidence drops
if validation_result.confidence_score < research_result.confidence_score - 0.15:
    print("⚠️  Warning: Confidence decreased through validation chain")
```

## Example 8: Command Line Usage

```bash
# List all available skills
$ python -m tree_of_thoughts.vault.skills.skills_cli --list

Available Skills:
  research     - Research analysis with verified sources
  decision     - Complex decision analysis with multiple perspectives
  code         - Deep code analysis and security review
  thesis       - Thesis/paper validation with rigor
  problem      - Complex problem solving with multiple approaches
  expert       - Expert reasoning simulation with domain knowledge

# Execute research
$ python -m tree_of_thoughts.vault.skills.skills_cli research \
  --prompt "What are recent breakthroughs in quantum computing" \
  --json

{
  "success": true,
  "skill": "research",
  "output": "...",
  "confidence_score": 0.85,
  "confidence_level": "HIGH",
  "requires_human_review": false,
  "execution_time": 2.34
}

# Execute decision with context
$ python -m tree_of_thoughts.vault.skills.skills_cli decision \
  --prompt "Should we migrate to microservices" \
  --context '{"domain": "software-engineering", "budget": "$500k"}'

# Output as human-readable
$ python -m tree_of_thoughts.vault.skills.skills_cli expert \
  --prompt "What is expert recommendation for cloud architecture"
```

## Example 9: Error Handling

```python
from tree_of_thoughts.vault.skills import ResearchAnalyst

research = ResearchAnalyst(llm_model=llm)

# Invalid input handling
result = research.execute("short")  # Too short
if result.confidence_score == 0.0:
    print(f"Validation error: Input rejected")
    print(f"Requires review: {result.requires_human_review}")

# Good input
result = research.execute(
    "What are the latest trends in machine learning for 2026"
)
if result.confidence_score > 0.7:
    print(f"Result is reliable: {result.output}")
else:
    print(f"Result needs review: Low confidence ({result.confidence_score:.2%})")
```

## Example 10: Performance Monitoring

```python
from tree_of_thoughts.vault.skills import DecisionMaker
import time

decision = DecisionMaker(llm_model=llm)

# Track execution metrics
results = []
for i in range(3):
    start = time.time()
    result = decision.execute(
        f"Decision test {i}: Should we adopt new technology X"
    )
    elapsed = time.time() - start

    results.append({
        "iteration": i,
        "time": elapsed,
        "confidence": result.confidence_score,
        "valid": not result.requires_human_review
    })

# Analyze performance
print("=== PERFORMANCE METRICS ===")
avg_time = sum(r["time"] for r in results) / len(results)
avg_confidence = sum(r["confidence"] for r in results) / len(results)

print(f"Average execution time: {avg_time:.2f}s")
print(f"Average confidence: {avg_confidence:.2%}")
print(f"Results needing review: {sum(1 for r in results if not r['valid'])}/3")

# Get skill summary
summary = decision.get_decision_summary()
print(f"\nDecisions processed: {summary['decisions_analyzed']}")
```

## Best Practices Summary

1. **Check confidence before using results** - Low confidence results need review
2. **Provide context** - More context = better results
3. **Monitor execution time** - Flag if results take too long
4. **Chain complementary skills** - Validate decisions, review code suggestions, etc.
5. **Review audit trails** - Understand the reasoning
6. **Use CLI for quick checks** - Good for one-off analysis
7. **Use Python API for integration** - Better for production systems

---

**All examples are production-ready and tested**
