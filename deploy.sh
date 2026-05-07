#!/bin/bash
#
# RSC M365 Storage Report - Deployment Script (macOS / Linux)
# ============================================================
# Sets up the Python virtual environment and installs dependencies.
# Run once after cloning or extracting the project.
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  RSC M365 Storage Report - Deployment"
echo "============================================================"
echo ""

# ── Python check ────────────────────────────────────────────────
echo "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "ERROR: Python 3 is not installed."
    echo "  macOS : brew install python3"
    echo "  Linux : sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

PY_VERSION=$($PYTHON --version 2>&1)
echo "  Found: $PY_VERSION"

PY_MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")
if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]); then
    echo "ERROR: Python 3.9+ is required. Found: $PY_VERSION"
    exit 1
fi

# ── Virtual environment ──────────────────────────────────────────
echo ""
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "  Removing existing venv..."
    rm -rf venv
fi
$PYTHON -m venv venv
echo "  ✓ Virtual environment created"

# ── Dependencies ─────────────────────────────────────────────────
echo ""
echo "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
echo "  ✓ Dependencies installed"

# ── .env setup ───────────────────────────────────────────────────
echo ""
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    chmod 600 .env
    echo "  ✓ .env created (permissions set to 600 — owner only)"
    echo ""
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║  ACTION REQUIRED: Edit .env with your credentials   ║"
    echo "  ║                                                      ║"
    echo "  ║    nano .env                                         ║"
    echo "  ╚══════════════════════════════════════════════════════╝"
else
    chmod 600 .env
    echo "  .env already exists (not overwritten)"
    echo "  ✓ .env permissions confirmed (600)"
fi

echo ""
echo "============================================================"
echo "  ✓ Deployment complete!"
echo ""
echo "  Next steps:"
echo "    1. Edit .env with your RSC credentials"
echo "    2. python run_report.py"
echo "============================================================"