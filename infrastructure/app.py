#!/usr/bin/env python3
"""CDK App entry point for the Data Center Investments Agent infrastructure."""

import aws_cdk as cdk

from lib.data_stack import DataStack
from lib.lambda_stack import LambdaStack
from lib.api_stack import ApiStack
from lib.agent_stack import AgentStack
from lib.frontend_stack import FrontendStack

app = cdk.App()

env = cdk.Environment(
    account=app.node.try_get_context("account") or None,
    region=app.node.try_get_context("region") or "us-east-1",
)

# --- Data Layer ---
data_stack = DataStack(app, "DcaiDataStack", env=env)

# --- Lambda Functions ---
lambda_stack = LambdaStack(
    app,
    "DcaiLambdaStack",
    data_stack=data_stack,
    env=env,
)

# --- API Gateway ---
api_stack = ApiStack(
    app,
    "DcaiApiStack",
    lambda_stack=lambda_stack,
    env=env,
)

# --- Bedrock Agent ---
agent_stack = AgentStack(
    app,
    "DcaiAgentStack",
    lambda_stack=lambda_stack,
    env=env,
)

# --- Frontend (S3 + CloudFront) ---
frontend_stack = FrontendStack(
    app,
    "DcaiFrontendStack",
    api_stack=api_stack,
    env=env,
)

app.synth()
