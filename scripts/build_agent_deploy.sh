#!/usr/bin/env bash
# Build the agent_deploy/ directory for Lambda packaging.
# CDK references ../agent_deploy from infrastructure/ so this must exist at repo root.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_DIR="${REPO_ROOT}/agent_deploy"

echo "Building agent_deploy/ in ${DEPLOY_DIR} ..."

rm -rf "${DEPLOY_DIR}"
mkdir -p "${DEPLOY_DIR}"

# Copy agent package (preserves 'from agent.xxx' imports)
cp -r "${REPO_ROOT}/agent" "${DEPLOY_DIR}/agent"

# Copy prompts (supervisor.py references ../prompts relative to agent/)
cp -r "${REPO_ROOT}/prompts" "${DEPLOY_DIR}/prompts"

# Remove __pycache__ dirs
find "${DEPLOY_DIR}" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

echo "Done. Contents:"
find "${DEPLOY_DIR}" -type f | sort
