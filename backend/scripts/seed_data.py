"""Seed synthetic demo data (only if no data exists). Usage: python -m scripts.seed_data [--force]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.seed import ensure_seeded, seed  # noqa: E402

if __name__ == "__main__":
    if "--force" in sys.argv:
        print("Re-seeded:", seed())
    else:
        print("Seeded synthetic demo data." if ensure_seeded() else "Data already present; use --force or reset_demo_data.")
