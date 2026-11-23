"""Demo authentication: PBKDF2 password hashes + HMAC-signed bearer tokens.

Prototype only — not production identity verification. Production needs a
hardened identity provider, MFA, session revocation and verified doctor
registration.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings
from .models import User
from .storage import get_repos

PBKDF2_ITERATIONS = 120_000


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iters, salt, hexdigest = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters))
        return hmac.compare_digest(digest.hex(), hexdigest)
    except (ValueError, TypeError):
        return False


_secret_cache: bytes | None = None


def _secret() -> bytes:
    """Signing secret: env var, else a random secret persisted in the data dir."""
    global _secret_cache
    if _secret_cache:
        return _secret_cache
    settings = get_settings()
    if settings.token_secret:
        _secret_cache = settings.token_secret.encode()
        return _secret_cache
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    path = settings.data_dir / ".token_secret"
    if not path.exists():
        path.write_text(secrets.token_hex(32), encoding="utf-8")
    _secret_cache = path.read_text(encoding="utf-8").strip().encode()
    return _secret_cache


def reset_secret_cache() -> None:
    global _secret_cache
    _secret_cache = None


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_token(user: User) -> str:
    ttl = get_settings().token_ttl_hours * 3600
    payload = {"sub": user.id, "role": user.role, "exp": int(time.time()) + ttl}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def decode_token(token: str) -> dict | None:
    try:
        body, sig = token.split(".")
        expected = _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_unb64(body))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    user: User

    @property
    def id(self) -> str:
        return self.user.id

    @property
    def role(self) -> str:
        return self.user.role

    @property
    def is_patient(self) -> bool:
        return self.user.role == "patient"

    @property
    def is_doctor(self) -> bool:
        return self.user.role == "doctor"


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> CurrentUser:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session", headers={"WWW-Authenticate": "Bearer"})
    user = get_repos().users.get(payload["sub"])
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return CurrentUser(user)


def require_patient(cu: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not cu.is_patient or not cu.user.patient_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Patient account required")
    return cu


def require_doctor(cu: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not cu.is_doctor or not cu.user.doctor_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Doctor account required")
    return cu
