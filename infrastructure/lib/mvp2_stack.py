"""Mvp2Stack — Self-contained deployment for AgentCore MVP-2 demo.

Deploys a completely independent stack with:
  - AgentCore supervisor Lambda (Strands SDK)
  - Dedicated API Gateway (REST)
  - Dedicated CloudFront distribution
  - Reuses existing DynamoDB tables and S3 buckets from DcaiDataStack

This preserves the existing running demo application untouched.
"""

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    Tags,
    aws_apigateway as apigw,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
)
from constructs import Construct


class Mvp2Stack(Stack):
    """Self-contained MVP-2 stack: AgentCore Lambda + API GW + CloudFront.

    Does NOT modify any existing stacks or resources. Reads from the shared
    DynamoDB tables deployed by DcaiDataStack.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        Tags.of(self).add("Project", "dc-invest-agent-mvp2")

        # -----------------------------------------------------------------
        # Reference existing DynamoDB tables by name (no cross-stack coupling)
        # -----------------------------------------------------------------
        table_names = {
            "TABLE_OPERATORS": "dcai-operators",
            "TABLE_METRICS": "dcai-metrics",
            "TABLE_ESG": "dcai-esg-profiles",
            "TABLE_MARKET": "dcai-market-data",
            "TABLE_SESSIONS": "dcai-sessions",
            "TABLE_TRACES": "dcai-traces",
            "TABLE_WORKATO_RUNS": "dcai-workato-runs",
        }

        # Reference existing S3 buckets
        reports_bucket_name = "dcaidatastack-reportsbucket4e7c5994-oiqnnizx3yjo"

        # -----------------------------------------------------------------
        # Lambda Layer — Strands Agents SDK dependencies
        # -----------------------------------------------------------------
        agent_deps_layer = _lambda.LayerVersion(
            self,
            "Mvp2AgentDepsLayer",
            layer_version_name="dcai-mvp2-agentcore-deps",
            description="Strands Agents SDK deps for MVP-2",
            code=_lambda.Code.from_asset("../layers/agentcore_deps"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            removal_policy=RemovalPolicy.DESTROY,
        )

        # -----------------------------------------------------------------
        # IAM Role — AgentCore supervisor Lambda
        # -----------------------------------------------------------------
        supervisor_role = iam.Role(
            self,
            "Mvp2SupervisorRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # DynamoDB read/write on all tables
        supervisor_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchGetItem",
                ],
                resources=[
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/dcai-*",
                ],
            )
        )

        # S3 read/write on reports bucket
        supervisor_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
                resources=[
                    f"arn:aws:s3:::{reports_bucket_name}",
                    f"arn:aws:s3:::{reports_bucket_name}/*",
                ],
            )
        )

        # Bedrock InvokeModel for Mistral models
        supervisor_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/mistral.*",
                ],
            )
        )

        # CloudWatch PutMetricData
        supervisor_role.add_to_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
            )
        )

        # -----------------------------------------------------------------
        # AgentCore Supervisor Lambda
        # -----------------------------------------------------------------
        self.supervisor_fn = _lambda.Function(
            self,
            "Mvp2SupervisorFn",
            function_name="dcai-mvp2-agentcore-supervisor",
            handler="agent.handler.handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset(
                "../agent_deploy",
            ),
            role=supervisor_role,
            memory_size=1024,
            timeout=Duration.seconds(90),
            environment={
                **table_names,
                "BUCKET_REPORTS": reports_bucket_name,
                "BEDROCK_MODEL_ID": "mistral.mistral-large-2402-v1:0",
                "WORKATO_ENDPOINT": "",  # Will be set after API is created
                "ARIZE_ENDPOINT": "",    # Will be set after API is created
                "AWS_REGION_NAME": "us-east-1",
            },
            layers=[agent_deps_layer],
            log_retention=logs.RetentionDays.TWO_WEEKS,
        )

        # -----------------------------------------------------------------
        # IAM Role — API handler Lambda (thin proxy)
        # -----------------------------------------------------------------
        api_handler_role = iam.Role(
            self,
            "Mvp2ApiHandlerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # Allow invoking the supervisor Lambda
        self.supervisor_fn.grant_invoke(api_handler_role)

        # DynamoDB read/write for sessions and health checks
        api_handler_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:DescribeTable",
                ],
                resources=[
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/dcai-*",
                ],
            )
        )

        # Bedrock (fallback path)
        api_handler_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeAgent", "bedrock:InvokeModel"],
                resources=["*"],
            )
        )

        # -----------------------------------------------------------------
        # API Query Handler Lambda (routes to AgentCore supervisor)
        # -----------------------------------------------------------------
        self.query_handler_fn = _lambda.Function(
            self,
            "Mvp2QueryHandlerFn",
            function_name="dcai-mvp2-api-query",
            handler="query_handler.handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset("../lambda/api"),
            role=api_handler_role,
            memory_size=512,
            timeout=Duration.seconds(95),
            environment={
                **table_names,
                "AGENTCORE_FUNCTION_NAME": "dcai-mvp2-agentcore-supervisor",
                "BEDROCK_AGENT_ID": "",
                "BEDROCK_AGENT_ALIAS_ID": "",
            },
            log_retention=logs.RetentionDays.TWO_WEEKS,
        )

        # -----------------------------------------------------------------
        # API Health Handler Lambda
        # -----------------------------------------------------------------
        self.health_handler_fn = _lambda.Function(
            self,
            "Mvp2HealthHandlerFn",
            function_name="dcai-mvp2-api-health",
            handler="health_handler.handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset("../lambda/api"),
            role=api_handler_role,
            memory_size=128,
            timeout=Duration.seconds(10),
            environment=table_names,
            log_retention=logs.RetentionDays.TWO_WEEKS,
        )

        # -----------------------------------------------------------------
        # Mock Workato Handler Lambda
        # -----------------------------------------------------------------
        mock_role = iam.Role(
            self,
            "Mvp2MockRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )
        mock_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                ],
                resources=[
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/dcai-*",
                ],
            )
        )
        mock_role.add_to_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
            )
        )

        self.mock_workato_fn = _lambda.Function(
            self,
            "Mvp2MockWorkatoFn",
            function_name="dcai-mvp2-mock-workato",
            handler="handler.handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset("../lambda/mock_services/workato"),
            role=mock_role,
            memory_size=256,
            timeout=Duration.seconds(15),
            environment=table_names,
            log_retention=logs.RetentionDays.TWO_WEEKS,
        )

        self.mock_arize_fn = _lambda.Function(
            self,
            "Mvp2MockArizeFn",
            function_name="dcai-mvp2-mock-arize",
            handler="handler.handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset("../lambda/mock_services/arize"),
            role=mock_role,
            memory_size=256,
            timeout=Duration.seconds(15),
            environment={**table_names, "TABLE_TRACES": "dcai-traces"},
            log_retention=logs.RetentionDays.TWO_WEEKS,
        )

        # -----------------------------------------------------------------
        # REST API Gateway — MVP-2 dedicated
        # -----------------------------------------------------------------
        self.api = apigw.RestApi(
            self,
            "Mvp2Api",
            rest_api_name="dc-invest-agent-mvp2-api",
            description="DC Investments Agent MVP-2 — AgentCore + Strands SDK",
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

        # /v1 routes
        v1 = self.api.root.add_resource("v1")

        query_resource = v1.add_resource("query")
        query_resource.add_method(
            "POST",
            apigw.LambdaIntegration(self.query_handler_fn),
            api_key_required=False,
        )

        health_resource = v1.add_resource("health")
        health_resource.add_method(
            "GET",
            apigw.LambdaIntegration(self.health_handler_fn),
            api_key_required=False,
        )

        # /mock routes
        mock_resource = self.api.root.add_resource("mock")

        workato_resource = mock_resource.add_resource("workato")
        workato_resource.add_proxy(
            default_integration=apigw.LambdaIntegration(self.mock_workato_fn),
            any_method=True,
        )
        workato_resource.add_method(
            "GET",
            apigw.LambdaIntegration(self.mock_workato_fn),
        )
        workato_resource.add_method(
            "POST",
            apigw.LambdaIntegration(self.mock_workato_fn),
        )

        arize_resource = mock_resource.add_resource("arize")
        arize_resource.add_proxy(
            default_integration=apigw.LambdaIntegration(self.mock_arize_fn),
            any_method=True,
        )
        arize_resource.add_method(
            "GET",
            apigw.LambdaIntegration(self.mock_arize_fn),
        )
        arize_resource.add_method(
            "POST",
            apigw.LambdaIntegration(self.mock_arize_fn),
        )

        # Note: WORKATO_ENDPOINT and ARIZE_ENDPOINT left empty at deploy time.
        # The supervisor agent works without them (tools return data directly).
        # Set post-deployment if mock tracing is needed:
        #   aws lambda update-function-configuration --function-name dcai-mvp2-agentcore-supervisor \
        #     --environment "Variables={...,WORKATO_ENDPOINT=https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/mock/workato}"

        # -----------------------------------------------------------------
        # S3 bucket for MVP-2 frontend
        # -----------------------------------------------------------------
        self.website_bucket = s3.Bucket(
            self,
            "Mvp2WebsiteBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # -----------------------------------------------------------------
        # CloudFront Distribution — MVP-2 dedicated
        # -----------------------------------------------------------------
        self.distribution = cloudfront.Distribution(
            self,
            "Mvp2Distribution",
            comment="DC Investments Agent — MVP-2 (AgentCore + Strands SDK)",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    self.website_bucket,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
            ),
            additional_behaviors={
                "/v1/*": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        f"{self.api.rest_api_id}.execute-api.{self.region}.amazonaws.com",
                        origin_path="/prod",
                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                ),
                "/mock/*": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        f"{self.api.rest_api_id}.execute-api.{self.region}.amazonaws.com",
                        origin_path="/prod",
                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                ),
            },
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
            ],
        )

        # -----------------------------------------------------------------
        # Deploy frontend to MVP-2 bucket
        # -----------------------------------------------------------------
        s3deploy.BucketDeployment(
            self,
            "Mvp2DeploySite",
            sources=[s3deploy.Source.asset("../frontend/dist")],
            destination_bucket=self.website_bucket,
            distribution=self.distribution,
            distribution_paths=["/*"],
        )

        # -----------------------------------------------------------------
        # Outputs
        # -----------------------------------------------------------------
        CfnOutput(
            self,
            "Mvp2CloudFrontURL",
            value=f"https://{self.distribution.distribution_domain_name}",
            description="MVP-2 CloudFront URL — AgentCore demo",
            export_name="dcai-mvp2-cloudfront-url",
        )
        CfnOutput(
            self,
            "Mvp2ApiUrl",
            value=self.api.url,
            export_name="dcai-mvp2-api-url",
        )
        CfnOutput(
            self,
            "Mvp2SupervisorArn",
            value=self.supervisor_fn.function_arn,
            export_name="dcai-mvp2-supervisor-arn",
        )
        CfnOutput(
            self,
            "Mvp2DistributionId",
            value=self.distribution.distribution_id,
            export_name="dcai-mvp2-distribution-id",
        )
