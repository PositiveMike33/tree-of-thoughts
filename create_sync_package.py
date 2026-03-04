#!/usr/bin/env python3
"""
Skills System Sync & Distribution Script

Crée une archive complète des fichiers du Skills System
pour synchronisation avec des vaults externes.
"""

import os
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

# Configuration
PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "dist"
VAULT_SYNC_DIR = OUTPUT_DIR / "vault_sync"

# Fichiers à inclure
FILES_TO_SYNC = {
    "Core Skills System": [
        "tree_of_thoughts/vault/skills/skills_manager.py",
        "tree_of_thoughts/vault/skills/skill_wrapper.py",
        "tree_of_thoughts/vault/skills/cli_handlers.py",
        "tree_of_thoughts/vault/skills/__init__.py",
    ],
    "Documentation": [
        "SKILLS_SYSTEM.md",
        "CLAUDE_CODE_SKILLS_INTEGRATION.md",
        "SKILLS_SYSTEM_SUMMARY.md",
    ],
    "Examples": [
        "examples/skills_system_demo.py",
    ],
}


def create_sync_package():
    """Crée un package de synchronisation complet."""

    print("🔄 Creating Skills System Sync Package...")
    print("=" * 70)

    # Créer les répertoires
    VAULT_SYNC_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Copier les fichiers
    print("\n1️⃣  Copying files...")
    for category, files in FILES_TO_SYNC.items():
        print(f"\n   📁 {category}")
        for file_path in files:
            src = PROJECT_ROOT / file_path
            if src.exists():
                # Créer la structure de répertoire
                relative_path = Path(file_path)
                dest = VAULT_SYNC_DIR / relative_path
                dest.parent.mkdir(parents=True, exist_ok=True)

                # Copier le fichier
                shutil.copy2(src, dest)
                print(f"      ✓ {file_path}")
            else:
                print(f"      ✗ NOT FOUND: {file_path}")

    # 2. Créer un manifest
    print("\n2️⃣  Creating manifest...")
    manifest = {
        "name": "Tree of Thoughts Skills System",
        "version": "1.1.0",
        "created": datetime.now().isoformat(),
        "description": "Complete Skills Management System with Real-time Optimization",
        "files": {
            "core": [
                "tree_of_thoughts/vault/skills/skills_manager.py",
                "tree_of_thoughts/vault/skills/skill_wrapper.py",
                "tree_of_thoughts/vault/skills/cli_handlers.py",
                "tree_of_thoughts/vault/skills/__init__.py",
            ],
            "documentation": [
                "SKILLS_SYSTEM.md",
                "CLAUDE_CODE_SKILLS_INTEGRATION.md",
                "SKILLS_SYSTEM_SUMMARY.md",
            ],
            "examples": [
                "examples/skills_system_demo.py",
            ],
        },
        "installation": {
            "windows": "Copy files to your project respecting the folder structure",
            "linux_mac": "Copy files to your project respecting the folder structure",
            "git": "Files are in branch: claude/vault-sync-openrouter-test-JQ8N9",
        },
        "imports": [
            "from tree_of_thoughts.vault.skills import SkillWrapper, SkillType",
            "from tree_of_thoughts.vault.skills import get_cli_handler",
            "from tree_of_thoughts.vault.skills import SkillsManagementSystem",
        ],
    }

    manifest_path = VAULT_SYNC_DIR / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"   ✓ Manifest created: {manifest_path.name}")

    # 3. Créer un script d'installation
    print("\n3️⃣  Creating installation script...")
    create_install_script()
    print(f"   ✓ Installation scripts created")

    # 4. Créer une archive ZIP
    print("\n4️⃣  Creating ZIP archive...")
    zip_path = create_zip_archive()
    print(f"   ✓ Archive: {zip_path.name}")

    # 5. Créer un guide de synchronisation
    print("\n5️⃣  Creating sync guide...")
    create_sync_guide()
    print(f"   ✓ Sync guide created")

    print("\n" + "=" * 70)
    print("✅ Sync package ready!\n")

    # Afficher le résumé
    print_summary()


def create_install_script():
    """Crée les scripts d'installation."""

    # Script Windows (PowerShell)
    powershell_script = '''# Tree of Thoughts Skills System - Installation Script (Windows)
# Usage: .\\install_skills.ps1

$ProjectRoot = $PSScriptRoot
$SourceDir = "$ProjectRoot\\vault_sync"
$DestDir = "."  # Changez selon votre projet

Write-Host "🔄 Installing Tree of Thoughts Skills System..." -ForegroundColor Cyan

# Fonction pour copier les fichiers
function Copy-FilesRecursive {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path $Source)) {
        Write-Host "✗ Source directory not found: $Source" -ForegroundColor Red
        return
    }

    Get-ChildItem -Path $Source -Recurse | ForEach-Object {
        $RelativePath = $_.FullName.Substring($Source.Length + 1)
        $DestPath = Join-Path $Destination $RelativePath

        if ($_ -is [System.IO.DirectoryInfo]) {
            New-Item -ItemType Directory -Path $DestPath -Force | Out-Null
        } else {
            New-Item -ItemType Directory -Path (Split-Path $DestPath) -Force | Out-Null
            Copy-Item -Path $_.FullName -Destination $DestPath -Force
            Write-Host "  ✓ $RelativePath"
        }
    }
}

# Copier les fichiers
Write-Host ""
Write-Host "Copying files..." -ForegroundColor Green
Copy-FilesRecursive -Source $SourceDir -Destination $DestDir

Write-Host ""
Write-Host "✅ Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Read SKILLS_SYSTEM.md"
Write-Host "  2. Run: python examples\\skills_system_demo.py"
Write-Host "  3. Test with: from tree_of_thoughts.vault.skills import SkillWrapper"
Write-Host ""
'''

    # Script Bash (Linux/Mac)
    bash_script = '''#!/bin/bash
# Tree of Thoughts Skills System - Installation Script (Linux/Mac)
# Usage: bash install_skills.sh

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$PROJECT_ROOT/vault_sync"
DEST_DIR="${1:-.}"  # Argument ou répertoire courant

echo "🔄 Installing Tree of Thoughts Skills System..."
echo ""

# Vérifier que le répertoire source existe
if [ ! -d "$SOURCE_DIR" ]; then
    echo "✗ Source directory not found: $SOURCE_DIR"
    exit 1
fi

# Copier les fichiers
echo "Copying files..."
find "$SOURCE_DIR" -type f | while read file; do
    relative_path="${file#$SOURCE_DIR/}"
    dest_path="$DEST_DIR/$relative_path"
    dest_dir="$(dirname "$dest_path")"

    mkdir -p "$dest_dir"
    cp "$file" "$dest_path"
    echo "  ✓ $relative_path"
done

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Read SKILLS_SYSTEM.md"
echo "  2. Run: python examples/skills_system_demo.py"
echo "  3. Test with: from tree_of_thoughts.vault.skills import SkillWrapper"
echo ""
'''

    # Sauvegarder les scripts
    ps1_path = VAULT_SYNC_DIR / "install_skills.ps1"
    ps1_path.write_text(powershell_script)

    bash_path = VAULT_SYNC_DIR / "install_skills.sh"
    bash_path.write_text(bash_script)
    os.chmod(bash_path, 0o755)


def create_zip_archive():
    """Crée une archive ZIP du package."""

    zip_path = OUTPUT_DIR / f"skills_system_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(VAULT_SYNC_DIR):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(VAULT_SYNC_DIR.parent)
                zipf.write(file_path, arcname)

    return zip_path


def create_sync_guide():
    """Crée un guide de synchronisation."""

    guide = f'''# Skills System Sync Guide

## 📋 Contents

This package contains the complete Tree of Thoughts Skills Management System:

### Core Files
- `tree_of_thoughts/vault/skills/skills_manager.py` - Central management system
- `tree_of_thoughts/vault/skills/skill_wrapper.py` - Execution wrapper
- `tree_of_thoughts/vault/skills/cli_handlers.py` - CLI handlers for each skill
- `tree_of_thoughts/vault/skills/__init__.py` - Module exports (UPDATED)

### Documentation
- `SKILLS_SYSTEM.md` - Complete architecture & usage guide (500+ lines)
- `CLAUDE_CODE_SKILLS_INTEGRATION.md` - Claude Code integration (700+ lines)
- `SKILLS_SYSTEM_SUMMARY.md` - Quick reference

### Examples
- `examples/skills_system_demo.py` - 8 complete demos

## 🚀 Installation

### Windows (PowerShell)
```powershell
cd /path/to/your/project
.\\install_skills.ps1
```

### Linux/Mac (Bash)
```bash
cd /path/to/your/project
bash install_skills.sh
```

### Manual Installation
1. Copy the folder structure from `vault_sync/` to your project root
2. Ensure the relative paths are preserved:
   - `tree_of_thoughts/vault/skills/` files
   - `examples/` files
   - Documentation files in root

## ✅ Verify Installation

```python
from tree_of_thoughts.vault.skills import SkillWrapper, SkillType

wrapper = SkillWrapper(user_id="test")
result = wrapper.execute_skill(SkillType.CODE_REVIEW, "Test prompt")
print(f"✓ Installation successful: {{result['success']}}")
```

## 📚 Next Steps

1. **Read the documentation:**
   ```bash
   cat SKILLS_SYSTEM.md
   cat CLAUDE_CODE_SKILLS_INTEGRATION.md
   ```

2. **Run the demo:**
   ```bash
   python examples/skills_system_demo.py
   ```

3. **Start using:**
   ```python
   from tree_of_thoughts.vault.skills import SkillWrapper, SkillType

   wrapper = SkillWrapper(user_id="your_id")
   result = wrapper.execute_skill(SkillType.CODE_REVIEW, "Your prompt")
   ```

## 🔄 Keep in Sync

To stay updated with improvements:

1. Check the Git branch: `claude/vault-sync-openrouter-test-JQ8N9`
2. Compare file versions with your local copies
3. Merge any updates from the Git repository

## 📞 Support

- Check `SKILLS_SYSTEM.md` for architecture questions
- Check `CLAUDE_CODE_SKILLS_INTEGRATION.md` for integration questions
- Run `examples/skills_system_demo.py` to see working examples

---

**Version:** 1.1.0
**Created:** {datetime.now().isoformat()}
**Status:** Production Ready
'''

    guide_path = VAULT_SYNC_DIR / "SYNC_GUIDE.md"
    guide_path.write_text(guide)


def print_summary():
    """Affiche un résumé du package créé."""

    print("📦 PACKAGE SUMMARY")
    print("=" * 70)

    # Compter les fichiers
    total_files = sum(1 for _ in VAULT_SYNC_DIR.rglob("*") if _.is_file())

    print(f"\n✓ Location: {OUTPUT_DIR}")
    print(f"✓ Sync Directory: {VAULT_SYNC_DIR}")
    print(f"✓ Total files: {total_files}")

    # Afficher la structure
    print("\n📂 Directory Structure:")
    for root, dirs, files in os.walk(VAULT_SYNC_DIR):
        level = root.replace(str(VAULT_SYNC_DIR), "").count(os.sep)
        indent = " " * 2 * level
        print(f"{indent}├── {os.path.basename(root)}/")
        subindent = " " * 2 * (level + 1)
        for file in files:
            print(f"{subindent}├── {file}")

    print("\n📥 Installation Options:")
    print("   1. Windows: Run install_skills.ps1")
    print("   2. Linux/Mac: Run install_skills.sh")
    print("   3. Manual: Copy files respecting folder structure")

    print("\n🔗 Files for Synchronization:")
    for category, files in FILES_TO_SYNC.items():
        print(f"\n   {category}:")
        for file in files:
            size = (VAULT_SYNC_DIR / file).stat().st_size if (VAULT_SYNC_DIR / file).exists() else 0
            print(f"      • {file} ({size:,} bytes)")

    # Afficher les fichiers ZIP créés
    zip_files = list(OUTPUT_DIR.glob("*.zip"))
    if zip_files:
        print("\n📦 Archives créées:")
        for zip_file in sorted(zip_files):
            size_mb = zip_file.stat().st_size / (1024 * 1024)
            print(f"      • {zip_file.name} ({size_mb:.2f} MB)")

    print("\n" + "=" * 70)
    print("✅ Ready to sync with external vaults!")
    print("\nYou can now:")
    print("  1. Download the dist/ folder")
    print("  2. Share dist/vault_sync with team members")
    print("  3. Use the installation scripts on target machines")


if __name__ == "__main__":
    create_sync_package()
