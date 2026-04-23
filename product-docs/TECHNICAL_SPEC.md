# Data Center Investments Agent — Technical Specification

**Version:** 1.0.0
**Author:** Platform Engineering
**Status:** Draft

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                   │
│   React Dashboard  ◄──►  API Gateway (REST + WebSocket)  ◄──►  WAF    │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                     AWS BEDROCK AGENTS                                   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              SUPERVISOR AGENT (Mistral Large 2)                 │    │
│  │         intent routing · orchestration · response synthesis     │    │
│  └────┬──────────────────┬──────────────────┬──────────────────────┘    │
│       │                  │                  │                            │
│  ┌────▼─────┐   ┌───────▼────────┐   ┌────▼──────┐                    │
│  │ Credit   │   │  Market        │   │  ESG      │                    │
│  │ Risk     │   │  Analytics     │   │  Risk     │                    │
│  │ Agent    │   │  Agent         │   │  Agent    │                    │
│  │ (Lg 2)   │   │  (Lg 2)        │   │  (Small)  │                    │
│  └────┬─────┘   └───────┬────────┘   └────┬──────┘                    │
│       │                  │                  │                            │
│  ┌────▼─────────────────▼──────────────────▼──────────────────────┐    │
│  │              ACTION GROUPS (Lambda Python 3.12)                 │    │
│  │  LookupCreditRating · GetFinancialMetrics · QueryMarketData    │    │
│  │  AssessESGRisk · GenerateReport · SyncMoodysData               │    │
│  └──────┬──────────────┬──────────────────┬───────────────────────┘    │
│         │              │                  │                             │
│  ┌──────▼──────┐ ┌─────▼───────┐  ┌──────▼──────────────┐             │
│  │  Bedrock    │ │  Bedrock    │  │  Bedrock Guardrails  │             │
│  │  Knowledge  │ │  LLMs       │  │  (content filters,   │             │
│  │  Bases      │ │             │  │   PII redaction)     │             │
│  └──────┬──────┘ └─────────────┘  └──────────────────────┘             │
└─────────┼──────────────────────────────────────────────────────────────┘
          │
┌─────────▼──────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                     │
│                                                                         │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ S3       │  │ OpenSearch │  │ Aurora        │  │ DynamoDB         │  │
│  │ Data Lake│  │ Serverless │  │ PostgreSQL    │  │ Session State    │  │
│  │ (Moody's,│  │ (vectors)  │  │ (financials)  │  │ Conversation Hx  │  │
│  │  docs)   │  │            │  │               │  │                  │  │
│  └──────────┘  └───────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
          │                                              │
┌─────────▼──────────────┐              ┌────────────────▼───────────────┐
│  INTEGRATION LAYER     │              │  OBSERVABILITY                  │
│                        │              │                                 │
│  Workato               │              │  Arize (LLM tracing, evals,    │
│   - Moody's data sync  │              │    prompt monitoring,           │
│   - CRM integration    │              │    embedding drift)             │
│   - Alert distribution │              │  CloudWatch (infra metrics)     │
│                        │              │  X-Ray (distributed tracing)    │
│  EventBridge (events)  │              │                                 │
│  Step Functions (wf)   │              │                                 │
└────────────────────────┘              └────────────────────────────────┘
```

---

## 2. Multi-Agent Architecture

The system uses Bedrock's multi-agent collaboration with a **Supervisor routing pattern**. The Supervisor classifies intent and delegates to the appropriate specialist sub-agent, then synthesizes the final response.

```
                        ┌──────────────────────┐
                        │    User Query         │
                        └──────────┬───────────┘
                                   │
                        ┌──────────▼───────────┐
                        │   SUPERVISOR AGENT    │
                        │   (Mistral Large 2)   │
                        │                       │
                        │  1. Classify intent    │
                        │  2. Route to sub-agent │
                        │  3. Synthesize output  │
                        └──┬───────┬─────────┬──┘
                           │       │         │
            ┌──────────────┘       │         └──────────────┐
            │                      │                        │
  ┌─────────▼────────┐ ┌──────────▼─────────┐ ┌────────────▼──────┐
  │  CREDIT RISK     │ │  MARKET ANALYTICS  │ │  ESG RISK         │
  │  SUB-AGENT       │ │  SUB-AGENT         │ │  SUB-AGENT        │
  │                  │ │                    │ │                    │
  │  Moody's ratings │ │  Supply/demand     │ │  PUE, carbon      │
  │  PD/LGD models   │ │  Pricing trends    │ │  Water usage      │
  │  Financial ratios│ │  Construction pipe │ │  Climate exposure  │
  └──────────────────┘ └────────────────────┘ └────────────────────┘
```

### Routing Logic

| Intent Pattern | Target Agent | Model | Latency Target |
|---|---|---|---|
| Credit ratings, default risk, Moody's data | Credit Risk | Mistral Large 2 (24.07) | < 8s |
| Market pricing, supply pipeline, vacancy | Market Analytics | Mistral Large 2 (24.07) | < 8s |
| Sustainability, PUE, carbon, climate | ESG Risk | Mistral Small (24.02) | < 3s |
| Cross-domain / portfolio-level | Supervisor (fan-out) | Mistral Large 2 (24.07) | < 15s |

---

## 3. Agent Specifications

### 3.1 Supervisor Agent

- **Model:** Mistral Large 2 (24.07) (`mistral.mistral-large-2407-v1:0`)
- **Role:** Intent classification, sub-agent delegation, response synthesis
- **Collaboration mode:** `SUPERVISOR_ROUTER`
- **Guardrail:** `dc-invest-guardrail-v1` (PII redaction, topic denial for non-financial queries)
- **Session:** DynamoDB-backed, 30-minute idle TTL

### 3.2 Credit Risk Agent

- **Model:** Mistral Large 2 (24.07)
- **Knowledge Base:** `kb-credit-risk` — Moody's reports, rating methodologies, default studies
- **Action Groups:** `LookupCreditRating`, `GetFinancialMetrics`, `SyncMoodysData`
- **Capabilities:** Issuer/facility rating lookup, PD/LGD estimation, DSCR/leverage analysis, watch-list monitoring

### 3.3 Market Analytics Agent

- **Model:** Mistral Large 2 (24.07)
- **Knowledge Base:** `kb-market-analytics` — CBRE/JLL reports, construction permits, pricing data
- **Action Groups:** `QueryMarketData`, `GenerateReport`
- **Capabilities:** Supply/demand analysis by metro, pricing trend modeling, construction pipeline tracking, absorption forecasting

### 3.4 ESG Risk Agent

- **Model:** Mistral Small (24.02) (`mistral.mistral-small-2402-v1:0`) — lower cost for structured lookups
- **Knowledge Base:** `kb-esg` — EPA data, ENERGY STAR, climate risk disclosures
- **Action Groups:** `AssessESGRisk`
- **Capabilities:** PUE benchmarking, Scope 1/2/3 carbon estimation, water stress scoring, physical climate risk (flood, heat, wildfire)

---

## 4. Action Groups

### 4.1 LookupCreditRating

```yaml
openapi: 3.0.0
info:
  title: Credit Rating Lookup
  version: 1.0.0
paths:
  /credit-rating:
    get:
      operationId: LookupCreditRating
      summary: Retrieve Moody's credit rating for a data center operator or facility
      parameters:
        - name: entity_name
          in: query
          required: true
          schema: { type: string }
        - name: rating_type
          in: query
          required: false
          schema:
            type: string
            enum: [issuer, facility, outlook]
      responses:
        "200":
          description: Rating details
          content:
            application/json:
              schema:
                type: object
                properties:
                  entity: { type: string }
                  rating: { type: string }
                  outlook: { type: string }
                  last_action_date: { type: string, format: date }
                  probability_of_default: { type: number }
                  loss_given_default: { type: number }
```

### 4.2 GetFinancialMetrics

```yaml
paths:
  /financial-metrics:
    get:
      operationId: GetFinancialMetrics
      summary: Query financial metrics (DSCR, leverage, EBITDA margin) for an entity
      parameters:
        - name: entity_id
          in: query
          required: true
          schema: { type: string }
        - name: metrics
          in: query
          required: false
          schema:
            type: array
            items:
              type: string
              enum: [dscr, leverage, ebitda_margin, revenue_growth, capex_ratio]
        - name: period
          in: query
          schema: { type: string, enum: [latest, trailing_4q, yoy] }
```

### 4.3 QueryMarketData

```yaml
paths:
  /market-data:
    get:
      operationId: QueryMarketData
      summary: Retrieve data center market analytics by metro area
      parameters:
        - name: metro
          in: query
          required: true
          schema: { type: string }
        - name: metric_type
          in: query
          schema:
            type: string
            enum: [supply, demand, vacancy, absorption, pricing, construction_pipeline]
        - name: date_range
          in: query
          schema: { type: string }
```

### 4.4 AssessESGRisk

```yaml
paths:
  /esg-risk:
    post:
      operationId: AssessESGRisk
      summary: Assess ESG risk profile for a data center facility
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [facility_id]
              properties:
                facility_id: { type: string }
                dimensions:
                  type: array
                  items:
                    type: string
                    enum: [pue, carbon, water, climate_physical, climate_transition]
```

### 4.5 GenerateReport / SyncMoodysData

- **GenerateReport:** Compiles multi-agent outputs into structured PDF/Markdown. Triggers Step Functions workflow for assembly, storage to S3, and distribution via Workato.
- **SyncMoodysData:** Invokes Workato recipe to pull latest Moody's rating actions. Writes raw JSON to S3, triggers EventBridge event for downstream processing.

---

## 5. Knowledge Base Configuration

| Knowledge Base | S3 Source Prefix | Chunking | Overlap | Embedding Model |
|---|---|---|---|---|
| `kb-credit-risk` | `s3://dc-invest-docs/moodys/` | Fixed, 512 tokens | 50 tokens | Titan Embeddings V2 |
| `kb-market-analytics` | `s3://dc-invest-docs/market/` | Fixed, 512 tokens | 50 tokens | Titan Embeddings V2 |
| `kb-esg` | `s3://dc-invest-docs/esg/` | Fixed, 256 tokens | 25 tokens | Titan Embeddings V2 |

- **Vector Store:** OpenSearch Serverless collection (`dc-invest-vectors`), `aoss` type
- **Index:** HNSW, `ef_construction=512`, `m=16`, cosine similarity
- **Sync Schedule:** Daily 02:00 UTC via EventBridge rule → Step Functions → `StartIngestionJob`

---

## 6. Workato Integration Layer

### Recipe Patterns

**Moody's Data Sync (scheduled, daily):**

```json
{
  "recipe": "moodys_daily_sync",
  "trigger": {
    "type": "scheduler",
    "cron": "0 1 * * *"
  },
  "steps": [
    {
      "action": "moodys_api.get_rating_actions",
      "params": { "since": "{{last_run_timestamp}}", "sector": "data_centers" }
    },
    {
      "action": "transform.map_fields",
      "mapping": {
        "entity_name": "{{issuer_name}}",
        "rating": "{{long_term_rating}}",
        "outlook": "{{rating_outlook}}",
        "action_date": "{{action_date}}"
      }
    },
    {
      "action": "aws_s3.upload_object",
      "params": {
        "bucket": "dc-invest-docs",
        "key": "moodys/ratings/{{today}}/actions.json"
      }
    },
    {
      "action": "aws_eventbridge.put_event",
      "params": {
        "source": "workato.moodys",
        "detail_type": "RatingActionIngested",
        "detail": "{{step2.output}}"
      }
    }
  ]
}
```

**Alert Distribution (event-driven):**

```json
{
  "recipe": "rating_downgrade_alert",
  "trigger": {
    "type": "webhook",
    "source": "EventBridge → API Destination"
  },
  "steps": [
    { "action": "filter", "condition": "{{event.action_type}} == 'downgrade'" },
    { "action": "salesforce.update_record", "object": "Opportunity", "field_match": "entity_id" },
    { "action": "slack.post_message", "channel": "#dc-credit-alerts" },
    { "action": "email.send", "to": "{{portfolio_manager_email}}", "template": "downgrade_alert" }
  ]
}
```

---

## 7. Arize Observability Setup

### Tracing Configuration

```python
# observability/arize_setup.py
from arize.otel import register
from openinference.instrumentation.bedrock import BedrockInstrumentor

ARIZE_SPACE_ID = "dc-invest-prod"
ARIZE_API_KEY = "{{secrets_manager:arize-api-key}}"

tracer_provider = register(
    space_id=ARIZE_SPACE_ID,
    api_key=ARIZE_API_KEY,
    project_name="dc-invest-agent",
)

BedrockInstrumentor().instrument(tracer_provider=tracer_provider)
```

### Evaluation Templates

| Eval Name | Type | Model | Threshold |
|---|---|---|---|
| `relevance` | RAG retrieval relevance | Mistral Small (24.02) | Score ≥ 0.7 |
| `faithfulness` | Hallucination detection | Mistral Large 2 (24.07) | Score ≥ 0.85 |
| `toxicity` | Content safety | Bedrock Guardrails | 0 violations |
| `latency_p95` | Performance | N/A | < 10s |

### Alert Rules

- **Embedding drift:** Cosine distance > 0.15 from baseline → Slack `#ml-ops`
- **Eval regression:** Rolling 1h `faithfulness` mean < 0.80 → PagerDuty
- **Error rate:** Action Group 5xx > 2% over 5 min → CloudWatch Alarm → SNS

---

## 8. Data Flow Diagrams

### Query Flow

```
User ──► API GW ──► Supervisor Agent ──► classify intent
                                             │
                    ┌────────────────────────┤
                    ▼                        ▼
              Sub-Agent(s)           Knowledge Base
              invoke Action          (RAG retrieval)
              Group Lambda               │
                    │                     │
                    ▼                     ▼
              Aurora / DynamoDB    OpenSearch Serverless
                    │                     │
                    └─────────┬───────────┘
                              ▼
                    Supervisor synthesizes
                              │
                              ▼
                    API GW ──► User
```

### Data Ingestion Flow

```
Workato (Moody's sync) ──► S3 raw/ ──► EventBridge
                                            │
                                            ▼
                                      Step Functions
                                       ┌────┴────┐
                                       ▼         ▼
                                  Aurora      KB Ingestion
                                (structured)  (embeddings →
                                              OpenSearch)
```

---

## 9. API Specifications

### REST Endpoints (API Gateway)

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/v1/query` | Submit natural language query to Supervisor | IAM / Cognito JWT |
| GET | `/v1/sessions/{id}` | Retrieve conversation history | IAM / Cognito JWT |
| POST | `/v1/reports/generate` | Trigger async report generation | IAM |
| GET | `/v1/health` | Service health check | None |

### WebSocket Events

| Event | Direction | Payload |
|---|---|---|
| `query.submit` | Client → Server | `{ "session_id": str, "message": str }` |
| `agent.token` | Server → Client | `{ "token": str, "agent": str }` |
| `agent.complete` | Server → Client | `{ "response": str, "sources": [...] }` |
| `agent.error` | Server → Client | `{ "code": str, "message": str }` |

---

## 10. Infrastructure

### CDK Stack Excerpt

```typescript
// lib/dc-invest-stack.ts
import * as cdk from "aws-cdk-lib";
import * as bedrock from "aws-cdk-lib/aws-bedrock";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as opensearch from "aws-cdk-lib/aws-opensearchserverless";

export class DcInvestAgentStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const vectorCollection = new opensearch.CfnCollection(this, "Vectors", {
      name: "dc-invest-vectors",
      type: "VECTORSEARCH",
    });

    const actionGroupFn = new lambda.Function(this, "CreditRatingFn", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "handlers.credit_rating.handler",
      code: lambda.Code.fromAsset("lambda/action_groups"),
      timeout: cdk.Duration.seconds(30),
      memorySize: 512,
      environment: {
        AURORA_CLUSTER_ARN: auroraCluster.clusterArn,
        ARIZE_SECRET_ARN: arizeSecret.secretArn,
      },
    });
  }
}
```

### VPC Layout

```
VPC (10.0.0.0/16)
├── Public Subnets (10.0.0.0/20)    — ALB, NAT Gateway
├── Private Subnets (10.0.16.0/20)  — Lambda, ECS tasks
├── Isolated Subnets (10.0.32.0/20) — Aurora, OpenSearch
│
├── VPC Endpoints (PrivateLink)
│   ├── com.amazonaws.bedrock-runtime
│   ├── com.amazonaws.s3
│   ├── com.amazonaws.dynamodb
│   ├── com.amazonaws.secretsmanager
│   └── com.amazonaws.execute-api
```

---

## 11. Security Architecture

### IAM Roles

| Role | Principal | Permissions |
|---|---|---|
| `BedrockAgentRole` | Bedrock Agent | `bedrock:InvokeModel`, `s3:GetObject`, `lambda:InvokeFunction` |
| `ActionGroupLambdaRole` | Lambda | `rds-data:ExecuteStatement`, `dynamodb:*Item`, `secretsmanager:GetSecretValue` |
| `KBIngestionRole` | Bedrock KB | `s3:GetObject`, `aoss:APIAccessAll` |

### Encryption

- **At rest:** KMS CMK `alias/dc-invest-key` for S3, DynamoDB, Aurora, OpenSearch
- **In transit:** TLS 1.2+ enforced on all endpoints; PrivateLink for AWS service calls

### Bedrock Guardrails

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
    definition: "Requests for medical, legal, or personal advice unrelated to data center investments"
pii_redaction:
  action: ANONYMIZE
  entities: [SSN, CREDIT_DEBIT_CARD_NUMBER, EMAIL, PHONE]
```

---

## 12. File / Project Structure

```
dc-invest-agent/
├── cdk/
│   ├── app.py
│   ├── cdk.json
│   └── lib/
│       ├── agent_stack.py
│       ├── data_stack.py
│       ├── network_stack.py
│       └── observability_stack.py
├── lambda/
│   ├── action_groups/
│   │   ├── handlers/
│   │   │   ├── credit_rating.py
│   │   │   ├── financial_metrics.py
│   │   │   ├── market_data.py
│   │   │   ├── esg_risk.py
│   │   │   ├── generate_report.py
│   │   │   └── sync_moodys.py
│   │   ├── shared/
│   │   │   ├── db.py
│   │   │   ├── arize_trace.py
│   │   │   └── models.py
│   │   └── requirements.txt
│   └── ingestion/
│       ├── process_moodys.py
│       └── requirements.txt
├── schemas/
│   ├── credit_rating_api.yaml
│   ├── financial_metrics_api.yaml
│   ├── market_data_api.yaml
│   └── esg_risk_api.yaml
├── prompts/
│   ├── supervisor_system.txt
│   ├── credit_risk_system.txt
│   ├── market_analytics_system.txt
│   └── esg_risk_system.txt
├── tests/
│   ├── unit/
│   ├── integration/
│   └── eval/
│       └── ragas_eval.py
├── docs/
│   ├── TECHNICAL_SPEC.md
│   └── runbooks/
├── buildspec.yml
└── README.md
```

---

## 13. Implementation Notes

### Lambda Action Group Handler

```python
# lambda/action_groups/handlers/credit_rating.py
import json
import boto3
from shared.db import execute_query
from shared.arize_trace import init_tracing

tracer = init_tracing("credit-rating-action")

def handler(event, context):
    """Bedrock Agent Action Group handler for LookupCreditRating."""
    agent = event.get("agent", {})
    action_group = event["actionGroup"]
    api_path = event.get("apiPath", "")
    parameters = {p["name"]: p["value"] for p in event.get("parameters", [])}

    entity_name = parameters.get("entity_name", "")
    rating_type = parameters.get("rating_type", "issuer")

    with tracer.start_as_current_span("lookup_credit_rating") as span:
        span.set_attribute("entity_name", entity_name)
        span.set_attribute("rating_type", rating_type)

        result = execute_query(
            "SELECT entity, rating, outlook, action_date, pd, lgd "
            "FROM credit_ratings WHERE entity_name = :name AND type = :type "
            "ORDER BY action_date DESC LIMIT 1",
            {"name": entity_name, "type": rating_type},
        )

        if not result:
            body = {"error": f"No rating found for {entity_name}"}
        else:
            row = result[0]
            body = {
                "entity": row["entity"],
                "rating": row["rating"],
                "outlook": row["outlook"],
                "last_action_date": str(row["action_date"]),
                "probability_of_default": float(row["pd"]),
                "loss_given_default": float(row["lgd"]),
            }

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "apiPath": api_path,
            "httpMethod": "GET",
            "httpStatusCode": 200,
            "responseBody": {"application/json": {"body": json.dumps(body)}},
        },
    }
```

### Chunking Strategy

- **Moody's reports (PDF):** 512-token fixed chunks, 50-token overlap. Metadata extraction: `entity_name`, `rating`, `report_date` injected as OpenSearch fields for hybrid search.
- **Market reports (PDF/XLSX):** 512-token chunks. Tables pre-processed to Markdown before chunking to preserve structure.
- **ESG disclosures:** 256-token chunks (shorter docs, higher precision needed). 25-token overlap.

### Prompt Engineering Guidelines

- System prompts stored in `prompts/` directory, version-controlled, deployed via CDK custom resource.
- All prompts include: role definition, output format constraints (JSON when calling tools), refusal instructions for out-of-scope queries.
- Supervisor prompt includes sub-agent capability summaries to improve routing accuracy.
- Use `<thinking>` tags in prompts for chain-of-thought on complex credit analysis.

### Cost Optimization

| Strategy | Detail |
|---|---|
| Model tiering | Mistral Small for ESG (structured lookups), Mistral Large 2 for credit/market (complex reasoning) |
| Caching | DynamoDB TTL-based response cache for identical queries within 1h window |
| KB retrieval | Top-k=5 with reranking to minimize token consumption |
| Provisioned throughput | Bedrock provisioned throughput for Mistral Large 2 during market hours (8am–6pm ET) |
| Lambda right-sizing | 512 MB for action groups, power-tuned via Lambda Power Tuning |
