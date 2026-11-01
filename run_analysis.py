#!/usr/bin/env python3
"""Run from any directory: python run_analysis.py [--output PATH]."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from cold_chain.pipeline import main

if __name__ == "__main__":
    main()
