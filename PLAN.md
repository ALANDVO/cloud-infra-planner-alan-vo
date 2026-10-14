# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

frontend

## Roadmap

### core-infrastructure — Core Project Infrastructure

Status: done

Acceptance:
- FastAPI backend with modular structure (app/main.py, api/, services/, models/, core/)
- Dockerfiles for backend with non-root users
- compose.yaml (backend + Keycloak) with persistent volumes, 127.0.0.1 ports
- pytest backend tests (>=12 meaningful tests)
- CI workflow running backend tests and backend Docker build
- portfolio.json at root with required schema
- pyproject.toml project metadata

Implementation: `backend/app/main.py`, `backend/app/core/`, `backend/app/api/`, `backend/app/services/`, `backend/app/models/`, `backend/app/schemas/`, `backend/Dockerfile`, `backend/.dockerignore`, `pyproject.toml`, `portfolio.json`, `compose.yaml`, `.github/workflows/ci.yml`, `CHANGELOG.md`, `.env.example`, `.gitignore`

Tests: `backend/tests/conftest.py`, `backend/tests/test_generator.py`, `backend/tests/test_validator.py`, `backend/tests/test_cost_estimator.py`, `backend/tests/test_auth.py`, `backend/tests/test_api_integration.py`

### generate-workflow — Natural Language to IaC Generation Workflow

Status: done

Acceptance:
- POST /api/generate accepting description, provider, target, use_llm
- Returns Terraform/CloudFormation/ARM template with validation summary and cost estimate, persisted with pagination/filtering
- Export/download via template field; cost estimation displayed alongside

Implementation: `backend/app/services/generator.py`, `backend/app/api/routes_generate.py`, `backend/app/models/generation.py`, `backend/app/schemas/generate.py`

Tests: `backend/tests/test_generator.py`, `backend/tests/test_api_integration.py`

### validate-workflow — IaC Validation & Linting Workflow

Status: done

Acceptance:
- POST /api/validate for Terraform/CloudFormation/ARM
- Returns syntax errors, best-practice warnings, missing required fields

Implementation: `backend/app/services/validator.py`, `backend/app/api/routes_validate.py`, `backend/app/schemas/validate.py`

Tests: `backend/tests/test_validator.py`, `backend/tests/test_api_integration.py`

### estimate-workflow — Cost Estimation Workflow

Status: done

Acceptance:
- POST /api/estimate from template or component list
- Returns monthly cost breakdown by resource and region

Implementation: `backend/app/services/cost_estimator.py`, `backend/app/api/routes_estimate.py`, `backend/app/schemas/estimate.py`

Tests: `backend/tests/test_cost_estimator.py`, `backend/tests/test_api_integration.py`

### llm-adapters — Multi-Provider LLM Adapters

Status: in_progress

Acceptance:
- OpenAI-compatible, Anthropic, Gemini, Ollama adapters in services/llm.py
- Configurable via LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL
- Deterministic offline core works without LLM key
- Keys only server-side, bounded timeouts, redacted errors

Implementation: `backend/app/services/llm.py`

Tests: `backend/tests/test_generator.py (offline path via use_llm=False)`

### auth-sso — Authentication, RBAC and SAML Brokering

Status: in_progress

Acceptance:
- local JWT login with HttpOnly cookie + CSRF endpoint
- viewer/operator/admin roles enforced on data endpoints
- role denial and unauthenticated rejection tests
- Keycloak OIDC + SAML identity brokering (planned)

Implementation: `backend/app/core/security.py`, `backend/app/core/config.py`, `backend/app/api/routes_auth.py`

Tests: `backend/tests/test_auth.py`

### frontend — React + TypeScript Vite Dashboard

Status: planned

Acceptance:
- Typed API client derived from backend routes
- Generate form, template display, cost panel, validation panel, dashboard
- Loading/error/empty states; create/import/search/detail/export workflows
- vitest frontend tests (>=3)

