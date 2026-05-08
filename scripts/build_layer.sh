#!/usr/bin/env bash
# Build the Lambda layer for AgentCore dependencies.
# Installs strands-agents + bedrock provider into layers/agentcore_deps/python/
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAYER_DIR="${REPO_ROOT}/layers/agentcore_deps/python"

echo "Installing AgentCore layer deps into ${LAYER_DIR} ..."

rm -rf "${LAYER_DIR}"
mkdir -p "${LAYER_DIR}"

pip install --target "${LAYER_DIR}" --no-cache-dir \
  strands-agents \
  strands-agents-bedrock \
  pydantic \
  opentelemetry-api \
  opentelemetry-sdk \
  opentelemetry-instrumentation \
  opentelemetry-instrumentation-threading \
  opentelemetry-semantic-conventions

# Remove botocore (Lambda runtime provides it) to save space
rm -rf "${LAYER_DIR}/botocore" "${LAYER_DIR}/botocore-"*.dist-info
rm -rf "${LAYER_DIR}"/*.dist-info/direct_url.json

echo "Done. Layer size:"
du -sh "${LAYER_DIR}"
