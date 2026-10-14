# backend/app/api/routes_generate.py
"""Generate workflow routes: NL → IaC template generation."""
from typing import List, Optional
import json
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from ..core.config import settings
from ..core.database import get_db
from ..models.generation import Generation, Provider, Target, GenerationStatus
from ..models.user import User, Role
from ..schemas.generate import GenerateRequest, GenerateResponse, GenerationListResponse
from ..services.generator import generator
from ..services.cost_estimator import cost_estimator
from ..services.validator import validator
from ..services.audit import audit_log
from ..api.routes_auth import get_current_user, require_role

router = APIRouter()


@router.post("", response_model=GenerateResponse, status_code=status.HTTP_201_CREATED, tags=["generate"])
async def generate_template(
    request: Request,
    payload: GenerateRequest,
    user: User = Depends(require_role(Role.OPERATOR, Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Generate IaC template from natural language description."""
    # Create generation record
    generation = Generation(
        user_id=user.id,
        description=payload.description,
        provider=payload.provider,
        target=payload.target,
        status=GenerationStatus.PENDING,
    )
    db.add(generation)
    await db.commit()
    await db.refresh(generation)

    await audit_log(db, action="generation_started", resource_type="generation", resource_id=str(generation.id), request=request)

    try:
        # Detect components from description
        components = generator.detect_components(payload.description)

        # Generate template
        template = await generator.generate(
            description=payload.description,
            provider=payload.provider,
            target=payload.target,
            components=components,
            use_llm=payload.use_llm,
        )

        # Validate generated template
        validation_result = await validator.validate(template, payload.provider.value, payload.target.value)

        # Estimate cost
        total_cost, resource_costs = cost_estimator.estimate(
            components=components,
            target=payload.target.value,
            regions=1,  # Default to single region
        )

        # Update generation record
        generation.template = template
        generation.validation_notes = validation_result.summary
        generation.cost_estimate_usd = total_cost
        generation.components = json.dumps(components)  # Store components as JSON
        generation.status = GenerationStatus.COMPLETED
        generation.completed_at = func.now()

        await db.commit()
        await db.refresh(generation)

        await audit_log(
            db,
            action="generation_completed",
            resource_type="generation",
            resource_id=str(generation.id),
            details={
                "provider": payload.provider.value,
                "target": payload.target.value,
                "components": components,
                "cost_estimate_usd": total_cost,
            },
            request=request,
        )

        return GenerateResponse(
            id=generation.id,
            description=generation.description,
            provider=generation.provider,
            target=generation.target,
            template=generation.template,
            validation_notes=generation.validation_notes,
            cost_estimate_usd=generation.cost_estimate_usd,
            components=components,
            status=generation.status,
            error_message=None,
            created_at=generation.created_at,
            completed_at=generation.completed_at,
        )

    except Exception as e:
        generation.status = GenerationStatus.FAILED
        generation.error_message = str(e)
        await db.commit()

        await audit_log(
            db,
            action="generation_failed",
            resource_type="generation",
            resource_id=str(generation.id),
            details={"error": str(e)},
            request=request,
        )

        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Generation failed: {e}")


@router.get("", response_model=GenerationListResponse, tags=["generate"])
async def list_generations(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[GenerationStatus] = Query(None, description="Filter by status"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's generation history with pagination."""
    query = select(Generation).where(Generation.user_id == user.id)

    if status_filter:
        query = query.where(Generation.status == status_filter)

    # Total count
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    # Paginated results
    query = query.order_by(desc(Generation.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    generations = result.scalars().all()

    items = []
    for g in generations:
        components = []
        if g.components:
            try:
                import json
                components = json.loads(g.components)
            except Exception:
                components = []

        items.append(GenerateResponse(
            id=g.id,
            description=g.description,
            provider=g.provider,
            target=g.target,
            template=g.template,
            validation_notes=g.validation_notes,
            cost_estimate_usd=g.cost_estimate_usd,
            components=components,
            status=g.status,
            error_message=g.error_message,
            created_at=g.created_at,
            completed_at=g.completed_at,
        ))

    return GenerationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{generation_id}", response_model=GenerateResponse, tags=["generate"])
async def get_generation(
    generation_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific generation by ID."""
    result = await db.execute(select(Generation).where(Generation.id == generation_id, Generation.user_id == user.id))
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation not found")

    components = []
    if generation.components:
        try:
            import json
            components = json.loads(generation.components)
        except Exception:
            components = []

    return GenerateResponse(
        id=generation.id,
        description=generation.description,
        provider=generation.provider,
        target=generation.target,
        template=generation.template,
        validation_notes=generation.validation_notes,
        cost_estimate_usd=generation.cost_estimate_usd,
        components=components,
        status=generation.status,
        error_message=generation.error_message,
        created_at=generation.created_at,
        completed_at=generation.completed_at,
    )


@router.delete("/{generation_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["generate"])
async def delete_generation(
    generation_id: int,
    request: Request,
    user: User = Depends(require_role(Role.OPERATOR, Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a generation record."""
    result = await db.execute(select(Generation).where(Generation.id == generation_id, Generation.user_id == user.id))
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation not found")

    await db.delete(generation)
    await db.commit()

    await audit_log(db, action="generation_deleted", resource_type="generation", resource_id=str(generation_id), request=request)