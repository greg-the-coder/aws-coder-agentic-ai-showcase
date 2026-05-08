#!/bin/bash
# Build the AgentCore dependencies Lambda layer.
# Run this script before `cdk deploy` to install the Python packages
# into the layer directory structure expected by AWS Lambda.
#
# Usage: ./build_layer.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYER_DIR="${SCRIPT_DIR}/python"

echo "==> Cleaning existing layer packages..."
rm -rf "${LAYER_DIR}"
mkdir -p "${LAYER_DIR}"

echo "==> Installing dependencies into ${LAYER_DIR}..."
pip install \
    --target "${LAYER_DIR}" \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    strands-agents \
    strands-agents-tools \
    boto3>=1.34.0 \
    2>&1 | tail -5

# Try installing strands-agents-bedrock (may not be available as binary)
pip install \
    --target "${LAYER_DIR}" \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    strands-agents-bedrock \
    2>&1 | tail -3 || \
pip install \
    --target "${LAYER_DIR}" \
    strands-agents-bedrock \
    2>&1 | tail -3

echo "==> Layer build complete. Size: $(du -sh "${LAYER_DIR}" | cut -f1)"
echo "==> Package count: $(find "${LAYER_DIR}" -name '*.dist-info' | wc -l)"
