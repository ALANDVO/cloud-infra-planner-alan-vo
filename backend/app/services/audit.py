# backend/app/services/audit.py
"""Audit logging service — records every security-relevant action."""
import json
from typing import Any, Optional

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit import AuditLog


async def audit_log(
    db: AsyncSession,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """Persist an audit-log entry.

    Extracts IP and user-agent from the optional request, serialises *details*
    as JSON, and writes a row to the ``audit_logs`` table.
    """
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    if request is not None:
        client_host = request.client.host if request.client else None
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        elif client_host:
            ip_address = client_host
        user_agent = request.headers.get("user-agent")

    log = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(details) if details else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_audit_logs(
    db: AsyncSession,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 200,
) -> list[AuditLog]:
    """Retrieve recent audit entries, optionally filtered."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()