# GitHub Copilot instructions

You are working in a demo repository that teaches **hosted AI agents on Azure AI
Foundry**. Suggestions should be exemplary — people read this code to learn.

## Context

Two hosted agents deploy from one `azure.yaml` to a single Foundry project:

- `src/devops-triage/` — incident triage via four function tools
- `src/docs-qa/` — grounded documentation Q&A via BM25 retrieval

Both use the `agent_framework` SDK with `ResponsesHostServer`, Python 3.14,
and `codeConfiguration` (code deploy — Foundry builds the runtime, the
`Dockerfile` is only used if you switch to container deploy).

## Layering rule — follow this

```
main.py        thin: @tool wrappers + Agent construction + server start
triage.py      pure domain logic, stdlib only, no framework imports
retrieval.py   pure retrieval logic, stdlib only, no framework imports
```

When asked to add agent capability, put the logic in the domain module and add
tests, then add the thin `@tool` wrapper. Never put business logic inside a
`@tool` function.

## Tool authoring pattern

```python
@tool(approval_mode="never_require")
def lookup_service_owner(
    service: Annotated[str, Field(description="Service name, id, or alias.")],
) -> str:
    """Look up ownership, on-call rotation, tier, SLA, and dependencies."""
    result = triage.lookup_service(service)
    logger.info("lookup_service_owner(%s) -> found=%s", service, result["found"])
    return json.dumps(result)
```

Required every time:
- `Annotated[..., Field(description=...)]` on every parameter — this text is the
  model's only guide to when and how to call the tool.
- A one-line docstring; it becomes the tool description.
- `json.dumps(...)` of a plain dict as the return value.
- A log line, so the tool call shows up in traces.

## Grounding and honesty

These agents must never fabricate. When editing instructions or tools, preserve:
- unknown input → return `found: False` plus the valid options, never a guess
- `docs-qa` with no retrieval hit → the exact refusal string
- every `docs-qa` answer ends with a `Sources:` line of real citations

These behaviours are asserted in `tests/` and in each agent's eval dataset under
`src/<agent>/datasets/`. If a change breaks them, the change is wrong.

## Testing

- `pytest` from the repo root. `tests/conftest.py` puts both agent directories
  on `sys.path`.
- Tests must not require Azure, network, or a model.
- New domain function → cover success, unknown-input, and determinism.

## azd usage

Because there are two agent services, always name the service:

```bash
azd ai agent run devops-triage --no-client
azd ai agent invoke devops-triage --local "..."
azd ai agent invoke docs-qa "..."
```

Use `--no-client` (not the deprecated `--no-inspector`). Run `azd ai agent doctor`
before proposing fixes for deployment problems — it names the failing check.

## Style

- Comment only what needs explaining, usually a *why*. No narration.
- Type hints everywhere; `from __future__ import annotations` at the top.
- Prefer standard library over new dependencies. A new dependency goes in the
  specific agent's `requirements.txt`.
- Markdown docs: sentence case headings, tables over prose lists for reference
  material, and always show real command output rather than invented output.

## Never

- Never commit `.env`, `.azure/`, keys, or connection strings.
- Never add platform variables that Foundry injects at runtime (`FOUNDRY_*`,
  `AGENT_*`) into `azure.yaml` `environmentVariables`.
- Never suggest `az cognitiveservices account deployment create` for model
  deployments in this repo — model deployments are declared in `azure.yaml`
  under `services.ai-project.deployments[]` and applied by `azd provision`.
