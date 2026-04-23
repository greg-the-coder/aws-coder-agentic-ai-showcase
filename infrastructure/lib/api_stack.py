"""ApiStack — API Gateway REST API with CORS, Lambda integrations, and usage plan."""

from aws_cdk import (
    CfnOutput,
    Duration,
    Stack,
    Tags,
    aws_apigateway as apigw,
)
from constructs import Construct

from lib.lambda_stack import LambdaStack


class ApiStack(Stack):
    """REST API Gateway fronting all Lambda handlers."""

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
        # REST API
        # -----------------------------------------------------------------
        self.api = apigw.RestApi(
            self,
            "DcInvestApi",
            rest_api_name="dc-invest-agent-api",
            description="Data Center Investments Agent — REST API (v2 open-access demo)",
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,
                throttling_burst_limit=50,
            ),
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
            ),
        )

        # -----------------------------------------------------------------
        # /v1 resource tree
        # -----------------------------------------------------------------
        v1 = self.api.root.add_resource("v1")

        # POST /v1/query
        query_resource = v1.add_resource("query")
        query_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.api_query_fn),
            api_key_required=False,  # Open for demo
        )

        # GET /v1/sessions/{id}
        sessions_resource = v1.add_resource("sessions")
        session_id_resource = sessions_resource.add_resource("{id}")
        session_id_resource.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_stack.api_sessions_fn),
            api_key_required=False,  # Open for demo
        )

        # GET /v1/health
        health_resource = v1.add_resource("health")
        health_resource.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_stack.api_health_fn),
            api_key_required=False,
        )

        # POST /v1/reports/generate
        reports_resource = v1.add_resource("reports")
        reports_generate_resource = reports_resource.add_resource("generate")
        reports_generate_resource.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.api_reports_fn),
            api_key_required=False,  # Open for demo
        )

        # -----------------------------------------------------------------
        # /mock resource tree — Workato & Arize mock endpoints
        # -----------------------------------------------------------------
        mock = self.api.root.add_resource("mock")

        # /mock/workato — proxy all routes to the handler
        workato = mock.add_resource("workato")
        workato_proxy = workato.add_proxy(
            default_integration=apigw.LambdaIntegration(lambda_stack.mock_workato_trigger_fn),
            any_method=True,
        )
        # Also add methods on /mock/workato itself
        workato.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_stack.mock_workato_status_fn),
        )
        workato.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.mock_workato_trigger_fn),
        )

        # /mock/arize — proxy all routes to the handler
        arize = mock.add_resource("arize")
        arize_proxy = arize.add_proxy(
            default_integration=apigw.LambdaIntegration(lambda_stack.mock_arize_query_fn),
            any_method=True,
        )
        arize.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_stack.mock_arize_query_fn),
        )
        arize.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_stack.mock_arize_ingest_fn),
        )

        # -----------------------------------------------------------------
        # API Key + Usage Plan (demo)
        # -----------------------------------------------------------------
        api_key = self.api.add_api_key(
            "DcInvestDemoKey",
            api_key_name="dc-invest-demo-key",
            description="Demo API key for the DC Invest Agent MVP",
        )

        usage_plan = self.api.add_usage_plan(
            "DcInvestUsagePlan",
            name="dc-invest-demo-plan",
            description="Demo usage plan — generous limits for testing",
            throttle=apigw.ThrottleSettings(
                rate_limit=50,
                burst_limit=25,
            ),
            quota=apigw.QuotaSettings(
                limit=1000,
                period=apigw.Period.DAY,
            ),
        )
        usage_plan.add_api_key(api_key)
        usage_plan.add_api_stage(stage=self.api.deployment_stage)

        # -----------------------------------------------------------------
        # Outputs
        # -----------------------------------------------------------------
        CfnOutput(self, "ApiUrl", value=self.api.url, export_name="dcai-api-url")
        CfnOutput(self, "ApiId", value=self.api.rest_api_id, export_name="dcai-api-id")
        CfnOutput(
            self,
            "ApiKeyId",
            value=api_key.key_id,
            export_name="dcai-api-key-id",
        )
