"""Local JSON-file store — HACKATHON DEMO ONLY.

One JSON file per collection under the data directory. Writes are atomic
(temp file + os.replace). A missing file is an empty collection. A corrupt
file is moved aside to `<name>.corrupt-<timestamp>.json` and treated as empty,
so the app keeps running; run `scripts/reset_demo_data` to restore seed data.

Not suitable for real patient data: no encryption at rest, no concurrency
control across processes, no backups, and cloud container disks are often
ephemeral.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger("mykshema.storage")


class JsonFileStore:
    label = "local-json"

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _file(self, collection: str) -> Path:
        if not collection.replace("_", "").isalnum():
            raise ValueError(f"invalid collection name: {collection!r}")
        return self.data_dir / f"{collection}.json"

    def load(self, collection: str) -> list[dict[str, Any]]:
        path = self._file(collection)
        with self._lock:
            if not path.exists():
                return []
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    raise ValueError("collection file must contain a JSON list")
                return [row for row in data if isinstance(row, dict)]
            except (ValueError, OSError) as exc:
                stamp = datetime.now().strftime("%Y%m%d%H%M%S")
                backup = path.with_name(f"{collection}.corrupt-{stamp}.json")
                try:
                    os.replace(path, backup)
                except OSError:
                    pass
                log.error("Corrupt data file %s (%s); moved to %s and continuing empty", path, exc, backup.name)
                return []

    def save(self, collection: str, rows: list[dict[str, Any]]) -> None:
        path = self._file(collection)
        with self._lock:
            fd, tmp = tempfile.mkstemp(prefix=f".{collection}.", suffix=".tmp", dir=self.data_dir)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(rows, fh, ensure_ascii=False, indent=1, default=str)
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(tmp, path)
            except BaseException:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise

    def collections(self) -> list[str]:
        return sorted(p.stem for p in self.data_dir.glob("*.json") if ".corrupt-" not in p.name)

    def clear(self) -> None:
        with self._lock:
            for p in self.data_dir.glob("*.json"):
                p.unlink(missing_ok=True)
