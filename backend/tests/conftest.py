import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MYKSHEMA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("MYKSHEMA_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MYKSHEMA_AI_RATE_LIMIT", "1000")
    from app import config, security, storage
    from app.services import ai

    config.override_settings(config.Settings())
    storage.reset_repos()
    security.reset_secret_cache()
    ai._calls.clear()
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
    storage.reset_repos()
    config._settings = None


def login(client, email):
    r = client.post("/api/auth/demo-login", json={"email": email, "password": "Demo@2036"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def patient(client):
    return login(client, "ananya.rao@demo.mykshema.test")


@pytest.fixture()
def rahul(client):
    return login(client, "rahul.menon@demo.mykshema.test")


@pytest.fixture()
def meera(client):
    return login(client, "meera.iyer@demo.mykshema.test")


@pytest.fixture()
def arjun(client):
    return login(client, "arjun.shah@demo.mykshema.test")


SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample-data"
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
