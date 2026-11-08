# backend/app/api/routes_auth.py
"""Authentication routes: login, logout, token refresh, CSRF, OIDC."""
from datetime import timedelta
import secrets
import httpx
from urllib.parse import urlencode
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
from ..services.keycloak import get_keycloak_client, KeycloakUserInfo


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
# Keycloak OIDC endpoints
@router.get("/oidc/login", tags=["auth"])
async def oidc_login(request: Request):
    """Initiate OIDC login flow with Keycloak."""
    keycloak = get_keycloak_client()
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Store state in session (using cookie for stateless approach)
    response = Response(content="", media_type="application/json")
    response.set_cookie(
        key="oidc_state",
        value=state,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=600,  # 10 minutes
    )
    
    # Build redirect URI
    redirect_uri = f"{settings.keycloak_url.rstrip('/')}/realms/{settings.keycloak_realm}/protocol/openid-connect/auth"
    # Actually use the client's method
    auth_url = keycloak.get_authorization_url(
        redirect_uri=f"{str(request.base_url).rstrip('/')}/api/auth/oidc/callback",
        state=state,
    )
    
    return {"authorization_url": auth_url}


@router.get("/oidc/callback", tags=["auth"])
async def oidc_callback(
    request: Request,
    response: Response,
    code: str = None,
    state: str = None,
    error: str = None,
    error_description: str = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle OIDC callback from Keycloak."""
    keycloak = get_keycloak_client()
    
    # Verify state parameter
    stored_state = request.cookies.get("oidc_state")
    if not stored_state or not state or not verify_csrf_token(state, stored_state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or missing state parameter")
    
    # Clear state cookie
    response.delete_cookie(key="oidc_state", httponly=True, secure=settings.environment == "production", samesite="lax")
    
    # Handle error from Keycloak
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"OIDC error: {error_description or error}")
    
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing authorization code")
    
    # Exchange code for tokens
    try:
        tokens = await keycloak.exchange_code_for_tokens(
            code=code,
            redirect_uri=f"{str(request.base_url).rstrip('/')}/api/auth/oidc/callback",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Token exchange failed: {e.response.text}")
    
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    id_token = tokens.get("id_token")
    
    if not access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No access token received")
    
    # Get user info from Keycloak
    try:
        userinfo = await keycloak.get_userinfo(access_token)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Userinfo request failed: {e.response.text}")
    
    # Map Keycloak roles to local roles
    role_mapping = {
        "admin": Role.ADMIN,
        "operator": Role.OPERATOR,
        "viewer": Role.VIEWER,
    }
    local_role = Role.VIEWER  # default
    for kc_role in userinfo.roles:
        if kc_role in role_mapping:
            local_role = role_mapping[kc_role]
            break
    
    # Find or create user
    result = await db.execute(select(User).where(User.email == userinfo.email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Create new user
        full_name = f"{userinfo.given_name or ''} {userinfo.family_name or ''}".strip() or userinfo.preferred_username or userinfo.email
        user = User(
            email=userinfo.email,
            hashed_password=hash_password(secrets.token_urlsafe(32)),  # Random password, OIDC only
            full_name=full_name,
            role=local_role,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        await audit_log(db, action="oidc_user_created", resource_type="user", resource_id=str(user.id), request=request)
    else:
        # Update role if changed
        if user.role != local_role:
            user.role = local_role
            await db.commit()
            await audit_log(db, action="oidc_role_updated", resource_type="user", resource_id=str(user.id), details={"new_role": local_role.value}, request=request)
    
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    
    # Create local JWT token
    local_token = create_access_token(subject=str(user.id), roles=[user.role.value])
    
    # Set HttpOnly cookie for browser clients
    response.set_cookie(
        key="access_token",
        value=local_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
    )
    
    # Store refresh token in secure HttpOnly cookie if present
    if refresh_token:
        response.set_cookie(
            key="oidc_refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=30 * 24 * 60 * 60,  # 30 days
        )
    
    await audit_log(db, action="oidc_login", resource_type="user", resource_id=str(user.id), request=request)
    
    # Redirect to frontend or return token
    frontend_url = str(request.base_url).rstrip('/')
    return TokenResponse(
        access_token=local_token,
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


@router.post("/oidc/logout", tags=["auth"])
async def oidc_logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Logout from both local and Keycloak session."""
    keycloak = get_keycloak_client()
    
    # Get refresh token from cookie
    refresh_token = request.cookies.get("oidc_refresh_token")
    
    # Clear local cookies
    response.delete_cookie(key="access_token", httponly=True, secure=settings.environment == "production", samesite="lax")
    response.delete_cookie(key="csrf_token", httponly=True, secure=settings.environment == "production", samesite="lax")
    response.delete_cookie(key="oidc_refresh_token", httponly=True, secure=True, samesite="lax")
    
    # Optionally revoke at Keycloak (requires offline_access scope and service account)
    # For now, just clear local session
    
    await audit_log(db, action="oidc_logout", resource_type="user", resource_id=str(user.id), request=request)
    
    # Return Keycloak logout URL for frontend to redirect
    logout_url = f"{keycloak.keycloak_url}/realms/{keycloak.realm}/protocol/openid-connect/logout"
    
    return {"message": "Logged out successfully", "keycloak_logout_url": logout_url}