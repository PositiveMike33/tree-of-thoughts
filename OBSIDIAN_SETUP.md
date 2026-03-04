# Obsidian Integration Setup Guide

Complete guide to integrate Tree of Thoughts with Obsidian vault and enable bidirectional synchronization.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Vault Structure](#vault-structure)
6. [Recommended Plugins](#recommended-plugins)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

- **Python 3.8+** with tree-of-thoughts installed
- **Obsidian** (latest version)
- **Docker** (if using remote vault at `D:/Vault/Vault/`)
- **Git** (for vault versioning)

### Required Python Packages

The following packages are automatically installed with the Obsidian integration:

```bash
pip install tree-of-thoughts[obsidian]
```

Or manually:

```bash
pip install PyYAML>=6.0 watchdog>=3.0.0 python-frontmatter>=1.0.0
```

## Installation

### 1. Update requirements.txt

Verify your `requirements.txt` includes the Obsidian integration dependencies:

```
PyYAML>=6.0
watchdog>=3.0.0
python-frontmatter>=1.0.0
```

### 2. Create Vault Structure

Create the following directory structure in your Obsidian vault:

```
D:/Vault/Vault/
├── 00-Index/
│   └── Tree of Thoughts Central Index.md
├── thinking/                    # Auto-created for ToT exports
├── states/                      # Auto-created for state files
├── analysis/                    # For synthesis and analysis
├── .obsidian/                   # Obsidian config (exists by default)
├── .vault-metadata/             # Auto-created for sync metadata
│   └── sync-log.json
└── exports/                     # JSON backups (auto-created)
```

### 3. Initialize Obsidian Vault

If you don't have an Obsidian vault at `D:/Vault/Vault/`:

1. Open Obsidian
2. Click **Create new vault**
3. Name it: `Vault`
4. Choose location: `D:/Vault/` (parent directory)
5. Click **Create**

## Configuration

### Python Configuration

To enable Obsidian export in your Tree of Thoughts execution:

```python
from tree_of_thoughts.treeofthoughts import TreeofThoughts
from tree_of_thoughts.models.openai_models import OpenAILanguageModel

# Initialize model
model = OpenAILanguageModel(api_key="your-api-key")

# Create ToT instance with Obsidian export enabled
tot = TreeofThoughts(
    model=model,
    export_to_obsidian=True,
    vault_path="D:/Vault/Vault/"  # Or use environment variable
)

# Run your Tree of Thoughts algorithm
result = tot.search(...)

# ToT results are automatically exported to Obsidian!
```

### Environment Variables (Optional)

Set environment variables to avoid hardcoding paths:

**Linux/Mac:**
```bash
export TOT_VAULT_PATH="/mnt/d/Vault/Vault/"
export TOT_EXPORT_DIR="./logs"
```

**Windows:**
```powershell
$env:TOT_VAULT_PATH = "D:/Vault/Vault/"
$env:TOT_EXPORT_DIR = "./logs"
```

Then in Python:

```python
import os
vault_path = os.getenv("TOT_VAULT_PATH", "D:/Vault/Vault/")
```

### Configuration File (Optional)

Create `.vault-config.json` in your project root:

```json
{
  "obsidian": {
    "vault_path": "D:/Vault/Vault/",
    "auto_export": true,
    "continuous_watch": true,
    "conflict_strategy": "last_write_wins",
    "debounce_delay_ms": 500,
    "ignore_patterns": [".conflict-", ".metadata-"]
  }
}
```

Load in Python:

```python
import json

with open(".vault-config.json") as f:
    config = json.load(f)

tot = TreeofThoughts(
    model=model,
    export_to_obsidian=config["obsidian"]["auto_export"],
    vault_path=config["obsidian"]["vault_path"]
)
```

## Usage

### Basic Export

```python
# ToT automatically exports after execution
result = tot.search(initial_state, num_iterations=5)
# Result is in D:/Vault/Vault/thinking/[DATE]/[algorithm]-[timestamp].md
```

### Manual Export

If needed, manually export to Obsidian:

```python
from tree_of_thoughts.exporters.obsidian_adapter import ObsidianAdapter

adapter = ObsidianAdapter(
    output_dir="./logs",
    vault_path="D:/Vault/Vault/"
)

output_path = adapter.export(
    tot_data=tot.tree,
    metadata={"algorithm": "DFS", "model": "GPT-4"},
    title="Problem: Game 24"
)

print(f"Exported to: {output_path}")
```

### Continuous Synchronization

Start automatic file watcher:

```python
from tree_of_thoughts.sync.obsidian_sync import ObsidianSync

sync = ObsidianSync(
    vault_path="D:/Vault/Vault/",
    local_path="./logs",
    enable_watcher=True
)

sync.start_continuous_sync()  # Runs in background

# ... your code ...

sync.stop_continuous_sync()  # Stop when done
```

### Viewing Sync Logs

Check synchronization history:

```bash
# View latest sync log
cat D:/Vault/Vault/.vault-metadata/sync-log.json | jq '.events[-5:]'

# Check for conflicts
grep "genuine_conflict" D:/Vault/Vault/.vault-metadata/sync-log.json
```

## Vault Structure

### Generated Note Structure

Each exported ToT execution creates a note with YAML frontmatter:

```markdown
---
uuid: 550e8400-e29b-41d4-a716-446655440000
type: thought
algorithm: MonteCarloTreeofThoughts
model: GPT-4
timestamp: 2026-03-04T12:34:56Z
tags: [tree-of-thoughts, reasoning, problem-solving]
status: completed
---

# Problem: Solve Math Problem

## Problem Statement
[Problem description]

## Thinking Tree
- **Initial State** (score: 0.87)
  - **Branch 1** (score: 0.92)
  - **Branch 2** (score: 0.45)
- **Alternative Approach** (score: 0.78)

## Final Solution
[Best solution found]

## Metadata
- Tokens used: 1,234
- Tree depth: 4
- Explored branches: 8
- Execution time: 12.3s

## Raw JSON
```json
[Raw tree structure]
```
```

### Directory Organization

```
D:/Vault/Vault/thinking/
├── 2026-03-01/
│   ├── game24-001.md
│   ├── game24-002.md
│   └── math-problem-001.md
├── 2026-03-02/
│   ├── crosswords-001.md
│   └── text-generation-001.md
└── 2026-03-03/
    └── ...
```

## Recommended Plugins

### Essential Plugins

**1. Dataview**
- Query ToT results by algorithm, model, or date
- Create dynamic dashboards

Example query:
```dataview
TABLE algorithm, model, timestamp
WHERE type = "thought" AND status = "completed"
SORT timestamp DESC
LIMIT 20
```

**2. Canvas**
- Visualize thinking trees as graph networks
- Show relationships between different solutions

**3. Obsidian Git**
- Auto-commit ToT exports after each run
- Full version history of thinking process

Setup:
```bash
cd D:/Vault/Vault/
git init
git config user.email "bot@tree-of-thoughts.local"
git config user.name "ToT Bot"
```

**4. Templater**
- Auto-generate templates for new ToT notes
- Pre-fill metadata fields

### Optional Plugins

**5. Graph Analysis**
- Visualize connections between thinking notes
- Identify patterns in problem-solving

**6. Periodic Notes**
- Create daily/weekly synthesis notes
- Summarize ToT outputs by time period

**7. Smart Typography**
- Professional formatting for mathematical content
- Auto-formatting for code blocks

## Troubleshooting

### Issue: Files Not Syncing

**Symptoms:**
- ToT exports, but files don't appear in `D:/Vault/Vault/`
- Modified files in Obsidian don't sync back

**Solutions:**

1. Check vault path configuration:
```python
from tree_of_thoughts.sync.obsidian_sync import ObsidianSync

sync = ObsidianSync(vault_path="D:/Vault/Vault/")
print(f"Vault path: {sync.vault_path}")
print(f"Vault exists: {sync.vault_path.exists()}")
```

2. Verify watchdog is installed:
```bash
pip list | grep watchdog
```

3. Check permissions:
```bash
ls -la D:/Vault/Vault/
```

4. View sync logs:
```bash
cat D:/Vault/Vault/.vault-metadata/sync-log.json
```

### Issue: Conflicts Between Local and Vault

**Symptoms:**
- `.conflict-[timestamp].md` files appear in vault

**Resolution:**

1. Review conflict file:
```bash
cat D:/Vault/Vault/conflicted-file.conflict-2026-03-04T12:34:56.md
```

2. Decide which version to keep
3. Delete conflict file when resolved
4. Re-sync if needed

### Issue: Obsidian Not Recognizing Notes

**Symptoms:**
- Notes appear in folder but not in Obsidian UI

**Solutions:**

1. Refresh vault:
   - In Obsidian, press `Ctrl+Shift+R` (Cmd+Shift+R on Mac)

2. Check file encoding:
   - All ToT exports are UTF-8, ensure Obsidian is set to UTF-8

3. Rebuild vault index:
   - Close Obsidian
   - Delete `.obsidian/cache` directory
   - Reopen Obsidian

### Issue: High CPU Usage from File Watcher

**Symptoms:**
- File watcher consuming significant CPU
- Disk activity excessive

**Solutions:**

1. Increase debounce delay:
```python
resolver = ConflictResolver(...)
resolver.MIN_SYNC_INTERVAL_SECONDS = 2.0  # Increase from 0.5s
```

2. Stop watcher when not needed:
```python
sync.stop_continuous_sync()
```

3. Limit watch scope:
```python
sync = ObsidianSync(
    vault_path="D:/Vault/Vault/thinking/",  # Only watching thinking/
    local_path="./logs",
    enable_watcher=True
)
```

## Advanced Usage

### Custom Export Metadata

Add custom fields to exported notes:

```python
metadata = {
    "algorithm": "DFS",
    "model": "GPT-4",
    "custom_field": "custom_value",
    "tags": ["optimization", "experimental"],
}

adapter.export(tot.tree, metadata, "My Experiment")
```

### Batch Export

Export multiple ToT executions:

```python
from pathlib import Path
import json

logs_dir = Path("./logs")
for json_file in logs_dir.glob("*.json"):
    with open(json_file) as f:
        data = json.load(f)

    adapter.export(data, {"algorithm": "BFS"}, json_file.stem)
```

### Integration with CI/CD

Add GitHub Actions workflow:

```yaml
name: Export ToT to Obsidian

on: [push]

jobs:
  export:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Mount Vault
        run: docker run -v D:/Vault/Vault/:/vault ...
      - name: Export
        run: python -m tree_of_thoughts.exporters.obsidian_adapter
```

## Support

For issues or questions:

1. Check sync logs: `D:/Vault/Vault/.vault-metadata/sync-log.json`
2. Review error messages: Run with `logging.basicConfig(level=logging.DEBUG)`
3. Test in isolation: Use examples from `examples/` directory
4. Report issues on GitHub with logs attached

## Next Steps

1. ✅ Install dependencies
2. ✅ Create vault structure
3. ✅ Configure Python integration
4. ✅ Install Obsidian plugins
5. ✅ Run first ToT export
6. ✅ Verify sync to vault
7. ✅ Set up continuous synchronization
8. ✅ Explore Dataview queries

Happy thinking! 🧠✨
