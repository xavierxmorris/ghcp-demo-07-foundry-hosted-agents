---
mode: agent
description: Add a new function tool to one of the hosted agents, following this repo's layering rule.
---

# Add a tool to a hosted agent

Add a new function tool to a Foundry hosted agent in this repository.

Ask me first, unless I already said:
- **Which agent** — `devops-triage` or `docs-qa`
- **What the tool does** and what it returns
- **Where the data comes from** — an existing fixture, a new fixture, or derived

## Follow this order

**1. Domain logic first.** Add the function to `src/<agent>/triage.py` or
`src/<agent>/retrieval.py`.
- Standard library only. No `agent_framework`, no `azure.*`, no network.
- Return a plain `dict`.
- Unknown or unmatched input returns `{"found": False, ...}` **plus the valid
  options**. Never guess, never invent an entity.
- Deterministic: identical input must produce identical output.

**2. Tests next**, in `tests/test_<agent>_*.py`. Cover, at minimum:
- the success path
- the unknown-input path, asserting no fabrication
- determinism (same call twice, same result)
- any boundary the logic introduces

Run `pytest` and make it green before continuing.

**3. Tool wrapper last**, in `src/<agent>/main.py`:

```python
@tool(approval_mode="never_require")
def my_tool(
    arg: Annotated[str, Field(description="Precise description the model reads.")],
) -> str:
    """One line describing when to use this tool."""
    result = triage.my_function(arg)
    logger.info("my_tool(%s) -> found=%s", arg, result["found"])
    return json.dumps(result)
```

- Every parameter needs `Annotated[..., Field(description=...)]`. That text is
  the model's only guide — vague descriptions cause wrong tool calls.
- The docstring becomes the tool description.
- Return `json.dumps(...)`.
- Include a log line so the call is visible in traces.

**4. Register it** in the `tools=[...]` list in `build_agent()`.

**5. Update `INSTRUCTIONS`** only if the agent's process changes — say when to
call the tool and how its output affects the answer.

**6. Add an eval case** to `src/<agent>/datasets/*/*.jsonl` exercising the new
behaviour, including the unknown-input case. Write a real `description`
explaining why the case exists.

## Verify before you report done

```bash
pytest
azd ai agent run <agent> --no-client       # wait for the "Running on" line
azd ai agent invoke <agent> --local "<a prompt that should trigger the tool>"
```

Confirm from the server log that the new tool was actually called. If the model
never calls it, the `Field` descriptions or the docstring are the problem — not
the code.

## Do not

- Put business logic inside the `@tool` function
- Add a runtime dependency unless genuinely unavoidable
- Weaken any existing never-fabricate rule
- Skip the tests
