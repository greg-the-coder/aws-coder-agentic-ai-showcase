"""LambdaStack — All Lambda functions for action groups, API handlers, mocks, and seeding."""

from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    Tags,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
)
from constructs import Construct

from lib.data_stack import DataStack


class LambdaStack(Stack):
    """Lambda functions for Bedrock action groups, API routing, mock services, and data seeding."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        data_stack: DataStack,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        Tags.of(self).add("Project", "dc-invest-agent")

        # Common environment variables shared by all functions
        common_env = {
            "TABLE_OPERATORS": data_stack.operators_table.table_name,
            "TABLE_METRICS": data_stack.metrics_table.table_name,
            "TABLE_ESG": data_stack.esg_profiles_table.table_name,
            "TABLE_MARKET": data_stack.market_data_table.table_name,
            "TABLE_SESSIONS": data_stack.sessions_table.table_name,
            "TABLE_TRACES": data_stack.traces_table.table_name,
            "TABLE_WORKATO_RUNS": data_stack.workato_runs_table.table_name,
            "BUCKET_DATA_LAKE": data_stack.data_lake_bucket.bucket_name,
            "BUCKET_REPORTS": data_stack.reports_bucket.bucket_name,
        }

        # Shared Lambda defaults
        fn_defaults = dict(
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=512,
            timeout=Duration.seconds(30),
            environment=common_env,
            log_retention=logs.RetentionDays.TWO_WEEKS,
        )

        # -----------------------------------------------------------------
        # Action-group handler IAM role (least-privilege for DynamoDB + S3)
        # -----------------------------------------------------------------
        action_group_role = iam.Role(
            self,
            "ActionGroupLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # Grant DynamoDB read/write for all tables
        for table in [
            data_stack.sessions_table,
            data_stack.operators_table,
            data_stack.metrics_table,
            data_stack.esg_profiles_table,
            data_stack.market_data_table,
            data_stack.traces_table,
            data_stack.workato_runs_table,
        ]:
            table.grant_read_write_data(action_group_role)

        # Grant S3 read/write for both buckets
        data_stack.data_lake_bucket.grant_read_write(action_group_role)
        data_stack.reports_bucket.grant_read_write(action_group_role)

        # -----------------------------------------------------------------
        # API handler IAM role (needs Bedrock invoke + DynamoDB)
        # -----------------------------------------------------------------
        api_handler_role = iam.Role(
            self,
            "ApiHandlerLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )
        api_handler_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeAgent",
                    "bedrock:InvokeModel",
                ],
                resources=["*"],
            )
        )
        data_stack.sessions_table.grant_read_write_data(api_handler_role)
        data_stack.traces_table.grant_read_write_data(api_handler_role)
        data_stack.reports_bucket.grant_read(api_handler_role)
        # Grant read on all tables for health checks and queries
        for table in [
            data_stack.operators_table,
            data_stack.metrics_table,
            data_stack.esg_profiles_table,
            data_stack.market_data_table,
        ]:
            table.grant_read_data(api_handler_role)

        # -----------------------------------------------------------------
        # Mock service role (minimal — just CloudWatch + DynamoDB writes)
        # -----------------------------------------------------------------
        mock_role = iam.Role(
            self,
            "MockServiceLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )
        data_stack.workato_runs_table.grant_read_write_data(mock_role)
        data_stack.traces_table.grant_read_write_data(mock_role)
        mock_role.add_to_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
            )
        )

        # -----------------------------------------------------------------
        # ACTION GROUP LAMBDAS
        # -----------------------------------------------------------------
        self.credit_rating_fn = _lambda.Function(
            self,
            "CreditRatingFn",
            function_name="dcai-credit-rating",
            handler="handlers.credit_rating.handler",
            code=_lambda.Code.from_asset("../lambda/action_groups"),
            role=action_group_role,
            **fn_defaults,
        )

        self.financial_metrics_fn = _lambda.Function(
            self,
            "FinancialMetricsFn",
            function_name="dcai-financial-metrics",
            handler="handlers.financial_metrics.handler",
            code=_lambda.Code.from_asset("../lambda/action_groups"),
            role=action_group_role,
            **fn_defaults,
        )

        self.market_data_fn = _lambda.Function(
            self,
            "MarketDataFn",
            function_name="dcai-market-data",
            handler="handlers.market_data.handler",
            code=_lambda.Code.from_asset("../lambda/action_groups"),
            role=action_group_role,
            **fn_defaults,
        )

        self.esg_risk_fn = _lambda.Function(
            self,
            "EsgRiskFn",
            function_name="dcai-esg-risk",
            handler="handlers.esg_risk.handler",
            code=_lambda.Code.from_asset("../lambda/action_groups"),
            role=action_group_role,
            **fn_defaults,
        )

        self.generate_report_fn = _lambda.Function(
            self,
            "GenerateReportFn",
            function_name="dcai-generate-report",
            handler="handlers.generate_report.handler",
            code=_lambda.Code.from_asset("../lambda/action_groups"),
            role=action_group_role,
            **fn_defaults,
        )

        self.sync_moodys_fn = _lambda.Function(
            self,
            "SyncMoodysFn",
            function_name="dcai-sync-moodys",
            handler="handlers.sync_moodys.handler",
            code=_lambda.Code.from_asset("../lambda/action_groups"),
            role=action_group_role,
            **fn_defaults,
        )

        # -----------------------------------------------------------------
        # API QUERY HANDLER — receives user query, invokes Bedrock Agent
        # -----------------------------------------------------------------
        self.api_query_fn = _lambda.Function(
            self,
            "ApiQueryFn",
            function_name="dcai-api-query",
            handler="query_handler.handler",
            code=_lambda.Code.from_asset("../lambda/api"),
            role=api_handler_role,
            **fn_defaults,
        )

        self.api_sessions_fn = _lambda.Function(
            self,
            "ApiSessionsFn",
            function_name="dcai-api-sessions",
            handler="sessions_handler.handler",
            code=_lambda.Code.from_asset("../lambda/api"),
            role=api_handler_role,
            **fn_defaults,
        )

        self.api_health_fn = _lambda.Function(
            self,
            "ApiHealthFn",
            function_name="dcai-api-health",
            handler="health_handler.handler",
            code=_lambda.Code.from_asset("../lambda/api"),
            role=api_handler_role,
            memory_size=128,
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(10),
            log_retention=logs.RetentionDays.TWO_WEEKS,
            environment=common_env,
        )

        self.api_reports_fn = _lambda.Function(
            self,
            "ApiReportsFn",
            function_name="dcai-api-reports",
            handler="reports_handler.handler",
            code=_lambda.Code.from_asset("../lambda/api"),
            role=api_handler_role,
            **fn_defaults,
        )

        # -----------------------------------------------------------------
        # MOCK WORKATO SERVICE
        # -----------------------------------------------------------------
        self.mock_workato_trigger_fn = _lambda.Function(
            self,
            "MockWorkatoTriggerFn",
            function_name="dcai-mock-workato-trigger",
            handler="handler.handler",
            code=_lambda.Code.from_asset("../lambda/mock_services/workato"),
            role=mock_role,
            **fn_defaults,
        )

        self.mock_workato_status_fn = _lambda.Function(
            self,
            "MockWorkatoStatusFn",
            function_name="dcai-mock-workato-status",
            handler="handler.handler",
            code=_lambda.Code.from_asset("../lambda/mock_services/workato"),
            role=mock_role,
            **fn_defaults,
        )

        # -----------------------------------------------------------------
        # MOCK ARIZE SERVICE
        # -----------------------------------------------------------------
        self.mock_arize_ingest_fn = _lambda.Function(
            self,
            "MockArizeIngestFn",
            function_name="dcai-mock-arize-ingest",
            handler="handler.handler",
            code=_lambda.Code.from_asset("../lambda/mock_services/arize"),
            role=mock_role,
            **fn_defaults,
        )

        self.mock_arize_query_fn = _lambda.Function(
            self,
            "MockArizeQueryFn",
            function_name="dcai-mock-arize-query",
            handler="handler.handler",
            code=_lambda.Code.from_asset("../lambda/mock_services/arize"),
            role=mock_role,
            **fn_defaults,
        )

        # -----------------------------------------------------------------
        # DATA SEEDING LAMBDA
        # -----------------------------------------------------------------
        self.seed_data_fn = _lambda.Function(
            self,
            "SeedDataFn",
            function_name="dcai-seed-data",
            handler="seed_data.handler",
            code=_lambda.Code.from_asset("../lambda/seed"),
            role=action_group_role,
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=512,
            timeout=Duration.seconds(120),  # seeding may take longer
            log_retention=logs.RetentionDays.TWO_WEEKS,
            environment=common_env,
        )
