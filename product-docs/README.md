# Data Center Investments Agent

An AI-powered investment analysis agent focused on the data center sector, deployed to **AWS Bedrock Agents** (Agent Core). The agent integrates **Moody's** credit risk analytics, leverages **Workato** for enterprise data pipelines, and uses **Arize** for LLM observability.

## Problem

Investment professionals analyzing the data center sector must manually aggregate credit ratings, financial metrics, market dynamics, and ESG data from disparate sources. This process is slow, error-prone, and does not scale across the rapidly growing universe of data center operators and REITs.

## Solution

A multi-agent system that provides natural language access to comprehensive data center investment intelligence:

- **Credit Risk Analysis** — Moody's ratings, probability of default, leverage ratios
- **Market Analytics** — Supply/demand by geography, pricing trends, construction pipeline
- **ESG Assessment** — PUE efficiency, carbon intensity, renewable energy, climate risk
- **Portfolio Risk** — Aggregated exposure, concentration analysis, watch-list alerts
- **Report Generation** — Automated investment memos and comparison reports

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Runtime | AWS Bedrock Agents, Python 3.12+, Lambda |
| LLM | Mistral Large 2 (reasoning), Mistral Small (fast), Titan Embeddings v2 |
| RAG | Bedrock Knowledge Bases, OpenSearch Serverless |
| Data | S3, DynamoDB, Aurora PostgreSQL |
| Integration | Workato (iPaaS), API Gateway |
| Observability | Arize (LLM), CloudWatch (infra), X-Ray (tracing) |
| Security | IAM, Secrets Manager, KMS, VPC, Bedrock Guardrails |
| IaC / CI/CD | AWS CDK (Python), CodePipeline |

## Documentation

- [Product Requirements (PRD)](./PRD.md) — Functional and non-functional requirements, user stories, success criteria
- [Technical Specification](./TECHNICAL_SPEC.md) — Architecture, multi-agent design, API specs, infrastructure
- [Data Model](./DATA_MODEL.md) — Type definitions, mock data, DynamoDB schemas, validation rules

## Architecture

```
┌──────────────┐     ┌──────────────────────────────────────┐
│   Analyst    │────▶│  API Gateway (REST / WebSocket)      │
│   (Chat UI)  │     └──────────────┬───────────────────────┘
└──────────────┘                    │
                     ┌──────────────▼───────────────────────┐
                     │      Supervisor Agent (Bedrock)       │
                     │   Routes to specialist sub-agents     │
                     └──┬──────────┬──────────┬─────────────┘
                        │          │          │
               ┌────────▼──┐ ┌────▼─────┐ ┌──▼──────────┐
               │  Credit   │ │  Market  │ │    ESG      │
               │  Risk     │ │ Analytics│ │    Risk     │
               │  Agent    │ │  Agent   │ │    Agent    │
               └─────┬─────┘ └────┬─────┘ └──────┬──────┘
                     │            │               │
          ┌──────────▼────────────▼───────────────▼──────┐
          │              Data Layer                       │
          │  Moody's (Workato) │ S3 │ DynamoDB │ Aurora  │
          └──────────────────────────────────────────────┘
                     │
          ┌──────────▼───────────────────────────────────┐
          │           Observability                      │
          │      Arize │ CloudWatch │ X-Ray              │
          └──────────────────────────────────────────────┘
```

## Getting Started

```bash
# Prerequisites: AWS CLI configured, CDK installed, Python 3.12+
cd infrastructure
pip install -r requirements.txt
cdk bootstrap
cdk deploy --all
```

## Status

**Phase:** Requirements Complete — Ready for Development
