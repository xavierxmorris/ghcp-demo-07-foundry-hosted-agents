#!/usr/bin/env bash
# Resets local demo state between presentations.
#
# Removes virtual environments, Python caches, and generated eval artifacts,
# then re-runs the Foundry health check.
#
# This does NOT touch Azure. Deployed agents stay warm, which is what you want
# between back-to-back sessions. For a full teardown run `azd down --purge`.
#
# Usage: ./scripts/reset-demo.sh [--keep-venvs]
set -euo pipefail

KEEP_VENVS=0
[[ "${1:-}" == "--keep-venvs" ]] && KEEP_VENVS=1

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

echo "==> Removing Python caches"
find . -path ./.venv -prune -o \
     \( -name '__pycache__' -o -name '.pytest_cache' -o -name '.ruff_cache' \) \
     -print -exec rm -rf {} + 2>/dev/null || true

echo "==> Removing generated eval artifacts"
# Authored datasets and rubrics are committed and must survive a reset. Only the
# generated baseline configs and any downloaded results are removed.
for agent in src/*/; do
  rm -rf "${agent}.agent_configs" "${agent}.foundry/results" "${agent}evaluators/smoke-core" 2>/dev/null || true
done

if [[ $KEEP_VENVS -eq 0 ]]; then
  echo "==> Removing virtual environments"
  rm -rf .venv .venv-tests src/devops-triage/.venv src/docs-qa/.venv
else
  echo "==> Keeping virtual environments (--keep-venvs)"
fi

echo "==> Foundry health check"
azd ai agent doctor || true

echo
echo "Reset complete. Azure resources were not touched."
echo "Full teardown:  azd down --purge"
