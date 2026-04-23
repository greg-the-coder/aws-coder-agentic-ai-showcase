# Data Center Investments Agent — Technical Design Document

**Version:** 1.0.0
**Author:** Platform Engineering
**Status:** Implementation-Ready
**Last Updated:** 2025-07-14
**Repository:** `aws-coder-agentic-ai-showcase`

---

## 1. Executive Summary

### 1.1 Problem Statement

Investment professionals covering the data center sector depend on fragmented, manual workflows to assess credit risk, compare financial metrics, and monitor market dynamics across operators such as Equinix, Digital Realty, QTS, and CyrusOne. Analysts manually cross-reference Moody's credit ratings, parse earnings transcripts, and aggregate ESG disclosures — a process that averages 4 hours per issuer, is error-prone, and does not scale across a growing universe of issuers.

### 1.2 Solution

The Data Center Investments Agent is a multi-agent AI conversational assistant deployed on **AWS Bedrock Agents**. A Supervisor Agent routes natural language queries to three specialist sub-agents — Credit Risk, Market Analytics, and ESG Risk — each backed by Lambda action groups that query DynamoDB-stored financial data. The system integrates Workato for data pipeline orchestration and Arize for LLM observability, both mocked at the MVP stage to eliminate third-party dependencies.

### 1.3 MVP Scope

**Included:**

- Supervisor + 3 sub-agent multi-agent collaboration via Bedrock Agents
- 6 Lambda-backed action groups (credit rating, financial metrics, market data, ESG risk, report generation, Moody's sync)
- 7 DynamoDB tables with seeded mock data for 6 data center operators
- REST API Gateway with 4 core endpoints + 4 mock service endpoints
- React SPA frontend with chat, dashboard, Workato panel, and Arize panel views
- Mock Workato service (recipe trigger, status polling, webhook simulation, connection health)
- Mock Arize service (trace ingestion, evaluations, metrics aggregation, dashboard data)
- CloudWatch custom metrics published by the Arize mock
- API key authentication for demo access
- CDK infrastructure-as-code across 4 stacks

**Excluded:**

- Real Workato license / live recipe execution
- Real Arize account / production OTEL tracing
- OpenSearch Serverless vector store (Knowledge Bases deferred)
- Aurora PostgreSQL (replaced by DynamoDB for MVP simplicity)
- WebSocket streaming (REST-only for MVP)
- Trade execution, non-data-center sectors, mobile application
- Custom model fine-tuning

### 1.4 Key Architectural Decisions

| Decision | Rationale |
|---|---|
| **DynamoDB over Aurora** | MVP does not require relational joins; DynamoDB is serverless, zero-admin, and sufficient for key-value/document lookups across 6 operators. Avoids VPC cold-start latency for Lambda. |
| **Mock Workato** | Workato is a licensed 3rd-party iPaaS. Mocking allows full demo without procurement. The mock Lambda returns realistic Workato API envelope formats so the swap is a configuration change. |
| **Mock Arize** | Arize is a 3rd-party LLM observability platform requiring an account and API key. The mock stores traces in DynamoDB and publishes CloudWatch metrics, simulating the observability pipeline end-to-end. |
| **Mistral models** | Mistral Large 2 for Supervisor + Credit + Market (complex reasoning); Mistral Small for ESG (structured lookups, lower cost). Both available on Bedrock. |
| **CfnAgent (L1)** | No L2 CDK construct exists for Bedrock Agents yet; CfnAgent provides full control over action group wiring and OpenAPI schema embedding. |
| **Single-Lambda per action group** | Each action group gets its own Lambda for independent scaling, deployment, and least-privilege IAM. |
| **PAY_PER_REQUEST billing** | All DynamoDB tables use on-demand billing — appropriate for MVP traffic patterns with no capacity planning required. |

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                   │
│                                                                             │
│    React SPA (Vite + TypeScript + Tailwind)                                │
│    ┌──────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐      │
│    │  Chat    │  │  Portfolio  │  │   Workato    │  │    Arize     │      │
│    │  Panel   │  │  Dashboard  │  │   Panel      │  │    Panel     │      │
│    └────┬─────┘  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘      │
│         └───────────────┴────────────────┴──────────────────┘              │
│                                  │                                          │
│                     ┌────────────▼──────────────┐                          │
│                     │   API Gateway (REST)      │                          │
│                     │   dc-invest-agent-api     │                          │
│                     │   Stage: prod             │                          │
│                     │   API Key: dc-invest-     │                          │
│                     │     demo-key              │                          │
│                     └────────────┬──────────────┘                          │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
              ┌────────────────────┼───────────────────────┐
              │                    │                        │
              ▼                    ▼                        ▼
┌─────────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐
│   /v1/* endpoints   │ │  /mock/workato/* │ │   /mock/arize/*          │
│                     │ │                  │ │                          │
│  POST /v1/query     │ │  POST  /trigger  │ │  POST  /ingest          │
│  GET  /v1/sessions  │ │  GET   /status   │ │  GET   /query           │
│  GET  /v1/health    │ │                  │ │                          │
│  POST /v1/reports   │ │  (Workato Mock   │ │  (Arize Mock Lambdas)   │
│                     │ │   Lambdas)       │ │                          │
│  (API Lambdas)      │ │                  │ │                          │
└────────┬────────────┘ └────────┬─────────┘ └────────────┬─────────────┘
         │                       │                         │
         ▼                       │                         │
┌──────────────────────────┐     │                         │
│     BEDROCK AGENTS       │     │                         │
│                          │     │                         │
│  ┌────────────────────┐  │     │                         │
│  │  SUPERVISOR AGENT  │  │     │                         │
│  │  dcai-supervisor   │  │     │                         │
│  │  Mistral Large 2   │  │     │                         │
│  └──┬──────┬──────┬───┘  │     │                         │
│     │      │      │      │     │                         │
│  ┌──▼──┐┌──▼───┐┌─▼───┐ │     │                         │
│  │Cred.││Mkt.  ││ESG  │ │     │                         │
│  │Risk ││Anal. ││Risk │ │     │                         │
│  │Agent││Agent ││Agent│ │     │                         │
│  │Lg 2 ││Lg 2  ││Sm   │ │     │                         │
│  └──┬──┘└──┬───┘└─┬───┘ │     │                         │
│     │      │      │      │     │                         │
│  ┌──▼──────▼──────▼───┐  │     │                         │
│  │  ACTION GROUPS     │  │     │                         │
│  │  (6 Lambdas)       │  │     │                         │
│  │  • LookupCredit    │  │     │                         │
│  │  • GetFinancial    │  │     │                         │
│  │  • QueryMarket     │  │     │                         │
│  │  • AssessESG       │  │     │                         │
│  │  • GenerateReport  │  │     │                         │
│  │  • SyncMoodys      │  │     │                         │
│  └──────────┬─────────┘  │     │                         │
└─────────────┼────────────┘     │                         │
              │                  │                         │
              ▼                  ▼                         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                     │
│                                                                          │
│  DynamoDB (7 tables)                      S3 (2 buckets)                │
│  ┌──────────────┐ ┌──────────────┐       ┌───────────────────┐         │
│  │dcai-sessions │ │dcai-operators│       │ Data Lake Bucket  │         │
│  │dcai-metrics  │ │dcai-esg-     │       │  /moodys/         │         │
│  │dcai-market-  │ │  profiles    │       │  /market/         │         │
│  │  data        │ │dcai-traces   │       │  /esg/            │         │
│  │dcai-workato- │ │              │       ├───────────────────┤         │
│  │  runs        │ │              │       │ Reports Bucket    │         │
│  └──────────────┘ └──────────────┘       │  (PDF/Markdown)   │         │
│                                           └───────────────────┘         │
├──────────────────────────────────────────────────────────────────────────┤
│                        OBSERVABILITY                                     │
│                                                                          │
│  CloudWatch                                                              │
│  ├── Namespace: DCInvestAgent                                           │
│  │   ├── TraceLatency (Milliseconds)                                    │
│  │   └── TokenCount (Count)                                             │
│  └── Lambda log groups (2-week retention)                               │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Multi-Agent Design

### 3.1 Supervisor Routing Pattern

The system implements Bedrock's `SUPERVISOR_ROUTER` collaboration mode. The Supervisor Agent receives every user query, classifies intent, delegates to the appropriate sub-agent(s), and synthesizes the final response. This pattern provides:

- **Single entry point** — API always invokes one agent ID (`dcai-supervisor`)
- **Intent-based routing** — no client-side routing logic needed
- **Fan-out capability** — portfolio/cross-domain queries trigger multiple sub-agents
- **Response synthesis** — Supervisor merges sub-agent outputs into a coherent answer

```
                          User Query
                              │
                              ▼
                    ┌───────────────────┐
                    │  SUPERVISOR AGENT │
                    │  dcai-supervisor  │
                    │                   │
                    │  Step 1: Classify │
                    │    intent using   │
                    │    system prompt  │
                    │                   │
                    │  Step 2: Select   │
                    │    action group   │
                    │    or fan-out     │
                    │                   │
                    │  Step 3: Invoke   │
                    │    Lambda(s)      │
                    │                   │
                    │  Step 4: Synth-   │
                    │    esize response │
                    │    with citations │
                    └─┬──────┬──────┬──┘
                      │      │      │
           ┌──────────┘      │      └──────────┐
           ▼                 ▼                  ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ CREDIT RISK  │ │   MARKET     │ │  ESG RISK    │
    │              │ │  ANALYTICS   │ │              │
    │ Action Groups│ │              │ │ Action Group │
    │ • LookupCR   │ │ Action Groups│ │ • AssessESG  │
    │ • GetFinMet  │ │ • QueryMkt   │ │              │
    │ • SyncMoodys │ │ • GenReport  │ │ Model:       │
    │              │ │              │ │ Mistral Small│
    │ Model:       │ │ Model:       │ │ (24.02)      │
    │ Mistral Lg 2 │ │ Mistral Lg 2 │ │              │
    └──────────────┘ └──────────────┘ └──────────────┘
```

### 3.2 Intent Classification Logic

The Supervisor uses Mistral Large 2's instruction-following to classify intent. The system prompt (`infrastructure/lib/agent_stack.py`, `_SUPERVISOR_INSTRUCTION`) instructs the agent to map queries into four categories:

| Intent Category | Trigger Keywords / Patterns | Target | Action Groups |
|---|---|---|---|
| `credit_risk` | credit, rating, Moody's, default, leverage, debt, PD, LGD, DSCR | Credit Risk Agent | `LookupCreditRating`, `GetFinancialMetrics`, `SyncMoodysData` |
| `market_analytics` | market, supply, demand, vacancy, pricing, Virginia, Dallas, construction | Market Analytics Agent | `QueryMarketData`, `GenerateReport` |
| `esg_risk` | ESG, PUE, carbon, renewable, water, climate, sustainability | ESG Risk Agent | `AssessESGRisk` |
| `cross_domain` | portfolio, compare across, overall risk, multiple domains | Supervisor fan-out | Multiple action groups invoked in sequence |

The query handler (`lambda/api/query_handler.py`) includes a fallback keyword-based classifier (`_classify_intent()`) used when the Bedrock Agent is not deployed, ensuring the demo works end-to-end even without Bedrock provisioning.

### 3.3 Sub-Agent Model Selection

| Agent | Foundation Model | Model ID | Rationale | Latency Target |
|---|---|---|---|---|
| Supervisor | Mistral Large 2 (24.02) | `mistral.mistral-large-2402-v1:0` | Complex reasoning for intent classification and response synthesis | < 15s |
| Credit Risk | Mistral Large 2 (24.02) | `mistral.mistral-large-2402-v1:0` | Financial analysis requires nuanced reasoning | < 8s |
| Market Analytics | Mistral Large 2 (24.02) | `mistral.mistral-large-2402-v1:0` | Comparative market analysis across metros | < 8s |
| ESG Risk | Mistral Small (24.02) | `mistral.mistral-small-2402-v1:0` | Structured lookups, lower cost for tabular data | < 3s |

### 3.4 Fan-Out for Cross-Domain Queries

When a user asks a portfolio-level question (e.g., "Give me a full risk assessment of Equinix including credit, market, and ESG"), the Supervisor:

1. Identifies the query as `cross_domain`
2. Invokes action groups sequentially: `LookupCreditRating` → `GetFinancialMetrics` → `QueryMarketData` → `AssessESGRisk`
3. Aggregates results from all action group responses
4. Synthesizes a unified narrative with section headers and data citations

### 3.5 Response Synthesis

The Supervisor's system prompt enforces:

- **Source citation** — every data point references its source (Moody's, CBRE, JLL, EPA)
- **Structured output** — tables for comparisons, bullet points for summaries
- **`<thinking>` tags** — complex credit analysis uses chain-of-thought before the visible answer
- **Refusal** — out-of-scope queries (medical, legal, non-financial) are declined with a redirect

---

## 4. Mock Integration Architecture

### 4.1 Workato Mock Service

**Location:** `lambda/mock_services/workato/handler.py`

**Why mock:** Workato is a licensed third-party iPaaS (Integration Platform as a Service). Running actual recipes requires a Workato workspace subscription, connector licenses for Moody's CreditView, Salesforce, and Slack, and OAuth2 credential configuration. Mocking allows the full data pipeline demonstration without any third-party procurement or credentials.

**API Endpoints:**

| Method | Path | Handler | Description |
|---|---|---|---|
| POST | `/mock/workato/recipes/{recipe_id}/trigger` | `_handle_trigger()` | Triggers a recipe run; creates a `wjob-*` record in `dcai-workato-runs` |
| GET | `/mock/workato/recipes/{recipe_id}/status` | `_handle_status()` | Returns mock `succeeded` status with records_processed=6, duration=12.4s |
| POST | `/mock/workato/webhooks/moodys-rating-action` | `_handle_moodys_webhook()` | Simulates an incoming Moody's webhook; stores `wevt-*` event in DynamoDB |
| GET | `/mock/workato/connections` | `_handle_connections()` | Returns 4 mock connections: Moody's CreditView, AWS S3, Salesforce, Slack |

**Response Envelope Format:**

All responses are wrapped in a Workato-compatible envelope:

```json
{
  "data": { ... },
  "metadata": {
    "request_id": "wreq-a1b2c3d4e5f6",
    "timestamp": "2025-07-14T12:00:00Z"
  }
}
```

Headers include `X-Workato-Request-Id` for traceability.

**Simulated Behaviors:**

1. **Recipe triggers** — generates a `wjob-*` UUID, writes a `running` status to `dcai-workato-runs`, returns immediately (simulating async job start)
2. **Status polling** — always returns `succeeded` with realistic metrics (6 records processed, 4 steps executed, 12.4s duration)
3. **Webhook events** — accepts a Moody's rating action payload, stores it as a `processed` event with `event_type: moodys-rating-action`
4. **Connection health** — returns 4 hardcoded connections all showing `status: active` with OAuth2/IAM/bot_token auth types

**Data Flow:**

```
Frontend ──POST──► API Gateway ──► Mock Workato Lambda
                                        │
                                        ├──► DynamoDB (dcai-workato-runs)
                                        │    Store job/event records
                                        │
                                        └──► Response to Frontend
                                             (Workato-format envelope)
```

**How to Swap for Real Workato:**

1. Replace the Lambda integration in `infrastructure/lib/api_stack.py` with an HTTP integration pointing to `https://www.workato.com/api/...`
2. Store Workato API token in Secrets Manager
3. Configure actual Workato recipes matching the recipe IDs used in the mock
4. Update environment variables in the action group Lambdas to point to real Workato endpoints
5. No frontend changes required — the API contract is identical

### 4.2 Arize Mock Service

**Location:** `lambda/mock_services/arize/handler.py`

**Why mock:** Arize is a third-party LLM observability and evaluation platform. Production integration requires an Arize account, API key, and OTEL (OpenTelemetry) collector configuration. The mock simulates the full observability pipeline: trace ingestion, storage, evaluation scoring, metrics aggregation, and dashboard data — all backed by DynamoDB and CloudWatch custom metrics.

**API Endpoints:**

| Method | Path | Handler | Description |
|---|---|---|---|
| POST | `/mock/arize/traces` | `_handle_post_trace()` | Accepts a trace span, stores to `dcai-traces`, publishes CloudWatch metrics |
| GET | `/mock/arize/traces/{trace_id}` | `_handle_get_trace()` | Returns trace details from DynamoDB |
| GET | `/mock/arize/evaluations` | `_handle_evaluations()` | Returns pre-computed evaluation scores for relevance, faithfulness, toxicity, latency |
| GET | `/mock/arize/metrics` | `_handle_metrics()` | Returns aggregated metrics: latency percentiles, token usage, throughput, quality, cost |
| GET | `/mock/arize/dashboard` | `_handle_dashboard()` | Returns full dashboard data: traces over time, model performance, alerts, embedding drift |

**Trace Ingestion Flow:**

```
Action Group Lambda ──trace_span()──► DynamoDB (dcai-traces)
                                           │
Mock Arize Lambda ◄──POST /traces──────────┘
       │
       ├──► DynamoDB (dcai-traces) — store full trace span
       │
       └──► CloudWatch PutMetricData
            Namespace: DCInvestAgent
            ├── TraceLatency (Milliseconds)
            └── TokenCount (Count)
```

**Evaluation Mock:**

The evaluations endpoint returns randomized-but-realistic scores within production-quality ranges:

| Eval Name | Score Range | Threshold | Status Logic |
|---|---|---|---|
| `relevance` | 0.75–0.95 | ≥ 0.70 | Always passing in mock |
| `faithfulness` | 0.85–0.98 | ≥ 0.85 | Always passing in mock |
| `toxicity` | 0 violations | 0 | Always passing (Bedrock Guardrails) |
| `latency_p95` | 3500–8500ms | < 10000ms | Always passing in mock |

Each evaluation includes the model used for scoring, sample count (150), and last evaluation timestamp.

**Dashboard Data Structure:**

The dashboard endpoint returns:

- **`traces_over_time`** — 6 hourly buckets with trace_count, avg_latency_ms, error_count
- **`model_performance`** — per-model breakdown (mistral-large-2407, mistral-small-2402) with invocation counts, avg latency, error rates
- **`alerts`** — 3 configured rules (embedding_drift, eval_regression, error_rate) all showing `status: ok`
- **`embedding_drift`** — current cosine distance (0.02–0.10) vs threshold (0.15), baseline date

**How to Swap for Real Arize:**

1. Install `arize` and `openinference-instrumentation-bedrock` packages in Lambda layers
2. Store Arize API key in Secrets Manager
3. Configure the OTEL tracer provider to point to Arize's collector endpoint
4. Replace mock `/evaluations`, `/metrics`, `/dashboard` calls with Arize's GraphQL API
5. Remove the mock Lambda endpoints from `api_stack.py`

---

## 5. Data Architecture

### 5.1 DynamoDB Table Schemas

All tables are provisioned in `infrastructure/lib/data_stack.py` with `PAY_PER_REQUEST` billing and `RemovalPolicy.DESTROY`.

#### Table 1: `dcai-sessions`

Conversation session state with TTL-based expiration.

| Attribute | Type | Role |
|---|---|---|
| `session_id` | String | **Partition Key** |
| `user_id` | String | GSI `user-index` PK |
| `created_at` | String (ISO 8601) | GSI `user-index` SK |
| `messages` | List\<Map\> | Array of `{role, content, ts}` |
| `agent_id` | String | Bedrock agent ID or "mock-agent" |
| `updated_at` | String (ISO 8601) | Last modification |
| `expires_at` | Number (epoch) | **TTL attribute** |
| `metadata` | Map | Extensible key-value metadata |

**GSI:** `user-index` — PK: `user_id`, SK: `created_at`

#### Table 2: `dcai-operators`

Data center operator master data — 6 seeded records.

| Attribute | Type | Role |
|---|---|---|
| `id` | String | **Partition Key** (`op-001` through `op-006`) |
| `name` | String | GSI `rating-index` SK |
| `ticker` | String \| null | NYSE/NASDAQ ticker |
| `moodys_rating` | String | GSI `rating-index` PK |
| `sector` | String | Moody's sector classification |
| `hq` | String | HQ country code (ISO 3166-1) |
| `market_cap` | Number \| null | USD millions |

**GSI:** `rating-index` — PK: `moodys_rating`, SK: `name`

#### Table 3: `dcai-metrics`

Quarterly financial metrics per operator — 12 seeded records (2 quarters × 6 operators).

| Attribute | Type | Role |
|---|---|---|
| `operator_id` | String | **Partition Key** |
| `period` | String | **Sort Key** (`2024-Q1`, `2024-Q2`) |
| `revenue` | Number | USD millions |
| `ebitda` | Number | USD millions |
| `ffo` | Number | Funds from operations, USD millions |
| `debt_to_ebitda` | Number | Leverage ratio |
| `interest_coverage` | Number | EBITDA / interest expense |
| `occupancy_rate` | Number | 0.0–1.0 |
| `capex` | Number | USD millions |
| `liquidity` | Number | USD millions |

**GSI:** `period-index` — PK: `period`, SK: `operator_id`

#### Table 4: `dcai-esg-profiles`

ESG risk profiles — 6 seeded records.

| Attribute | Type | Role |
|---|---|---|
| `operator_id` | String | **Partition Key** |
| `pue` | Number | Power Usage Effectiveness (1.0–3.0) |
| `carbon_intensity` | Number | kg CO₂e per MWh |
| `renewable_pct` | Number | 0.0–1.0 |
| `water_usage` | Number | Liters per kWh |
| `climate_risk_score` | Number | Moody's CIS 0–100 |
| `green_bond_outstanding` | Number | USD millions |

No GSI.

#### Table 5: `dcai-market-data`

Market analytics by metro area — 5 seeded records.

| Attribute | Type | Role |
|---|---|---|
| `market_id` | String | **Partition Key** (`mkt-nova`, `mkt-dfw`, `mkt-phx`, `mkt-sin`, `mkt-fra`) |
| `region` | String | `NA`, `EMEA`, `APAC`, `LATAM` |
| `market_name` | String | Human-readable name |
| `total_capacity_mw` | Number | Megawatts |
| `absorption_rate` | Number | MW absorbed trailing 12 months |
| `vacancy_rate` | Number | 0.0–1.0 |
| `avg_price_per_kw` | Number | USD per kW/month |
| `construction_pipeline_mw` | Number | MW under construction |
| `yoy_growth` | Number | Year-over-year capacity growth |

No GSI.

#### Table 6: `dcai-traces`

Agent execution traces for observability.

| Attribute | Type | Role |
|---|---|---|
| `trace_id` | String | **Partition Key** |
| `session_id` | String | **Sort Key** |
| `agent_name` | String | e.g., `credit-risk-agent` |
| `action` | String | e.g., `LookupCreditRating` |
| `input` | Map | Action input parameters |
| `output` | Map | Action output payload |
| `latency_ms` | Number | Execution duration |
| `token_count` | Number | Tokens consumed |
| `cost_usd` | Number | Estimated cost |
| `timestamp` | String (ISO 8601) | When the trace was recorded |

No GSI.

#### Table 7: `dcai-workato-runs`

Workato integration run logs.

| Attribute | Type | Role |
|---|---|---|
| `run_id` | String | **Partition Key** (`wjob-*` or `wevt-*`) |
| `recipe_id` | String | Workato recipe identifier |
| `status` | String | `running`, `succeeded`, `processed` |
| `triggered_at` | String (ISO 8601) | Trigger timestamp |
| `triggered_by` | String | `api`, `webhook` |
| `records_processed` | Number | Count of records |
| `event_type` | String (optional) | e.g., `moodys-rating-action` |
| `payload` | String (optional) | JSON-serialized webhook payload |

No GSI.

### 5.2 S3 Bucket Structure

Both buckets are created in `DataStack` with auto-generated names, versioning enabled, S3-managed encryption, `BLOCK_ALL` public access, and SSL enforcement.

**Data Lake Bucket:**

```
s3://<auto-generated>/
├── moodys/
│   ├── ratings/
│   │   └── {date}/actions.json
│   └── reports/
│       └── {entity_id}/{report_date}.pdf
├── market/
│   ├── cbre/
│   └── jll/
└── esg/
    ├── epa/
    └── energy_star/
```

**Reports Bucket:**

```
s3://<auto-generated>/
├── {session_id}/
│   ├── {report_id}.pdf
│   └── {report_id}.md
└── templates/
    └── credit_analysis.md
```

### 5.3 Data Seeding Strategy

A dedicated Lambda function (`lambda/seed/seed_handler.py`, CDK name `dcai-seed-data`) loads mock data into all DynamoDB tables. This function:

- Has a 120-second timeout (vs. 30s for action groups) to accommodate batch writes
- Uses the same `ActionGroupLambdaRole` for DynamoDB access
- Populates data from the definitions in `product-docs/DATA_MODEL.md`:
  - 6 operators in `dcai-operators`
  - 12 financial metric records (2 quarters × 6 operators) in `dcai-metrics`
  - 6 ESG profiles in `dcai-esg-profiles`
  - 5 market data records in `dcai-market-data`

**Seeded Operator Universe:**

| ID | Name | Ticker | Rating | Scenario |
|---|---|---|---|---|
| op-001 | Equinix Inc. | EQIX | A3 | Investment-grade leader |
| op-002 | Digital Realty Trust | DLR | Baa2 | Moderate leverage, deleveraging |
| op-003 | QTS Realty Trust | — | Ba2 | Blackstone take-private |
| op-004 | CyrusOne LLC | — | Ba3 | KKR/GIP private equity transition |
| op-005 | CoreSite Realty | COR | Baa3 | Hyperscaler concentration |
| op-006 | Switch Inc. | SWCH | B1 | 100% renewable, speculative-grade |

---

## 6. API Design

### 6.1 REST API Contract

**Base URL:** `https://{api-id}.execute-api.{region}.amazonaws.com/prod`

Defined in `infrastructure/lib/api_stack.py`. Stage: `prod`. Throttling: 100 req/s rate, 50 burst.

#### Core Endpoints

##### POST /v1/query

Submit a natural language query to the Supervisor Agent.

**Auth:** API key required (`X-Api-Key` header)

**Request:**

```json
{
  "session_id": "optional-uuid-auto-generated-if-omitted",
  "message": "Compare leverage ratios for Equinix and Digital Realty"
}
```

**Response (200):**

```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "response": "Based on Moody's latest assessment, Equinix Inc. (EQIX) maintains...",
  "source": "bedrock-agent",
  "latency_ms": 3421.5,
  "timestamp": "2025-07-14T12:00:00Z"
}
```

The `source` field indicates whether the response came from:
- `bedrock-agent` — live Bedrock Agent invocation
- `mock-fallback` — Bedrock Agent failed, fell back to keyword-based mock
- `mock` — Bedrock Agent not configured (no `BEDROCK_AGENT_ID` env var)

**Error (400):**

```json
{
  "error": "message field is required"
}
```

##### GET /v1/sessions/{id}

Retrieve conversation history for a session.

**Auth:** API key required

**Response (200):**

```json
{
  "session_id": "a1b2c3d4-...",
  "messages": [
    { "role": "user", "content": "...", "ts": "2025-07-14T12:00:00Z" },
    { "role": "assistant", "content": "...", "ts": "2025-07-14T12:00:03Z" }
  ],
  "created_at": "2025-07-14T12:00:00Z"
}
```

##### GET /v1/health

Service health check. No authentication required.

**Response (200):**

```json
{
  "status": "healthy",
  "timestamp": "2025-07-14T12:00:00Z"
}
```

##### POST /v1/reports/generate

Trigger async report generation.

**Auth:** API key required

**Request:**

```json
{
  "operator_id": "op-001",
  "sections": ["credit", "market", "esg", "recommendation"]
}
```

#### Mock Service Endpoints

No API key required for mock endpoints.

##### POST /mock/workato/trigger

Trigger a Workato recipe run.

**Request:**

```json
{
  "recipe_id": "moodys_daily_sync",
  "source": "api"
}
```

**Response (200):**

```json
{
  "data": {
    "job_id": "wjob-a1b2c3d4e5f6",
    "status": "running",
    "recipe_id": "moodys_daily_sync"
  },
  "metadata": {
    "request_id": "wreq-f6e5d4c3b2a1",
    "timestamp": "2025-07-14T12:00:00Z"
  }
}
```

##### GET /mock/workato/status/{run_id}

Poll recipe run status.

##### POST /mock/arize/ingest

Ingest a trace span.

**Request:**

```json
{
  "trace_id": "trace-abc123",
  "session_id": "session-xyz",
  "agent_name": "credit-risk-agent",
  "action": "LookupCreditRating",
  "latency_ms": 245.3,
  "token_count": 85
}
```

##### GET /mock/arize/query

Query traces, evaluations, metrics, or dashboard data (route determined by path).

### 6.2 Error Handling Patterns

All Lambda handlers follow a consistent error pattern:

```json
{
  "statusCode": 400,
  "headers": {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
  },
  "body": "{\"error\": \"descriptive error message\"}"
}
```

| Status | Condition |
|---|---|
| 200 | Successful operation |
| 400 | Missing required parameter, invalid JSON body |
| 404 | Entity not found (operator, trace, route) |
| 500 | Internal error (DynamoDB failure, Bedrock timeout) |

The query handler (`lambda/api/query_handler.py`) implements graceful degradation: if Bedrock Agent invocation fails, it falls back to mock responses rather than returning a 500.

### 6.3 CORS Configuration

Configured at the API Gateway level in `api_stack.py`:

```python
default_cors_preflight_options=apigw.CorsOptions(
    allow_origins=apigw.Cors.ALL_ORIGINS,
    allow_methods=apigw.Cors.ALL_METHODS,
    allow_headers=[
        "Content-Type",
        "X-Amz-Date",
        "Authorization",
        "X-Api-Key",
        "X-Amz-Security-Token",
    ],
)
```

The query handler also adds CORS headers in its Lambda response for non-preflight requests:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

---

## 7. Frontend Architecture

### 7.1 Technology Stack

| Layer | Technology |
|---|---|
| Framework | React 18 + TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS (dark terminal theme) |
| Routing | React Router v6 (`BrowserRouter`) |
| HTTP Client | Fetch API via service modules |

**Entry point:** `frontend/src/main.tsx` → `frontend/src/App.tsx`

### 7.2 Component Hierarchy

```
App.tsx
├── BrowserRouter
│   └── Routes
│       └── Route (Layout.tsx)
│           ├── / ──────────────── ChatPanel.tsx
│           │                      ├── MessageBubble.tsx
│           │                      └── FeedbackButtons.tsx
│           │
│           ├── /dashboard ─────── PortfolioDashboard.tsx
│           │                      ├── OperatorCard.tsx
│           │                      ├── RiskSummary.tsx
│           │                      └── AlertsPanel.tsx
│           │
│           ├── /workato ────────── WorkatoPanel.tsx
│           │
│           └── /arize ──────────── ArizePanel.tsx
│
└── Shared Components (Common/)
    ├── DataTable.tsx
    ├── MetricCard.tsx
    └── StatusBadge.tsx
```

### 7.3 Service Layer

Located in `frontend/src/services/`:

| File | Purpose |
|---|---|
| `api.ts` | Core API client — `POST /v1/query`, `GET /v1/sessions/{id}`, `GET /v1/health` |
| `workato.ts` | Workato mock API client — trigger, status, connections |
| `arize.ts` | Arize mock API client — traces, evaluations, metrics, dashboard |

### 7.4 Four Main Views

**1. Chat Panel (`/`)**

- Primary interaction surface
- Message thread with user/assistant bubbles
- Thumbs up/down feedback buttons on each response
- Session persistence across page reloads via session_id
- Shows `source` indicator (bedrock-agent vs mock)

**2. Portfolio Dashboard (`/dashboard`)**

- Operator cards with rating, outlook, and key metrics
- Risk summary widget (weighted-average rating, top concentration, geo concentration)
- Alerts panel showing recent rating actions and market events

**3. Workato Panel (`/workato`)**

- Recipe trigger button with live status polling
- Connection health dashboard (4 mock connections)
- Webhook simulation form for Moody's rating actions
- Run history from `dcai-workato-runs` table

**4. Arize Panel (`/arize`)**

- Evaluation scores (relevance, faithfulness, toxicity, latency)
- Latency percentile charts (p50, p95, p99)
- Token usage and cost metrics
- Model performance comparison (Large 2 vs Small)
- Alert rule status
- Embedding drift monitoring

### 7.5 Demo Data Fallback

When the API is unavailable, the frontend renders using hardcoded demo data. The query handler's mock response system (`_MOCK_RESPONSES` in `lambda/api/query_handler.py`) ensures the chat always returns meaningful content. This enables the frontend to be demonstrated standalone or with a partially deployed backend.

### 7.6 Design Theme

Dark terminal theme implemented via Tailwind CSS. Color palette aligns with a professional financial terminal aesthetic — dark backgrounds with high-contrast data elements.

---

## 8. CDK Infrastructure

### 8.1 Four-Stack Decomposition

Defined in `infrastructure/app.py`:

```python
data_stack    = DataStack(app, "DcaiDataStack", env=env)
lambda_stack  = LambdaStack(app, "DcaiLambdaStack", data_stack=data_stack, env=env)
api_stack     = ApiStack(app, "DcaiApiStack", lambda_stack=lambda_stack, env=env)
agent_stack   = AgentStack(app, "DcaiAgentStack", lambda_stack=lambda_stack, env=env)
```

**Dependency graph:**

```
DcaiDataStack
      │
      ▼
DcaiLambdaStack ◄──── data_stack (table names, bucket names, IAM grants)
      │
      ├──────────────► DcaiApiStack      (Lambda function references)
      │
      └──────────────► DcaiAgentStack    (Lambda function ARNs for action groups)
```

### 8.2 Resource Summary Per Stack

#### DcaiDataStack (`infrastructure/lib/data_stack.py`)

| Resource Type | Count | Names |
|---|---|---|
| DynamoDB Table | 7 | `dcai-sessions`, `dcai-operators`, `dcai-metrics`, `dcai-esg-profiles`, `dcai-market-data`, `dcai-traces`, `dcai-workato-runs` |
| DynamoDB GSI | 3 | `user-index`, `rating-index`, `period-index` |
| S3 Bucket | 2 | Auto-generated (Data Lake, Reports) |
| CfnOutput | 11 | Table ARNs (7), table names (7), bucket names (2) — some overlap |

#### DcaiLambdaStack (`infrastructure/lib/lambda_stack.py`)

| Resource Type | Count | Names / Details |
|---|---|---|
| Lambda Function | 15 | 6 action groups + 4 API handlers + 2 Workato mocks + 2 Arize mocks + 1 seed |
| IAM Role | 3 | `ActionGroupLambdaRole`, `ApiHandlerLambdaRole`, `MockServiceLambdaRole` |
| CloudWatch Log Group | 15 | One per Lambda (2-week retention) |

**Lambda Functions Detail:**

| Function Name | Handler | Role | Memory | Timeout |
|---|---|---|---|---|
| `dcai-credit-rating` | `handlers.credit_rating.handler` | ActionGroupLambdaRole | 512 MB | 30s |
| `dcai-financial-metrics` | `handlers.financial_metrics.handler` | ActionGroupLambdaRole | 512 MB | 30s |
| `dcai-market-data` | `handlers.market_data.handler` | ActionGroupLambdaRole | 512 MB | 30s |
| `dcai-esg-risk` | `handlers.esg_risk.handler` | ActionGroupLambdaRole | 512 MB | 30s |
| `dcai-generate-report` | `handlers.generate_report.handler` | ActionGroupLambdaRole | 512 MB | 30s |
| `dcai-sync-moodys` | `handlers.sync_moodys.handler` | ActionGroupLambdaRole | 512 MB | 30s |
| `dcai-api-query` | `api.query_handler.handler` | ApiHandlerLambdaRole | 512 MB | 30s |
| `dcai-api-sessions` | `api.sessions_handler.handler` | ApiHandlerLambdaRole | 512 MB | 30s |
| `dcai-api-health` | `api.health_handler.handler` | ApiHandlerLambdaRole | 128 MB | 10s |
| `dcai-api-reports` | `api.reports_handler.handler` | ApiHandlerLambdaRole | 512 MB | 30s |
| `dcai-mock-workato-trigger` | `mocks.workato_trigger.handler` | MockServiceLambdaRole | 512 MB | 30s |
| `dcai-mock-workato-status` | `mocks.workato_status.handler` | MockServiceLambdaRole | 512 MB | 30s |
| `dcai-mock-arize-ingest` | `mocks.arize_ingest.handler` | MockServiceLambdaRole | 512 MB | 30s |
| `dcai-mock-arize-query` | `mocks.arize_query.handler` | MockServiceLambdaRole | 512 MB | 30s |
| `dcai-seed-data` | `seed.seed_handler.handler` | ActionGroupLambdaRole | 512 MB | 120s |

#### DcaiApiStack (`infrastructure/lib/api_stack.py`)

| Resource Type | Count | Details |
|---|---|---|
| REST API | 1 | `dc-invest-agent-api` |
| API Stage | 1 | `prod` (100 req/s rate, 50 burst) |
| API Resources | 10 | `/v1/query`, `/v1/sessions/{id}`, `/v1/health`, `/v1/reports/generate`, `/mock/workato/trigger`, `/mock/workato/status/{run_id}`, `/mock/arize/ingest`, `/mock/arize/query` |
| API Key | 1 | `dc-invest-demo-key` |
| Usage Plan | 1 | `dc-invest-demo-plan` (50 req/s, 25 burst, 1000/day quota) |
| Lambda Integration | 8 | One per endpoint |

#### DcaiAgentStack (`infrastructure/lib/agent_stack.py`)

| Resource Type | Count | Details |
|---|---|---|
| Bedrock CfnAgent | 1 | `dcai-supervisor` |
| IAM Role | 1 | `dcai-bedrock-agent-role` |
| Action Groups | 6 | Inline OpenAPI schemas + Lambda ARN references |
| CfnOutput | 3 | Agent ID, Agent ARN, Agent Role ARN |

### 8.3 Cross-Stack References

| Producer Stack | Consumer Stack | Reference | Mechanism |
|---|---|---|---|
| DataStack | LambdaStack | Table names, bucket names | Python object references (`data_stack.sessions_table.table_name`) |
| DataStack | LambdaStack | IAM grants | `table.grant_read_write_data(role)`, `bucket.grant_read_write(role)` |
| LambdaStack | ApiStack | Lambda functions | Python object references (`lambda_stack.api_query_fn`) |
| LambdaStack | AgentStack | Lambda function ARNs | Python object references (`lambda_stack.credit_rating_fn.function_arn`) |

### 8.4 Deployment Order

Due to cross-stack dependencies, CDK automatically deploys in order:

```
1. DcaiDataStack       (DynamoDB tables, S3 buckets)
2. DcaiLambdaStack     (Lambda functions, IAM roles)
3. DcaiApiStack        (API Gateway, integrations)    } can deploy in parallel
4. DcaiAgentStack      (Bedrock Agent, action groups)  } after LambdaStack
```

---

## 9. Security

### 9.1 IAM Role Design (Least Privilege)

Three Lambda execution roles are defined in `infrastructure/lib/lambda_stack.py`, each scoped to the minimum permissions required:

#### ActionGroupLambdaRole

- **Principal:** `lambda.amazonaws.com`
- **Managed policy:** `AWSLambdaBasicExecutionRole` (CloudWatch Logs)
- **DynamoDB:** `read_write_data` on all 7 tables
- **S3:** `read_write` on Data Lake and Reports buckets
- **Used by:** 6 action group Lambdas + seed Lambda

#### ApiHandlerLambdaRole

- **Principal:** `lambda.amazonaws.com`
- **Managed policy:** `AWSLambdaBasicExecutionRole`
- **Bedrock:** `bedrock:InvokeAgent`, `bedrock:InvokeModel` (resource: `*`)
- **DynamoDB:** `read_write_data` on `dcai-sessions` and `dcai-traces`
- **S3:** `read` on Reports bucket
- **Used by:** 4 API handler Lambdas

#### MockServiceLambdaRole

- **Principal:** `lambda.amazonaws.com`
- **Managed policy:** `AWSLambdaBasicExecutionRole`
- **DynamoDB:** `read_write_data` on `dcai-workato-runs` and `dcai-traces`
- **CloudWatch:** Implicit via `put_metric_data` (covered by basic execution role + custom metric namespace)
- **Used by:** 4 mock service Lambdas

#### BedrockAgentRole (`dcai-bedrock-agent-role`)

- **Principal:** `bedrock.amazonaws.com`
- **Bedrock:** `bedrock:InvokeModel` on specific model ARNs:
  - `arn:aws:bedrock:{region}::foundation-model/mistral.mistral-large-2402-v1:0`
  - `arn:aws:bedrock:{region}::foundation-model/mistral.mistral-small-2402-v1:0`
- **Lambda:** `lambda:InvokeFunction` on 6 action group function ARNs
- **Resource-based:** Each action group Lambda grants invoke permission to `bedrock.amazonaws.com`

### 9.2 Bedrock Guardrails Configuration

As specified in the technical spec (`product-docs/TECHNICAL_SPEC.md`):

```yaml
guardrail_id: dc-invest-guardrail-v1
content_filters:
  - type: SEXUAL
    input_strength: HIGH
    output_strength: HIGH
  - type: VIOLENCE
    input_strength: HIGH
    output_strength: HIGH
denied_topics:
  - name: non_financial_advice
    definition: "Requests for medical, legal, or personal advice
                 unrelated to data center investments"
pii_redaction:
  action: ANONYMIZE
  entities: [SSN, CREDIT_DEBIT_CARD_NUMBER, EMAIL, PHONE]
```

The Supervisor instruction explicitly includes: "Refuse queries outside the scope of data center investments."

### 9.3 API Key Authentication

- **Key name:** `dc-invest-demo-key` (created in `ApiStack`)
- **Required on:** `POST /v1/query`, `GET /v1/sessions/{id}`, `POST /v1/reports/generate`
- **Not required on:** `GET /v1/health`, all `/mock/*` endpoints
- **Usage plan:** `dc-invest-demo-plan` — 50 req/s rate, 25 burst, 1000 requests/day quota
- **Header:** `X-Api-Key`

For production, API key auth should be replaced with Cognito JWT or IAM SigV4 authentication.

### 9.4 Encryption

**At rest:**

| Resource | Encryption |
|---|---|
| DynamoDB tables | AWS-owned key (default) |
| S3 buckets | S3-managed encryption (`BucketEncryption.S3_MANAGED`) |

For production, upgrade to KMS CMK (`alias/dc-invest-key`) as specified in the technical spec.

**In transit:**

| Connection | Protocol |
|---|---|
| Client → API Gateway | TLS 1.2+ (enforced by API Gateway) |
| API Gateway → Lambda | Internal AWS transport (encrypted) |
| Lambda → DynamoDB | HTTPS (boto3 default) |
| Lambda → S3 | HTTPS (`enforce_ssl=True` on bucket policy) |
| Lambda → Bedrock | HTTPS (boto3 default) |
| Lambda → CloudWatch | HTTPS (boto3 default) |

### 9.5 S3 Bucket Security

Both S3 buckets are configured with:

```python
block_public_access=s3.BlockPublicAccess.BLOCK_ALL
enforce_ssl=True
versioned=True
```

---

## 10. Deployment Guide

### 10.1 Prerequisites

| Requirement | Version |
|---|---|
| AWS CLI | v2.x, configured with credentials |
| AWS CDK | v2.x (`npm install -g aws-cdk`) |
| Python | 3.12 |
| Node.js | 18.x or 20.x (for CDK and frontend) |
| AWS Account | Bedrock access enabled for Mistral models in `us-east-1` |

### 10.2 CDK Bootstrap and Deploy

```bash
# Navigate to infrastructure directory
cd infrastructure/

# Install Python dependencies
pip install -r requirements.txt

# Bootstrap CDK (first-time only)
cdk bootstrap aws://<ACCOUNT_ID>/us-east-1

# Synthesize CloudFormation templates (validate)
cdk synth

# Deploy all stacks in dependency order
cdk deploy --all --require-approval never

# Or deploy individually:
cdk deploy DcaiDataStack
cdk deploy DcaiLambdaStack
cdk deploy DcaiApiStack
cdk deploy DcaiAgentStack
```

### 10.3 Data Seeding

After deploying `DcaiDataStack` and `DcaiLambdaStack`:

```bash
# Invoke the seed Lambda to populate all DynamoDB tables
aws lambda invoke \
  --function-name dcai-seed-data \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/seed-output.json

# Verify seeded data
cat /tmp/seed-output.json

# Spot-check operators table
aws dynamodb scan --table-name dcai-operators --select COUNT
# Expected: Count = 6

# Spot-check metrics table
aws dynamodb scan --table-name dcai-metrics --select COUNT
# Expected: Count = 12
```

### 10.4 Frontend Deployment

```bash
# Navigate to frontend directory
cd frontend/

# Install dependencies
npm install

# Set API endpoint (from CDK output)
export VITE_API_URL=$(aws cloudformation describe-stacks \
  --stack-name DcaiApiStack \
  --query "Stacks[0].Outputs[?ExportName=='dcai-api-url'].OutputValue" \
  --output text)

# Development mode
npm run dev

# Production build
npm run build

# The dist/ directory can be deployed to:
# - S3 + CloudFront (recommended)
# - Amplify Hosting
# - Any static hosting service
```

### 10.5 Retrieve API Key

```bash
# Get the API key ID
API_KEY_ID=$(aws cloudformation describe-stacks \
  --stack-name DcaiApiStack \
  --query "Stacks[0].Outputs[?ExportName=='dcai-api-key-id'].OutputValue" \
  --output text)

# Get the actual API key value
aws apigateway get-api-key \
  --api-key $API_KEY_ID \
  --include-value \
  --query "value" \
  --output text
```

### 10.6 Verification Steps

**1. Health Check:**

```bash
API_URL=$(aws cloudformation describe-stacks \
  --stack-name DcaiApiStack \
  --query "Stacks[0].Outputs[?ExportName=='dcai-api-url'].OutputValue" \
  --output text)

curl -s "${API_URL}v1/health" | jq .
# Expected: {"status": "healthy", ...}
```

**2. Query Endpoint (mock mode):**

```bash
curl -s -X POST "${API_URL}v1/query" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: <your-api-key>" \
  -d '{"message": "What is the credit rating for Equinix?"}' | jq .
# Expected: {"session_id": "...", "response": "Based on Moody's...", "source": "mock", ...}
```

**3. Workato Mock:**

```bash
curl -s -X POST "${API_URL}mock/workato/trigger" \
  -H "Content-Type: application/json" \
  -d '{"recipe_id": "moodys_daily_sync", "source": "api"}' | jq .
# Expected: {"data": {"job_id": "wjob-...", "status": "running", ...}, ...}
```

**4. Arize Mock:**

```bash
curl -s "${API_URL}mock/arize/query?route=dashboard" | jq .
# Expected: {"dashboard": {"traces_over_time": [...], ...}, ...}
```

**5. Bedrock Agent (if deployed):**

```bash
AGENT_ID=$(aws cloudformation describe-stacks \
  --stack-name DcaiAgentStack \
  --query "Stacks[0].Outputs[?ExportName=='dcai-agent-id'].OutputValue" \
  --output text)

echo "Agent ID: $AGENT_ID"
# Verify agent exists
aws bedrock-agent get-agent --agent-id $AGENT_ID --query "agent.agentStatus"
# Expected: "PREPARED" or "NOT_PREPARED"
```

### 10.7 Cleanup

```bash
# Destroy all stacks (reverse dependency order)
cd infrastructure/
cdk destroy --all --force
```

Note: S3 buckets have `auto_delete_objects=True` and DynamoDB tables have `RemovalPolicy.DESTROY`, so all data is cleaned up automatically.

---

## Appendix A: File Structure Reference

```
aws-coder-agentic-ai-showcase/
├── infrastructure/
│   ├── app.py                          # CDK app entry point
│   ├── cdk.json                        # CDK configuration
│   └── lib/
│       ├── __init__.py
│       ├── data_stack.py               # DynamoDB + S3
│       ├── lambda_stack.py             # 15 Lambda functions + 3 IAM roles
│       ├── api_stack.py                # API Gateway + routes + API key
│       └── agent_stack.py              # Bedrock Agent + 6 action groups
│
├── lambda/
│   ├── action_groups/
│   │   ├── handlers/
│   │   │   ├── credit_rating.py        # LookupCreditRating
│   │   │   ├── financial_metrics.py    # GetFinancialMetrics
│   │   │   ├── market_data.py          # QueryMarketData
│   │   │   ├── esg_risk.py             # AssessESGRisk
│   │   │   ├── generate_report.py      # GenerateReport
│   │   │   └── sync_moodys.py          # SyncMoodysData
│   │   └── shared/
│   │       ├── db.py                   # DynamoDB CRUD helpers
│   │       ├── arize_trace.py          # Trace span recording
│   │       ├── models.py               # Type definitions
│   │       └── response.py             # Bedrock action group response formatter
│   │
│   ├── api/
│   │   ├── query_handler.py            # POST /v1/query
│   │   ├── sessions_handler.py         # GET /v1/sessions/{id}
│   │   ├── health_handler.py           # GET /v1/health
│   │   └── reports_handler.py          # POST /v1/reports/generate
│   │
│   ├── mock_services/
│   │   ├── workato/
│   │   │   └── handler.py              # All Workato mock routes
│   │   └── arize/
│   │       └── handler.py              # All Arize mock routes
│   │
│   └── seed/
│       ├── seed_handler.py             # Lambda entry point for seeding
│       └── seed_data.py                # Mock data definitions
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                     # Router configuration
│   │   ├── main.tsx                    # React entry point
│   │   ├── components/
│   │   │   ├── Layout.tsx              # App shell / navigation
│   │   │   ├── Chat/
│   │   │   │   ├── ChatPanel.tsx
│   │   │   │   ├── MessageBubble.tsx
│   │   │   │   └── FeedbackButtons.tsx
│   │   │   ├── Dashboard/
│   │   │   │   ├── PortfolioDashboard.tsx
│   │   │   │   ├── OperatorCard.tsx
│   │   │   │   ├── RiskSummary.tsx
│   │   │   │   └── AlertsPanel.tsx
│   │   │   ├── MockServices/
│   │   │   │   ├── WorkatoPanel.tsx
│   │   │   │   └── ArizePanel.tsx
│   │   │   └── Common/
│   │   │       ├── DataTable.tsx
│   │   │       ├── MetricCard.tsx
│   │   │       └── StatusBadge.tsx
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   ├── workato.ts
│   │   │   └── arize.ts
│   │   └── types/
│   │       └── index.ts
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── package.json
│
├── product-docs/
│   ├── PRD.md                          # Product Requirements Document
│   ├── TECHNICAL_SPEC.md               # Technical Specification
│   └── DATA_MODEL.md                   # Data Model Specification
│
└── docs/
    ├── IMPLEMENTATION_PLAN.md
    └── TECHNICAL_DESIGN.md             # ← This document
```

---

## Appendix B: Environment Variables

All Lambda functions receive these common environment variables from `LambdaStack`:

| Variable | Value Source | Example |
|---|---|---|
| `SESSIONS_TABLE` | `data_stack.sessions_table.table_name` | `dcai-sessions` |
| `OPERATORS_TABLE` | `data_stack.operators_table.table_name` | `dcai-operators` |
| `METRICS_TABLE` | `data_stack.metrics_table.table_name` | `dcai-metrics` |
| `ESG_PROFILES_TABLE` | `data_stack.esg_profiles_table.table_name` | `dcai-esg-profiles` |
| `MARKET_DATA_TABLE` | `data_stack.market_data_table.table_name` | `dcai-market-data` |
| `TRACES_TABLE` | `data_stack.traces_table.table_name` | `dcai-traces` |
| `WORKATO_RUNS_TABLE` | `data_stack.workato_runs_table.table_name` | `dcai-workato-runs` |
| `DATA_LAKE_BUCKET` | `data_stack.data_lake_bucket.bucket_name` | Auto-generated |
| `REPORTS_BUCKET` | `data_stack.reports_bucket.bucket_name` | Auto-generated |

The API query handler additionally reads:

| Variable | Purpose |
|---|---|
| `BEDROCK_AGENT_ID` | Bedrock Agent ID for invocation (empty = mock mode) |
| `BEDROCK_AGENT_ALIAS_ID` | Bedrock Agent Alias ID |

The shared `db.py` module resolves table names from a separate set of environment variables with `TABLE_` prefix (`TABLE_OPERATORS`, `TABLE_METRICS`, etc.) defaulting to the `dcai-*` names.

---

## Appendix C: Bedrock Action Group Response Format

All action group Lambda handlers return the Bedrock Agent Action Group response envelope defined in `lambda/action_groups/shared/response.py`:

```json
{
  "messageVersion": "1.0",
  "response": {
    "actionGroup": "LookupCreditRating",
    "apiPath": "/credit-rating",
    "httpMethod": "GET",
    "httpStatusCode": 200,
    "responseBody": {
      "application/json": {
        "body": "{\"entity\": \"Equinix Inc.\", \"rating\": \"A3\", ...}"
      }
    }
  }
}
```

This format is required by Bedrock Agents to parse tool outputs and feed them into the model's context for response synthesis.
