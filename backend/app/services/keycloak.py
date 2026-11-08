# backend/app/services/keycloak.py
"""Keycloak OIDC integration for authentication and token validation."""
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from jose import jwt, JWTError
from jose.utils import base64url_decode

from ..core.config import settings


@dataclass
class KeycloakUserInfo:
    """User info from Keycloak."""
    sub: str
    email: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    preferred_username: Optional[str] = None
    roles: List[str] = None

    def __post_init__(self):
        if self.roles is None:
            self.roles = []


class KeycloakOIDCClient:
    """Keycloak OIDC client for token validation and user info."""

    def __init__(self):
        self.keycloak_url = settings.keycloak_url.rstrip("/")
        self.realm = settings.keycloak_realm
        self.client_id = settings.keycloak_client_id
        self.client_secret = settings.keycloak_client_secret
        self._jwks: Optional[Dict[str, Any]] = None
        self._jwks_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs"
        self._well_known_url = f"{self.keycloak_url}/realms/{self.realm}/.well-known/openid-configuration"

    async def _fetch_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from Keycloak."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(self._jwks_url)
            resp.raise_for_status()
            return resp.json()

    async def get_jwks(self) -> Dict[str, Any]:
        """Get JWKS with caching."""
        if self._jwks is None:
            self._jwks = await self._fetch_jwks()
        return self._jwks

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token against Keycloak JWKS."""
        # Get JWKS
        jwks = await self.get_jwks()

        # Get token header to find kid
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise ValueError("Token missing kid header")

        # Find matching key
        key = None
        for k in jwks.get("keys", []):
            if k.get("kid") == kid:
                key = k
                break

        if not key:
            # Refresh JWKS and try once more
            self._jwks = None
            jwks = await self._fetch_jwks()
            for k in jwks.get("keys", []):
                if k.get("kid") == kid:
                    key = k
                    break
            if not key:
                raise ValueError(f"Key with kid '{kid}' not found in JWKS")

        # Construct public key from JWK
        public_key = self._jwk_to_pem(key)

        # Decode and validate token
        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=f"{self.keycloak_url}/realms/{self.realm}",
            )
            return payload
        except JWTError as e:
            raise ValueError(f"Token validation failed: {e}")

    def _jwk_to_pem(self, jwk: Dict[str, Any]) -> str:
        """Convert JWK to PEM format for python-jose."""
        # For RS256, we need to reconstruct the RSA public key
        from jose.backends import RSAKey
        return RSAKey(jwk, "RS256").public_key()

    async def get_userinfo(self, access_token: str) -> KeycloakUserInfo:
        """Get user info from Keycloak using access token."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return KeycloakUserInfo(
                sub=data.get("sub", ""),
                email=data.get("email", ""),
                given_name=data.get("given_name"),
                family_name=data.get("family_name"),
                preferred_username=data.get("preferred_username"),
                roles=data.get("roles", []),
            )

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Generate Keycloak authorization URL."""
        from urllib.parse import urlencode
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile roles",
            "state": state,
        }
        return f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/auth?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access/refresh tokens."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
            resp = await client.post(
                f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            return resp.json()

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
            resp = await client.post(
                f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            return resp.json()


# Singleton instance
_keycloak_client: Optional[KeycloakOIDCClient] = None


def get_keycloak_client() -> KeycloakOIDCClient:
    """Get or create Keycloak OIDC client singleton."""
    global _keycloak_client
    if _keycloak_client is None:
        _keycloak_client = KeycloakOIDCClient()
    return _keycloak_client

