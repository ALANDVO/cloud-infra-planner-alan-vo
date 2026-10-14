# backend/tests/test_api_integration.py
"""End-to-end workflow tests crossing the real HTTP boundary.

Covers the complete Generate -> Validate -> Estimate cycle for the
deterministic offline core (no LLM network calls in CI).
"""
import json

from app.models.generation import Provider


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


GEN_DESCRIPTION = (
    "A highly available 3-tier web app with an internet-facing load balancer, "
    "RDS Postgres, ElastiCache Redis, S3 storage and SQS queues on AWS"
)


def test_full_generate_workflow(client, operator_token):
    headers = _bearer(operator_token)
    desc = (
        "3-tier web app with ALB, RDS Postgres, Redis, S3 and SQS queues "
        "on AWS, multi-region high availability"
    )
    resp = client.post(
        "/api/generate",
        headers=headers,
        json={"description": desc, "provider": "terraform", "target": "aws", "use_llm": False},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "completed"
    assert body["cost_estimate_usd"] is not None and body["cost_estimate_usd"] > 0
    assert "template" in body and body["template"]
    assert "network" in body["components"] and "compute" in body["components"]
    gen_id = body["id"]

    # fetch single
    got = client.get(f"/api/generate/{gen_id}", headers=headers)
    assert got.status_code == 200
    assert got.json()["id"] == gen_id
    assert "template" in got.json()

    # list with pagination
    listed = client.get("/api/generate", headers=headers)
    assert listed.status_code == 200
    page = listed.json()
    assert page["total"] >= 1
    assert any(item["id"] == gen_id for item in page["items"])

    # delete
    deleted = client.delete(f"/api/generate/{gen_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/generate/{gen_id}", headers=headers).status_code == 404


def test_validate_generated_template_over_http(client, operator_token):
    headers = _bearer(operator_token)
    # generate first
    gen = client.post(
        "/api/generate",
        headers=headers,
        json={"description": GEN_DESCRIPTION, "provider": "terraform", "target": "aws", "use_llm": False},
    )
    assert gen.status_code == 201
    template = gen.json()["template"]

    # validate the produced template
    val = client.post(
        "/api/validate",
        headers=headers,
        json={"template": template, "provider": "terraform", "target": "aws"},
    )
    assert val.status_code == 200
    vbody = val.json()
    assert vbody["valid"] is True
    assert isinstance(vbody["issues"], list)
    assert vbody["summary"]


def test_validate_rejects_malformed_template(client, operator_token):
    headers = _bearer(operator_token)
    val = client.post(
        "/api/validate",
        headers=headers,
        json={"template": "{not valid json", "provider": "arm", "target": "azure"},
    )
    assert val.status_code == 200
    assert val.json()["valid"] is False
    assert any(i["severity"] == "error" for i in val.json()["issues"])


def test_estimate_workflow_from_components(client, operator_token):
    headers = _bearer(operator_token)
    est = client.post(
        "/api/estimate",
        headers=headers,
        json={"components": ["network", "compute", "database", "cache"], "target": "aws", "regions": 1},
    )
    assert est.status_code == 200
    body = est.json()
    assert body["total_monthly_usd"] > 0
    assert len(body["resources"]) == 4
    assert "aws" in body["breakdown_by_region"]
    assert any(r["resource_type"] == "database" for r in body["resources"])


def test_estimate_workflow_from_template(client, operator_token):
    headers = _bearer(operator_token)
    # generate a template, then estimate from it via component extraction
    gen = client.post(
        "/api/generate",
        headers=headers,
        json={"description": "web app with load balancer, rds postgres, redis and S3",
              "provider": "terraform", "target": "aws", "use_llm": False},
    )
    assert gen.status_code == 201
    template = gen.json()["template"]
    est = client.post(
        "/api/estimate",
        headers=headers,
        json={"template": template, "target": "aws", "regions": 1},
    )
    assert est.status_code == 200
    assert est.json()["total_monthly_usd"] > 0


def test_health_and_openapi(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/openapi.json").status_code == 200