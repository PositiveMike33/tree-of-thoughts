"""
Advanced Skills Package for Tree of Thoughts

Provides domain-specific skills that leverage the complete ToT + validation stack:
- Research Analyst: Comprehensive research with verified sources (A* algorithm)
- Decision Maker: Multi-option evaluation and recommendation (BEST algorithm)
- Code Reviewer: Code quality and security analysis (BFS algorithm)
- Thesis Validator: Academic claim validation (MCTS algorithm)
- Problem Solver: Multi-solution path exploration (BFS/DFS hybrid)
- Expert Simulator: Domain expertise simulation (DFS algorithm)

Each skill combines:
- Tree of Thoughts algorithm for reasoning path generation
- Multi-level validation (syntactic, completeness, consistency)
- Fact-checking with meta-evaluation
- Triple-blind validation with consensus scoring
- Structured results with confidence scores and audit trails
"""

__version__ = "0.1.0"

# Exports will be added as skills are implemented
__all__ = []
