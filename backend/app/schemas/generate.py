# backend/app/schemas/generate.py
"""Generate request/response schemas."""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from ..models.generation import Provider, Target, GenerationStatus


class GenerateRequest(BaseModel):
    description: str = Field(..., min_length=10, max_length=5000, description="Natural language infrastructure description")
    provider: Provider = Field(..., description="IaC provider")
    target: Target = Field(..., description="Cloud target")
    use_llm: bool = Field(default=True, description="Whether to use LLM for enhancement")


class GenerateResponse(BaseModel):
    id: int
    description: str
    provider: Provider
    target: Target
    template: Optional[str] = None
    validation_notes: Optional[str] = None
    cost_estimate_usd: Optional[float] = None
    components: List[str] = []
    status: GenerationStatus
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GenerationListResponse(BaseModel):
    items: List[GenerateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int