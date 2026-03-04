#!/usr/bin/env bash
# =============================================================================
# entrypoint.sh — Tree of Thoughts vault container entry point
#
# 1. Validates required environment variables
# 2. Checks vault section mounts
# 3. Delegates to vault_sync.py with all CLI arguments
# =============================================================================
set -euo pipefail

# ── ANSI helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── 1. Validate API key ───────────────────────────────────────────────────────
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    error "ANTHROPIC_API_KEY is not set."
    error "Copy .env.example to .env and add your Anthropic API key."
    exit 1
fi
success "ANTHROPIC_API_KEY is set."

# ── 2. Check vault mounts ─────────────────────────────────────────────────────
VAULT_ROOT="${VAULT_ROOT:-/vault}"
REQUIRED_SECTIONS=(
    "_PSYCHE"
    "_BRAIN"
    "KNOWLEDGE"
    "RAPPORT QUOTIDIEN, HEBDOMADAIRE,MENSUEL & ANNUEL"
)

info "Checking vault mounts under ${VAULT_ROOT}…"
ALL_OK=true

for section in "${REQUIRED_SECTIONS[@]}"; do
    path="${VAULT_ROOT}/${section}"
    if [[ -d "$path" ]]; then
        success "  ✓ ${path}"
    else
        warn "  ✗ ${path} — not mounted or directory missing."
        ALL_OK=false
    fi
done

if [[ "$ALL_OK" != "true" ]]; then
    warn "Some vault sections are not mounted."
    warn "Check your docker-compose.yml volume bindings and .env host paths."
    warn "Continuing — missing sections will be created if writable."
fi

# ── 3. Delegate to vault_sync.py ─────────────────────────────────────────────
info "Launching vault_sync.py…"
echo ""

exec python /app/vault_sync.py "$@"
