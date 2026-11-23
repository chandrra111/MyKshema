"""Storage boundary.

The UI, API routes and business logic talk only to `Repository` objects.
Today these are backed by `JsonFileStore` (or `MemoryStore`). A future
PostgreSQL adapter implements the same `DocumentStore` protocol (or replaces
`Repository` with SQL-backed classes exposing the same methods) without any
change above this layer. See docs/POSTGRES_MIGRATION.md.
"""
from __future__ import annotations

from typing import Any, Callable, Generic, Iterable, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class DocumentStore(Protocol):
    """A minimal collection-of-records store."""

    label: str

    def load(self, collection: str) -> list[dict[str, Any]]: ...

    def save(self, collection: str, rows: list[dict[str, Any]]) -> None: ...

    def collections(self) -> list[str]: ...

    def clear(self) -> None: ...


class NotFoundError(KeyError):
    pass


class Repository(Generic[T]):
    """Typed CRUD over one collection."""

    def __init__(self, store: DocumentStore, collection: str, model: type[T]):
        self.store = store
        self.collection = collection
        self.model = model

    # -- reads
    def all(self) -> list[T]:
        out: list[T] = []
        for row in self.store.load(self.collection):
            try:
                out.append(self.model.model_validate(row))
            except Exception:  # skip a corrupt row rather than failing the request
                continue
        return out

    def find(self, predicate: Callable[[T], bool] | None = None, **equals: Any) -> list[T]:
        rows = self.all()
        if equals:
            rows = [r for r in rows if all(getattr(r, k, None) == v for k, v in equals.items())]
        if predicate:
            rows = [r for r in rows if predicate(r)]
        return rows

    def first(self, **equals: Any) -> T | None:
        found = self.find(**equals)
        return found[0] if found else None

    def get(self, record_id: str) -> T | None:
        return self.first(id=record_id)

    def require(self, record_id: str) -> T:
        rec = self.get(record_id)
        if rec is None:
            raise NotFoundError(f"{self.collection}/{record_id}")
        return rec

    # -- writes
    def _dump(self, rec: T) -> dict[str, Any]:
        return rec.model_dump(mode="json")

    def add(self, rec: T) -> T:
        rows = self.store.load(self.collection)
        rows.append(self._dump(rec))
        self.store.save(self.collection, rows)
        return rec

    def add_many(self, recs: Iterable[T]) -> None:
        rows = self.store.load(self.collection)
        rows.extend(self._dump(r) for r in recs)
        self.store.save(self.collection, rows)

    def update(self, rec: T) -> T:
        rows = self.store.load(self.collection)
        rec_id = getattr(rec, "id")
        for i, row in enumerate(rows):
            if row.get("id") == rec_id:
                rows[i] = self._dump(rec)
                self.store.save(self.collection, rows)
                return rec
        raise NotFoundError(f"{self.collection}/{rec_id}")

    def delete(self, record_id: str) -> bool:
        rows = self.store.load(self.collection)
        kept = [r for r in rows if r.get("id") != record_id]
        if len(kept) == len(rows):
            return False
        self.store.save(self.collection, kept)
        return True

    def replace_all(self, recs: Iterable[T]) -> None:
        self.store.save(self.collection, [self._dump(r) for r in recs])
