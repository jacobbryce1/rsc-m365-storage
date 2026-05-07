#!/bin/bash
#
# RSC M365 Storage Report - Deployment Script (Linux)
# ====================================================
# Distro-aware: installs python3-venv / python3-pip via apt or dnf/yum
# if not already present, then sets up the virtual environment.
#
# Supported distros: Ubuntu, Debian, RHEL, Rocky, Alma, Fedora, CentOS Stream
#
# Usage:
#   chmod +x deploy_linux.sh
#   ./deploy_linux.sh
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  RSC M365 Storage Report - Linux Deployment"
echo "============================================================"
echo ""

# ── Detect distro ────────────────────────────────────────────────
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
    echo "  Detected: ${PRETTY_NAME:-$ID}"
else
    DISTRO="unknown"
    echo "  Distro: unknown — skipping package manager check"
fi

# ── Install prerequisites if needed ──────────────────────────────
echo ""
echo "Checking prerequisites..."

install_prereqs() {
    case $DISTRO in
        ubuntu|debian)
            echo "  Installing python3, python3-venv, python3-pip..."
            sudo apt-get update -qq
            sudo apt-get install -y -qq python3 python3-venv python3-pip
            ;;
        centos|rhel|rocky|alma|fedora)
            echo "  Installing python3, python3-pip..."
            sudo dnf install -y python3 python3-pip 2>/dev/null || \
            sudo yum install -y python3 python3-pip
            ;;
        *)
            echo "  Unknown distro. Ensure python3, python3-venv, and python3-pip are installed."
            ;;
    esac
}

if ! command -v python3 &> /dev/null; then
    echo "  python3 not found — attempting to install..."
    install_prereqs
fi

if ! python3 -m venv --help &> /dev/null 2>&1; then
    echo "  python3-venv not available — attempting to install..."
    install_prereqs
fi

PYTHON=python3
PY_VERSION=$($PYTHON --version 2>&1)
echo "  ✓ $PY_VERSION"

# ── Virtual environment ──────────────────────────────────────────
echo ""
echo "Creating virtual environment..."
if [ -d "venv" ]; then
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
    cp .env.example .env
    chmod 600 .env
    echo "  ✓ .env created (permissions set to 600 — owner only)"
    echo ""
    echo "  ┌──────────────────────────────────────────────────────┐"
    echo "  │  ACTION REQUIRED: Edit .env with your credentials   │"
    echo "  │                                                      │"
    echo "  │    nano .env                                         │"
    echo "  └──────────────────────────────────────────────────────┘"
else
    chmod 600 .env
    echo "  .env already exists (not overwritten)"
    echo "  ✓ .env permissions confirmed (600)"
fi

# ── Optional: monthly cron job ───────────────────────────────────
echo ""
read -p "  Set up monthly cron job? (y/N): " setup_cron
if [[ "$setup_cron" =~ ^[Yy]$ ]]; then
    CRON_CMD="0 6 1 * * cd $SCRIPT_DIR && ./venv/bin/python final_m365_report.py >> $SCRIPT_DIR/output/cron.log 2>&1"
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "  ✓ Cron job added (runs 1st of every month at 6:00 AM)"
    echo "    To review or remove: crontab -e"
fi

echo ""
echo "============================================================"
echo "  ✓ Deployment complete!"
echo ""
echo "  To run:"
echo "    python run_report.py"
echo "============================================================"