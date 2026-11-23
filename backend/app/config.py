"""Application settings, read from environment variables.

Every setting is optional. MyKshema runs with no database and no OpenAI key.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    """Minimal .env loader (no extra dependency). Existing env vars win."""
    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def _path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    return Path(value).resolve() if value else default


@dataclass(frozen=True)
class Settings:
    app_name: str = "MyKshema API"
    data_dir: Path = field(default_factory=lambda: _path("MYKSHEMA_DATA_DIR", BACKEND_DIR / "data"))
    upload_dir: Path = field(default_factory=lambda: _path("MYKSHEMA_UPLOAD_DIR", BACKEND_DIR / "uploads"))
    # "json" (default, persisted to local files) or "memory" (clearly labelled, lost on restart)
    storage_backend: str = field(default_factory=lambda: os.getenv("MYKSHEMA_STORAGE", "json").lower())
    max_upload_mb: int = field(default_factory=lambda: int(os.getenv("MYKSHEMA_MAX_UPLOAD_MB", "10")))
    token_ttl_hours: int = field(default_factory=lambda: int(os.getenv("MYKSHEMA_TOKEN_TTL_HOURS", "12")))
    token_secret: str | None = field(default_factory=lambda: os.getenv("MYKSHEMA_TOKEN_SECRET") or None)
    cors_origins: list[str] = field(
        default_factory=lambda: [
            o.strip()
            for o in os.getenv("MYKSHEMA_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
            if o.strip()
        ]
    )
    openai_api_key: str | None = field(default_factory=lambda: os.getenv("OPENAI_API_KEY") or None)
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    openai_base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    ai_rate_limit_per_minute: int = field(default_factory=lambda: int(os.getenv("MYKSHEMA_AI_RATE_LIMIT", "20")))
    auto_seed: bool = field(default_factory=lambda: os.getenv("MYKSHEMA_AUTO_SEED", "true").lower() != "false")

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def live_ai_enabled(self) -> bool:
        return bool(self.openai_api_key)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def override_settings(settings: Settings) -> None:
    """Used by tests to point storage at a temporary directory."""
    global _settings
    _settings = settings
