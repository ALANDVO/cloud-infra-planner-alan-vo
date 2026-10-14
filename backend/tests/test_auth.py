# backend/tests/test_auth.py
"""Tests for authentication and role-based authorization over the HTTP boundary."""
import pytest
from app.core.security import create_access_token


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_generate_rejected(client):
    resp = client.post(
        "/api/generate",
        json={"description": "a web app with load balancer and rds postgres",
              "provider": "terraform", "target": "aws"},
    )
    assert resp.status_code == 401


def test_unauthenticated_list_rejected(client):
    resp = client.get("/api/generate")
    assert resp.status_code == 401


def test_unauthenticated_estimate_rejected(client):
    resp = client.post(
        "/api/estimate",
        json={"components": ["compute"], "target": "aws"},
    )
    assert resp.status_code == 401


def test_login_bad_password_rejected(client, operator):
    resp = client.post(
        "/api/auth/login",
        json={"email": operator.email, "password": "definitely-wrong"},
    )
    assert resp.status_code == 401


def test_login_bad_credentials_unknown_user(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert resp.status_code == 401


def test_demo_setup_returns_token_and_me(client):
    resp = client.post("/api/auth/demo-setup")
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body
    token = body["access_token"]
    me = client.get("/api/auth/me", headers=_bearer(token))
    assert me.status_code == 200
    assert me.json()["email"] == "demo@example.com"
    assert me.json()["role"] == "operator"


def test_invalid_token_rejected(client):
    resp = client.get("/api/auth/me", headers=_bearer("not.a.real.token"))
    assert resp.status_code == 401


def test_role_denial_generate_for_viewer(client, viewer_token):
    """A viewer (read role) must be denied the operator+ generate write."""
    resp = client.post(
        "/api/generate",
        headers=_bearer(viewer_token),
        json={"description": "a 3-tier web app with load balancer, rds and s3",
              "provider": "terraform", "target": "aws"},
    )
    assert resp.status_code == 403


def test_operator_can_authenticate_and_access_me(client, operator_token):
    me = client.get("/api/auth/me", headers=_bearer(operator_token))
    assert me.status_code == 200
    assert me.json()["role"] == "operator"
    assert me.json()["email"] == "operator@example.com"


def test_fresh_token_propagates_into_authorized_request(client, operator):
    token = create_access_token(subject=str(operator.id), roles=[operator.role.value])
    # generate requires operator role; token carries it
    resp = client.post(
        "/api/generate",
        headers=_bearer(token),
        json={"description": "a 3-tier web app with load balancer, rds and s3",
              "provider": "terraform", "target": "aws"},
    )
    assert resp.status_code == 201
    assert "template" in resp.json()

def test_demo_mode_refused_in_production(monkeypatch):
    """Demo mode must not be usable in production (contract requirement)."""
    from app.core.config import Settings, validate_production_settings

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("CSRF_SECRET", "y" * 32)
    with pytest.raises(RuntimeError):
        validate_production_settings(Settings())


def test_production_requires_real_secrets(monkeypatch):
    """Production with the shipped dev-default secrets must be refused."""
    from app.core.config import Settings, validate_production_settings

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("CSRF_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        validate_production_settings(Settings())