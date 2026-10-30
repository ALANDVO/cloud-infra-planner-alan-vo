# Changelog

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project are documented here. The format is
[Keep a Changelog](https://keepachangelog.com/) and this project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **React + TypeScript Vite frontend** (`frontend/`) with a complete dashboard for the three core workflows:
  - **Generate**: Natural language form with provider/target selection and optional LLM advisory
  - **History**: Paginated, filterable list of all generations with view/download/delete actions
  - **Detail**: Full template view with syntax highlighting, validation panel, and cost estimation sidebar
  - **Settings**: Profile, permissions, security, notifications, appearance
- Typed API client (`frontend/src/api/client.ts`) derived from backend OpenAPI contracts
- Syntax highlighting via `react-syntax-highlighter` for Terraform/CloudFormation/ARM templates
- Responsive professional UI with loading/error/empty states throughout
- 17 vitest unit tests covering GenerateForm, TemplateDisplay, and API client
- Dockerfile and nginx config for production frontend serving
- Added frontend to CI workflow (build + test)

### Changed
- Updated `compose.yaml` to include frontend service with reverse proxy to backend
- Updated README with frontend quickstart and architecture diagram

### Fixed
- Removed legacy `main.py` and `llm_client.py` from root
- Fixed TypeScript strict mode compliance across frontend codebase
## [1.0.0] - 2026-10-14
### Added
- FastAPI backend with modular structure: `app/`, `api/`, `services/`, `models/`,
  `core/`, `schemas/` and a `create_app()` factory.
- Deterministic NL -> IaC **Generator** service (`services/generator.py`): renders
  valid Terraform (HCL), CloudFormation (YAML) and ARM (JSON) templates from
  keyword-detected infrastructure components. Works fully offline; an optional,
  grounded LLM pass can suggest extra components when an `LLM_API_KEY` is
  configured (safe fallback to the deterministic core on any error).
- IaC **Validator** service (`services/validator.py`): structural validation
  (balanced braces / JSON / YAML parsing, required blocks and resource
  attributes) plus best-practice checks (open security groups, S3 without
  versioning, RDS without backup retention, provider-prefix mismatch).
- **Cost Estimator** service with per-cloud pricing, region multipliers and an
  HA premium.
- JWT bearer-token auth: `POST /api/auth/login`, `/api/auth/logout`,
  `/api/auth/me`, `/api/auth/csrf`, `/api/auth/demo-setup`, `GET /api/health`.
- Role-based authorization: the generate (create/delete) endpoints require
  `operator`/`admin`; read endpoints require an authenticated viewer.
- Audit logging for all security-relevant actions.
- SQLite persistence (SQLAlchemy async) with pagination, filtering and UTC
  timestamps.
- Backend `Dockerfile` (non-root) and `compose.yaml` (backend + Keycloak, ports
  bound to 127.0.0.1) with persistent volumes and healthchecks.
- `pyproject.toml` project metadata and `.github/workflows/ci.yml` (backend
  pytest + backend image build on `ubuntu-latest`).
- Comprehensive backend test suite covering the generator, validator, cost
  estimator, auth/role denial and the end-to-end generate -> validate -> estimate
  HTTP workflows.

### Known limitations (planned / not yet implemented)
- Frontend (React + TypeScript + Vite) is not yet built; the API is the current
  interface. Tracked under the `frontend` feature.
- Keycloak OIDC authorization-code login (state + nonce + PKCE) is the intended
  SSO architecture but is not yet wired into the auth flow; the app currently
  authenticates via local JWT (demo mode on `localhost`).
- SAML identity brokering is documented as a future milestone.
- LLM providers (Anthropic, Gemini, Ollama) are plumbed through adapters but not
  exercised in CI; all network LLM calls are mocked/unused offline.

### Security
- JWT secret, CSRF secret and `LLM_API_KEY` MUST be supplied via environment in
  production; the app refuses to boot in production with default secrets.
- Demo mode binds to localhost and is refused in production.
- No real credentials, tokens or private URLs are committed.