# Data Center Investments Agent — MVP 2 (AgentCore Branch)

AI-powered multi-agent system for data center sector investment analysis, built on **AWS Bedrock AgentCore** with **Strands Agents SDK** and **Mistral Large 3**.

This branch (`coder-agents-mvp-2`) enhances the original solution by deploying the agent logic on a Strands SDK-based runtime (stepping stone to full Bedrock AgentCore managed runtime), while preserving Mistral Large 3 as the LLM, Workato for iPaaS, and Arize for LLM observability.

---

## What's New in MVP-2

| Feature | MVP-1 (main branch) | MVP-2 (this branch) |
|---------|---------------------|---------------------|
| Agent Framework | None (declarative CfnAgent) | **Strands Agents SDK** with `@tool` decorators |
| Agent Runtime | Opaque Bedrock Agent service | Lambda-hosted Strands agent (AgentCore-ready) |
| Tool Execution | 6 separate Lambda functions + OpenAPI schemas | In-process `@tool` functions (single Lambda) |
| Model Control | Implicit (Bedrock Agent calls model) | Explicit `BedrockModel` with full config control |
| Query Routing | Priority: AgentCore > Bedrock Agent > Mock | Cascading fallback chain |
| Session Memory | Basic DynamoDB append | Context-aware (retrieves recent history) |
| Invocation | `invoke_agent()` | `lambda:InvokeFunction` → Strands `agent(message)` |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  FRONTEND — CloudFront + S3                                         │
│  React SPA: Chat | Dashboard | Workato Panel | Arize Panel          │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ POST /v1/query
┌─────────────────────────────▼───────────────────────────────────────┐
│  API LAYER — API Gateway REST (/prod)                                │
│  /v1/* (core) | /mock/workato/* | /mock/arize/*                     │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│  QUERY HANDLER LAMBDA (dcai-api-query)                               │
│  Routes to: AgentCore → Bedrock Agent → Mock (cascade fallback)      │
│  Stores session turns in DynamoDB                                    │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ lambda:InvokeFunction
┌─────────────────────────────▼───────────────────────────────────────┐
│  AGENTCORE SUPERVISOR LAMBDA (dcai-agentcore-supervisor)             │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Strands Agents SDK (Python 3.12)                            │    │
│  │                                                              │    │
│  │  Agent(                                                      │    │
│  │    model = BedrockModel("mistral.mistral-large-2402-v1:0")   │    │
│  │    system_prompt = supervisor_system.txt                      │    │
│  │    tools = [                                                  │    │
│  │      @tool lookup_credit_rating  → DynamoDB                  │    │
│  │      @tool get_financial_metrics → DynamoDB                  │    │
│  │      @tool query_market_data     → DynamoDB                  │    │
│  │      @tool assess_esg_risk       → DynamoDB                  │    │
│  │      @tool generate_report       → S3                        │    │
│  │      @tool sync_moodys_data      → Workato (mock)            │    │
│  │    ]                                                          │    │
│  │  )                                                            │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│  DATA LAYER                                                          │
│  DynamoDB (7 tables) | S3 (data lake + reports) | CloudWatch        │
└─────────────────────────────────────────────────────────────────────┘

MOCK INTEGRATIONS (preserved):
  ┌──────────────┐     ┌──────────────┐
  │   Workato    │     │    Arize     │
  │  (Mock iPaaS)│     │ (Mock Obs)   │
  └──────────────┘     └──────────────┘
```

---

## Project Structure (New/Changed Files)

```
aws-coder-agentic-ai-showcase/
├── agent/                        # NEW — Strands Agents SDK implementation
│   ├── __init__.py
│   ├── config.py                 # Environment-driven configuration
│   ├── db.py                     # DynamoDB helpers (standalone)
│   ├── handler.py                # Lambda/AgentCore entry point
│   ├── requirements.txt          # strands-agents, strands-agents-bedrock, boto3
│   ├── supervisor.py             # Agent creation with BedrockModel + tools
│   └── tools/
│       ├── __init__.py
│       ├── credit_rating.py      # @tool lookup_credit_rating
│       ├── financial_metrics.py  # @tool get_financial_metrics
│       ├── market_data.py        # @tool query_market_data
│       ├── esg_risk.py           # @tool assess_esg_risk
│       ├── generate_report.py    # @tool generate_report
│       └── sync_moodys.py        # @tool sync_moodys_data
├── layers/                       # NEW — Lambda layer for agent dependencies
│   └── agentcore_deps/
│       ├── build_layer.sh        # Script to install packages
│       └── python/               # Layer packages directory
├── infrastructure/
│   ├── app.py                    # UPDATED — adds DcaiAgentCoreStack
│   └── lib/
│       ├── agentcore_stack.py    # NEW — AgentCore Lambda + Layer + IAM
│       ├── lambda_stack.py       # UPDATED — query handler routes to AgentCore
│       └── ...                   # (existing stacks unchanged)
├── lambda/
│   └── api/
│       └── query_handler.py      # UPDATED — AgentCore > Bedrock > Mock cascade
└── ...                           # (all other files unchanged)
```

---

## Deployment

### Prerequisites (same as MVP-1 plus)

- Strands Agents SDK packages (installed via layer build script)

### 1. Build the Lambda Layer

```bash
cd layers/agentcore_deps
./build_layer.sh
```

### 2. Deploy all stacks

```bash
cd infrastructure
cdk deploy --all --require-approval never
```

This deploys 6 stacks:

| Stack | Resources |
|-------|-----------|
| `DcaiDataStack` | 7 DynamoDB tables, 2 S3 buckets |
| `DcaiLambdaStack` | API handlers (updated), action group handlers, mock services, seed |
| `DcaiApiStack` | REST API Gateway |
| `DcaiAgentStack` | Bedrock Agent (preserved as fallback) |
| `DcaiAgentCoreStack` | **NEW** — Strands supervisor Lambda + deps layer |
| `DcaiFrontendStack` | CloudFront + S3 |

### 3. Test the AgentCore path

```bash
# Direct invocation of the AgentCore supervisor:
aws lambda invoke \
  --function-name dcai-agentcore-supervisor \
  --payload '{"body": "{\"session_id\": \"test-01\", \"message\": \"What is the credit rating for Equinix?\"}"}' \
  /dev/stdout

# Via the API (routes through query handler → AgentCore):
curl -X POST https://<api-url>/prod/v1/query \
  -H "Content-Type: application/json" \
  -d '{"session_id": "demo-mvp2", "message": "What is the credit rating for Equinix?"}'
```

The response `source` field will show `"agentcore-strands"` when the Strands agent handles the request.

---

## Query Routing (Cascading Fallback)

The query handler uses this priority:

1. **AgentCore** (if `AGENTCORE_FUNCTION_NAME` env var is set) — invokes the Strands SDK supervisor Lambda
2. **Bedrock Agent** (if `BEDROCK_AGENT_ID` is set) — falls back to the original CfnAgent
3. **Mock** — keyword-based classification with static responses

If AgentCore fails, it cascades to Bedrock Agent, then to mock. This ensures the demo always works.

---

## Migration Path to Full AgentCore Runtime

This branch deploys the Strands agent as a Lambda function. The code is structured for minimal changes when migrating to AgentCore managed runtime:

1. **Container/code bundle** — The `agent/` directory is already self-contained; package it as an ECR image or S3 bundle
2. **Endpoint** — Replace `lambda:InvokeFunction` with `bedrock-agentcore:invoke-agent-runtime`
3. **Memory** — Replace DynamoDB session storage with AgentCore Memory service
4. **Gateway** — Route Workato calls through AgentCore Gateway with OAuth2 credentials
5. **Observability** — Add OpenInference instrumentation for Arize integration

---

## License

See [LICENSE](./LICENSE).
