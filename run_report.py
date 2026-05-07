#!/usr/bin/env python3
"""
RSC M365 Licensing Compliance & Storage Report
===============================================
Cross-platform entry-point. Run this script to generate the report.

Usage:
    python run_report.py

This wrapper ensures you are running inside the virtual environment
created by the deploy script. If the venv does not exist, it will
print instructions and exit cleanly.
"""

import os
import subprocess
import sys


def main() -> None:
    # Always run relative to the script's own directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    if not os.path.exists("venv"):
        print("ERROR: Virtual environment not found.")
        print("       Run the deploy script first to set up the environment:")
        print("")
        print("         macOS/Linux : ./deploy.sh  or  ./deploy_linux.sh")
        print("         Windows     : deploy.bat")
        sys.exit(1)

    # Resolve the python executable inside the venv
    if sys.platform == "win32":
        python = os.path.join(script_dir, "venv", "Scripts", "python.exe")
    else:
        python = os.path.join(script_dir, "venv", "bin", "python")

    if not os.path.exists(python):
        print(f"ERROR: Python executable not found at: {python}")
        print("       Try deleting the venv/ directory and re-running the deploy script.")
        sys.exit(1)

    result = subprocess.run([python, "final_m365_report.py"], cwd=script_dir)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()