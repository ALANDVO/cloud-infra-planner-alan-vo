# backend/app/schemas/estimate.py
"""Cost estimation request/response schemas."""
from typing import Optional, List
from pydantic import BaseModel, Field


class ResourceCost(BaseModel):
    resource_type: str
    resource_name: str
    monthly_cost_usd: float
    region: str
    details: Optional[dict] = None


class EstimateRequest(BaseModel):
    template: Optional[str] = Field(default=None, max_length=100000, description="IaC template")
    components: Optional[List[str]] = Field(default=None, description="Component list if no template")
    target: str = Field(..., description="Cloud target (aws, gcp, azure)")
    regions: int = Field(default=1, ge=1, le=10, description="Number of regions")


class EstimateResponse(BaseModel):
    total_monthly_usd: float
    resources: List[ResourceCost] = []
    breakdown_by_service: dict = {}
    breakdown_by_region: dict = {}
    assumptions: List[str] = []