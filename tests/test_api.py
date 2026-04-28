"""
Tests for the Text-to-Video Studio API.
Uses httpx + pytest-asyncio to test FastAPI endpoints.
"""

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Force CPU mode and test secret for CI
os.environ["DEVICE"] = "cpu"
os.environ["SECRET_KEY"] = "test-secret-key-for-ci"

from backend.main import app
from backend.database import init_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db(tmp_path):
    """Initialize a fresh database for each test."""
    os.environ["DATA_DIR"] = str(tmp_path)
    # Re-import config to pick up new DATA_DIR would be complex,
    # so we just init the DB at the default location
    await init_db()
    yield


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_client(client):
    """Authenticated client -- registers a unique user and returns (client, token, user)."""
    import uuid
    uid = uuid.uuid4().hex[:8]
    res = await client.post("/api/auth/register", json={
        "username": f"user_{uid}",
        "email": f"{uid}@example.com",
        "password": "testpass123",
    })
    assert res.status_code == 200, f"Register failed: {res.text}"
    data = res.json()
    token = data["access_token"]
    user = data["user"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client, token, user


# ═══════════════════════════════════════
# Health
# ═══════════════════════════════════════

@pytest.mark.asyncio
async def test_health(client):
    res = await client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "gpu_available" in data
    assert "model_id" in data


# ═══════════════════════════════════════
# Auth
# ═══════════════════════════════════════

@pytest.mark.asyncio
async def test_register(client):
    import uuid
    uid = uuid.uuid4().hex[:8]
    res = await client.post("/api/auth/register", json={
        "username": f"reg_{uid}",
        "email": f"reg_{uid}@example.com",
        "password": "secure123",
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["username"] == f"reg_{uid}"
    assert data["user"]["email"] == f"reg_{uid}@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_username(client):
    await client.post("/api/auth/register", json={
        "username": "dupuser",
        "email": "dup1@example.com",
        "password": "pass123456",
    })
    res = await client.post("/api/auth/register", json={
        "username": "dupuser",
        "email": "dup2@example.com",
        "password": "pass123456",
    })
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_login(client):
    # Register first
    await client.post("/api/auth/register", json={
        "username": "loginuser",
        "email": "login@example.com",
        "password": "mypassword",
    })
    # Login
    res = await client.post("/api/auth/login", json={
        "username": "loginuser",
        "password": "mypassword",
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/auth/register", json={
        "username": "wrongpw",
        "email": "wrong@example.com",
        "password": "correct",
    })
    res = await client.post("/api/auth/login", json={
        "username": "wrongpw",
        "password": "incorrect",
    })
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_me(auth_client):
    client, token, user = auth_client
    res = await client.get("/api/auth/me")
    assert res.status_code == 200
    assert res.json()["username"] == user["username"]


@pytest.mark.asyncio
async def test_unauthorized_access(client):
    res = await client.get("/api/tasks")
    assert res.status_code in [401, 403]


# ═══════════════════════════════════════
# Tasks (without actual generation)
# ═══════════════════════════════════════

@pytest.mark.asyncio
async def test_list_tasks_empty(auth_client):
    client, token, user = auth_client
    res = await client.get("/api/tasks")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_generate_validation(auth_client):
    client, token, user = auth_client
    # Too short prompt
    res = await client.post("/api/generate", json={
        "prompt": "Hi",
        "resolution": 512,
    })
    assert res.status_code == 422  # Validation error

    # Invalid resolution
    res = await client.post("/api/generate", json={
        "prompt": "A beautiful sunset over the ocean",
        "resolution": 999,
    })
    assert res.status_code == 400


# ═══════════════════════════════════════
# Pipeline utilities
# ═══════════════════════════════════════

def test_split_text_to_sentences():
    from backend.pipeline import split_text_to_sentences

    # Basic split
    result = split_text_to_sentences("Hello world. This is a test. Third sentence.")
    assert len(result) == 3
    assert result[0] == "Hello world."

    # Single sentence
    result = split_text_to_sentences("Just one sentence here")
    assert len(result) == 1

    # Empty-ish input
    result = split_text_to_sentences("   ")
    assert len(result) == 1

    # Question marks and exclamation
    result = split_text_to_sentences("Is this working? Yes it is! Great.")
    assert len(result) == 3
