#!/usr/bin/env bash
# Dev container bootstrap. Runs once after the container is created.
set -euo pipefail

echo "==> Installing Python dev dependencies"
pip install --upgrade pip
pip install -r requirements-dev.txt

echo "==> Installing agent runtime dependencies"
pip install -r src/devops-triage/requirements.txt
pip install -r src/docs-qa/requirements.txt
pip install uv

echo "==> Installing the Azure Developer CLI"
curl -fsSL https://aka.ms/install-azd.sh | bash

echo "==> Installing Foundry azd extensions"
azd extension install azure.ai.agents --no-prompt || true
azd extension install azure.ai.projects --no-prompt || true

echo "==> Verifying the test suite"
pytest -q

cat <<'EOF'

  Ready.

  Next steps:
    az login && azd auth login          # use the SAME account for both
    azd init -e <env> --subscription <id> -l northcentralus
    azd provision
    azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME gpt-5.4-mini
    azd deploy

  Start the lab at docs/00-prerequisites.md

EOF
