"""Configuration module for the DC Investments Agent."""

import os

# DynamoDB table names
TABLE_OPERATORS = os.environ.get("TABLE_OPERATORS", "dcai-operators")
TABLE_METRICS = os.environ.get("TABLE_METRICS", "dcai-metrics")
TABLE_ESG = os.environ.get("TABLE_ESG", "dcai-esg-profiles")
TABLE_MARKET = os.environ.get("TABLE_MARKET", "dcai-market-data")
TABLE_SESSIONS = os.environ.get("TABLE_SESSIONS", "dcai-sessions")
TABLE_TRACES = os.environ.get("TABLE_TRACES", "dcai-traces")
TABLE_WORKATO_RUNS = os.environ.get("TABLE_WORKATO_RUNS", "dcai-workato-runs")

# S3
BUCKET_REPORTS = os.environ.get("BUCKET_REPORTS", "dc-invest-reports")

# External endpoints
WORKATO_ENDPOINT = os.environ.get("WORKATO_ENDPOINT", "")
ARIZE_ENDPOINT = os.environ.get("ARIZE_ENDPOINT", "")

# Bedrock model
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "mistral.mistral-large-2402-v1:0")

# AWS
AWS_REGION = os.environ.get("AWS_REGION_NAME", os.environ.get("AWS_REGION", "us-east-1"))
