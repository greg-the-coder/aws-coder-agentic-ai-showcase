"""AgentCoreStack — Strands Agent deployed as Lambda (stepping stone to AgentCore managed runtime)."""

from aws_cdk import (
    CfnOutput,
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
from lib.api_stack import ApiStack


class DcaiAgentCoreStack(Stack):
    """Deploys the Strands supervisor agent as a Lambda function.

    This is a stepping stone to full AgentCore managed runtime — once AgentCore
    CDK L2 constructs are available, the Lambda can be migrated to AgentCore
    runtime with minimal code changes.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        data_stack: DataStack,
        api_stack: ApiStack,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        Tags.of(self).add("Project", "dc-invest-agent")

        # -----------------------------------------------------------------
        # Lambda Layer — agent dependencies (strands-agents, boto3, etc.)
        # -----------------------------------------------------------------
        self.agent_deps_layer = _lambda.LayerVersion(
            self,
            "AgentDepsLayer",
            layer_version_name="dcai-agentcore-deps",
            description="Dependencies for Strands agent: strands-agents, strands-agents-bedrock, boto3",
            code=_lambda.Code.from_asset("../layers/agentcore_deps"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            removal_policy=RemovalPolicy.DESTROY,
        )

        # -----------------------------------------------------------------
        # IAM Role — least-privilege for the supervisor agent
        # -----------------------------------------------------------------
        agent_role = iam.Role(
            self,
            "AgentCoreSupervisorRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # DynamoDB read/write on all 7 tables
        for table in [
            data_stack.operators_table,
            data_stack.metrics_table,
            data_stack.esg_profiles_table,
            data_stack.market_data_table,
            data_stack.sessions_table,
            data_stack.traces_table,
            data_stack.workato_runs_table,
        ]:
            table.grant_read_write_data(agent_role)

        # S3 read/write on reports bucket
        data_stack.reports_bucket.grant_read_write(agent_role)

        # Bedrock InvokeModel for Mistral models
        agent_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/mistral.*",
                ],
            )
        )

        # CloudWatch PutMetricData for custom metrics
        agent_role.add_to_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
            )
        )

        # -----------------------------------------------------------------
        # Environment variables
        # -----------------------------------------------------------------
        api_url = api_stack.api.url

        environment = {
            "TABLE_OPERATORS": data_stack.operators_table.table_name,
            "TABLE_METRICS": data_stack.metrics_table.table_name,
            "TABLE_ESG": data_stack.esg_profiles_table.table_name,
            "TABLE_MARKET": data_stack.market_data_table.table_name,
            "TABLE_SESSIONS": data_stack.sessions_table.table_name,
            "TABLE_TRACES": data_stack.traces_table.table_name,
            "TABLE_WORKATO_RUNS": data_stack.workato_runs_table.table_name,
            "BUCKET_REPORTS": data_stack.reports_bucket.bucket_name,
            "BEDROCK_MODEL_ID": "mistral.mistral-large-2402-v1:0",
            "WORKATO_ENDPOINT": f"{api_url}mock/workato",
            "ARIZE_ENDPOINT": f"{api_url}mock/arize",
            "AWS_REGION_NAME": "us-east-1",
        }

        # -----------------------------------------------------------------
        # Lambda Function — Strands Supervisor Agent
        # -----------------------------------------------------------------
        self.supervisor_fn = _lambda.Function(
            self,
            "AgentCoreSupervisorFn",
            function_name="dcai-agentcore-supervisor",
            handler="agent.handler.handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset("../agent"),
            role=agent_role,
            memory_size=1024,
            timeout=Duration.seconds(90),
            environment=environment,
            layers=[self.agent_deps_layer],
            log_retention=logs.RetentionDays.TWO_WEEKS,
        )

        # -----------------------------------------------------------------
        # Outputs
        # -----------------------------------------------------------------
        CfnOutput(
            self,
            "SupervisorFunctionArn",
            value=self.supervisor_fn.function_arn,
            export_name="dcai-agentcore-supervisor-arn",
        )
