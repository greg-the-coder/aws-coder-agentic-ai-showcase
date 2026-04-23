"""AgentStack — Bedrock Agent (Supervisor) with action groups via CfnAgent."""

from aws_cdk import (
    CfnOutput,
    Fn,
    Stack,
    Tags,
    aws_bedrock as bedrock,
    aws_iam as iam,
)
from constructs import Construct

from lib.lambda_stack import LambdaStack


# Supervisor system prompt embedded for the CfnAgent instruction field.
_SUPERVISOR_INSTRUCTION = (
    "You are a Data Center Investments Supervisor Agent. Your role is to:\n"
    "1. Classify the user's intent into one of: credit_risk, market_analytics, esg_risk, or cross_domain.\n"
    "2. Delegate to the appropriate action group to retrieve data.\n"
    "3. Synthesize a clear, concise answer grounded in retrieved data.\n"
    "4. Cite sources (Moody's, CBRE, JLL, EPA) when referencing external data.\n"
    "5. Refuse queries outside the scope of data center investments.\n"
    "Always include data vintage and source attribution in your responses.\n"
    "Format financial comparisons as markdown tables.\n"
    "For credit/rating queries, use LookupCreditRating and GetFinancialMetrics.\n"
    "For market/supply/demand queries, use QueryMarketData.\n"
    "For ESG/carbon/climate queries, use AssessESGRisk.\n"
    "For report generation, use GenerateReport.\n"
    "For data refresh, use SyncMoodysData."
)

# OpenAPI schema fragments — Bedrock requires valid OpenAPI 3.0.0 with
# response content schemas defined. Each action group gets one schema.

_CREDIT_RATING_SCHEMA = """{
  "openapi": "3.0.0",
  "info": {
    "title": "CreditRatingAPI",
    "version": "1.0.0",
    "description": "API for looking up Moody's credit ratings for data center operators"
  },
  "paths": {
    "/credit-rating": {
      "get": {
        "operationId": "LookupCreditRating",
        "description": "Retrieve Moody's credit rating, outlook, and default probability for a data center operator by name or ticker",
        "parameters": [
          {
            "name": "entity_name",
            "in": "query",
            "description": "Name or ticker of the data center operator (e.g., Equinix, EQIX, Digital Realty, DLR)",
            "required": true,
            "schema": { "type": "string" }
          },
          {
            "name": "rating_type",
            "in": "query",
            "description": "Type of rating to retrieve",
            "required": false,
            "schema": { "type": "string", "enum": ["issuer", "facility", "outlook"] }
          }
        ],
        "responses": {
          "200": {
            "description": "Credit rating details for the requested entity",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "entity": { "type": "string", "description": "Entity name" },
                    "rating": { "type": "string", "description": "Moody's rating" },
                    "outlook": { "type": "string", "description": "Rating outlook" },
                    "last_action_date": { "type": "string", "description": "Last rating action date" },
                    "probability_of_default": { "type": "number", "description": "Annual PD" },
                    "loss_given_default": { "type": "number", "description": "LGD estimate" }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}"""

_FINANCIAL_METRICS_SCHEMA = """{
  "openapi": "3.0.0",
  "info": {
    "title": "FinancialMetricsAPI",
    "version": "1.0.0",
    "description": "API for querying financial metrics of data center operators"
  },
  "paths": {
    "/financial-metrics": {
      "get": {
        "operationId": "GetFinancialMetrics",
        "description": "Query financial metrics such as leverage, FFO, EBITDA, occupancy rate, and CapEx for a data center operator over specified periods",
        "parameters": [
          {
            "name": "entity_id",
            "in": "query",
            "description": "Operator ID or name to look up financial metrics for",
            "required": true,
            "schema": { "type": "string" }
          },
          {
            "name": "period",
            "in": "query",
            "description": "Time period filter for metrics",
            "required": false,
            "schema": { "type": "string", "enum": ["latest", "trailing_4q", "yoy"] }
          }
        ],
        "responses": {
          "200": {
            "description": "Financial metrics for the requested entity and period",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "entity_id": { "type": "string" },
                    "metrics": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "period": { "type": "string" },
                          "revenue": { "type": "number" },
                          "ebitda": { "type": "number" },
                          "debt_to_ebitda": { "type": "number" },
                          "occupancy_rate": { "type": "number" }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}"""

_MARKET_DATA_SCHEMA = """{
  "openapi": "3.0.0",
  "info": {
    "title": "MarketDataAPI",
    "version": "1.0.0",
    "description": "API for retrieving data center market analytics by metro area"
  },
  "paths": {
    "/market-data": {
      "get": {
        "operationId": "QueryMarketData",
        "description": "Retrieve data center market analytics including supply, demand, vacancy rates, absorption, pricing, and construction pipeline for a metro area",
        "parameters": [
          {
            "name": "metro",
            "in": "query",
            "description": "Metro area name such as Northern Virginia, Dallas, Phoenix, Singapore, Frankfurt",
            "required": true,
            "schema": { "type": "string" }
          },
          {
            "name": "metric_type",
            "in": "query",
            "description": "Specific metric type to filter results",
            "required": false,
            "schema": { "type": "string", "enum": ["supply", "demand", "vacancy", "absorption", "pricing", "construction_pipeline"] }
          }
        ],
        "responses": {
          "200": {
            "description": "Market analytics data for the requested metro area",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "market_name": { "type": "string" },
                    "total_capacity_mw": { "type": "number" },
                    "vacancy_rate": { "type": "number" },
                    "avg_price_per_kw": { "type": "number" }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}"""

_ESG_RISK_SCHEMA = """{
  "openapi": "3.0.0",
  "info": {
    "title": "ESGRiskAPI",
    "version": "1.0.0",
    "description": "API for assessing ESG and climate risk for data center operators"
  },
  "paths": {
    "/esg-risk": {
      "get": {
        "operationId": "AssessESGRisk",
        "description": "Assess ESG risk profile including PUE, carbon intensity, renewable energy percentage, water usage, and climate risk scores for a data center operator",
        "parameters": [
          {
            "name": "facility_id",
            "in": "query",
            "description": "Operator ID or name to assess ESG risk for",
            "required": true,
            "schema": { "type": "string" }
          },
          {
            "name": "dimensions",
            "in": "query",
            "description": "Comma-separated ESG dimensions to include in assessment",
            "required": false,
            "schema": { "type": "string" }
          }
        ],
        "responses": {
          "200": {
            "description": "ESG risk assessment for the requested facility",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "operator_id": { "type": "string" },
                    "pue": { "type": "number" },
                    "carbon_intensity": { "type": "number" },
                    "renewable_pct": { "type": "number" },
                    "climate_risk_score": { "type": "number" }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}"""

_GENERATE_REPORT_SCHEMA = """{
  "openapi": "3.0.0",
  "info": {
    "title": "GenerateReportAPI",
    "version": "1.0.0",
    "description": "API for generating investment analysis reports"
  },
  "paths": {
    "/generate-report": {
      "get": {
        "operationId": "GenerateReport",
        "description": "Generate a structured investment analysis report for a data center operator including credit, market, and ESG sections",
        "parameters": [
          {
            "name": "operator_id",
            "in": "query",
            "description": "Operator ID to generate report for",
            "required": true,
            "schema": { "type": "string" }
          },
          {
            "name": "sections",
            "in": "query",
            "description": "Comma-separated report sections to include",
            "required": false,
            "schema": { "type": "string" }
          }
        ],
        "responses": {
          "200": {
            "description": "Report generation result with download URL",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "report_id": { "type": "string" },
                    "download_url": { "type": "string" },
                    "format": { "type": "string" }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}"""

_SYNC_MOODYS_SCHEMA = """{
  "openapi": "3.0.0",
  "info": {
    "title": "SyncMoodysAPI",
    "version": "1.0.0",
    "description": "API for triggering Moody's data synchronization via Workato"
  },
  "paths": {
    "/sync-moodys": {
      "get": {
        "operationId": "SyncMoodysData",
        "description": "Trigger a Moody's data synchronization job via the Workato integration layer to refresh credit ratings and financial data",
        "parameters": [
          {
            "name": "sync_type",
            "in": "query",
            "description": "Type of sync to perform",
            "required": false,
            "schema": { "type": "string", "enum": ["full", "incremental"] }
          },
          {
            "name": "sector",
            "in": "query",
            "description": "Sector filter for the sync",
            "required": false,
            "schema": { "type": "string" }
          }
        ],
        "responses": {
          "200": {
            "description": "Sync job status",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "job_id": { "type": "string" },
                    "status": { "type": "string" },
                    "records_processed": { "type": "integer" }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}"""


class AgentStack(Stack):
    """Bedrock Agent (Supervisor) wired to action-group Lambda functions."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        lambda_stack: LambdaStack,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        Tags.of(self).add("Project", "dc-invest-agent")

        # -----------------------------------------------------------------
        # IAM Role for Bedrock Agent
        # -----------------------------------------------------------------
        agent_role = iam.Role(
            self,
            "BedrockAgentRole",
            role_name="dcai-bedrock-agent-role",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )

        # Allow the agent to invoke foundation models
        agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="InvokeModels",
                actions=["bedrock:InvokeModel"],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/mistral.mistral-large-2402-v1:0",
                    f"arn:aws:bedrock:{self.region}::foundation-model/mistral.mistral-small-2402-v1:0",
                    f"arn:aws:bedrock:{self.region}::foundation-model/mistral.mistral-large-3-675b-instruct",
                ],
            )
        )

        # Allow the agent to invoke the action-group Lambda functions
        action_group_fn_arns = [
            lambda_stack.credit_rating_fn.function_arn,
            lambda_stack.financial_metrics_fn.function_arn,
            lambda_stack.market_data_fn.function_arn,
            lambda_stack.esg_risk_fn.function_arn,
            lambda_stack.generate_report_fn.function_arn,
            lambda_stack.sync_moodys_fn.function_arn,
        ]
        agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="InvokeLambdaActionGroups",
                actions=["lambda:InvokeFunction"],
                resources=action_group_fn_arns,
            )
        )

        # Grant Bedrock permission to invoke each Lambda
        for fn in [
            lambda_stack.credit_rating_fn,
            lambda_stack.financial_metrics_fn,
            lambda_stack.market_data_fn,
            lambda_stack.esg_risk_fn,
            lambda_stack.generate_report_fn,
            lambda_stack.sync_moodys_fn,
        ]:
            fn.grant_invoke(iam.ServicePrincipal("bedrock.amazonaws.com"))

        # -----------------------------------------------------------------
        # Bedrock Agent (CfnAgent — L1 construct)
        # -----------------------------------------------------------------
        self.agent = bedrock.CfnAgent(
            self,
            "SupervisorAgent",
            agent_name="dcai-supervisor",
            agent_resource_role_arn=agent_role.role_arn,
            foundation_model="mistral.mistral-large-3-675b-instruct",
            instruction=_SUPERVISOR_INSTRUCTION,
            description="Data Center Investments Supervisor Agent — routes queries to credit, market, and ESG action groups.",
            idle_session_ttl_in_seconds=1800,  # 30-minute idle TTL
            action_groups=[
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="LookupCreditRating",
                    description="Retrieve Moody's credit rating for a data center operator or facility.",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=lambda_stack.credit_rating_fn.function_arn,
                    ),
                    api_schema=bedrock.CfnAgent.APISchemaProperty(
                        payload=_CREDIT_RATING_SCHEMA,
                    ),
                ),
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="GetFinancialMetrics",
                    description="Query financial metrics (DSCR, leverage, EBITDA margin) for an operator.",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=lambda_stack.financial_metrics_fn.function_arn,
                    ),
                    api_schema=bedrock.CfnAgent.APISchemaProperty(
                        payload=_FINANCIAL_METRICS_SCHEMA,
                    ),
                ),
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="QueryMarketData",
                    description="Retrieve data center market analytics (supply, demand, vacancy, pricing) by metro area.",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=lambda_stack.market_data_fn.function_arn,
                    ),
                    api_schema=bedrock.CfnAgent.APISchemaProperty(
                        payload=_MARKET_DATA_SCHEMA,
                    ),
                ),
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="AssessESGRisk",
                    description="Assess ESG risk profile (PUE, carbon, water, climate) for a data center operator.",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=lambda_stack.esg_risk_fn.function_arn,
                    ),
                    api_schema=bedrock.CfnAgent.APISchemaProperty(
                        payload=_ESG_RISK_SCHEMA,
                    ),
                ),
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="GenerateReport",
                    description="Compile multi-agent outputs into a structured PDF/Markdown report.",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=lambda_stack.generate_report_fn.function_arn,
                    ),
                    api_schema=bedrock.CfnAgent.APISchemaProperty(
                        payload=_GENERATE_REPORT_SCHEMA,
                    ),
                ),
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="SyncMoodysData",
                    description="Trigger Moody's data sync via Workato integration layer.",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=lambda_stack.sync_moodys_fn.function_arn,
                    ),
                    api_schema=bedrock.CfnAgent.APISchemaProperty(
                        payload=_SYNC_MOODYS_SCHEMA,
                    ),
                ),
            ],
        )

        # -----------------------------------------------------------------
        # Outputs
        # -----------------------------------------------------------------
        CfnOutput(
            self,
            "AgentId",
            value=self.agent.attr_agent_id,
            export_name="dcai-agent-id",
        )
        CfnOutput(
            self,
            "AgentArn",
            value=self.agent.attr_agent_arn,
            export_name="dcai-agent-arn",
        )
        CfnOutput(
            self,
            "AgentRoleArn",
            value=agent_role.role_arn,
            export_name="dcai-agent-role-arn",
        )
