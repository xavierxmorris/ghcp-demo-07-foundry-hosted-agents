# 00 — Prerequisites and setup

**Time:** ~10 minutes

## What you need

| Tool | Minimum tested | Install |
| --- | --- | --- |
| Azure Developer CLI (`azd`) | 1.28.0 | <https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd> |
| Azure CLI (`az`) | 2.87.0 | <https://learn.microsoft.com/cli/azure/install-azure-cli> |
| Python | 3.14 (3.13 works too) | <https://www.python.org/downloads/> |
| Git | any recent | <https://git-scm.com/> |
| GitHub CLI (`gh`) | optional, for module 09 | <https://cli.github.com/> |

Plus an **Azure subscription** where you can create resources and assign roles.
Owner is easiest. Contributor alone is not enough — you need to grant yourself a
Foundry data-plane role, which requires `Microsoft.Authorization/roleAssignments/write`.

> **Zero-install option:** open this repo in a GitHub Codespace. The
> [dev container](../.devcontainer/devcontainer.json) installs `azd`, `az`,
> Python 3.14, and the Foundry azd extensions for you.

## 1. Verify your tooling

```bash
azd version
az version
python --version
```

## 2. Sign in — with the *same* account for both

This is the single most common setup failure, so do it deliberately:

```bash
az login
azd auth login
```

Now confirm they match:

```bash
az ad signed-in-user show --query userPrincipalName -o tsv
azd auth login --check-status
```

If those two print **different** accounts, fix it before going further:

```bash
azd auth login --use-device-code   # sign in as the same account az is using
```

**Why it matters.** `azd provision` grants the Foundry data-plane role to the
principal it provisions with. If `azd` later runs as a different identity, every
`azd ai agent` command fails with `HTTP 403 (wrong tenant or insufficient RBAC)`
— even if that identity is subscription **Owner**. Owner is a control-plane role;
Foundry projects need a data-plane role (`Foundry User` or `Azure AI Developer`).

We hit exactly this while building the repo. The fix is in
[troubleshooting](troubleshooting.md#403-from-the-foundry-endpoint).

## 3. Install the Foundry azd extensions

```bash
azd extension install azure.ai.agents
azd extension install azure.ai.projects
```

Already installed? Make sure they're current — an out-of-date extension against a
newer template is another failure we hit:

```bash
azd extension upgrade --all
```

## 4. Clone and verify

```bash
git clone https://github.com/xavierxmorris/ghcp-demo-07-foundry-hosted-agents.git
cd ghcp-demo-07-foundry-hosted-agents

python -m venv .venv
# Windows:        .venv\Scripts\Activate.ps1
# macOS / Linux:  source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Expected:

```
55 passed in 0.12s
```

Those tests exercise the agents' tool logic with **no Azure resources and no
model calls**. If they pass, your Python environment is good and you can do
module 01 and 02 entirely offline.

## 5. Pick a region

This lab uses **`northcentralus`**, which supports Foundry hosted agents. If you
use another region, confirm your model is available there first:

```bash
az cognitiveservices account list-skus --location <region> -o table
```

## 6. Choose your azd environment name

`azd` groups all state (subscription, region, endpoints, agent versions) under a
named environment. The name becomes part of your resource group name, so keep it
short and unique:

```bash
azd init -e my-agents --subscription <subscription-id> -l northcentralus
```

> If you re-run this lab later, use a **new** environment name. Azure resource
> groups stuck in `Deleting` state will otherwise collide with the old name.

## Cost expectations

| Resource | Idle cost |
| --- | --- |
| Azure AI Services account + Foundry project | none |
| `gpt-5.4-mini` GlobalStandard deployment | none — pay per token |
| Log Analytics + Application Insights | pay per GB ingested (pennies here) |
| Hosted agents | billed while serving requests |

A complete run of this lab costs well under a dollar. Always finish with:

```bash
azd down --purge
```

---

Next → [01 — Scaffold an agent with Copilot](01-scaffold-with-copilot.md)
