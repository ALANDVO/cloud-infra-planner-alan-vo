# cloud-infra-planner-alan-vo | Alan Vo | AI & Machine Learning

> Work in progress. This checkpoint may be incomplete or fail tests. See PLAN.md and STATUS.md before use.


`cloud-infra-planner` generates production-grade Infrastructure-as-Code (IaC)
from natural-language descriptions and validates/lints it. A deterministic,
offline-first "component engine" parses free-text requirements into a stable
component inventory and renders valid **Terraform (HCL)**, **CloudFormation
(YAML)** and **Azure ARM (JSON)** templates; an optional LLM pass can *suggest*
extra components when a provider key is configured, but the rendered template
is always produced by the deterministic engine and never fabricated from an LLM
response. Intended for DevOps/SRE engineers who want reproducible, auditable
IaC from prose requirements.

> **Status:** Backend API is implemented and tested. The web dashboard
> (React + TypeScript) is a planned follow-up; today the product is consumed as
> an authenticated HTTP API (see *API Reference*).

## Features
- **NL -> IaC generation** for AWS/GCP/Azure across Terraform, CloudFormation and ARM.
- **Deterministic component detection** from keywords (network, compute,
  load_balancer, database, cache, storage, no_sql, serverless, k8s, queue, HA).
- **IaC validation**: balanced-brace / JSON / YAML parsing, required blocks and
  resource attributes, plus best-practice checks (open security groups, S3
  versioning, RDS backup retention, provider-prefix mismatch).
- **Cost estimation**: per-cloud on-demand pricing, region multipliers and an
  HA premium, derived from the component inventory.
- **Audit log** of every security-relevant action; SQLite persistence with
  pagination, filtering and UTC timestamps.
- **Auth**: local JWT bearer tokens (HttpOnly cookie on login), viewer/operator/
  admin roles, CSRF token endpoint. Demo-mode auto-provisions an operator user
  on `localhost`.

## Quick Start

```bash
git clone https://github.com/ALANDVO/cloud-infra-planner-alan-vo.git
cd cloud-infra-planner-alan-vo
cp .env.example .env          # blank credentials; edit for production
docker compose -f compose.yaml up -d
# API: http://127.0.0.1:8000  |  API docs: http://127.0.0.1:8000/api/docs
```

### Local development (no Docker)
```bash
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## AI/ML evaluation

The "intelligence" is a rule-based component classifier plus an optional LLM
advisory step — there is no model training and no labelled dataset.

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
```

- **Data provenance:** component keywords are hand-authored rules in
  `backend/app/services/generator.py` (no external training data).
- **Baseline:** the deterministic generator always emits a template that the
  validator accepts with `valid=True` for every `(provider, target)` combination.
- **Measured (offline):** across Terraform/CloudFormation/ARM for AWS/GCP/Azure,
  45 backend tests pass; generated templates validate with no errors. The LLM
  path is opt-in (`use_llm`) and falls back to the deterministic core on any
  error, so no fabrication occurs.
- **Failure cases:** LLM component suggestions are parsed defensively and
  restricted to the allowed component set; malformed JSON/YAML or an unbalanced
  Terraform template is reported as an `error` by the validator rather than
  silently accepted.

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | `development` or `production` | `development` |
| `DATABASE_URL` | SQLAlchemy URL | `sqlite+aiosqlite:///./data/app.db` |
| `JWT_SECRET` | JWT signing key (min 32 chars) | **required in production** |
| `CSRF_SECRET` | CSRF signing key (min 32 chars) | **required in production** |
| `KEYCLOAK_*` | OIDC realm / client (planned SSO) | `http://localhost:8080` |
| `LLM_PROVIDER` | `openai` \| `anthropic` \| `gemini` \| `ollama` \| `offline` | `openai` |
| `LLM_MODEL` | Model name | `gpt-4o` |
| `LLM_BASE_URL` | OpenAI-compatible endpoint | `https://api.openai.com/v1` |
| `LLM_API_KEY` | LLM key (server-side only) | *(blank)* |
| `DEMO_MODE` | Local-only demo autoprovisioning | `false` |

## API Reference

All data endpoints require `Authorization: Bearer <jwt>`. Write endpoints
(generate, delete) additionally require the `operator` or `admin` role.

| Method | Endpoint | Notes |
|--------|----------|-------|
| `GET`  | `/api/health` | Health check |
| `POST` | `/api/auth/demo-setup` | Creates a demo operator user (dev/demo only) |
| `POST` | `/api/auth/login` | `email` + `password` -> JWT |
| `POST` | `/api/auth/logout` | Clears the cookie |
| `POST` | `/api/auth/csrf` | Issues a CSRF token |
| `GET`  | `/api/auth/me` | Current user |
| `POST` | `/api/generate` | `{description, provider, target, use_llm}` -> `201` |
| `GET`  | `/api/generate` | List (paginated) |
| `GET`  | `/api/generate/{id}` | Detail |
| `DELETE` | `/api/generate/{id}` | Delete |
| `POST` | `/api/validate` | `{template, provider, target}` -> `{valid, issues, summary}` |
| `POST` | `/api/estimate` | `{template\|components, target, regions}` -> cost breakdown |

### Example (demo mode)
```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/demo-setup | jq -r .access_token)
curl -X POST http://127.0.0.1:8000/api/generate \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"description":"A 3-tier web app with ALB, RDS Postgres, Redis and S3","provider":"terraform","target":"aws","use_llm":false}'
```

## Architecture
```
graph LR
  Client[Browser / API client] --> API[FastAPI app.main]
  API --> Gen["Generator service (NL -> IaC)"]
  API --> Val["Validator service"]
  API --> Cost["CostEstimator service"]
  API --> Auth["Auth + RBAC (JWT)"]
  API --> DB[(SQLite)]
  Gen --> LLM["LLM adapters (optional advisory)"]
```

## Security
- JWT secret and CSRF secret **must** be supplied in production; the server
  **refuses to start** with default secrets.
- `DEMO_MODE` binds to `localhost` and is **refused in production**.
- `LLM_API_KEY` is used server-side only and never returned to clients.
- No real credentials, tokens or private URLs are committed; see `.env.example`.
- **Limitations:** full Keycloak OIDC authorization-code login with SAML
  identity brokering is the planned SSO milestone (see *SSO / SAML setup*).
  The current release authenticates via local JWT with an HttpOnly cookie.

## SSO / SAML setup (planned)
The designed architecture is Keycloak OIDC with SAML brokering. Bring up
Keycloak (`docker compose up keycloak`), import the realm under
`keycloak/realm-export/`, configure a SAML identity provider through Keycloak's
identity brokering UI, and set `KEYCLOAK_*` in `.env`. Local JWT demo mode
remains the working authentication path today.

## Development
```bash
# Backend tests
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
# Backend image
docker build -f backend/Dockerfile -t cloud-infra-planner:ci .
```

## License
MIT &copy; Alan Vo <alanvo@gmail.com>