#!/usr/bin/env python3
"""
QuantumQA Test Runner - Simplified Entry Point
This is a convenience wrapper around the unified quantumqa_runner.py
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Forward all arguments to the unified runner."""
    script_path = Path(__file__).parent / "quantumqa_runner.py"
    
    # Forward all command line arguments
    cmd = [sys.executable, str(script_path)] + sys.argv[1:]
    
    # Execute the unified runner
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
