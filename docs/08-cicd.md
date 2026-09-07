# 08 — CI/CD with GitHub Actions

**Time:** ~20 minutes
**Goal:** tests on every PR, and a deploy on merge — with no secrets in GitHub.

Two workflows ship with this repo:

| Workflow | Trigger | Does |
| --- | --- | --- |
| [`ci.yml`](../.github/workflows/ci.yml) | every push + PR; reusable by deployment | Lint, run domain and CI-contract tests, validate both agents, model bindings and nonempty evaluation datasets |
| [`deploy-agents.yml`](../.github/workflows/deploy-agents.yml) | push to `main`, or manual | `azd provision` + `azd deploy`, then a smoke invoke |

## CI needs nothing

`ci.yml` runs `ruff` and `pytest`. Because the domain modules have no framework
or Azure dependencies, CI needs **no Azure credentials at all** — which is the
practical payoff of the layering rule. Deployment calls this same workflow and
must pass it for the exact revision being deployed before obtaining an OIDC token.

## Deployment uses OIDC, not secrets

Never put a client secret in GitHub. Use **workload identity federation**: GitHub
mints a short-lived token, Azure trusts it for a specific repo and environment, and no
long-lived credential exists anywhere.

### 1. Create an app registration and service principal

```bash
APP_ID=$(az ad app create --display-name "gh-foundry-agents" --query appId -o tsv)
az ad sp create --id "$APP_ID"
```

### 2. Federate it to your repo

```bash
az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "github-production",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:xavierxmorris/ghcp-demo-07-foundry-hosted-agents:environment:production",
  "audiences": ["api://AzureADTokenExchange"]
}'
```

The `subject` is matched exactly. This workflow already declares the `production`
environment, so a branch-only credential does not match. Create that GitHub
environment and restrict its deployment branches to `main`; configure reviewers
where your plan supports them. The workflow also rejects deployment from other
refs. Do not add a pull-request federation credential to make CI pass: offline
CI must not receive deployment access.

### 3. Grant roles

Two levels, because deploying an agent touches both planes:

```bash
SP_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)
SUB=$(az account show --query id -o tsv)

# Control plane -- create/update resources
az role assignment create --assignee-object-id "$SP_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Contributor" \
  --scope "/subscriptions/$SUB/resourceGroups/rg-<env>"

# Data plane -- register agent versions on the Foundry project
az role assignment create --assignee-object-id "$SP_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Foundry User" \
  --scope "$(az cognitiveservices account show -n <account> -g rg-<env> --query id -o tsv)"
```

Forgetting the second one is the classic CI failure: provision succeeds, deploy
fails with `403`. Same control-plane/data-plane split as
[module 03](03-provision-azure.md#rbac-the-trap-worth-understanding).

### 4. Add repository variables

Settings → Secrets and variables → Actions → **Variables** (these are identifiers,
not secrets):

| Variable | Value |
| --- | --- |
| `AZURE_CLIENT_ID` | the `appId` from step 1 |
| `AZURE_TENANT_ID` | `az account show --query tenantId -o tsv` |
| `AZURE_SUBSCRIPTION_ID` | `az account show --query id -o tsv` |
| `AZURE_ENV_NAME` | your azd environment name |
| `AZURE_LOCATION` | `northcentralus` |

All five variables are required. A completely unconfigured clone reports a
deployment skip; partial configuration fails with the missing variable names.
Only the deployment job receives `id-token: write`.

### 5. Push

```bash
git push origin main
```

The workflow authenticates via OIDC, runs `azd provision --no-prompt` (a no-op
when nothing changed), `azd deploy --no-prompt`, and finishes with a smoke invoke
against the freshly deployed agent. If the smoke invoke fails, the job fails.
Push deployments always run the smoke assertions. Only a manual dispatch can
explicitly opt out with `smoke_test: false`. Deployments serialize without
cancelling a provisioning operation already in progress.

Tooling is pinned to Azure Developer CLI **1.33.0** and the SHA-pinned
`Azure/setup-azd` **v2.4.0** and `azure/login` **v3.0.2** actions. The current
`microsoft.foundry` extension installs its required agent/project dependencies;
installation errors are not ignored. Reviewed **7 September 2026** against the
[hosted-agent CI/CD quickstart](https://learn.microsoft.com/azure/foundry/agents/quickstarts/set-up-cicd-hosted-agent?pivots=azd)
and [GitHub OIDC subject guidance](https://docs.github.com/en/actions/reference/security/oidc).

## Adding an eval gate

Quality gates are the real reason to have CI for an agent. Because evals cost
tokens and take minutes, gate on merges to `main`, not on every PR push:

```yaml
- name: Run eval suite
  run: |
    azd ai agent eval run --config ./src/devops-triage/eval.yaml --name triage-core --output json > eval.json
    python - <<'PY'
    import json, sys
    r = json.load(open("eval.json"))
    passed, total = r["passed"], r["total"]
    print(f"eval: {passed}/{total}")
    if passed / total < 0.75:
        sys.exit("eval pass rate below 75% threshold")
    PY
```

Pick the threshold from your **current** baseline, not an aspiration. This repo's
first `triage-core` run scored 6/12; a 75% gate would block every deploy. Start
at or slightly below where you are, then ratchet it up as you improve the agent —
a gate you routinely override is not a gate.

## Environments and approvals

For a real pipeline, use GitHub Environments:

```yaml
jobs:
  deploy-production:
    environment: production      # required reviewers, wait timers
```

and a separate azd environment per stage:

```bash
azd env new staging
azd env new production
azd env select production
```

Each keeps its own subscription, region, endpoints, and agent versions.

## Rollback

Agent versions are immutable, so rollback is a pin rather than a redeploy:

```bash
azd ai agent show devops-triage --output json     # list versions
azd ai agent invoke devops-triage --version 1 "..."  # verify the old one
```

Then revert the commit and let the pipeline deploy a new version built from the
known-good source.

---

← [07 — Observability](07-observability.md) · Next → [09 — Copilot coding agent](09-coding-agent.md)
