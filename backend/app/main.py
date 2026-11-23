"""MyKshema API — hackathon prototype (BUILD 2036).

Runs with no database (local JSON files) and no OpenAI key (deterministic,
clearly labelled demo mode). Synthetic data only.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .routers import access, ai, analytics, auth, consultations, documents, medications, patients
from .security import CurrentUser, get_current_user
from .seed import ensure_seeded, seed
from .services.audit import audit
from .storage import get_repos

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()
    s.upload_dir.mkdir(parents=True, exist_ok=True)
    if s.auto_seed and ensure_seeded():
        logging.getLogger("mykshema").info("Seeded synthetic demo data into %s", get_repos().store.label)
    yield


app = FastAPI(
    title="MyKshema API",
    version="0.1.0",
    summary="Your Health. Your History. Your Well-being. — AI-powered personal health intelligence (prototype).",
    description="Hackathon prototype with synthetic data only. Not a medical device. Local JSON storage is for "
                "demonstration and is not suitable for real patient data.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_origin_regex=os.getenv("MYKSHEMA_CORS_ORIGIN_REGEX") or None,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse({"error": {"status": exc.status_code, "message": exc.detail}}, status_code=exc.status_code,
                        headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse({"error": {"status": 422, "message": "Validation failed", "details": details}}, status_code=422)


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("mykshema").exception("Unhandled error: %s", exc)
    return JSONResponse({"error": {"status": 500, "message": "Internal server error"}}, status_code=500)


for r in (auth, patients, documents, medications, analytics, ai, access, consultations):
    app.include_router(r.router)


@app.get("/health", tags=["system"])
def health() -> dict:
    s = get_settings()
    repos = get_repos()
    return {
        "status": "ok",
        "app": "MyKshema",
        "storage": repos.store.label,
        "database": "none (hackathon demo)",
        "live_ai": s.live_ai_enabled,
        "ai_mode": "live" if s.live_ai_enabled else "DEMO MODE - NOT LIVE AI",
        "users": len(repos.users.all()),
    }


@app.post("/api/demo/reset", tags=["system"], summary="Restore the synthetic demo data (demo only)")
def demo_reset(cu: CurrentUser = Depends(get_current_user)) -> dict:
    if os.getenv("MYKSHEMA_ALLOW_DEMO_RESET", "true").lower() == "false":
        raise HTTPException(403, "Demo reset disabled")
    counts = seed()
    audit(None, "demo.reset", detail=f"reset by {cu.user.email}")
    return {"reset": True, "counts": counts}
