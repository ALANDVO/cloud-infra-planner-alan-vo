# backend/app/api/routes_auth.py
"""Authentication routes: login, logout, token refresh, CSRF."""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.config import settings
from ..core.database import get_db
from ..core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    generate_csrf_token,
    verify_csrf_token,
    hash_token,
)
from ..models.user import User, Role
from ..schemas.auth import LoginRequest, TokenResponse, UserResponse, CsrfResponse, RefreshRequest
from ..services.audit import audit_log

router = APIRouter()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to get current authenticated user from JWT."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]
    try:
        payload = decode_token(token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: missing subject")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


def require_role(*allowed_roles: Role):
    """Dependency factory for role-based access control."""
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return role_checker


@router.post("/csrf", response_model=CsrfResponse, tags=["auth"])
async def get_csrf_token(request: Request):
    """Get a CSRF token for form submissions."""
    # In production, store in session; for stateless, return signed token
    token = generate_csrf_token()
    response = Response(content="", media_type="application/json")
    # Set as HttpOnly cookie for cookie-based auth flows
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=3600,
    )
    return CsrfResponse(csrf_token=token)


@router.post("/login", response_model=TokenResponse, tags=["auth"])
async def login(
    request: Request,
    response: Response,
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT access token."""
    # Find user by email
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        await audit_log(db, action="login_failed", resource_type="user", details={"email": credentials.email}, request=request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    # Create access token
    access_token = create_access_token(subject=str(user.id), roles=[user.role.value])

    # Set HttpOnly cookie for browser clients
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
    )

    await audit_log(db, action="login", resource_type="user", resource_id=str(user.id), request=request)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
        ),
    )


@router.post("/logout", tags=["auth"])
async def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Logout user (clear cookie)."""
    response.delete_cookie(key="access_token", httponly=True, secure=settings.environment == "production", samesite="lax")
    response.delete_cookie(key="csrf_token", httponly=True, secure=settings.environment == "production", samesite="lax")
    await audit_log(db, action="logout", resource_type="user", resource_id=str(user.id), request=request)
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=TokenResponse, tags=["auth"])
async def refresh_token(
    request: Request,
    response: Response,
    refresh_data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token (not implemented for MVP)."""
    # For MVP, we don't implement refresh tokens; just re-login
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Refresh tokens not implemented; please log in again")


@router.get("/me", response_model=UserResponse, tags=["auth"])
async def get_current_user_info(user: User = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
    )


# Demo user creation endpoint (only in development/demo mode)
@router.post("/demo-setup", tags=["auth"])
async def demo_setup(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a demo user for testing (development/demo mode only)."""
    if not settings.demo_mode and settings.environment != "development":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not available in production")

    # Check if demo user exists
    result = await db.execute(select(User).where(User.email == "demo@example.com"))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email="demo@example.com",
            hashed_password=hash_password("demopassword123"),
            full_name="Demo User",
            role=Role.OPERATOR,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        await audit_log(db, action="demo_user_created", resource_type="user", resource_id=str(user.id), request=request)

    # Log in the demo user
    access_token = create_access_token(subject=str(user.id), roles=[user.role.value])

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
        ),
    )