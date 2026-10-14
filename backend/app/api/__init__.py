# backend/app/api/__init__.py
"""API routes package."""
from . import routes_auth, routes_generate, routes_validate, routes_estimate

__all__ = [
    "routes_auth",
    "routes_generate",
    "routes_validate",
    "routes_estimate",
]