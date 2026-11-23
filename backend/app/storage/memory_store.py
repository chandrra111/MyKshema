"""In-memory fallback store — DEMO ONLY, all data is lost on restart.

Enable with MYKSHEMA_STORAGE=memory (useful on read-only/ephemeral hosts).
"""
from __future__ import annotations

import copy
import threading
from typing import Any


class MemoryStore:
    label = "in-memory (non-persistent)"

    def __init__(self) -> None:
        self._data: dict[str, list[dict[str, Any]]] = {}
        self._lock = threading.RLock()

    def load(self, collection: str) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._data.get(collection, []))

    def save(self, collection: str, rows: list[dict[str, Any]]) -> None:
        with self._lock:
            self._data[collection] = copy.deepcopy(rows)

    def collections(self) -> list[str]:
        return sorted(self._data)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
