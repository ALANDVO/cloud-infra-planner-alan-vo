# backend/tests/test_generator.py
"""Tests for the deterministic NL -> IaC generator."""
import asyncio

from app.services.generator import Generator, generator, detect_components
from app.services.validator import validator
from app.models.generation import Provider, Target


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


# --- component detection ----------------------------------------------------

def test_detect_components_3tier_web_app():
    comps = detect_components(
        "A highly available 3-tier web app with ALB, RDS Postgres and S3"
    )
    assert "network" in comps
    assert "compute" in comps
    assert "load_balancer" in comps
    assert "database" in comps
    assert "cache" not in comps  # no redis/elasticache mentioned


def test_detect_components_serverless_redis():
    comps = detect_components(
        "Serverless API with Lambda, API Gateway and Redis cache on AWS"
    )
    assert "serverless" in comps
    assert "cache" in comps
    assert "queue" not in comps


def test_detect_components_defaults_to_network_compute():
    comps = detect_components("build me some infrastructure please")
    assert comps == ["network", "compute"]


def test_detect_components_detects_all_kinds():
    desc = ("EKS kubernetes, SQS queues, DynamoDB NoSQL, BigQuery, "
            "multi-region high availability, GCP cloud run, azure container apps")
    comps = detect_components(desc)
    for want in ("k8s", "queue", "no_sql", "serverless", "ha"):
        assert want in comps


# --- deterministic generation + structural validity ------------------------

def test_generate_terraform_aws_valid():
    desc = "A highly available 3-tier web app with ALB, RDS Postgres, cache and S3"
    comps = detect_components(desc)
    tpl = asyncio.run(generator.generate(desc, Provider.TERRAFORM, Target.AWS, components=comps, use_llm=False))
    assert 'terraform {\n  required_version' in tpl
    assert "resource \"aws_instance\"" in tpl
    assert "resource \"aws_vpc\"" in tpl
    res = asyncio.run(validator.validate(tpl, Provider.TERRAFORM.value, Target.AWS.value))
    # generated output should be structurally valid (no errors); HA RDS may warn
    assert res.valid


def test_generate_all_formats_validate():
    desc = "Serverless API with Lambda, API Gateway, DynamoDB and S3"
    comps = detect_components(desc)
    for prov in (Provider.TERRAFORM, Provider.CLOUDFORMATION, Provider.ARM):
        tpl = asyncio.run(generator.generate(desc, prov, Target.AWS, components=comps, use_llm=False))
        res = asyncio.run(validator.validate(tpl, prov.value, Target.AWS.value))
        assert res.valid, (prov.value, [i.message for i in res.issues])


def test_generate_is_deterministic():
    desc = "A web app with load balancer, RDS postgres and S3"
    comps = detect_components(desc)
    a = asyncio.run(generator.generate(desc, Provider.TERRAFORM, Target.AWS, components=comps, use_llm=False))
    b = asyncio.run(generator.generate(desc, Provider.TERRAFORM, Target.AWS, components=comps, use_llm=False))
    assert a == b


def test_generate_gcp_and_azure_terraform():
    desc = "Kubernetes cluster with compute nodes and a redis cache"
    comps = detect_components(desc)
    for tgt in (Target.GCP, Target.AZURE):
        tpl = asyncio.run(generator.generate(desc, Provider.TERRAFORM, tgt, components=comps, use_llm=False))
        assert "terraform" in tpl.lower()
        assert "resource " in tpl
        res = asyncio.run(validator.validate(tpl, Provider.TERRAFORM.value, tgt.value))
        assert res.valid


def test_generate_arm_is_valid_json():
    desc = "Azure AKS cluster with VM scale set and storage account"
    comps = detect_components(desc)
    tpl = asyncio.run(generator.generate(desc, Provider.ARM, Target.AZURE, components=comps, use_llm=False))
    import json
    data = json.loads(tpl)  # must parse as JSON
    assert "$schema" in data
    assert isinstance(data["resources"], list) and data["resources"]