# cloud-infra-planner-alan-vo

> Generates production-grade Terraform, CloudFormation, or ARM templates from natural language descriptions, with validation, cost estimation, and module composition.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-React-3178C6)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)
![SSO](https://img.shields.io/badge/SSO-SAML%20%2F%20OAuth2-8A2BE2)
![License](https://img.shields.io/badge/License-MIT-green)
![AI](https://img.shields.io/badge/AI-Powered-purple)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

</div>

## Why cloud-infra-planner-alan-vo?

Generates production-grade Terraform, CloudFormation, or ARM templates from natural language descriptions, with validation, cost estimation, and module composition.

Built by [Alan Vo](https://github.com/ALANDVO) — AI/ML & cybersecurity engineer.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     cloud-infra-planner-alan-vo                                    │
├─────────────┬─────────────┬─────────────┬───────────────────┤
│  Frontend   │   API Layer │  Services   │   LLM Engine      │
│  React/TS   │  FastAPI    │  Domain     │  Multi-provider   │
│  Dashboard  │  SSO/SAML   │  Logic      │  OpenAI/Claude/   │
│  Real-time  │  JWT Auth   │  Processing │  Gemini/Ollama    │
└─────────────┴─────────────┴─────────────┴───────────────────┘
         │              │              │               │
         ▼              ▼              ▼               ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────┐
    │ Browser │   │  REST   │   │  Domain │   │  LLM API    │
    │  SPA    │   │  API    │   │  Logic  │   │  (any)      │
    └─────────┘   └─────────┘   └─────────┘   └─────────────┘
```

## Features

- **Natural language → Terraform HCL for AWS, GCP, Azure**
- **Natural language → CloudFormation YAML and Azure ARM templates**
- **Architecture pattern detection: web app, API, data pipeline, serverless, microservices**
- **Cost estimation from generated resource inventory**
- **Multi-region and high-availability configuration from NL requirements**
- **Terraform module composition for reusable infrastructure blocks**
- **Validation and linting of generated IaC before apply**

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/ALANDVO/cloud-infra-planner-alan-vo.git
cd cloud-infra-planner-alan-vo
cp .env.example .env
docker compose up -d
# Open http://localhost:3000
```

### Local Development

```bash
git clone https://github.com/ALANDVO/cloud-infra-planner-alan-vo.git
cd cloud-infra-planner-alan-vo
pip install -r requirements.txt
```

## Usage

```
python main.py generate "A highly available 3-tier web app with ALB, 2 ASG instances, RDS Postgres, and ElastiCache" --provider terraform --target aws
python main.py generate "Serverless API with Lambda, API Gateway, DynamoDB, and S3" --provider terraform --target aws --output main.tf
python main.py generate "GCP: Cloud Run service with Cloud SQL and Memorystore" --provider terraform --target gcp
python main.py generate "Azure: AKS cluster with 3 nodes and ACR" --provider arm --target azure
python main.py validate main.tf --target aws
python main.py estimate main.tf
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | LLM API key (OpenAI, Anthropic, Gemini) | Required |
| `LLM_BASE_URL` | Custom LLM endpoint (Ollama, vLLM) | `https://api.openai.com/v1` |
| `LLM_MODEL` | Model name | `gpt-4o` |
| `SAML_IDP_ENTITY` | SAML Identity Provider URL | — |
| `JWT_SECRET` | JWT signing secret | Generate one |

## Tech Stack

`Python` `Terraform` `CloudFormation` `AWS` `GCP` `Azure` `IaC` `LLM`

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Login (SSO or email) |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/stats` | Statistics & metrics |
| `POST` | `/api/process` | Main processing endpoint |
| `GET` | `/api/results` | Query results |

## SSO Setup

### SAML
1. Set `SAML_IDP_ENTITY` to your IdP URL
2. Set `SAML_IDP_CERT` to your IdP certificate
3. Set `SAML_ACS_URL` to `https://yourdomain.com/saml/acs`

### OAuth2
1. Register your app with the OAuth provider
2. Set `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET`
3. Set `OAUTH_REDIRECT_URI`

## License

MIT — see [LICENSE](LICENSE)

---

**Built by [Alan Vo](https://github.com/ALANDVO)** | alanvo@gmail.com | AI, ML & Cybersecurity


