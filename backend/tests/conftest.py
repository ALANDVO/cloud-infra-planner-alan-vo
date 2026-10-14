# backend/tests/conftest.py
"""Shared test fixtures.

The application uses an async (aiosqlite) engine bound to ``DATABASE_URL``.
To avoid SQLite async-connection/event-loop cross-contamination we:
  * point the async engine at a temp-file SQLite DB (set before import),
  * create schema + seed data with a *separate* synchronous engine that hits
    the same file,
  * exercise the app through a session-scoped ``TestClient`` (single
    thread/event-loop, so the async engine's connections never cross loops).
"""
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

_DB_PATH = Path(__file__).resolve().parent / "test_async.db"
if _DB_PATH.exists():
    _DB_PATH.unlink()

# Configure a deterministic, offline-safe environment BEFORE importing the app
# (settings are populated at first import).
os.environ["ENVIRONMENT"] = "development"
os.environ["DEMO_MODE"] = "true"
os.environ["JWT_SECRET"] = "test-jwt-secret-key-for-testing-only-0001"
os.environ["CSRF_SECRET"] = "test-csrf-secret-key-for-testing-only-0001"
os.environ["LLM_PROVIDER"] = "offline"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_PATH}"
os.environ["KEYCLOAK_URL"] = "http://localhost:8080"

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.main import app  # noqa: E402  (triggers async engine creation)
from app.core.database import Base  # noqa: E402
from app.core.security import hash_password, create_access_token  # noqa: E402
from app.models.user import User, Role  # noqa: E402
from app.models.generation import Generation  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402

_SYNC_URL = f"sqlite:///{_DB_PATH}"
_sync_engine = create_engine(_SYNC_URL)


def setup_schema() -> None:
    Base.metadata.create_all(_sync_engine)


def _wipe() -> None:
    with _sync_engine.begin() as conn:
        for tbl in ("generations", "audit_logs", "users"):
            conn.execute(text(f"DELETE FROM {tbl}"))


# Ensure schema exists before any test runs.
setup_schema()


def _make_user(email: str, role: Role, password: str = "password123") -> User:
    with Session(_sync_engine) as s:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name="Test User",
            role=role,
            is_active=True,
        )
        s.add(user)
        s.commit()
        s.refresh(user)
        return user


def _token(user: User) -> str:
    return create_access_token(subject=str(user.id), roles=[user.role.value])


import pytest  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Single TestClient for the whole session: one thread, one event loop."""
    return TestClient(app)


@pytest.fixture()
def viewer() -> User:
    user = _make_user("viewer@example.com", Role.VIEWER)
    yield user
    _wipe()


@pytest.fixture()
def operator() -> User:
    user = _make_user("operator@example.com", Role.OPERATOR)
    yield user
    _wipe()


@pytest.fixture()
def viewer_token(viewer: User) -> str:
    return _token(viewer)


@pytest.fixture()
def operator_token(operator: User) -> str:
    return _token(operator)


@pytest.fixture()
def auth_operator() -> dict:
    """Return {'user': User, 'token': str} and clean up afterwards."""
    user = _make_user("op@example.com", Role.OPERATOR)
    data = {"user": user, "token": _token(user)}
    yield data
    _wipe()


@pytest.fixture()
def auth_viewer() -> dict:
    user = _make_user("vi@example.com", Role.VIEWER)
    data = {"user": user, "token": _token(user)}
    yield data
    _wipe()


@pytest.fixture(autouse=True)
def _isolate_each_test():
    """Ensure a clean DB row state for every test."""
    _wipe()
    yield
    _wipe()