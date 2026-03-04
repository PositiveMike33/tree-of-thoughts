# Tree of Thoughts Vault Integration

Complete integration of Tree of Thoughts with Obsidian Vault and OpenRouter LLM for creating organized thought nodes.

## Features

- **5 Vault Sections**: `_PSYCHE`, `_BRAIN`, `KNOWLEDGE`, `PLANNING`, `RAPPORT`
- **Complete Responses**: Fixed truncation issues with max_tokens=5000
- **Intelligent Parsing**: Automatic splitting by headers → numbered sections → paragraphs
- **Multi-Language**: Support for English and French
- **Psychological Depth**: PSYCHE section with French language support
- **Node Synthesis**: Automatic generation of synthesis notes and neural maps
- **Configurable**: All settings via `.env` file

## Setup

### 1. Get OpenRouter API Key

1. Visit [openrouter.ai](https://openrouter.ai)
2. Sign up or log in
3. Go to [Keys](https://openrouter.ai/keys) and copy your API key

### 2. Configure Environment

```bash
# Copy the template
cp .env.template .env

# Edit .env and add your API key
# OPENROUTER_API_KEY=your-key-here
```

### 3. Install Dependencies (if needed)

```bash
pip install requests python-dotenv
```

## Usage

### Run a Session

**English (BRAIN section)**:
```bash
python -m tree_of_thoughts.vault.vault_sync_simple session \
  "What are the implications of quantum computing on cryptography?"
```

**French (PSYCHE section)**:
```bash
python -m tree_of_thoughts.vault.vault_sync_simple session \
  "Comment comprendre mes traumas complexes et en guérir?" \
  --section PSYCHE \
  --language french
```

**With all options**:
```bash
python -m tree_of_thoughts.vault.vault_sync_simple session \
  --prompt "Your question here" \
  --section BRAIN \
  --language english \
  --depth 0 \
  --parent parent-node-id \
  --verbose
```

### Generate Reports

```bash
# Daily report
python -m tree_of_thoughts.vault.vault_sync_simple report --type daily

# Weekly report
python -m tree_of_thoughts.vault.vault_sync_simple report --section BRAIN --type weekly

# Monthly report
python -m tree_of_thoughts.vault.vault_sync_simple report --type monthly
```

## Output Structure

```
./vault/
├── _PSYCHE/
│   └── ToT/
│       ├── node-id-1.md
│       ├── node-id-2.md
│       ├── synthesis_*.md
│       └── neural_map.md
├── _BRAIN/
│   └── ToT/
├── KNOWLEDGE/
│   └── ToT/
├── PLANNING/
│   └── ToT/
└── RAPPORT/
    └── ToT/
```

## System Prompts by Section

### PSYCHE
- Psychological exploration and self-discovery
- Minimum 3 distinct sections per session
- 300+ words per section
- French language support
- Focus on beliefs, emotions, personal growth

### BRAIN
- Logical reasoning and analysis
- Step-by-step argumentation
- Multiple perspectives
- Evidence-based conclusions

### KNOWLEDGE
- Systematic information compilation
- Comprehensive and well-organized
- Definitions and context
- Current understanding

### PLANNING
- Strategic planning and action items
- Goals and objectives
- Specific steps and timelines
- Resource requirements

### RAPPORT
- Relationship and connection analysis
- Communication patterns
- Relational dynamics
- Connection opportunities

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | Required | Your OpenRouter API key |
| `OPENROUTER_MODEL` | `cognitivecomputations/dolphin-mistral-24b-venice-edition:free` | Model to use |
| `OPENROUTER_MAX_TOKENS` | `5000` | Maximum tokens in response |
| `OPENROUTER_TEMPERATURE` | `0.7` | Response creativity (0-2) |
| `OPENROUTER_TIMEOUT` | `60` | API timeout in seconds |
| `VAULT_ROOT` | `./vault` | Vault directory path |

## API Classes

### SimplifiedVaultSync

Main CLI interface class.

```python
from tree_of_thoughts.vault import SimplifiedVaultSync

sync = SimplifiedVaultSync()

# Run session
result = sync.session(
    prompt="Your question",
    section="BRAIN",
    language="english"
)

# Generate report
report = sync.report(section="BRAIN", report_type="daily")
```

### ObsidianVaultIntegration

Vault file operations.

```python
from tree_of_thoughts.vault import ObsidianVaultIntegration, ThoughtNode, VaultSection

vault = ObsidianVaultIntegration()

# Create note
node = ThoughtNode(
    text="Your thought content",
    section=VaultSection.BRAIN,
    evaluation=0.85
)
path = vault.create_note(node)

# Generate synthesis
synthesis = vault.create_synthesis_note(nodes, VaultSection.BRAIN, "Title", "prompt")

# Create neural map
neural_map = vault.create_neural_map(VaultSection.BRAIN)
```

### VaultSection Enum

```python
from tree_of_thoughts.vault import VaultSection

VaultSection.PSYCHE      # _PSYCHE
VaultSection.BRAIN       # _BRAIN
VaultSection.KNOWLEDGE   # KNOWLEDGE
VaultSection.PLANNING    # PLANNING
VaultSection.RAPPORT     # RAPPORT
```

### ThoughtNode Dataclass

```python
from tree_of_thoughts.vault import ThoughtNode, VaultSection

node = ThoughtNode(
    text="Your thought content here",
    section=VaultSection.BRAIN,
    depth=1,
    evaluation=0.85,
    confidence=0.90,
    tags=["reasoning", "analysis"],
    language="english"
)

# Check properties
node.get_word_count()   # Returns word count
node.is_complete()      # Check if >= 300 words
```

## Response Quality

The system ensures complete, untruncated responses by:

1. **High Token Limit**: max_tokens=5000 (vs 50 default)
2. **Structured Prompts**: Section-specific instructions for complete answers
3. **Intelligent Parsing**: Respects natural boundaries (headers, sections)
4. **Validation**: Ensures minimum 300 words per node
5. **Fallback Strategies**: Multiple parsing approaches if first fails

### Response Parsing Strategy

The system tries these approaches in order:

1. **Markdown Headers**: Split by `##` or `###` headers
2. **Numbered Sections**: Split by `1. 2. 3.` patterns
3. **Paragraphs**: Split by double newlines
4. **Full Response**: Use entire response if no structure found

## Examples

### Example 1: Exploring Complex Emotions (PSYCHE)

```bash
python -m tree_of_thoughts.vault.vault_sync_simple session \
  "Comment gérer l'anxiété et la dépression ensemble?" \
  --section PSYCHE \
  --language french \
  --verbose
```

**Output**: 3-4 nodes created with psychological depth, saved to `vault/_PSYCHE/ToT/`

### Example 2: Technical Analysis (BRAIN)

```bash
python -m tree_of_thoughts.vault.vault_sync_simple session \
  "Explain the CAP theorem and its implications for distributed databases"
```

**Output**: Multiple nodes with logical reasoning, saved to `vault/_BRAIN/ToT/`

### Example 3: Knowledge Building (KNOWLEDGE)

```bash
python -m tree_of_thoughts.vault.vault_sync_simple session \
  "What are the main concepts in quantum mechanics?" \
  --section KNOWLEDGE
```

**Output**: Comprehensive knowledge nodes saved to `vault/KNOWLEDGE/ToT/`

## Markdown Format

Generated notes use this structure:

```markdown
---
id: 8a3f2b1c
section: _BRAIN
depth: 1
evaluation: 0.87
confidence: 0.90
timestamp: 2026-03-04T11:20:30
tags: reasoning, analysis
language: english
type: thought_node
---

# 8a3f2b1c — _BRAIN

## Pensée / Thought

[Full thought content here...]

## Contexte / Context

**Section**: [[_BRAIN]]
**Depth**: 1
**Evaluation**: 87%
**Confidence**: 90%
...
```

## Troubleshooting

### "OPENROUTER_API_KEY not found"

Make sure you have `.env` file with your API key:
```bash
cp .env.template .env
# Edit .env and add your key
```

### "Response may be incomplete"

The system will warn if responses appear truncated, but will continue processing. Check generated notes for completeness.

### Empty vault directory

Make sure `VAULT_ROOT` path exists and is writable. The system creates it automatically if needed.

## Performance

- **First request**: ~10-30 seconds (depends on OpenRouter queue)
- **Subsequent requests**: ~5-15 seconds
- **Response size**: Typically 1500-2500 tokens (~6000-10000 characters)

## Limitations

- OpenRouter API depends on external service availability
- Response quality depends on selected model
- Large prompts may exceed token limits (use --depth 0 for root analysis)

## Future Enhancements

- [ ] Integration with Tree of Thoughts algorithms
- [ ] Multiple model comparison
- [ ] Batch processing
- [ ] Automatic continuation detection
- [ ] Citation and source tracking
- [ ] Real-time streaming responses
- [ ] Web UI for easier interaction

## Related Files

- `/tree_of_thoughts/vault/__init__.py` - Package exports
- `/tree_of_thoughts/vault/openrouter_config.py` - LLM configuration
- `/tree_of_thoughts/vault/tree_of_thoughts_vault_integration.py` - Core classes
- `/tree_of_thoughts/vault/vault_sync_simple.py` - CLI interface
- `/.env.template` - Configuration template

## License

Part of the Tree of Thoughts project.
