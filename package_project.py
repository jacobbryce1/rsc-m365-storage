#!/usr/bin/env python3
"""
Package the RSC M365 Storage Report project for distribution.
Creates a clean distributable zip file with only production files.

Changes v2.1:
- SECURITY.md included in package
- requirements.txt updated with urllib3 and certifi entries
- .env.example updated with RSC_CA_BUNDLE optional var
- deploy.sh now sets chmod 600 .env after creation
- deploy_linux.sh now sets chmod 600 .env after creation
"""

import os
import shutil
import zipfile
from datetime import datetime


def package():
    project_name = "rsc-m365-storage-report"
    timestamp = datetime.now().strftime("%Y%m%d")
    zip_name = f"{project_name}-{timestamp}.zip"

    # Files to include directly from the source tree
    include_files = [
        "final_m365_report.py",
        "requirements.txt",
        ".env.example",
        "README.md",
        "SECURITY.md",
        "src/__init__.py",
        "src/auth.py",
        "src/graphql_client.py",
    ]

    # Create a staging directory
    stage_dir = f"dist/{project_name}"
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    os.makedirs(stage_dir, exist_ok=True)
    os.makedirs(f"{stage_dir}/src", exist_ok=True)
    os.makedirs(f"{stage_dir}/output", exist_ok=True)

    # Copy files from source tree
    for f in include_files:
        src = f
        dst = os.path.join(stage_dir, f)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  ✓ {f}")
        else:
            print(f"  ⚠ Missing: {f}")

    # Placeholder so output/ directory exists in the zip
    open(f"{stage_dir}/output/.gitkeep", "w").close()

    # -----------------------------------------------------------------------
    # run_report.py — cross-platform entry-point wrapper
    # -----------------------------------------------------------------------
    with open(f"{stage_dir}/run_report.py", "w") as f:
        f.write('''#!/usr/bin/env python3
"""
RSC M365 Licensing Compliance & Storage Report
Run this script to generate the report.

Usage:
    python run_report.py
"""

import subprocess
import sys
import os


def main():
    # Ensure we\'re in the right directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Check if venv exists
    if not os.path.exists("venv"):
        print("Virtual environment not found. Run the deploy script first.")
        print("  macOS/Linux: ./deploy.sh")
        print("  Windows:     deploy.bat")
        sys.exit(1)

    # Determine python path
    if sys.platform == "win32":
        python = os.path.join("venv", "Scripts", "python.exe")
    else:
        python = os.path.join("venv", "bin", "python")

    if not os.path.exists(python):
        print(f"Python not found at: {python}")
        sys.exit(1)

    result = subprocess.run(
        [python, "final_m365_report.py"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
''')
    print("  ✓ run_report.py (generated)")

    # -----------------------------------------------------------------------
    # deploy.sh — macOS / Linux
    # -----------------------------------------------------------------------
    with open(f"{stage_dir}/deploy.sh", "w") as f:
        f.write(r'''#!/bin/bash
#
# RSC M365 Storage Report - Deployment Script (macOS/Linux)
# =========================================================
# Sets up the Python virtual environment and installs dependencies.
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo " RSC M365 Storage Report - Deployment"
echo "============================================================"
echo ""

# Check Python version
echo "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "ERROR: Python 3 is not installed."
    echo "  macOS: brew install python3"
    echo "  Linux: sudo apt install python3 python3-venv python3-pip"
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

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "  Removing existing venv..."
    rm -rf venv
fi
$PYTHON -m venv venv
echo "  ✓ Virtual environment created"

# Activate and install
echo ""
echo "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
echo "  ✓ Dependencies installed"

# .env setup
echo ""
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    chmod 600 .env
    echo "  ✓ .env created (permissions set to 600)"
    echo ""
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║  ACTION REQUIRED: Edit .env with your credentials   ║"
    echo "  ║                                                      ║"
    echo "  ║  nano .env                                           ║"
    echo "  ╚══════════════════════════════════════════════════════╝"
else
    echo "  .env already exists (not overwritten)"
    chmod 600 .env
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
''')
    os.chmod(f"{stage_dir}/deploy.sh", 0o755)
    print("  ✓ deploy.sh (generated)")

    # -----------------------------------------------------------------------
    # deploy_linux.sh — distro-aware Linux deployment
    # -----------------------------------------------------------------------
    with open(f"{stage_dir}/deploy_linux.sh", "w") as f:
        f.write(r'''#!/bin/bash
#
# RSC M365 Storage Report - Deployment Script (Linux)
# ====================================================
# Handles Linux-specific prerequisites (python3-venv package, etc.)
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo " RSC M365 Storage Report - Linux Deployment"
echo "============================================================"
echo ""

# Detect distro
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
    echo "  Detected: $PRETTY_NAME"
else
    DISTRO="unknown"
fi

# Check/install prerequisites
echo ""
echo "Checking prerequisites..."

install_prereqs() {
    case $DISTRO in
        ubuntu|debian)
            echo "  Installing python3-venv and python3-pip..."
            sudo apt-get update -qq
            sudo apt-get install -y -qq python3 python3-venv python3-pip
            ;;
        centos|rhel|rocky|alma|fedora)
            echo "  Installing python3 and python3-pip..."
            sudo dnf install -y python3 python3-pip 2>/dev/null || \
            sudo yum install -y python3 python3-pip
            ;;
        *)
            echo "  Unknown distro. Please ensure python3, python3-venv, python3-pip are installed."
            ;;
    esac
}

if ! command -v python3 &> /dev/null; then
    echo "  Python3 not found. Attempting to install..."
    install_prereqs
fi

if ! python3 -m venv --help &> /dev/null; then
    echo "  python3-venv not available. Installing..."
    install_prereqs
fi

PYTHON=python3
PY_VERSION=$($PYTHON --version 2>&1)
echo "  ✓ $PY_VERSION"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    rm -rf venv
fi
$PYTHON -m venv venv
echo "  ✓ Virtual environment created"

# Install dependencies
echo ""
echo "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
echo "  ✓ Dependencies installed"

# .env setup
echo ""
if [ ! -f ".env" ]; then
    cp .env.example .env
    chmod 600 .env
    echo "  ✓ .env created (permissions set to 600)"
    echo ""
    echo "  ┌──────────────────────────────────────────────────────┐"
    echo "  │  ACTION REQUIRED: Edit .env with your credentials   │"
    echo "  │                                                      │"
    echo "  │  nano .env                                           │"
    echo "  └──────────────────────────────────────────────────────┘"
else
    chmod 600 .env
    echo "  .env exists — permissions confirmed (600)"
fi

# Optional: set up cron for monthly execution
echo ""
read -p "  Set up monthly cron job? (y/N): " setup_cron
if [[ "$setup_cron" =~ ^[Yy]$ ]]; then
    CRON_CMD="0 6 1 * * cd $SCRIPT_DIR && ./venv/bin/python final_m365_report.py >> $SCRIPT_DIR/output/cron.log 2>&1"
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "  ✓ Cron job added (runs 1st of every month at 6 AM)"
    echo "    To remove: crontab -e"
fi

echo ""
echo "============================================================"
echo "  ✓ Deployment complete!"
echo ""
echo "  To run:"
echo "    python run_report.py"
echo "============================================================"
''')
    os.chmod(f"{stage_dir}/deploy_linux.sh", 0o755)
    print("  ✓ deploy_linux.sh (generated)")

    # -----------------------------------------------------------------------
    # deploy.bat — Windows
    # -----------------------------------------------------------------------
    with open(f"{stage_dir}/deploy.bat", "w") as f:
        f.write('''@echo off
REM RSC M365 Storage Report - Deployment Script (Windows)
REM =====================================================

echo ============================================================
echo RSC M365 Storage Report - Deployment
echo ============================================================
echo.

REM Check Python
echo Checking Python...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Download from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VERSION=%%i
echo Found: %PY_VERSION%

REM Create virtual environment
echo.
echo Creating virtual environment...
if exist venv (
    echo Removing existing venv...
    rmdir /s /q venv
)
python -m venv venv
echo Virtual environment created

REM Activate and install
echo.
echo Installing dependencies...
call venv\\Scripts\\activate.bat
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
echo Dependencies installed

REM .env setup
echo.
if not exist .env (
    echo Creating .env from template...
    copy .env.example .env >nul
    echo .env created
    echo.
    echo ======================================================
    echo ACTION REQUIRED: Edit .env with your credentials
    echo.
    echo notepad .env
    echo ======================================================
) else (
    echo .env already exists (not overwritten)
)

echo.
echo ============================================================
echo Deployment complete!
echo.
echo To run the report:
echo python run_report.py
echo ============================================================
echo.
pause
''')
    print("  ✓ deploy.bat (generated)")

    # -----------------------------------------------------------------------
    # requirements.txt — written into zip (v2.1: adds urllib3 + certifi)
    # -----------------------------------------------------------------------
    with open(f"{stage_dir}/requirements.txt", "w") as f:
        f.write("""# RSC M365 Storage Report — Python dependencies
# ================================================
# All minimum versions set to latest stable as of 2026-05.
# Run: pip install --upgrade -r requirements.txt  to pull CVE patches.

requests>=2.32.0          # HTTP client
urllib3>=2.2.0            # TLS backend used by requests
certifi>=2024.2.2         # CA bundle — update regularly
pandas>=2.2.0             # DataFrame / Excel output
python-dotenv>=1.0.1      # .env file loading
python-dateutil>=2.9.0    # Date parsing utilities
tabulate>=0.9.0           # Console table formatting
openpyxl>=3.1.2           # Excel (.xlsx) writer engine
""")
    print("  ✓ requirements.txt (v2.1 — urllib3 + certifi added)")

    # -----------------------------------------------------------------------
    # .env.example — written into zip (v2.1: adds RSC_CA_BUNDLE)
    # -----------------------------------------------------------------------
    with open(f"{stage_dir}/.env.example", "w") as f:
        f.write("""# =============================================================
# RSC M365 Storage Report — Configuration Template
# =============================================================
# Copy this file to .env and fill in your values.
#
#   cp .env.example .env
#   chmod 600 .env      # macOS/Linux: restrict to your user only
#
# NEVER commit .env to source control.
# .env is listed in .gitignore — keep it that way.
# =============================================================


# -------------------------------------------------------------
# REQUIRED: Rubrik Security Cloud (RSC) connection
# -------------------------------------------------------------

# Your RSC instance URL — no trailing slash
# Format: https://<your-org>.my.rubrik.com
RSC_URL=https://YOUR_ORG.my.rubrik.com

# Service account credentials
# Create in RSC: Settings → Service Accounts → Create Service Account
# Assign read-only access to M365 objects and Reports
# Copy the Client ID and Secret immediately — the secret is shown only once
RSC_CLIENT_ID=your-client-id-here
RSC_CLIENT_SECRET=your-client-secret-here


# -------------------------------------------------------------
# OPTIONAL: TLS / network settings
# -------------------------------------------------------------

# Path to a custom CA bundle file (PEM format)
# Required only if you're behind a corporate proxy or use private PKI
# Leave commented out to use the system default CA store
# RSC_CA_BUNDLE=/path/to/your/ca-bundle.crt
""")
    print("  ✓ .env.example (v2.1 — RSC_CA_BUNDLE added)")

    # -----------------------------------------------------------------------
    # Build the zip
    # -----------------------------------------------------------------------
    zip_path = os.path.join("dist", zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(stage_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, "dist")
                zf.write(file_path, arcname)

    print(f"\n{'='*60}")
    print(f"  ✓ Package created: {zip_path}")
    print(f"  Size: {os.path.getsize(zip_path) / 1024:.1f} KB")
    print(f"{'='*60}")

    print(f"\n  Contents of {zip_name}:")
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in sorted(zf.namelist()):
            print(f"    {info}")


if __name__ == "__main__":
    print("=" * 60)
    print("  Packaging RSC M365 Storage Report")
    print("=" * 60 + "\n")
    package()