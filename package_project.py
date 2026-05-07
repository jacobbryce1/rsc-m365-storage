#!/usr/bin/env python3
"""
Package the RSC M365 Storage Report project for distribution.
Creates a clean distributable zip file with only production files.
"""

import os
import shutil
import zipfile
from datetime import datetime


def package():
    project_name = "rsc-m365-storage-report"
    timestamp = datetime.now().strftime("%Y%m%d")
    zip_name = f"{project_name}-{timestamp}.zip"
    
    # Files to include in the package
    include_files = [
        "final_m365_report.py",
        "requirements.txt",
        ".env.example",
        "README.md",
        "src/__init__.py",
        "src/auth.py",
        "src/graphql_client.py",
    ]
    
    include_dirs = [
        "output",
    ]
    
    # Create a staging directory
    stage_dir = f"dist/{project_name}"
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    os.makedirs(stage_dir, exist_ok=True)
    os.makedirs(f"{stage_dir}/src", exist_ok=True)
    os.makedirs(f"{stage_dir}/output", exist_ok=True)
    
    # Copy files
    for f in include_files:
        src = f
        dst = os.path.join(stage_dir, f)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  ✓ {f}")
        else:
            print(f"  ⚠ Missing: {f}")
    
    # Create .gitkeep in output
    open(f"{stage_dir}/output/.gitkeep", "w").close()
    
    # Create the main entry point wrapper
    with open(f"{stage_dir}/run_report.py", "w") as f:
        f.write('''#!/usr/bin/env python3
"""
RSC M365 Storage & FETB Consumption Report
Run this script to generate the report.

Usage:
    python run_report.py
"""
import subprocess
import sys
import os

def main():
    # Ensure we're in the right directory
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
    
    # Run the report
    result = subprocess.run([python, "final_m365_report.py"], cwd=os.path.dirname(os.path.abspath(__file__)))
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
''')
    print(f"  ✓ run_report.py (wrapper)")
    
    # Create deploy.sh (macOS/Linux)
    with open(f"{stage_dir}/deploy.sh", "w") as f:
        f.write('''#!/bin/bash
#
# RSC M365 Storage Report - Deployment Script (macOS/Linux)
# =========================================================
# This script sets up the Python environment and installs dependencies.
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  RSC M365 Storage Report - Deployment"
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
    echo "  macOS:  brew install python3"
    echo "  Linux:  sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

PY_VERSION=$($PYTHON --version 2>&1)
echo "  Found: $PY_VERSION"

# Check minimum version
PY_MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]); then
    echo "ERROR: Python 3.8+ is required. Found: $PY_VERSION"
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

# Check for .env
echo ""
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "  ✓ .env created"
    echo ""
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║  ACTION REQUIRED: Edit .env with your credentials   ║"
    echo "  ║                                                      ║"
    echo "  ║  nano .env                                           ║"
    echo "  ║    or                                                ║"
    echo "  ║  open .env                                           ║"
    echo "  ╚══════════════════════════════════════════════════════╝"
else
    echo "  .env already exists (not overwritten)"
fi

echo ""
echo "============================================================"
echo "  ✓ Deployment complete!"
echo ""
echo "  To run the report:"
echo "    source venv/bin/activate"
echo "    python final_m365_report.py"
echo ""
echo "  Or simply:"
echo "    python run_report.py"
echo "============================================================"
''')
    os.chmod(f"{stage_dir}/deploy.sh", 0o755)
    print(f"  ✓ deploy.sh (macOS/Linux)")
    
    # Create deploy.bat (Windows)
    with open(f"{stage_dir}/deploy.bat", "w") as f:
        f.write('''@echo off
REM RSC M365 Storage Report - Deployment Script (Windows)
REM =====================================================
REM This script sets up the Python environment and installs dependencies.
REM

echo ============================================================
echo   RSC M365 Storage Report - Deployment
echo ============================================================
echo.

REM Check Python
echo Checking Python...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo   Download from: https://www.python.org/downloads/
    echo   Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VERSION=%%i
echo   Found: %PY_VERSION%

REM Create virtual environment
echo.
echo Creating virtual environment...
if exist venv (
    echo   Removing existing venv...
    rmdir /s /q venv
)
python -m venv venv
echo   Virtual environment created

REM Activate and install
echo.
echo Installing dependencies...
call venv\\Scripts\\activate.bat
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
echo   Dependencies installed

REM Check for .env
echo.
if not exist .env (
    echo Creating .env from template...
    copy .env.example .env >nul
    echo   .env created
    echo.
    echo   ======================================================
    echo   ACTION REQUIRED: Edit .env with your credentials
    echo.
    echo     notepad .env
    echo   ======================================================
) else (
    echo   .env already exists (not overwritten)
)

echo.
echo ============================================================
echo   Deployment complete!
echo.
echo   To run the report:
echo     venv\\Scripts\\activate.bat
echo     python final_m365_report.py
echo.
echo   Or simply:
echo     python run_report.py
echo ============================================================
echo.
pause
''')
    print(f"  ✓ deploy.bat (Windows)")
    
    # Create deploy_linux.sh (specific Linux considerations)
    with open(f"{stage_dir}/deploy_linux.sh", "w") as f:
        f.write('''#!/bin/bash
#
# RSC M365 Storage Report - Deployment Script (Linux)
# ====================================================
# Handles Linux-specific prerequisites (python3-venv package, etc.)
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  RSC M365 Storage Report - Linux Deployment"
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

# Check if venv module is available
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
    echo "  ✓ .env created from template"
    echo ""
    echo "  ┌──────────────────────────────────────────────────────┐"
    echo "  │  ACTION REQUIRED: Edit .env with your credentials    │"
    echo "  │                                                      │"
    echo "  │  nano .env                                           │"
    echo "  │  vi .env                                             │"
    echo "  └──────────────────────────────────────────────────────┘"
else
    echo "  .env exists (not overwritten)"
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
echo "    source venv/bin/activate"
echo "    python final_m365_report.py"
echo "============================================================"
''')
    os.chmod(f"{stage_dir}/deploy_linux.sh", 0o755)
    print(f"  ✓ deploy_linux.sh")
    
    # Update requirements.txt to be clean
    with open(f"{stage_dir}/requirements.txt", "w") as f:
        f.write("""requests>=2.31.0
pandas>=2.0.0
python-dotenv>=1.0.0
python-dateutil>=2.8.2
tabulate>=0.9.0
openpyxl>=3.1.0
""")
    print(f"  ✓ requirements.txt (clean)")
    
    # Update .env.example
    with open(f"{stage_dir}/.env.example", "w") as f:
        f.write("""# Rubrik Security Cloud Configuration
# =====================================
# Copy this file to .env and fill in your values.
# NEVER commit .env to source control.

# Your RSC instance URL (no trailing slash)
RSC_URL=https://YOUR_ORG.my.rubrik.com

# Service Account credentials
# Created in RSC: Settings > Service Accounts
RSC_CLIENT_ID=your-client-id-here
RSC_CLIENT_SECRET=your-client-secret-here
""")
    print(f"  ✓ .env.example")
    
    # Create the zip
    zip_path = f"dist/{zip_name}"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(stage_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, "dist")
                zf.write(file_path, arcname)
    
    print(f"\n{'='*60}")
    print(f"  ✓ Package created: {zip_path}")
    print(f"    Size: {os.path.getsize(zip_path) / 1024:.1f} KB")
    print(f"{'='*60}")
    
    # List contents
    print(f"\n  Contents of {zip_name}:")
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in sorted(zf.namelist()):
            print(f"    {info}")


if __name__ == "__main__":
    print("="*60)
    print("  Packaging RSC M365 Storage Report")
    print("="*60 + "\n")
    package()
