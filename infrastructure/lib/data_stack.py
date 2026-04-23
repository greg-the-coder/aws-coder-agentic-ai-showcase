"""DataStack — DynamoDB tables and S3 buckets for the DC Invest Agent."""

from aws_cdk import (
    CfnOutput,
    RemovalPolicy,
    Stack,
    Tags,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
)
from constructs import Construct


class DataStack(Stack):
    """Provisions all persistent storage: DynamoDB tables and S3 buckets."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        Tags.of(self).add("Project", "dc-invest-agent")

        # ---------------------------------------------------------------
        # DynamoDB Tables
        # ---------------------------------------------------------------

        # dcai-sessions — conversation session state
        self.sessions_table = dynamodb.Table(
            self,
            "SessionsTable",
            table_name="dcai-sessions",
            partition_key=dynamodb.Attribute(
                name="session_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="expires_at",
        )
        self.sessions_table.add_global_secondary_index(
            index_name="user-index",
            partition_key=dynamodb.Attribute(
                name="user_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at", type=dynamodb.AttributeType.STRING
            ),
        )

        # dcai-operators — data center operator master data
        self.operators_table = dynamodb.Table(
            self,
            "OperatorsTable",
            table_name="dcai-operators",
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        self.operators_table.add_global_secondary_index(
            index_name="rating-index",
            partition_key=dynamodb.Attribute(
                name="moodys_rating", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="name", type=dynamodb.AttributeType.STRING
            ),
        )

        # dcai-metrics — quarterly financial metrics
        self.metrics_table = dynamodb.Table(
            self,
            "MetricsTable",
            table_name="dcai-metrics",
            partition_key=dynamodb.Attribute(
                name="operator_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="period", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        self.metrics_table.add_global_secondary_index(
            index_name="period-index",
            partition_key=dynamodb.Attribute(
                name="period", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="operator_id", type=dynamodb.AttributeType.STRING
            ),
        )

        # dcai-esg-profiles — ESG risk profiles per operator
        self.esg_profiles_table = dynamodb.Table(
            self,
            "EsgProfilesTable",
            table_name="dcai-esg-profiles",
            partition_key=dynamodb.Attribute(
                name="operator_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # dcai-market-data — market analytics by metro area
        self.market_data_table = dynamodb.Table(
            self,
            "MarketDataTable",
            table_name="dcai-market-data",
            partition_key=dynamodb.Attribute(
                name="market_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # dcai-traces — agent execution traces for observability
        self.traces_table = dynamodb.Table(
            self,
            "TracesTable",
            table_name="dcai-traces",
            partition_key=dynamodb.Attribute(
                name="trace_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="session_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # dcai-workato-runs — Workato integration run logs
        self.workato_runs_table = dynamodb.Table(
            self,
            "WorkatoRunsTable",
            table_name="dcai-workato-runs",
            partition_key=dynamodb.Attribute(
                name="run_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ---------------------------------------------------------------
        # S3 Buckets
        # ---------------------------------------------------------------

        # Data lake bucket with prefixes: /moodys/, /market/, /esg/
        self.data_lake_bucket = s3.Bucket(
            self,
            "DataLakeBucket",
            bucket_name=None,  # auto-generated to avoid global-name collisions
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

        # Reports bucket for generated PDF / Markdown reports
        self.reports_bucket = s3.Bucket(
            self,
            "ReportsBucket",
            bucket_name=None,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

        # ---------------------------------------------------------------
        # CloudFormation Outputs
        # ---------------------------------------------------------------

        CfnOutput(self, "SessionsTableArn", value=self.sessions_table.table_arn, export_name="dcai-sessions-arn")
        CfnOutput(self, "OperatorsTableArn", value=self.operators_table.table_arn, export_name="dcai-operators-arn")
        CfnOutput(self, "MetricsTableArn", value=self.metrics_table.table_arn, export_name="dcai-metrics-arn")
        CfnOutput(self, "EsgProfilesTableArn", value=self.esg_profiles_table.table_arn, export_name="dcai-esg-profiles-arn")
        CfnOutput(self, "MarketDataTableArn", value=self.market_data_table.table_arn, export_name="dcai-market-data-arn")
        CfnOutput(self, "TracesTableArn", value=self.traces_table.table_arn, export_name="dcai-traces-arn")
        CfnOutput(self, "WorkatoRunsTableArn", value=self.workato_runs_table.table_arn, export_name="dcai-workato-runs-arn")
        CfnOutput(self, "DataLakeBucketName", value=self.data_lake_bucket.bucket_name, export_name="dcai-data-lake-bucket")
        CfnOutput(self, "ReportsBucketName", value=self.reports_bucket.bucket_name, export_name="dcai-reports-bucket")

        CfnOutput(self, "SessionsTableName", value=self.sessions_table.table_name)
        CfnOutput(self, "OperatorsTableName", value=self.operators_table.table_name)
        CfnOutput(self, "MetricsTableName", value=self.metrics_table.table_name)
        CfnOutput(self, "EsgProfilesTableName", value=self.esg_profiles_table.table_name)
        CfnOutput(self, "MarketDataTableName", value=self.market_data_table.table_name)
        CfnOutput(self, "TracesTableName", value=self.traces_table.table_name)
        CfnOutput(self, "WorkatoRunsTableName", value=self.workato_runs_table.table_name)
