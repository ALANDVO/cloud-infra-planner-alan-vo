# backend/app/main.py
"""FastAPI application factory."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .core.config import settings, validate_production_settings
from .core.database import init_db, close_db
from .api import routes_generate, routes_validate, routes_estimate, routes_auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Validate production settings
    validate_production_settings(settings)
    # Initialize database
    await init_db()
    yield
    # Cleanup
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="cloud-infra-planner-alan-vo",
        description="Generates production-grade Terraform, CloudFormation, or ARM templates from natural language descriptions, with validation, cost estimation, and module composition.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.environment != "production" else None,
        redoc_url="/api/redoc" if settings.environment != "production" else None,
        openapi_url="/api/openapi.json" if settings.environment != "production" else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(routes_auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(routes_generate.router, prefix="/api/generate", tags=["generate"])
    app.include_router(routes_validate.router, prefix="/api/validate", tags=["validate"])
    app.include_router(routes_estimate.router, prefix="/api/estimate", tags=["estimate"])

    # Health check
    @app.get("/api/health", tags=["health"])
    async def health_check():
        return {"status": "ok", "version": "1.0.0"}

    # Serve frontend build in production
    frontend_dist = os.path.join(os.path.dirname(__file__), "../../frontend/dist")
    if os.path.isdir(frontend_dist):
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app


app = create_app()