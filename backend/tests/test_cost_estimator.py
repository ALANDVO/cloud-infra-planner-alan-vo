# backend/tests/test_cost_estimator.py
"""Tests for the deterministic cost estimator."""
from app.services.cost_estimator import CostEstimator, cost_estimator


def test_estimate_returns_total_and_resources():
    total, resources = cost_estimator.estimate(["network", "compute"], "aws", regions=1)
    assert total > 0
    assert len(resources) == 2
    names = {r["resource_type"] for r in resources}
    assert names == {"network", "compute"}
    # per-resource cost equals the configured unit cost
    by_type = {r["resource_type"]: r for r in resources}
    assert by_type["compute"]["monthly_cost_usd"] == 98
    assert by_type["network"]["monthly_cost_usd"] == 10
    assert by_type["compute"]["unit_cost_usd"] == 98
    assert by_type["compute"]["region"] == "aws"


def test_estimate_multi_region_increases_cost():
    single, _ = cost_estimator.estimate(["compute"], "aws", regions=1)
    multi, resources = cost_estimator.estimate(["compute"], "aws", regions=2)
    assert multi > single
    # 2 regions -> 1.5x multiplier
    assert resources[0]["monthly_cost_usd"] == 98 * 1.5


def test_estimate_ha_premium():
    base, _ = cost_estimator.estimate(["compute"], "aws", regions=1)
    ha_total, _ = cost_estimator.estimate(["compute", "ha"], "aws", regions=1)
    assert ha_total > base
    # HA applies a 1.4x multiplier and rounds to nearest int
    assert ha_total == round(base * 1.4)


def test_estimate_unknown_component_is_free():
    total, resources = cost_estimator.estimate(["compute", "dragon"], "aws", regions=1)
    assert "dragon" in {r["resource_type"] for r in resources}
    assert any(r["monthly_cost_usd"] == 0 for r in resources)


def test_estimate_uses_target_specific_pricing():
    gcp_total, _ = cost_estimator.estimate(["compute"], "gcp", regions=1)
    aws_total, _ = cost_estimator.estimate(["compute"], "aws", regions=1)
    az_total, _ = cost_estimator.estimate(["compute"], "azure", regions=1)
    # each cloud has its own compute baseline
    assert {gcp_total, aws_total, az_total} == {90, 98, 100}