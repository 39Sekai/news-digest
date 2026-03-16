#!/usr/bin/env python3
"""
Setup script for Daily News Digest v2
Run once to initialize environment
"""

import os
import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
LOG_DIR = DATA_DIR / "logs"
CONFIG_DIR = REPO_ROOT / "config"

REQUIRED_DIRS = [DATA_DIR, LOG_DIR, CONFIG_DIR]


def check_python_version():
    """Verify Python 3.11+ is installed."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print(f"❌ Python 3.11+ required, found {version.major}.{version.minor}")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True


def install_dependencies():
    """Install Python packages from requirements.txt using uv."""
    req_file = REPO_ROOT / "requirements.txt"
    if not req_file.exists():
        print("❌ requirements.txt not found")
        return False
    
    print("Installing dependencies with uv...")
    result = subprocess.run(
        ["uv", "pip", "install", "-r", str(req_file)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ uv pip install failed:\n{result.stderr}")
        return False
    
    print("✓ Dependencies installed")
    return True


def create_directories():
    """Create required data directories."""
    for directory in REQUIRED_DIRS:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ {directory}")
    return True


def setup_cron_digest():
    """Make cron-digest.py executable."""
    cron_script = REPO_ROOT / "scripts" / "cron-digest.py"
    if cron_script.exists():
        os.chmod(cron_script, 0o755)
        print(f"✓ Made {cron_script.name} executable")
        return True
    print(f"⚠ {cron_script.name} not found (will be created)")
    return True  # Not fatal - might not be committed yet


def main():
    print("=" * 50)
    print("Daily News Digest v2 - Setup")
    print("=" * 50)
    
    all_ok = True
    
    print("\n1. Checking Python version...")
    all_ok &= check_python_version()
    
    print("\n2. Creating directories...")
    all_ok &= create_directories()
    
    print("\n3. Installing dependencies...")
    all_ok &= install_dependencies()
    
    print("\n4. Setting up scripts...")
    all_ok &= setup_cron_digest()
    
    print("\n" + "=" * 50)
    if all_ok:
        print("✅ Setup complete!")
        print(f"\nNext steps:")
        print(f"  1. Review config in: {CONFIG_DIR}")
        print(f"  2. Test pipeline: uv run python scripts/cron-digest.py --test")
        print(f"  3. Dry run: uv run python scripts/cron-digest.py --dry-run")
        print(f"\nData will be stored in: {DATA_DIR}")
        print(f"Logs will be written to: {LOG_DIR}")
    else:
        print("❌ Setup failed - see errors above")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
