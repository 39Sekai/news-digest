#!/usr/bin/env python3
"""News Digest CLI Entry Point

Usage:
    ./news-digest.py <command>
    python news-digest.py <command>
    uv run python news-digest.py <command>
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.cli import main

if __name__ == "__main__":
    sys.exit(main())
