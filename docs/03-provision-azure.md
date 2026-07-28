# 03 — Provision Azure

**Time:** ~10 minutes
**Goal:** create the Foundry project and model deployment, and understand what you just paid for.

## One command

```bash
azd provision
```

Real output from building this repo:

```
Reading subscription and location from environment...
Subscription: ME-MngEnvMCAP200728-xaviermorris-1
Location: North Central US

Preparing Foundry provisioning template...
Starting ARM deployment "azd-foundry-my-agents-be8b83b1"...
Foundry deployment in progress
...
SUCCESS: Your application was provisioned in Azure in 1 minute 55 seconds.
```

## What it created

| Resource | Purpose |
| --- | --- |
| Resource group `rg-<env>` | Container for everything; `azd down` deletes it |
| Azure AI Services account | The Foundry account (`cog-*`) |
| Foundry **project** | The scope agents and model deployments live in |
| Model deployment `gpt-5.4-mini` | From `services.ai-project.deployments[]` in `azure.yaml` |
| Log Analytics workspace | Backing store for telemetry |
| Application Insights | Agent traces land here — see module 07 |

Inspect the resulting state:

```bash
azd env get-values
```

The values that matter downstream:

```
AZURE_AI_ACCOUNT_NAME="cog-a1b2c3d4e5f6g"
AZURE_AI_PROJECT_NAME="my-agents"
FOUNDRY_PROJECT_ENDPOINT="https://cog-a1b2c3d4e5f6g.services.ai.azure.com/api/projects/my-agents"
AZURE_RESOURCE_GROUP="rg-my-agents"
```

## The one manual step

`azd provision` does **not** set `AZURE_AI_MODEL_DEPLOYMENT_NAME`, but both agent
service blocks reference `${AZURE_AI_MODEL_DEPLOYMENT_NAME}`. Set it now or the
deploy ships agents that can't reach a model:

```bash
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME gpt-5.4-mini
```

Then write the local `.env` for each agent so `azd ai agent run` works offline
from Azure config:

```bash
# src/devops-triage/.env  and  src/docs-qa/.env
FOUNDRY_PROJECT_ENDPOINT=https://<account>.services.ai.azure.com/api/projects/<project>
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-5.4-mini
```

> **Keep `.env` and the azd env in sync.** `azd ai agent run` injects azd env
> values into the process *before* Python loads `.env`, and the sample uses
> `load_dotenv()` which does not override existing process variables. A stale
> `AZURE_AI_MODEL_DEPLOYMENT_NAME` in the azd env therefore wins, and shows up as
> a confusing `404` from the responses API.

## Check your work

```bash
azd ai agent doctor
```

This is the single most useful command in the toolchain. It checks local config,
auth, endpoint reachability, RBAC, and deployment status, and names the exact
failing check:

```
Local
   (✓) azure.yaml present and parseable
   (✓) agent definition valid (per service)
Authentication
   (✓) authentication
Remote
   (✓) Foundry project endpoint reachable
   (✓) Developer has required role on Foundry project
   (x) Hosted agents are active
       2 of 2 agents have not been deployed
```

That last failure is expected — deploying is module 05.

## RBAC: the trap worth understanding

If `doctor` reports:

```
(x) Foundry project endpoint reachable
    Foundry returned HTTP 403 (wrong tenant or insufficient RBAC).
```

…you are almost certainly hitting the **control-plane vs data-plane** split.
Subscription `Owner` is a control-plane role. Calling a Foundry project endpoint
is a **data-plane** operation and needs `Foundry User` or `Azure AI Developer` on
the AI Services account.

`azd provision` grants that role to the principal that provisioned. If `azd` and
`az` are signed in as different accounts, the role lands on one identity and your
calls come from the other.

Fix by granting the role to the identity `azd` is actually using:

```bash
SCOPE=$(az cognitiveservices account show \
  --name <account> --resource-group <rg> --query id -o tsv)

az role assignment create \
  --assignee-object-id $(az ad user show --id <upn> --query id -o tsv) \
  --assignee-principal-type User \
  --role "Foundry User" \
  --scope "$SCOPE"
```

Allow 30–60 seconds for propagation, then re-run `azd ai agent doctor`.

## If provisioning fails

| Error | Cause | Fix |
| --- | --- | --- |
| `InvalidTemplate: parameters ... do not correspond` | A stale `infra/` folder from an older starter template conflicts with the `microsoft.foundry` provider | Delete `infra/` — with `infra: provider: microsoft.foundry` the provider supplies its own template. This repo ships without one. |
| `InsufficientQuota` | No capacity for the model SKU in the region | Lower `capacity` in `azure.yaml`, or pick another region |
| Resource group stuck `Deleting` | A previous `azd down` still running | Use a new `azd env` name |

## Cost

Idle cost is essentially zero — you pay for model tokens and Log Analytics
ingestion. When finished:

```bash
azd down --purge
```

`--purge` matters: without it the AI Services account is soft-deleted and the
name stays reserved.

---

← [02 — Anatomy](02-anatomy-of-a-hosted-agent.md) · Next → [04 — Run locally](04-run-locally.md)
