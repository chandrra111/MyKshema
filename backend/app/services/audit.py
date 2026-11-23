from __future__ import annotations

from ..models import AuditLog, new_id
from ..security import CurrentUser
from ..storage import get_repos


def audit(
    actor: CurrentUser | None,
    action: str,
    *,
    patient_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: str | None = None,
    outcome: str = "success",
) -> None:
    get_repos().audit_logs.add(
        AuditLog(
            id=new_id("aud"),
            actor_user_id=actor.id if actor else None,
            actor_role=actor.role if actor else None,
            actor_name=actor.user.display_name if actor else "system",
            action=action,
            patient_id=patient_id,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            outcome=outcome,  # type: ignore[arg-type]
        )
    )
