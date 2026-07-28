# Hosted AI Agents on Azure AI Foundry — built with GitHub Copilot

> A hands-on, demo-ready reference repo showing how to go from an empty folder to
> **two production-shaped AI agents running on Azure AI Foundry**, using
> **GitHub Copilot** as the pair-programmer the whole way.

Everything in this repo has been **executed end to end against a real Azure
subscription** — provisioned, deployed, and invoked. The commands in the lab are
the commands that actually ran.

---

## What you get

Two hosted agents, deliberately different in shape, sharing one Foundry project:

| Agent | What it does | Teaches |
| --- | --- | --- |
| **`devops-triage`** | Takes a production incident report, assigns a severity, finds the owning team, correlates recent deploys, and returns a structured triage summary with runbook steps. | **Function/tool calling** — four tools, multi-step reasoning, strict output contracts |
| **`docs-qa`** | Answers questions about the Contoso Payments platform strictly from a bundled documentation corpus, with citations — and refuses when the answer isn't there. | **Grounding** — BM25 retrieval, citation discipline, measurable "I don't know" |

Both are **hosted agents**: your code, your tools, running *inside* Foundry
Agent Service. Foundry handles the container build, hosting, identity, scaling,
versioning, and tracing. You write `main.py`.

---

## Why this repo exists

Most agent samples show you a single `main.py` and stop. Real work needs the
rest of the loop:

```
scaffold → run locally → provision → deploy → invoke → evaluate → observe → iterate → CI/CD
```

This repo walks the whole loop, and shows **where GitHub Copilot fits at each
step** — not as a novelty, but as the thing that writes the tools, the tests,
the eval cases, and the workflow files.

---

## Architecture

```
                        ┌──────────────────────────────────────────────┐
                        │           Azure AI Foundry project           │
                        │                                              │
   azd deploy ────────► │  ┌────────────────────┐  ┌────────────────┐  │
                        │  │  devops-triage     │  │  docs-qa       │  │
                        │  │  (hosted agent)    │  │ (hosted agent) │  │
                        │  │                    │  │                │  │
                        │  │  4 function tools  │  │  BM25 retrieval│  │
                        │  └─────────┬──────────┘  └───────┬────────┘  │
                        │            │                     │           │
                        │            └──────────┬──────────┘           │
                        │                       ▼                      │
                        │            ┌──────────────────────┐          │
                        │            │  gpt-5.4-mini        │          │
                        │            │  (model deployment)  │          │
                        │            └──────────────────────┘          │
                        │                                              │
                        │   Managed identity · versioning · tracing    │
                        └───────────────────┬──────────────────────────┘
                                            │ OpenTelemetry
                                            ▼
                                  ┌──────────────────────┐
                                  │ Application Insights │
                                  └──────────────────────┘
```

One `azure.yaml` describes all of it. See [`docs/02-anatomy-of-a-hosted-agent.md`](docs/02-anatomy-of-a-hosted-agent.md).

---

## Quickstart (about 10 minutes)

### Prerequisites

| Tool | Minimum | Check |
| --- | --- | --- |
| [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) | 1.28.0 | `azd version` |
| [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) | 2.87.0 | `az version` |
| Python | 3.14 (3.13 also supported) | `python --version` |
| An Azure subscription | Owner or Contributor + User Access Administrator | `az account show` |

> Prefer zero installs? Open this repo in a **GitHub Codespace** — the
> [dev container](.devcontainer/devcontainer.json) has everything pre-installed.

### Run it

```bash
git clone https://github.com/xavierxmorris/ghcp-demo-07-foundry-hosted-agents.git
cd ghcp-demo-07-foundry-hosted-agents

# 1. Sign in. Use the SAME account for both -- see docs/troubleshooting.md.
az login
azd auth login

# 2. Create the azd environment
azd env new my-agents --subscription <subscription-id> --location northcentralus

# 3. Provision the Foundry project + model deployment (~2 min)
azd provision

# 4. Tell the agents which model deployment to use
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME gpt-5.4-mini

# 5. Deploy both agents (~2 min)
azd deploy

# 6. Talk to them
azd ai agent invoke devops-triage "Checkout is returning 5xx for 12% of requests, ~3000 users affected."
azd ai agent invoke docs-qa "How long do I have to respond to a Mastercard chargeback?"
```

**Tear down when you're done — this costs money:**

```bash
azd down --purge
```

---

## What the agents actually say

`devops-triage`, given a real-shaped incident report:

```
**Severity:** SEV2 - Major functionality broken with 12% 5xxs, payment failures,
3,000 users affected, and revenue impact.
**Service:** Checkout API (tier-1) - owned by Payments Core
**Page:** payments-core-primary via #payments-core-oncall
**Likely cause:** chk-2291 — high-risk deploy 2 hours ago enabling connection
pooling v2 for the ledger client and raising pool size 20 -> 80
**Next actions:**
1. Confirm the blast radius on the Checkout API dashboard.
2. Check whether errors correlate with a deploy in the last 4 hours; roll back first.
3. Inspect ledger-service dependency health -- checkout 503s when ledger write latency > 2s.
**Runbook:** https://runbooks.contoso.example/checkout-api/5xx-surge
```

`docs-qa`, when the answer **is** in the corpus:

```
If the merchant balance is lower than the refund amount, the refund is queued with
status `pending_funds` for up to 7 days. Contoso retries automatically each day. If
the balance is still insufficient after 7 days, the refund is cancelled and a
`refund.cancelled` webhook fires.

Sources: refunds-policy#Insufficient balance
```

…and when it **isn't**:

```
I don't have that in the Contoso Payments documentation.
```

That last one is the money shot. It's also
[an automated eval case](src/docs-qa/datasets/grounding-core/grounding-core.jsonl).

---

## The lab

Work through these in order, or jump to what you need.

| # | Module | Time | You'll learn |
| --- | --- | --- | --- |
| 00 | [Prerequisites & setup](docs/00-prerequisites.md) | 10 min | Tooling, auth, the account-mismatch trap |
| 01 | [Scaffold an agent with Copilot](docs/01-scaffold-with-copilot.md) | 15 min | `azd ai agent init`, prompting Copilot to build tools |
| 02 | [Anatomy of a hosted agent](docs/02-anatomy-of-a-hosted-agent.md) | 15 min | `azure.yaml`, protocols, code vs container deploy |
| 03 | [Provision Azure](docs/03-provision-azure.md) | 10 min | What `azd provision` creates, RBAC, cost |
| 04 | [Run and debug locally](docs/04-run-locally.md) | 15 min | `azd ai agent run`, the Inspector, fast iteration |
| 05 | [Deploy to Foundry](docs/05-deploy-to-foundry.md) | 10 min | Immutable versions, rollback, the Playground |
| 06 | [Evaluate quality](docs/06-evaluate.md) | 20 min | Eval datasets, graders, regression gates |
| 07 | [Observability & tracing](docs/07-observability.md) | 15 min | App Insights, KQL, debugging a bad answer |
| 08 | [CI/CD with GitHub Actions](docs/08-cicd.md) | 20 min | OIDC federated credentials, deploy on merge |
| 09 | [Hand work to the Copilot coding agent](docs/09-coding-agent.md) | 15 min | `copilot-setup-steps.yml`, issue-driven development |

Supporting material:

- [Architecture deep-dive](docs/architecture.md)
- [Troubleshooting](docs/troubleshooting.md) — every error we actually hit, and the fix
- [Presenter guide](docs/presenter-guide.md) — timings, talk track, reset script

---

## How GitHub Copilot is wired in

This repo is itself an example of **customising Copilot for a domain**:

| File | Purpose |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | Cross-tool agent instructions (Copilot CLI, Claude Code, Codex) |
| [`.github/copilot-instructions.md`](.github/copilot-instructions.md) | Repo-wide rules Copilot applies to every suggestion |
| [`.github/prompts/`](.github/prompts/) | Reusable prompt files — add a tool, write eval cases, debug a deploy |
| [`.github/chatmodes/`](.github/chatmodes/) | A focused "Foundry agent developer" chat mode |
| [`.github/workflows/copilot-setup-steps.yml`](.github/workflows/copilot-setup-steps.yml) | Pre-installs tooling for the Copilot **coding agent** |
| [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/) | Issues shaped for assigning straight to Copilot |

Try it: open Copilot CLI in this repo and ask

> *Add a `check_service_dependencies` tool to the devops-triage agent that walks
> the dependency graph and flags any dependency with an open incident. Follow the
> existing tool patterns and add tests.*

---

## Repo layout

```
.
├── azure.yaml                  # ← the whole deployment, both agents, one file
├── src/
│   ├── devops-triage/
│   │   ├── main.py             # agent definition + @tool functions
│   │   ├── triage.py           # deterministic domain logic (unit-testable)
│   │   ├── data/               # service catalogue, deploys, runbooks
│   │   ├── eval.yaml           # eval suite definition
│   │   ├── datasets/           # 12 authored eval cases
│   │   └── evaluators/         # weighted judging rubric
│   └── docs-qa/
│       ├── main.py             # agent definition + @tool functions
│       ├── retrieval.py        # BM25 over the corpus, stdlib only
│       ├── knowledge/          # the documentation corpus
│       ├── eval.yaml
│       ├── datasets/           # 15 authored eval cases, 3 of them refusals
│       └── evaluators/
├── tests/                      # 55 unit tests, no Azure required
├── docs/                       # the lab
└── .github/                    # Copilot customisation + CI/CD
```

**Design rule:** tool logic lives in a plain module (`triage.py`, `retrieval.py`)
with no framework imports, so it is unit-testable without a model. `main.py` only
wires those functions to the agent. See [`docs/architecture.md`](docs/architecture.md).

---

## Testing

```bash
python -m venv .venv && .venv/Scripts/activate   # Windows
# source .venv/bin/activate                       # macOS / Linux
pip install -r requirements-dev.txt
pytest
```

55 tests, no Azure resources, no model calls, runs in under a second.

---

## Cost

Provisioning creates a Foundry account + project, a `gpt-5.4-mini` GlobalStandard
deployment, Log Analytics, and Application Insights. The infrastructure is
essentially free at idle; you pay for **model tokens** and Log Analytics
ingestion. A full run of this lab costs well under a dollar.

`azd down --purge` removes everything.

---

## License

[MIT](LICENSE). The Contoso Payments documentation and the service/incident data
are fictional and exist only to make the demo concrete.
