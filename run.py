"""Run from a source checkout using a Python environment with dependencies installed."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from fusion_native_mcp.server import main

if __name__ == "__main__":
    main()
