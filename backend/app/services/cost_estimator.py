# backend/app/services/cost_estimator.py
"""Deterministic cost estimation from detected infrastructure components."""
from typing import Dict, List, Tuple


# Monthly base costs in USD per component, keyed by cloud target.
_BASE_COSTS: Dict[str, Dict[str, int]] = {
    "aws": {
        "network": 10,
        "compute": 98,
        "load_balancer": 16,
        "database": 150,
        "cache": 80,
        "storage": 5,
        "no_sql": 25,
        "serverless": 10,
        "queue": 2,
        "k8s": 350,
        "ha": 200,
    },
    "gcp": {
        "network": 10,
        "compute": 90,
        "load_balancer": 16,
        "database": 140,
        "cache": 75,
        "storage": 5,
        "no_sql": 30,
        "serverless": 10,
        "queue": 2,
        "k8s": 330,
        "ha": 190,
    },
    "azure": {
        "network": 10,
        "compute": 100,
        "load_balancer": 16,
        "database": 160,
        "cache": 85,
        "storage": 5,
        "no_sql": 35,
        "serverless": 10,
        "queue": 2,
        "k8s": 360,
        "ha": 210,
    },
}

# Human-readable resource names per (target, component).
_RESOURCE_NAMES: Dict[str, Dict[str, str]] = {
    "aws": {
        "network": "VPC + Subnets + Route Tables + IGW",
        "compute": "EC2 Launch Template + Auto Scaling Group",
        "load_balancer": "Application Load Balancer (ALB)",
        "database": "RDS PostgreSQL (Multi-AZ)",
        "cache": "ElastiCache Redis (Replication Group)",
        "storage": "S3 Bucket + Bucket Policy",
        "no_sql": "DynamoDB Table",
        "serverless": "Lambda Function + API Gateway",
        "queue": "SQS Queue + SNS Topic",
        "k8s": "EKS Cluster + Managed Node Group",
        "ha": "Multi-AZ / Multi-Region Redundancy",
    },
    "gcp": {
        "network": "VPC Network + Subnets + Firewall",
        "compute": "Compute Engine Instance Template + MIG",
        "load_balancer": "External HTTP(S) Load Balancer",
        "database": "Cloud SQL (PostgreSQL HA)",
        "cache": "Memorystore for Redis",
        "storage": "Cloud Storage Bucket",
        "no_sql": "Bigtable Instance",
        "serverless": "Cloud Run Service",
        "queue": "Pub/Sub Topic",
        "k8s": "GKE Cluster + Node Pool",
        "ha": "Multi-zone / Multi-region Redundancy",
    },
    "azure": {
        "network": "Virtual Network + Subnets + NSG",
        "compute": "Linux VM Scale Set",
        "load_balancer": "Azure Load Balancer",
        "database": "Azure Database for PostgreSQL (Flexible Server, Zone-Redundant)",
        "cache": "Azure Cache for Redis",
        "storage": "Storage Account (Standard)",
        "no_sql": "Cosmos DB Account",
        "serverless": "Function App (Consumption)",
        "queue": "Service Bus Queue",
        "k8s": "AKS Cluster",
        "ha": "Zone-Redundant / Failover",
    },
}

# Region multipliers — multi-region deployments cost more.
_REGION_MULTIPLIERS: Dict[int, float] = {1: 1.0, 2: 1.5, 3: 2.0}


class CostEstimator:
    """Deterministic cost estimation from component lists."""

    def __init__(self) -> None:
        self._base_costs = _BASE_COSTS
        self._resource_names = _RESOURCE_NAMES

    def estimate(
        self, components: List[str], target: str, regions: int = 1
    ) -> Tuple[float, List[Dict]]:
        """Return (total_monthly_usd, per_resource_cost_list).

        ``total`` rounds to the nearest integer for HA premiums.
        Per-resource entries carry unit cost, region count, and a human name.
        """
        costs = self._base_costs.get(target, self._base_costs["aws"])
        names = self._resource_names.get(target, self._resource_names["aws"])
        region_mult = _REGION_MULTIPLIERS.get(regions, 1.0 + 0.25 * (regions - 1))
        resources: List[Dict] = []
        total = 0.0
        for comp in components:
            if comp == "ha":
                # HA is a multiplier modifier, not a standalone billed resource.
                continue
            unit = costs.get(comp, 0)
            per_resource = unit * region_mult
            resources.append(
                {
                    "resource_type": comp,
                    "resource_name": names.get(comp, comp),
                    "monthly_cost_usd": per_resource,
                    "unit_cost_usd": float(unit),
                    "regions": regions,
                    "region": target,
                }
            )
            total += per_resource
        if "ha" in components:
            total = round(total * 1.4)
        return total, resources


cost_estimator = CostEstimator()