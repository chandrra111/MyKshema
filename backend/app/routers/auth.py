from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..security import CurrentUser, create_token, get_current_user, verify_password
from ..services.audit import audit
from ..storage import get_repos

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


def user_out(cu_user) -> dict:  # noqa: ANN001
    r = get_repos()
    profile = None
    if cu_user.patient_id:
        p = r.patients.get(cu_user.patient_id)
        profile = p.model_dump(mode="json") if p else None
    elif cu_user.doctor_id:
        d = r.doctors.get(cu_user.doctor_id)
        profile = d.model_dump(mode="json") if d else None
    return {"id": cu_user.id, "email": cu_user.email, "role": cu_user.role, "display_name": cu_user.display_name,
            "patient_id": cu_user.patient_id, "doctor_id": cu_user.doctor_id, "profile": profile, "is_demo": True}


@router.post("/demo-login", summary="Sign in with a demo account (prototype auth, not production identity)")
def demo_login(body: LoginIn) -> dict:
    user = get_repos().users.first(email=body.email.strip().lower())
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid demo email or password")
    audit(CurrentUser(user), "auth.login", patient_id=user.patient_id, detail="demo login")
    return {"access_token": create_token(user), "token_type": "bearer", "user": user_out(user)}


@router.get("/me")
def me(cu: CurrentUser = Depends(get_current_user)) -> dict:
    return user_out(cu.user)


@router.get("/demo-accounts", summary="Public list of fictional demo accounts")
def demo_accounts() -> dict:
    from ..seed import DEMO_PASSWORD

    users = get_repos().users.all()
    return {
        "password": DEMO_PASSWORD,
        "notice": "Fictional demo accounts with synthetic data only.",
        "accounts": [{"email": u.email, "role": u.role, "display_name": u.display_name} for u in users],
    }
