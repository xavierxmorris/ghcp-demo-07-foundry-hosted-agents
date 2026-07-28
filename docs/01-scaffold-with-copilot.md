# 01 — Scaffold an agent with GitHub Copilot

**Time:** ~15 minutes
**Goal:** understand how the agents in this repo were created, and create a third one yourself.

## The two-step scaffold

Creating a hosted agent is two commands. The first bootstraps the azd
environment; the second scaffolds the agent from a sample.

```bash
mkdir my-agent && cd my-agent

# 1. Bootstrap azd with subscription + region BEFORE scaffolding.
azd init -t Azure-Samples/azd-ai-starter-basic . \
  -e my-agent-dev \
  --subscription <subscription-id> \
  -l northcentralus \
  --no-prompt
```

> **Why order matters.** If `AZURE_SUBSCRIPTION_ID` and `AZURE_LOCATION` aren't
> set before the next step, `azd ai agent init` can't resolve the model catalogue
> and leaves a literal `{{AZURE_AI_MODEL_DEPLOYMENT_NAME}}` placeholder in
> `azure.yaml` that fails at deploy time.

Then pick a sample and scaffold:

```bash
# 2. See what's available
azd ai agent sample list --featured-only --language python --output json

# 3. Scaffold from the sample's manifestUrl
azd ai agent init --no-prompt \
  -m "https://github.com/microsoft-foundry/foundry-samples/blob/main/samples/python/hosted-agents/agent-framework/responses/02-tools/azure.yaml" \
  --deploy-mode code \
  --runtime python_3_14 \
  --entry-point main.py \
  --agent-name my-agent
```

Flag notes, all of which bite if you get them wrong:

| Flag | Rule |
| --- | --- |
| `--runtime` | Must be a full token: `python_3_13`, `python_3_14`, or `dotnet_10`. Bare `python` fails. |
| `--entry-point` | Must match a real file in the scaffolded source. A wrong value scaffolds fine and then breaks local run and deploy. |
| `--deploy-mode code` | Code deploy — Foundry builds the runtime from `requirements.txt`. Omit it in non-interactive mode and you get container deploy instead. |
| `--project-id` | Add this to target an **existing** Foundry project instead of creating one. |

### Which sample?

The two agents here started from these:

| Agent | Sample | Why |
| --- | --- | --- |
| `devops-triage` | `02-tools` — *Agent with Local Tools* | Already wires `@tool` functions |
| `docs-qa` | `01-basic` — *Basic agent (Responses)* | Clean base; retrieval added by hand |

## Where Copilot does the work

`azd ai agent init` gives you a generic sample: a `get_weather` tool and a
"friendly assistant" prompt. Turning that into something real is where Copilot
earns its keep.

This is the actual shape of the prompt that produced `devops-triage`:

> Replace the sample tool in `src/devops-triage/main.py` with an incident-triage
> agent for a payments platform. It needs four tools: classify severity SEV1–SEV4
> from a severity matrix, look up a service's owning team and on-call rotation,
> list deployments in a trailing time window, and fetch the runbook that best
> matches a symptom.
>
> Put all the domain logic in a separate `triage.py` with **no framework imports**
> so it is unit-testable, backed by JSON fixtures in `data/`. Keep `main.py` as
> thin `@tool` wrappers that return `json.dumps(...)`.
>
> The agent must never invent a service, team, deployment id, or runbook URL — an
> unknown service returns `found: False` plus the list of known services. Write
> the system prompt to enforce a fixed output structure. Add pytest tests
> covering the success path, the unknown-input path, and determinism.

Four things make that prompt work, and they generalise:

1. **State the architecture, not just the feature.** "Domain logic in a separate
   module with no framework imports" is what makes the result testable.
2. **Name the failure mode you care about.** "Never invent a service" produces
   defensive tool returns instead of optimistic ones.
3. **Ask for the tests in the same breath.** Retrofitting tests is harder than
   generating them alongside.
4. **Be concrete about the contract.** "Returns `json.dumps(...)`" removes a whole
   class of type mismatches.

Because [`.github/copilot-instructions.md`](../.github/copilot-instructions.md)
already encodes the layering rule and tool pattern, follow-up prompts can be much
shorter — Copilot has the conventions in context.

## Try it: add a third tool

With the repo open in Copilot CLI or VS Code:

> Add a `check_dependency_health` tool to the devops-triage agent. It should take
> a service name, walk `depends_on` from the service catalogue, and return each
> dependency with its tier and whether it has had a high-risk deploy in the last
> 12 hours. Follow the existing patterns in `triage.py` and `main.py`, and add
> tests.

Then verify:

```bash
pytest
azd ai agent run devops-triage --no-client
# in a second terminal:
azd ai agent invoke devops-triage --local "Is anything checkout depends on unhealthy?"
```

There's also a reusable prompt file for this —
[`.github/prompts/add-agent-tool.prompt.md`](../.github/prompts/add-agent-tool.prompt.md).

## What init actually wrote

```
azure.yaml                    # agent service block appended
src/my-agent/
  main.py                     # the agent
  requirements.txt            # runtime deps -- Foundry installs these
  Dockerfile                  # only used in container deploy mode
  .env.example
  .azdignore                  # excluded from the deploy package
```

Module 02 pulls `azure.yaml` apart field by field.

---

← [00 — Prerequisites](00-prerequisites.md) · Next → [02 — Anatomy of a hosted agent](02-anatomy-of-a-hosted-agent.md)
