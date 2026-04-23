# Data Center Investments Agent — Implementation Plan

**Version:** 1.0.0
**Status:** Ready for Review
**Last Updated:** 2025-07-14
**Estimated Total Effort:** ~18–22 working days

---

## Table of Contents

- [Phase 1: Infrastructure Foundation (CDK)](#phase-1-infrastructure-foundation-cdk)
- [Phase 2: Mock Services Layer](#phase-2-mock-services-layer)
- [Phase 3: Data Layer & Mock Data Seeding](#phase-3-data-layer--mock-data-seeding)
- [Phase 4: Agent Lambda Functions (Action Groups)](#phase-4-agent-lambda-functions-action-groups)
- [Phase 5: Bedrock Agent Configuration](#phase-5-bedrock-agent-configuration)
- [Phase 6: Frontend Chat Application](#phase-6-frontend-chat-application)
- [Phase 7: Integration & Demo](#phase-7-integration--demo)
- [Risk Register](#risk-register)
- [Dependency Graph](#dependency-graph)

---

## Project Root Structure

```
aws-coder-agentic-ai-showcase/
├── cdk/                          # AWS CDK infrastructure (Python)
│   ├── app.py
│   ├── cdk.json
│   ├── requirements.txt
│   └── stacks/
│       ├── __init__.py
│       ├── data_stack.py         # DynamoDB, S3
│       ├── api_stack.py          # API Gateway, Lambda integrations
│       ├── agent_stack.py        # Bedrock Agent, KB, Guardrails
│       └── frontend_stack.py     # S3 hosting, CloudFront
├── lambda/
│   ├── action_groups/            # Bedrock Agent action group handlers
│   │   ├── handlers/
│   │   │   ├── credit_rating.py
│   │   │   ├── financial_metrics.py
│   │   │   ├── market_data.py
│   │   │   ├── esg_risk.py
│   │   │   ├── generate_report.py
│   │   │   └── sync_moodys.py
│   │   ├── shared/
│   │   │   ├── __init__.py
│   │   │   ├── db.py
│   │   │   ├── arize_trace.py
│   │   │   └── models.py
│   │   └── requirements.txt
│   ├── mock_workato/             # Workato mock service
│   │   ├── handler.py
│   │   ├── recipes.py
│   │   ├── webhooks.py
│   │   └── requirements.txt
│   ├── mock_arize/               # Arize mock service
│   │   ├── handler.py
│   │   ├── traces.py
│   │   ├── evaluations.py
│   │   ├── metrics.py
│   │   └── requirements.txt
│   └── seed/                     # Data seeding scripts
│       ├── seed_dynamodb.py
│       ├── seed_s3.py
│       └── mock_data/
│           ├── operators.json
│           ├── metrics.json
│           ├── markets.json
│           ├── esg_profiles.json
│           ├── credit_ratings.json
│           └── sessions.json
├── schemas/                      # OpenAPI specs for Action Groups
│   ├── credit_rating_api.yaml
│   ├── financial_metrics_api.yaml
│   ├── market_data_api.yaml
│   ├── esg_risk_api.yaml
│   ├── generate_report_api.yaml
│   └── sync_moodys_api.yaml
├── prompts/                      # Agent system prompts
│   ├── supervisor_system.txt
│   ├── credit_risk_system.txt
│   ├── market_analytics_system.txt
│   └── esg_risk_system.txt
├── frontend/                     # React SPA
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── public/
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts
│       ├── components/
│       │   ├── Chat/
│       │   │   ├── ChatPanel.tsx
│       │   │   ├── MessageBubble.tsx
│       │   │   ├── MessageInput.tsx
│       │   │   ├── FeedbackButtons.tsx
│       │   │   └── SourceAttribution.tsx
│       │   ├── Dashboard/
│       │   │   ├── PortfolioDashboard.tsx
│       │   │   ├── RiskSummary.tsx
│       │   │   └── AlertFeed.tsx
│       │   ├── Watchlist/
│       │   │   └── WatchlistSidebar.tsx
│       │   ├── Observability/
│       │   │   ├── ArizePanel.tsx
│       │   │   └── WorkatoPanel.tsx
│       │   └── Layout/
│       │       ├── AppShell.tsx
│       │       └── NavBar.tsx
│       ├── hooks/
│       │   ├── useChat.ts
│       │   └── usePortfolio.ts
│       ├── types/
│       │   └── index.ts
│       └── styles/
│           └── globals.css
├── knowledge_base_docs/          # Source docs for Bedrock KB
│   ├── moodys/
│   │   ├── equinix_rating_report.md
│   │   ├── dlr_rating_report.md
│   │   ├── qts_rating_report.md
│   │   ├── cyrusone_rating_report.md
│   │   ├── coresite_rating_report.md
│   │   └── switch_rating_report.md
│   ├── market/
│   │   ├── nova_market_report.md
│   │   ├── dfw_market_report.md
│   │   └── apac_market_report.md
│   └── esg/
│       ├── esg_methodology.md
│       └── climate_risk_framework.md
├── tests/
│   ├── unit/
│   │   ├── test_credit_rating.py
│   │   ├── test_financial_metrics.py
│   │   ├── test_mock_workato.py
│   │   └── test_mock_arize.py
│   └── integration/
│       ├── test_agent_e2e.py
│       └── test_api_gateway.py
├── docs/
│   └── IMPLEMENTATION_PLAN.md    # This file
├── product-docs/
│   ├── PRD.md
│   ├── TECHNICAL_SPEC.md
│   └── DATA_MODEL.md
└── README.md
```

---

## Phase 1: Infrastructure Foundation (CDK)

**Goal:** Stand up all AWS resources required by subsequent phases.
**Estimated Duration:** 3–4 days

### Success Criteria
- `cdk deploy --all` completes without errors
- All DynamoDB tables exist with correct key schemas and GSIs
- All S3 buckets exist with lifecycle policies
- API Gateway deployed with placeholder integrations returning 200
- IAM roles created with least-privilege policies

### Tasks

| # | Task | File(s) | Effort | Depends On |
|---|------|---------|--------|------------|
| 1.1 | Initialize CDK Python project with `cdk init app --language python` | `cdk/app.py`, `cdk/cdk.json`, `cdk/requirements.txt` | S | — |
| 1.2 | Create `DataStack` — DynamoDB tables: `dcai-sessions`, `dcai-operators`, `dcai-metrics`, `dcai-esg-profiles`, `dcai-market-data`, `dcai-traces` | `cdk/stacks/data_stack.py` | M | 1.1 |
| 1.3 | Create `DataStack` — S3 buckets: `dcai-data-lake-{account}`, `dcai-kb-docs-{account}`, `dcai-reports-{account}` with versioning, encryption (SSE-S3), and lifecycle rules (IA after 90d, Glacier after 365d) | `cdk/stacks/data_stack.py` | S | 1.1 |
| 1.4 | Create `ApiStack` — REST API Gateway with resource tree for: `/v1/query`, `/v1/sessions/{id}`, `/v1/reports/generate`, `/v1/health`, `/mock/workato/*`, `/mock/arize/*` | `cdk/stacks/api_stack.py` | M | 1.1 |
| 1.5 | Create IAM roles: `BedrockAgentRole`, `ActionGroupLambdaRole`, `MockServiceLambdaRole`, `KBIngestionRole` | `cdk/stacks/api_stack.py` (inline) | M | 1.1 |
| 1.6 | Create `AgentStack` — placeholder Bedrock Agent, Knowledge Base, and Guardrail resources (L1 constructs via `CfnAgent`) | `cdk/stacks/agent_stack.py` | M | 1.2, 1.3 |
| 1.7 | Create `FrontendStack` — S3 bucket for static hosting + CloudFront distribution with OAI | `cdk/stacks/frontend_stack.py` | S | 1.1 |
| 1.8 | Wire stacks in `app.py` with cross-stack references | `cdk/app.py` | S | 1.2–1.7 |
| 1.9 | Validate: `cdk synth`, `cdk diff`, `cdk deploy --all` | — | S | 1.8 |

### DynamoDB Table Specifications

| Table | PK (HASH) | SK (RANGE) | GSI | TTL Field |
|-------|-----------|-----------|-----|-----------|
| `dcai-sessions` | `session_id` (S) | — | `user-index`: PK=`user_id`, SK=`created_at` | `expires_at` |
| `dcai-operators` | `id` (S) | — | `rating-index`: PK=`moodys_rating`, SK=`name` | — |
| `dcai-metrics` | `operator_id` (S) | `period` (S) | `period-index`: PK=`period`, SK=`operator_id` | — |
| `dcai-esg-profiles` | `operator_id` (S) | — | — | — |
| `dcai-market-data` | `market_id` (S) | — | `region-index`: PK=`region`, SK=`market_name` | — |
| `dcai-traces` | `trace_id` (S) | — | `session-index`: PK=`session_id`, SK=`trace_id` | `expires_at` |

### S3 Bucket Specifications

| Bucket | Purpose | Versioning | Encryption | Lifecycle |
|--------|---------|-----------|-----------|-----------|
| `dcai-data-lake-{account}` | Raw Moody's data, Parquet files | Enabled | SSE-S3 | IA @ 90d, Glacier @ 365d |
| `dcai-kb-docs-{account}` | Knowledge Base source documents (Markdown, PDF) | Enabled | SSE-S3 | — |
| `dcai-reports-{account}` | Generated reports (PDF, MD) | Enabled | SSE-S3 | Expire @ 90d |

---

## Phase 2: Mock Services Layer

**Goal:** Provide fully functional Workato and Arize mock APIs so the agent and frontend can operate without real third-party accounts.
**Estimated Duration:** 3–4 days

### Success Criteria
- All mock endpoints return realistic JSON payloads
- Workato mock simulates recipe trigger → status polling lifecycle (PENDING → RUNNING → COMPLETED)
- Arize mock stores traces in DynamoDB and serves dashboard metrics
- CloudWatch custom metrics published by Arize mock (latency, token counts)
- All endpoints callable via `curl` through API Gateway

### 2A: Workato Mock Service

Lambda functions behind API Gateway that simulate Workato recipe orchestration.

#### Endpoints

| Method | Path | Description | Response Shape |
|--------|------|-------------|---------------|
| `POST` | `/mock/workato/recipes/{recipe_id}/trigger` | Trigger a recipe run; returns `run_id` and status `PENDING` | `{ "run_id": str, "recipe_id": str, "status": "PENDING", "started_at": str }` |
| `GET` | `/mock/workato/recipes/{recipe_id}/status` | Poll recipe status; cycles through `PENDING` → `RUNNING` → `COMPLETED` based on elapsed time | `{ "run_id": str, "status": str, "progress_pct": int, "output": {...} }` |
| `POST` | `/mock/workato/webhooks/moodys-rating-action` | Simulate incoming Moody's webhook; writes event to DynamoDB and returns ack | `{ "event_id": str, "received": true, "processed_at": str }` |
| `GET` | `/mock/workato/connections` | List mock connections (Moody's, S3, EventBridge) with health status | `{ "connections": [{ "id": str, "name": str, "provider": str, "status": "active" }] }` |

#### Tasks

| # | Task | File(s) | Effort | Depends On |
|---|------|---------|--------|------------|
| 2.1 | Implement Workato recipe trigger + status Lambda handler | `lambda/mock_workato/handler.py`, `lambda/mock_workato/recipes.py` | M | 1.4 |
| 2.2 | Implement Workato webhook receiver (Moody's rating action) | `lambda/mock_workato/webhooks.py` | S | 1.2, 1.4 |
| 2.3 | Implement connections list endpoint | `lambda/mock_workato/handler.py` | S | 1.4 |
| 2.4 | Add API Gateway routes for `/mock/workato/*` with Lambda proxy integration in CDK | `cdk/stacks/api_stack.py` | S | 1.4, 2.1 |
| 2.5 | Create `requirements.txt` for mock_workato Lambda layer | `lambda/mock_workato/requirements.txt` | S | — |
| 2.6 | Unit tests for Workato mock | `tests/unit/test_mock_workato.py` | S | 2.1–2.3 |

#### Workato Mock — Realistic Response Examples

**POST `/mock/workato/recipes/{recipe_id}/trigger`**
```json
{
  "run_id": "run-a1b2c3d4",
  "recipe_id": "recipe-moodys-sync-001",
  "status": "PENDING",
  "started_at": "2025-07-14T10:00:00Z",
  "recipe_name": "Moody's Daily Rating Sync",
  "trigger_type": "on_demand",
  "steps_total": 4,
  "steps_completed": 0
}
```

**GET `/mock/workato/recipes/{recipe_id}/status`**
```json
{
  "run_id": "run-a1b2c3d4",
  "recipe_id": "recipe-moodys-sync-001",
  "status": "COMPLETED",
  "progress_pct": 100,
  "started_at": "2025-07-14T10:00:00Z",
  "completed_at": "2025-07-14T10:00:12Z",
  "output": {
    "records_processed": 6,
    "records_failed": 0,
    "s3_path": "s3://dcai-data-lake/moodys/ratings/2025-07-14/actions.json"
  },
  "steps": [
    { "name": "moodys_api.get_rating_actions", "status": "completed", "duration_ms": 2300 },
    { "name": "transform.map_fields",          "status": "completed", "duration_ms": 150 },
    { "name": "aws_s3.upload_object",           "status": "completed", "duration_ms": 890 },
    { "name": "aws_eventbridge.put_event",      "status": "completed", "duration_ms": 210 }
  ]
}
```

**POST `/mock/workato/webhooks/moodys-rating-action`**
```json
{
  "event_id": "evt-moodys-20250714-001",
  "received": true,
  "processed_at": "2025-07-14T10:05:00Z",
  "payload_summary": {
    "issuer": "Digital Realty Trust",
    "action_type": "outlook_change",
    "new_outlook": "POS",
    "previous_outlook": "STA"
  }
}
```

**GET `/mock/workato/connections`**
```json
{
  "connections": [
    { "id": "conn-001", "name": "Moody's CreditView API", "provider": "moodys_creditview", "status": "active", "last_used": "2025-07-14T09:55:00Z" },
    { "id": "conn-002", "name": "AWS S3 Data Lake",       "provider": "aws_s3",             "status": "active", "last_used": "2025-07-14T10:00:12Z" },
    { "id": "conn-003", "name": "AWS EventBridge",        "provider": "aws_eventbridge",    "status": "active", "last_used": "2025-07-14T10:00:12Z" },
    { "id": "conn-004", "name": "Slack #dc-credit-alerts","provider": "slack",              "status": "active", "last_used": "2025-07-13T16:30:00Z" }
  ]
}
```

### 2B: Arize Mock Service

Lambda functions behind API Gateway that simulate Arize LLM observability platform.

#### Endpoints

| Method | Path | Description | Response Shape |
|--------|------|-------------|---------------|
| `POST` | `/mock/arize/traces` | Ingest one or more LLM trace spans; stores to `dcai-traces` DynamoDB table | `{ "trace_id": str, "span_count": int, "ingested_at": str }` |
| `GET` | `/mock/arize/traces/{trace_id}` | Retrieve full trace with all spans | `{ "trace_id": str, "spans": [...], "total_latency_ms": int }` |
| `GET` | `/mock/arize/evaluations` | Return evaluation results (relevance, faithfulness, toxicity) | `{ "evaluations": [{ "name": str, "score": float, "threshold": float }] }` |
| `GET` | `/mock/arize/metrics` | Aggregated metrics: latency p50/p95, token counts, accuracy, cost | `{ "latency_p50_ms": int, "latency_p95_ms": int, ... }` |
| `GET` | `/mock/arize/dashboard` | Dashboard summary: trace volume, error rate, eval scores, top agents | `{ "summary": {...}, "agents": [...], "recent_traces": [...] }` |

#### Tasks

| # | Task | File(s) | Effort | Depends On |
|---|------|---------|--------|------------|
| 2.7 | Implement trace ingest handler — validate spans, write to `dcai-traces`, publish CloudWatch custom metrics (`DCInvestAgent/TraceLanency`, `DCInvestAgent/TokenCount`) | `lambda/mock_arize/handler.py`, `lambda/mock_arize/traces.py` | M | 1.2, 1.4 |
| 2.8 | Implement trace retrieval handler — query by `trace_id`, reconstruct span tree | `lambda/mock_arize/traces.py` | S | 2.7 |
| 2.9 | Implement evaluations endpoint — return deterministic mock eval scores with configurable jitter | `lambda/mock_arize/evaluations.py` | S | 1.4 |
| 2.10 | Implement metrics aggregation endpoint — compute p50/p95 latency from DynamoDB scan, aggregate token counts | `lambda/mock_arize/metrics.py` | M | 2.7 |
| 2.11 | Implement dashboard summary endpoint — combine metrics + recent traces + per-agent breakdown | `lambda/mock_arize/handler.py` | S | 2.9, 2.10 |
| 2.12 | Add API Gateway routes for `/mock/arize/*` with Lambda proxy integration in CDK | `cdk/stacks/api_stack.py` | S | 1.4, 2.7 |
| 2.13 | Create `requirements.txt` for mock_arize Lambda layer | `lambda/mock_arize/requirements.txt` | S | — |
| 2.14 | Unit tests for Arize mock | `tests/unit/test_mock_arize.py` | S | 2.7–2.11 |

#### Arize Mock — Realistic Response Examples

**POST `/mock/arize/traces`**
```json
{
  "trace_id": "tr-20250714-abc123",
  "span_count": 4,
  "ingested_at": "2025-07-14T10:02:00Z",
  "project": "dc-invest-agent"
}
```

**GET `/mock/arize/traces/{trace_id}`**
```json
{
  "trace_id": "tr-20250714-abc123",
  "session_id": "sess-001",
  "total_latency_ms": 4820,
  "total_tokens": 2150,
  "total_cost_usd": 0.0043,
  "spans": [
    {
      "span_id": "sp-001",
      "agent_name": "supervisor",
      "action": "classify_intent",
      "input": { "message": "Compare Equinix and Digital Realty leverage ratios" },
      "output": { "intent": "financial_comparison", "target_agent": "credit_risk" },
      "latency_ms": 320,
      "token_count": 185,
      "model": "mistral.mistral-large-2407-v1:0"
    },
    {
      "span_id": "sp-002",
      "agent_name": "credit_risk",
      "action": "GetFinancialMetrics",
      "input": { "entity_id": "op-001", "metrics": ["debt_to_ebitda"], "period": "trailing_4q" },
      "output": { "results": [{"period": "2024-Q1", "debt_to_ebitda": 3.8}, {"period": "2024-Q2", "debt_to_ebitda": 3.7}] },
      "latency_ms": 1850,
      "token_count": 820,
      "model": "mistral.mistral-large-2407-v1:0"
    }
  ]
}
```

**GET `/mock/arize/metrics`**
```json
{
  "period": "last_24h",
  "latency_p50_ms": 2400,
  "latency_p95_ms": 7800,
  "total_queries": 142,
  "total_tokens": 312000,
  "avg_tokens_per_query": 2197,
  "estimated_cost_usd": 0.62,
  "accuracy_score": 0.94,
  "faithfulness_score": 0.91,
  "relevance_score": 0.88,
  "error_rate": 0.02,
  "by_agent": {
    "supervisor": { "invocations": 142, "avg_latency_ms": 310 },
    "credit_risk": { "invocations": 85, "avg_latency_ms": 3200 },
    "market_analytics": { "invocations": 38, "avg_latency_ms": 2800 },
    "esg_risk": { "invocations": 19, "avg_latency_ms": 1500 }
  }
}
```

**GET `/mock/arize/dashboard`**
```json
{
  "summary": {
    "total_traces_24h": 142,
    "avg_latency_ms": 3100,
    "error_rate_pct": 2.1,
    "avg_faithfulness": 0.91,
    "avg_relevance": 0.88,
    "token_burn_rate_per_hour": 13000
  },
  "agents": [
    { "name": "credit_risk",      "call_share_pct": 59.9, "avg_latency_ms": 3200, "accuracy": 0.96 },
    { "name": "market_analytics",  "call_share_pct": 26.8, "avg_latency_ms": 2800, "accuracy": 0.93 },
    { "name": "esg_risk",          "call_share_pct": 13.4, "avg_latency_ms": 1500, "accuracy": 0.90 }
  ],
  "recent_traces": [
    { "trace_id": "tr-20250714-abc123", "query": "Compare EQIX and DLR leverage", "latency_ms": 4820, "status": "ok" },
    { "trace_id": "tr-20250714-def456", "query": "ESG risk for N. Virginia facilities", "latency_ms": 2100, "status": "ok" }
  ],
  "alerts": [
    { "type": "eval_regression", "message": "faithfulness dropped below 0.85 for 10min window", "ts": "2025-07-14T08:22:00Z", "resolved": true }
  ]
}
```

---

## Phase 3: Data Layer & Mock Data Seeding

**Goal:** Populate all DynamoDB tables with realistic mock data from DATA_MODEL.md and upload Knowledge Base source documents to S3.
**Estimated Duration:** 2 days

### Success Criteria
- All 6 DynamoDB tables populated with seeded data
- Knowledge Base S3 bucket contains Moody's reports, market reports, and ESG docs
- Seeding is idempotent (re-runnable without duplicates)
- All data passes validation rules from DATA_MODEL.md § 7

### Tasks

| # | Task | File(s) | Effort | Depends On |
|---|------|---------|--------|------------|
| 3.1 | Create JSON fixture files for all 6 operators (from DATA_MODEL.md § 2.1) | `lambda/seed/mock_data/operators.json` | S | — |
| 3.2 | Create JSON fixture for credit ratings (one per operator, include previous_rating and analyst) | `lambda/seed/mock_data/credit_ratings.json` | S | — |
| 3.3 | Create JSON fixture for financial metrics (Q1+Q2 2024 per operator = 12 records, from § 2.3) | `lambda/seed/mock_data/metrics.json` | S | — |
| 3.4 | Create JSON fixture for market data (5 markets, from § 2.2) | `lambda/seed/mock_data/markets.json` | S | — |
| 3.5 | Create JSON fixture for ESG profiles (6 operators, from § 2.4) | `lambda/seed/mock_data/esg_profiles.json` | S | — |
| 3.6 | Create JSON fixture for sample sessions and traces | `lambda/seed/mock_data/sessions.json` | S | — |
| 3.7 | Write DynamoDB seeding script — reads all fixture files, batch-writes to tables, validates against rules | `lambda/seed/seed_dynamodb.py` | M | 1.2, 3.1–3.6 |
| 3.8 | Write mock Moody's rating reports (6 Markdown files, ~500 words each) for Knowledge Base | `knowledge_base_docs/moodys/*.md` | M | — |
| 3.9 | Write mock market reports (3 Markdown files) for Knowledge Base | `knowledge_base_docs/market/*.md` | S | — |
| 3.10 | Write ESG methodology and climate risk framework docs for Knowledge Base | `knowledge_base_docs/esg/*.md` | S | — |
| 3.11 | Write S3 upload script — uploads all knowledge_base_docs to `dcai-kb-docs-{account}` | `lambda/seed/seed_s3.py` | S | 1.3, 3.8–3.10 |
| 3.12 | Create combined seeding entry point / Makefile target | `Makefile` or `scripts/seed_all.sh` | S | 3.7, 3.11 |

### Data Volume Summary

| Table | Record Count | Notes |
|-------|-------------|-------|
| `dcai-operators` | 6 | Equinix, DLR, QTS, CyrusOne, CoreSite, Switch |
| `dcai-metrics` | 12 | 2 quarters × 6 operators |
| `dcai-market-data` | 5 | N.VA, DFW, Phoenix, Singapore, Frankfurt |
| `dcai-esg-profiles` | 6 | One per operator |
| `dcai-sessions` | 3 | Sample conversation sessions for demo |
| `dcai-traces` | 10 | Sample trace records for Arize mock dashboard |

---

## Phase 4: Agent Lambda Functions (Action Groups)

**Goal:** Implement all 6 action group Lambda handlers that Bedrock Agents will invoke, plus shared utilities.
**Estimated Duration:** 4–5 days

### Success Criteria
- Each handler accepts Bedrock Agent Action Group event format and returns valid `messageVersion: "1.0"` response
- All handlers read from DynamoDB (not Aurora — MVP simplification)
- All handlers send trace data to Arize mock via HTTP POST
- `SyncMoodysData` successfully calls Workato mock trigger endpoint
- Unit tests pass for each handler

### Handler Specifications

Each handler follows this pattern:
```python
def handler(event, context):
    # 1. Parse Bedrock Agent Action Group event
    # 2. Extract parameters from event["parameters"] or event["requestBody"]
    # 3. Start Arize trace span
    # 4. Query DynamoDB for data
    # 5. Format response
    # 6. Close trace span with latency + token count
    # 7. Return Bedrock Agent response envelope
```

### Tasks

| # | Task | File(s) | Effort | Depends On |
|---|------|---------|--------|------------|
| 4.1 | Implement shared DynamoDB client utility — table name resolution from env vars, get/query/scan helpers | `lambda/action_groups/shared/db.py` | M | 1.2 |
| 4.2 | Implement shared Arize trace utility — HTTP client that POSTs spans to `/mock/arize/traces`, context manager for span lifecycle | `lambda/action_groups/shared/arize_trace.py` | M | 2.7 |
| 4.3 | Implement shared Pydantic/dataclass models — `CreditRatingResponse`, `FinancialMetricsResponse`, `MarketDataResponse`, `ESGRiskResponse`, `BedrockAgentResponse` | `lambda/action_groups/shared/models.py` | S | — |
| 4.4 | Implement `LookupCreditRating` handler — query `dcai-operators` for rating, outlook, watch_status; support `rating_type` filter; include Moody's attribution | `lambda/action_groups/handlers/credit_rating.py` | M | 4.1, 4.2, 4.3 |
| 4.5 | Implement `GetFinancialMetrics` handler — query `dcai-metrics` by operator_id + period range; support metric selection; compute trends | `lambda/action_groups/handlers/financial_metrics.py` | M | 4.1, 4.2, 4.3 |
| 4.6 | Implement `QueryMarketData` handler — query `dcai-market-data` by metro name or region; support metric_type filter | `lambda/action_groups/handlers/market_data.py` | M | 4.1, 4.2, 4.3 |
| 4.7 | Implement `AssessESGRisk` handler — query `dcai-esg-profiles` by operator_id; support dimension filtering (pue, carbon, water, etc.) | `lambda/action_groups/handlers/esg_risk.py` | M | 4.1, 4.2, 4.3 |
| 4.8 | Implement `GenerateReport` handler — aggregate data from multiple tables; format as Markdown; upload to `dcai-reports-{account}` S3 bucket; return presigned URL | `lambda/action_groups/handlers/generate_report.py` | L | 4.1, 4.2, 4.3, 1.3 |
| 4.9 | Implement `SyncMoodysData` handler — call Workato mock trigger endpoint, poll status, return sync result | `lambda/action_groups/handlers/sync_moodys.py` | M | 4.1, 4.2, 2.1 |
| 4.10 | Create OpenAPI schemas for all 6 action groups | `schemas/credit_rating_api.yaml`, `schemas/financial_metrics_api.yaml`, `schemas/market_data_api.yaml`, `schemas/esg_risk_api.yaml`, `schemas/generate_report_api.yaml`, `schemas/sync_moodys_api.yaml` | M | — |
| 4.11 | Create Lambda requirements.txt with dependencies | `lambda/action_groups/requirements.txt` | S | — |
| 4.12 | Unit tests for all handlers | `tests/unit/test_credit_rating.py`, `tests/unit/test_financial_metrics.py`, `tests/unit/test_market_data.py`, `tests/unit/test_esg_risk.py` | M | 4.4–4.9 |
| 4.13 | Add action group Lambdas to CDK with env vars and IAM permissions | `cdk/stacks/api_stack.py` | M | 4.4–4.9 |

### Shared Utility Interfaces

**`db.py`**
```python
def get_item(table_name: str, key: dict) -> dict | None
def query_items(table_name: str, key_condition: str, expr_values: dict, index: str = None) -> list[dict]
def scan_items(table_name: str, filter_expr: str = None) -> list[dict]
def put_item(table_name: str, item: dict) -> None
def batch_write(table_name: str, items: list[dict]) -> None
```

**`arize_trace.py`**
```python
class ArizeTracer:
    def __init__(self, agent_name: str, mock_endpoint: str)
    def start_span(self, action: str, input_data: dict) -> SpanContext
    def end_span(self, span: SpanContext, output_data: dict, token_count: int) -> None
    def flush(self) -> None
```

**`models.py`**
```python
@dataclass
class BedrockAgentResponse:
    action_group: str
    api_path: str
    http_method: str
    http_status_code: int
    body: dict
    def to_event(self) -> dict  # Returns Bedrock Agent response envelope
```

---

## Phase 5: Bedrock Agent Configuration

**Goal:** Configure the Supervisor multi-agent system with 3 sub-agents, Knowledge Bases, and Guardrails.
**Estimated Duration:** 3–4 days

### Success Criteria
- Supervisor Agent correctly routes credit queries to Credit Risk agent, market queries to Market Analytics agent, ESG queries to ESG Risk agent
- Knowledge Base retrieval returns relevant chunks from uploaded docs
- Guardrails block PII and off-topic queries
- Agent invocable via `bedrock-agent-runtime:InvokeAgent` API
- Multi-turn conversation maintains context within session

### Tasks

| # | Task | File(s) | Effort | Depends On |
|---|------|---------|--------|------------|
| 5.1 | Write Supervisor Agent system prompt — role definition, sub-agent capabilities, routing rules, output format constraints | `prompts/supervisor_system.txt` | M | — |
| 5.2 | Write Credit Risk Agent system prompt — Moody's data expert persona, citation requirements, financial ratio analysis instructions | `prompts/credit_risk_system.txt` | M | — |
| 5.3 | Write Market Analytics Agent system prompt — data center market analyst persona, geographic analysis, supply/demand expertise | `prompts/market_analytics_system.txt` | S | — |
| 5.4 | Write ESG Risk Agent system prompt — sustainability analyst persona, PUE/carbon/water expertise, climate risk methodology | `prompts/esg_risk_system.txt` | S | — |
| 5.5 | Configure Bedrock Guardrail `dc-invest-guardrail-v1` — content filters (SEXUAL, VIOLENCE = HIGH), denied topics (non-financial advice), PII redaction (SSN, CC, EMAIL, PHONE) | `cdk/stacks/agent_stack.py` | M | 1.6 |
| 5.6 | Create Knowledge Base `kb-credit-risk` — S3 source `dcai-kb-docs/moodys/`, fixed 512-token chunks, 50-token overlap, Titan Embeddings V2 | `cdk/stacks/agent_stack.py` | M | 1.3, 3.8 |
| 5.7 | Create Knowledge Base `kb-market-analytics` — S3 source `dcai-kb-docs/market/` | `cdk/stacks/agent_stack.py` | S | 1.3, 3.9 |
| 5.8 | Create Knowledge Base `kb-esg` — S3 source `dcai-kb-docs/esg/`, 256-token chunks, 25-token overlap | `cdk/stacks/agent_stack.py` | S | 1.3, 3.10 |
| 5.9 | Configure Credit Risk Sub-Agent — model `mistral.mistral-large-2407-v1:0`, attach KB `kb-credit-risk`, action groups `LookupCreditRating`, `GetFinancialMetrics`, `SyncMoodysData` | `cdk/stacks/agent_stack.py` | M | 5.2, 5.5, 5.6, 4.13 |
| 5.10 | Configure Market Analytics Sub-Agent — model `mistral.mistral-large-2407-v1:0`, attach KB `kb-market-analytics`, action groups `QueryMarketData`, `GenerateReport` | `cdk/stacks/agent_stack.py` | M | 5.3, 5.5, 5.7, 4.13 |
| 5.11 | Configure ESG Risk Sub-Agent — model `mistral.mistral-small-2402-v1:0`, attach KB `kb-esg`, action group `AssessESGRisk` | `cdk/stacks/agent_stack.py` | S | 5.4, 5.5, 5.8, 4.13 |
| 5.12 | Configure Supervisor Agent — model `mistral.mistral-large-2407-v1:0`, collaboration mode `SUPERVISOR_ROUTER`, link sub-agents, attach guardrail | `cdk/stacks/agent_stack.py` | L | 5.1, 5.9–5.11 |
| 5.13 | Trigger Knowledge Base ingestion jobs (sync S3 docs → vector store) | `scripts/sync_knowledge_bases.sh` | S | 5.6–5.8, 3.11 |
| 5.14 | Smoke test: invoke Supervisor Agent with sample queries via AWS CLI | — | M | 5.12, 5.13 |

### Agent Model Configuration

| Agent | Model ID | Max Tokens | Temperature | Top-P |
|-------|----------|-----------|-------------|-------|
| Supervisor | `mistral.mistral-large-2407-v1:0` | 4096 | 0.1 | 0.9 |
| Credit Risk | `mistral.mistral-large-2407-v1:0` | 4096 | 0.0 | 0.9 |
| Market Analytics | `mistral.mistral-large-2407-v1:0` | 4096 | 0.1 | 0.9 |
| ESG Risk | `mistral.mistral-small-2402-v1:0` | 2048 | 0.0 | 0.9 |

---

## Phase 6: Frontend Chat Application

**Goal:** Build a React SPA with chat interface, portfolio dashboard, observability panels, and deploy to S3 + CloudFront.
**Estimated Duration:** 4–5 days

### Success Criteria
- Chat panel sends queries to `/v1/query` and renders Markdown/table responses
- Portfolio dashboard displays watchlist with ratings and risk summary
- Feedback buttons (thumbs up/down) POST to Arize mock
- Arize panel shows live trace/metric data from mock
- Workato panel shows pipeline status from mock
- App deployed and accessible via CloudFront URL
- Responsive layout (desktop primary, tablet acceptable)

### Tasks

| # | Task | File(s) | Effort | Depends On |
|---|------|---------|--------|------------|
| 6.1 | Initialize React + Vite + TypeScript project with Tailwind CSS | `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/styles/globals.css` | S | — |
| 6.2 | Define TypeScript types matching DATA_MODEL.md interfaces | `frontend/src/types/index.ts` | S | — |
| 6.3 | Implement API client — wrapper around fetch for `/v1/*` and `/mock/*` endpoints | `frontend/src/api/client.ts` | S | — |
| 6.4 | Implement `AppShell` layout — header, sidebar, main content area, tab navigation (Chat / Dashboard) | `frontend/src/components/Layout/AppShell.tsx`, `frontend/src/components/Layout/NavBar.tsx` | M | 6.1 |
| 6.5 | Implement `ChatPanel` — message list, auto-scroll, loading indicator | `frontend/src/components/Chat/ChatPanel.tsx` | M | 6.3, 6.4 |
| 6.6 | Implement `MessageBubble` — user vs. assistant styling, Markdown rendering (react-markdown + remark-gfm for tables), code block support | `frontend/src/components/Chat/MessageBubble.tsx` | M | 6.5 |
| 6.7 | Implement `MessageInput` — text area, send button, keyboard shortcut (Ctrl+Enter) | `frontend/src/components/Chat/MessageInput.tsx` | S | 6.5 |
| 6.8 | Implement `FeedbackButtons` — thumbs up/down on each assistant message; POST to `/mock/arize/traces` with feedback | `frontend/src/components/Chat/FeedbackButtons.tsx` | S | 6.3, 6.5 |
| 6.9 | Implement `SourceAttribution` — collapsible panel showing data source, vintage, Moody's disclaimer | `frontend/src/components/Chat/SourceAttribution.tsx` | S | 6.6 |
| 6.10 | Implement `useChat` hook — manages messages state, session ID, send/receive lifecycle | `frontend/src/hooks/useChat.ts` | M | 6.3 |
| 6.11 | Implement `WatchlistSidebar` — list of operators with rating, outlook, click to query | `frontend/src/components/Watchlist/WatchlistSidebar.tsx` | M | 6.3 |
| 6.12 | Implement `PortfolioDashboard` — risk summary, concentration metrics, weighted average rating | `frontend/src/components/Dashboard/PortfolioDashboard.tsx` | M | 6.3 |
| 6.13 | Implement `RiskSummary` — card layout showing key portfolio metrics | `frontend/src/components/Dashboard/RiskSummary.tsx` | S | 6.12 |
| 6.14 | Implement `AlertFeed` — recent rating actions and material changes | `frontend/src/components/Dashboard/AlertFeed.tsx` | S | 6.12 |
| 6.15 | Implement `usePortfolio` hook — fetches operator list, computes aggregates | `frontend/src/hooks/usePortfolio.ts` | S | 6.3 |
| 6.16 | Implement `ArizePanel` — displays trace list, metrics charts (latency, token counts), eval scores; polls `/mock/arize/dashboard` | `frontend/src/components/Observability/ArizePanel.tsx` | L | 6.3 |
| 6.17 | Implement `WorkatoPanel` — displays pipeline status, connection health, recent runs; polls `/mock/workato/connections` and recipe status | `frontend/src/components/Observability/WorkatoPanel.tsx` | M | 6.3 |
| 6.18 | Wire `App.tsx` with routing (react-router) and compose all components | `frontend/src/App.tsx` | M | 6.4–6.17 |
| 6.19 | Build production bundle and deploy to S3 via CDK | `cdk/stacks/frontend_stack.py` | S | 1.7, 6.18 |
| 6.20 | End-to-end frontend smoke test | — | S | 6.19 |

### Component Hierarchy

```
App
├── AppShell
│   ├── NavBar (Chat | Dashboard | Observability tabs)
│   ├── WatchlistSidebar
│   └── Main Content Area
│       ├── [Chat View]
│       │   ├── ChatPanel
│       │   │   ├── MessageBubble (× N)
│       │   │   │   ├── SourceAttribution
│       │   │   │   └── FeedbackButtons
│       │   │   └── MessageInput
│       ├── [Dashboard View]
│       │   ├── PortfolioDashboard
│       │   │   ├── RiskSummary
│       │   │   └── AlertFeed
│       └── [Observability View]
│           ├── ArizePanel
│           └── WorkatoPanel
```

---

## Phase 7: Integration & Demo

**Goal:** Validate end-to-end flows, prepare demo scenarios, and verify production deployment.
**Estimated Duration:** 2–3 days

### Success Criteria
- All 5 demo scenarios execute successfully end-to-end
- Agent responses include source attribution and are factually consistent with seeded data
- Arize mock dashboard shows traces generated during demo
- Workato mock shows successful recipe runs triggered during demo
- No critical errors in CloudWatch logs
- Deployment is repeatable via `cdk deploy --all` + seed scripts

### Demo Scenarios (Mapping to PRD User Stories)

| # | Scenario | PRD Story | Expected Flow |
|---|----------|-----------|---------------|
| D1 | **Leverage Comparison** — "Compare Equinix and Digital Realty leverage ratios over the last 2 quarters" | US 2.1.1 | Supervisor → Credit Risk Agent → `GetFinancialMetrics` (op-001, op-002) → formatted table with Moody's attribution |
| D2 | **ESG Risk Assessment** — "What is the ESG risk profile for Switch's data centers? How does their PUE compare to industry average?" | US 2.1.2 | Supervisor → ESG Risk Agent → `AssessESGRisk` (op-006) → KB retrieval for methodology context → summary with CIS score |
| D3 | **Portfolio Aggregation** — "Aggregate credit exposure across all 6 operators in my watchlist" | US 2.2.1 | Supervisor → Credit Risk Agent (fan-out) → `LookupCreditRating` × 6 → weighted average rating, concentration breakdown |
| D4 | **Market Analysis** — "Show me supply and demand dynamics for Northern Virginia and Dallas" | US 2.1.1 | Supervisor → Market Analytics Agent → `QueryMarketData` (mkt-nova, mkt-dfw) → comparison table with construction pipeline |
| D5 | **Report Generation** — "Generate a weekly summary report for the data center sector" | US 2.3.2 | Supervisor → Market Analytics Agent → `GenerateReport` → Markdown report uploaded to S3 → presigned URL returned |

### Tasks

| # | Task | File(s) | Effort | Depends On |
|---|------|---------|--------|------------|
| 7.1 | Write integration test: D1 — leverage comparison | `tests/integration/test_agent_e2e.py` | M | Phase 4, Phase 5 |
| 7.2 | Write integration test: D2 — ESG risk assessment | `tests/integration/test_agent_e2e.py` | M | Phase 4, Phase 5 |
| 7.3 | Write integration test: D3 — portfolio aggregation | `tests/integration/test_agent_e2e.py` | M | Phase 4, Phase 5 |
| 7.4 | Write integration test: D4 — market analysis | `tests/integration/test_agent_e2e.py` | S | Phase 4, Phase 5 |
| 7.5 | Write integration test: D5 — report generation | `tests/integration/test_agent_e2e.py` | S | Phase 4, Phase 5 |
| 7.6 | Verify Arize mock dashboard populated after demo runs | — | S | 7.1–7.5 |
| 7.7 | Verify Workato mock shows recipe runs from SyncMoodysData calls | — | S | 7.1–7.5 |
| 7.8 | Full `cdk destroy` → `cdk deploy` → seed → demo cycle to confirm repeatable deployment | — | M | All |
| 7.9 | Update `README.md` with setup instructions, architecture diagram, and demo walkthrough | `README.md` | M | All |
| 7.10 | Record demo script with step-by-step instructions for each scenario | `docs/DEMO_SCRIPT.md` | S | 7.1–7.5 |

---

## Risk Register

| # | Risk | Probability | Impact | Mitigation |
|---|------|------------|--------|-----------|
| R1 | Bedrock Agent multi-agent collaboration (`SUPERVISOR_ROUTER`) may have limited CDK L1 support; CfnAgent properties may be incomplete | Medium | High | Fall back to AWS CLI / SDK scripts for agent creation if CDK constructs are insufficient. Wrap in a CDK custom resource Lambda. |
| R2 | Mistral model IDs may not be available in target region | Medium | High | Configure model ID as CDK context parameter; document fallback to `anthropic.claude-3-haiku` or `amazon.titan-text-express-v1`. |
| R3 | Knowledge Base ingestion may fail if OpenSearch Serverless collection is slow to provision | Low | Medium | MVP can skip OpenSearch and use in-memory retrieval in the action group Lambda. Add OpenSearch as a follow-on enhancement. |
| R4 | Lambda cold start latency may exceed Bedrock Agent timeout (30s default) | Medium | Medium | Set Lambda memory to 512MB+; use provisioned concurrency for demo; keep handler imports minimal. |
| R5 | Frontend CORS issues with API Gateway | Medium | Low | Configure CORS in CDK API Gateway resource; add OPTIONS method to all resources. |
| R6 | DynamoDB on-demand capacity may throttle during batch seed operations | Low | Low | Use batch_write with exponential backoff; seed is a one-time operation. |
| R7 | Bedrock Guardrail configuration may block legitimate financial queries containing risk-related terms | Medium | Medium | Test guardrail with all 5 demo scenarios before deployment; tune denied topic definitions. |
| R8 | CloudFront distribution provisioning takes 15-30 minutes | Low | Low | Deploy frontend stack first; use S3 website endpoint for dev testing. |

---

## Dependency Graph

```
Phase 1 (CDK Infrastructure)
  │
  ├──► Phase 2 (Mock Services)
  │       │
  │       └──► Phase 4 (Action Group Lambdas) ──► Phase 5 (Bedrock Agents)
  │                                                       │
  ├──► Phase 3 (Data Seeding) ─────────────────────────►──┤
  │                                                       │
  └──► Phase 6 (Frontend) ────────────────────────────►───┤
                                                          │
                                                          ▼
                                                   Phase 7 (Integration)
```

**Critical path:** Phase 1 → Phase 2 → Phase 4 → Phase 5 → Phase 7

**Parallelizable:**
- Phase 3 (Data Seeding) can run in parallel with Phase 2 (Mock Services)
- Phase 6 (Frontend) can start after Phase 1 completes, runs in parallel with Phases 2–5
- Phase 3 data fixtures (tasks 3.1–3.6, 3.8–3.10) can start immediately (no infra dependency)

---

## Effort Summary

| Phase | Estimated Days | Task Count |
|-------|---------------|------------|
| Phase 1: Infrastructure Foundation | 3–4 | 9 |
| Phase 2: Mock Services Layer | 3–4 | 14 |
| Phase 3: Data Layer & Seeding | 2 | 12 |
| Phase 4: Action Group Lambdas | 4–5 | 13 |
| Phase 5: Bedrock Agent Config | 3–4 | 14 |
| Phase 6: Frontend | 4–5 | 20 |
| Phase 7: Integration & Demo | 2–3 | 10 |
| **Total** | **21–27** | **92** |

With parallelization (Phases 3+6 overlapping 2+4), effective calendar time: **~18–22 working days**.
