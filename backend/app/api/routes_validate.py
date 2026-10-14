# backend/app/api/routes_validate.py
"""Validate workflow routes: IaC template validation."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..schemas.validate import ValidateRequest, ValidateResponse
from ..services.validator import validator
from ..services.audit import audit_log
from ..api.routes_auth import get_current_user

router = APIRouter()


@router.post("", response_model=ValidateResponse, tags=["validate"])
async def validate_template(
    request: Request,
    payload: ValidateRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate an IaC template for syntax, best practices, and cloud-specific rules."""
    try:
        result = await validator.validate(
            template=payload.template,
            provider=payload.provider,
            target=payload.target,
        )

        await audit_log(
            db,
            action="template_validated",
            resource_type="validation",
            details={
                "valid": result.valid,
                "issue_count": len(result.issues),
                "provider": payload.provider,
                "target": payload.target,
            },
            request=request,
        )

        return result

    except Exception as e:
        await audit_log(
            db,
            action="validation_failed",
            resource_type="validation",
            details={"error": str(e)},
            request=request,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Validation failed: {e}")