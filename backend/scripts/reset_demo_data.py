"""Wipe local JSON data + uploads and restore the synthetic demo dataset.
Usage: python -m scripts.reset_demo_data"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.seed import seed  # noqa: E402

if __name__ == "__main__":
    s = get_settings()
    counts = seed()
    print(f"Demo data reset. Storage: {s.data_dir} | uploads: {s.upload_dir}")
    for k, v in counts.items():
        print(f"  {k:20s} {v}")
