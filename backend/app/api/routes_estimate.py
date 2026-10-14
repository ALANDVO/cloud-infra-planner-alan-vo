# backend/app/api/routes_estimate.py
"""Estimate workflow routes: Cost estimation from templates or components."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..schemas.estimate import EstimateRequest, EstimateResponse
from ..services.cost_estimator import cost_estimator
from ..services.validator import validator
from ..services.audit import audit_log
from ..api.routes_auth import get_current_user

router = APIRouter()


@router.post("", response_model=EstimateResponse, tags=["estimate"])
async def estimate_cost(
    request: Request,
    payload: EstimateRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Estimate monthly cost from IaC template or component list."""
    try:
        components = payload.components

        # If template provided but no components, extract components from template
        if not components and payload.template:
            validation_result = await validator.validate(payload.template, None, payload.target)
            # Extract resource types from validation issues/summary as a fallback
            # For MVP, we'll use a simple keyword-based extraction
            components = _extract_components_from_template(payload.template, payload.target)

        if not components:
            # Default to basic network + compute
            components = ["network", "compute"]

        total_cost, resource_costs = cost_estimator.estimate(
            components=components,
            target=payload.target,
            regions=payload.regions,
        )

        # Build response
        from ..schemas.estimate import ResourceCost
        resources = [
            ResourceCost(
                resource_type=rc["resource_type"],
                resource_name=rc["resource_name"],
                monthly_cost_usd=rc["monthly_cost_usd"],
                region=rc["region"],
                details=rc.get("details"),
            )
            for rc in resource_costs
        ]

        # Breakdowns
        breakdown_by_service = {}
        for rc in resource_costs:
            svc = rc["resource_type"]
            breakdown_by_service[svc] = breakdown_by_service.get(svc, 0) + rc["monthly_cost_usd"]

        breakdown_by_region = {}
        for rc in resource_costs:
            reg = rc["region"]
            breakdown_by_region[reg] = breakdown_by_region.get(reg, 0) + rc["monthly_cost_usd"]

        assumptions = [
            f"Estimated for {payload.target.upper()} in {payload.regions} region(s)",
            "Prices based on on-demand/public pricing (no discounts)",
            "Storage costs assume 100GB baseline",
            "Compute assumes 24/7 runtime",
        ]

        result = EstimateResponse(
            total_monthly_usd=total_cost,
            resources=resources,
            breakdown_by_service=breakdown_by_service,
            breakdown_by_region=breakdown_by_region,
            assumptions=assumptions,
        )

        await audit_log(
            db,
            action="cost_estimated",
            resource_type="estimate",
            details={
                "total_monthly_usd": total_cost,
                "target": payload.target,
                "regions": payload.regions,
                "components": components,
            },
            request=request,
        )

        return result

    except Exception as e:
        await audit_log(
            db,
            action="estimation_failed",
            resource_type="estimate",
            details={"error": str(e)},
            request=request,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Estimation failed: {e}")


def _extract_components_from_template(template: str, target: str) -> list[str]:
    """Simple keyword-based component extraction from template."""
    components = []
    template_lower = template.lower()

    # AWS
    if target == "aws":
        if "vpc" in template_lower or "subnet" in template_lower:
            components.append("network")
        if "instance" in template_lower or "autoscaling" in template_lower or "ec2" in template_lower:
            components.append("compute")
        if "alb" in template_lower or "load_balancer" in template_lower or "elb" in template_lower:
            components.append("load_balancer")
        if "rds" in template_lower or "database" in template_lower:
            components.append("database")
        if "elasticache" in template_lower or "redis" in template_lower:
            components.append("cache")
        if "s3" in template_lower or "bucket" in template_lower:
            components.append("storage")
        if "dynamodb" in template_lower:
            components.append("no_sql")
        if "lambda" in template_lower:
            components.append("serverless")
        if "eks" in template_lower or "kubernetes" in template_lower:
            components.append("k8s")
        if "sqs" in template_lower or "queue" in template_lower:
            components.append("queue")
        if "multi_az" in template_lower or "availability_zone" in template_lower:
            components.append("ha")

    # GCP
    elif target == "gcp":
        if "vpc" in template_lower or "subnet" in template_lower:
            components.append("network")
        if "compute" in template_lower or "instance" in template_lower:
            components.append("compute")
        if "load_balancer" in template_lower or "forwarding_rule" in template_lower:
            components.append("load_balancer")
        if "sql" in template_lower or "database" in template_lower:
            components.append("database")
        if "memorystore" in template_lower or "redis" in template_lower:
            components.append("cache")
        if "storage" in template_lower or "bucket" in template_lower:
            components.append("storage")
        if "bigtable" in template_lower or "firestore" in template_lower:
            components.append("no_sql")
        if "cloud_run" in template_lower or "cloud_function" in template_lower:
            components.append("serverless")
        if "gke" in template_lower or "kubernetes" in template_lower:
            components.append("k8s")
        if "pubsub" in template_lower or "queue" in template_lower:
            components.append("queue")
        if "multi_zone" in template_lower or "multi_region" in template_lower:
            components.append("ha")

    # Azure
    elif target == "azure":
        if "vnet" in template_lower or "subnet" in template_lower:
            components.append("network")
        if "virtual_machine" in template_lower or "vm" in template_lower or "scale_set" in template_lower:
            components.append("compute")
        if "load_balancer" in template_lower or "application_gateway" in template_lower:
            components.append("load_balancer")
        if "sql" in template_lower or "database" in template_lower or "postgresql" in template_lower:
            components.append("database")
        if "cache" in template_lower or "redis" in template_lower:
            components.append("cache")
        if "storage_account" in template_lower or "blob" in template_lower:
            components.append("storage")
        if "cosmos" in template_lower:
            components.append("no_sql")
        if "function" in template_lower or "container_app" in template_lower:
            components.append("serverless")
        if "aks" in template_lower or "kubernetes" in template_lower:
            components.append("k8s")
        if "service_bus" in template_lower or "queue" in template_lower:
            components.append("queue")
        if "zone" in template_lower or "availability" in template_lower:
            components.append("ha")

    return components if components else ["network", "compute"]