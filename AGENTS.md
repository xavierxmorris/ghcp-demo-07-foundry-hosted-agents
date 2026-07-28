# Agent Instructions

This repository is a teaching demo: **hosted AI agents on Azure AI Foundry,
built with GitHub Copilot**. It contains two hosted agents deployed from a
single `azure.yaml`.

This project was built with the microsoft-foundry skill. Before working on or answering questions about foundry agents, read the microsoft-foundry skill first.

## Repository map

| Path | What it is |
| --- | --- |
| `azure.yaml` | The whole deployment: Foundry project, model deployment, both agents |
| `src/devops-triage/` | Incident-triage agent — function/tool calling |
| `src/docs-qa/` | Documentation Q&A agent — grounded retrieval |
| `tests/` | Unit tests for the tool layer, no Azure needed |
| `src/<agent>/eval.yaml` + `datasets/` + `evaluators/` | Eval suite per agent |
| `docs/` | The step-by-step lab |
| `.github/` | Copilot customisation, CI/CD |

## The one architectural rule

**Tool logic never lives in `main.py`.**

- `main.py` — imports `agent_framework`, defines `@tool` wrappers, builds the
  `Agent`, starts `ResponsesHostServer`. Thin.
- `triage.py` / `retrieval.py` — plain Python, **no framework imports**, pure
  functions, deterministic. This is where behaviour lives.

Why: the domain module is unit-testable in milliseconds without a model, an
Azure resource, or a network call. When you add capability, add it to the domain
module first, test it, then expose a thin `@tool` wrapper.

## Adding a tool

1. Write the function in `triage.py` or `retrieval.py`. Return a plain `dict`.
2. Add tests to `tests/`. Cover the success path, the unknown-input path, and
   determinism.
3. Add a `@tool(approval_mode="never_require")` wrapper in `main.py` that calls
   it and returns `json.dumps(result)`.
4. Annotate every parameter with `Annotated[T, Field(description=...)]` — the
   description is what the model sees when deciding whether to call the tool.
5. Update the agent's `instructions` if the tool changes the expected process.
6. Run `pytest`, then `azd ai agent run <service> --no-client` and invoke it.

## Never invent data

Both agents are built to be honest:

- `devops-triage` must only report services, teams, deployments, and runbooks
  that the tools returned. Unknown service → say so and list known ones.
- `docs-qa` must only answer from retrieved chunks and must cite them. No
  retrieval hit → `"I don't have that in the Contoso Payments documentation."`

If you change the instructions, do not weaken these. They are covered by eval
cases under `src/<agent>/datasets/`.

## Commands

```bash
# Tests (no Azure required)
pytest

# Local run + invoke  (two terminals; run from repo root)
azd ai agent run devops-triage --no-client
azd ai agent invoke devops-triage --local "Checkout is throwing 5xx"

# Deploy + remote invoke
azd deploy
azd ai agent invoke devops-triage "Checkout is throwing 5xx"

# Health check -- run this first when anything is broken
azd ai agent doctor

# Tear down
azd down --purge
```

With two agent services in `azure.yaml`, **always pass the service name** to
`azd ai agent run` and `azd ai agent invoke`, or azd will refuse with
`multiple azure.ai.agent services found`.

## Conventions

- Python 3.14, runtime token `python_3_14` in `azure.yaml`.
- Standard library only in the agent domain modules. Adding a dependency means
  adding it to `requirements.txt` in **that agent's** directory.
- Tools return JSON strings; domain functions return dicts.
- Docstrings explain *why*, not *what*. Don't narrate obvious code.
- Never commit `.env`, `.azure/`, or anything containing an endpoint with a
  real resource name in a secret context.

## Gotchas that have already bitten us

- `az` and `azd` can be signed in as **different accounts**. Foundry data-plane
  calls fail with 403 even when you are subscription Owner. See
  `docs/troubleshooting.md`.
- Subscription `Owner` does **not** grant Foundry data-plane access. You need
  `Foundry User` / `Azure AI Developer` on the AI Services account.
- `--no-inspector` is deprecated; use `--no-client`.
- Keep the local `.venv` inside `src/<agent>/`, next to `requirements.txt`.
