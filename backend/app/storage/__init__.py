"""Repository container. Swap the store here to change persistence."""
from __future__ import annotations

from functools import cached_property

from .. import models as m
from ..config import Settings, get_settings
from .base import DocumentStore, NotFoundError, Repository
from .json_store import JsonFileStore
from .memory_store import MemoryStore

__all__ = ["Repos", "get_repos", "reset_repos", "NotFoundError", "Repository"]


def build_store(settings: Settings) -> DocumentStore:
    if settings.storage_backend == "memory":
        return MemoryStore()
    return JsonFileStore(settings.data_dir)


class Repos:
    def __init__(self, store: DocumentStore):
        self.store = store

    def _r(self, name: str, model):  # noqa: ANN001
        return Repository(self.store, name, model)

    @cached_property
    def users(self) -> Repository[m.User]: return self._r("users", m.User)
    @cached_property
    def patients(self) -> Repository[m.PatientProfile]: return self._r("patients", m.PatientProfile)
    @cached_property
    def doctors(self) -> Repository[m.DoctorProfile]: return self._r("doctors", m.DoctorProfile)
    @cached_property
    def access_requests(self) -> Repository[m.AccessRequest]: return self._r("access_requests", m.AccessRequest)
    @cached_property
    def access_grants(self) -> Repository[m.AccessGrant]: return self._r("access_grants", m.AccessGrant)
    @cached_property
    def documents(self) -> Repository[m.Document]: return self._r("documents", m.Document)
    @cached_property
    def extractions(self) -> Repository[m.Extraction]: return self._r("extractions", m.Extraction)
    @cached_property
    def conditions(self) -> Repository[m.Condition]: return self._r("conditions", m.Condition)
    @cached_property
    def allergies(self) -> Repository[m.Allergy]: return self._r("allergies", m.Allergy)
    @cached_property
    def medications(self) -> Repository[m.Medication]: return self._r("medications", m.Medication)
    @cached_property
    def medication_events(self) -> Repository[m.MedicationEvent]: return self._r("medication_events", m.MedicationEvent)
    @cached_property
    def observations(self) -> Repository[m.Observation]: return self._r("observations", m.Observation)
    @cached_property
    def consultations(self) -> Repository[m.Consultation]: return self._r("consultations", m.Consultation)
    @cached_property
    def prescriptions(self) -> Repository[m.Prescription]: return self._r("prescriptions", m.Prescription)
    @cached_property
    def ai_summaries(self) -> Repository[m.AISummary]: return self._r("ai_summaries", m.AISummary)
    @cached_property
    def audit_logs(self) -> Repository[m.AuditLog]: return self._r("audit_logs", m.AuditLog)


_repos: Repos | None = None


def get_repos() -> Repos:
    global _repos
    if _repos is None:
        _repos = Repos(build_store(get_settings()))
    return _repos


def reset_repos() -> None:
    global _repos
    _repos = None
