"""Real, read-only launch inventory and brief selection. No generation actions."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from launchlens.inventory_ui import main

main()
