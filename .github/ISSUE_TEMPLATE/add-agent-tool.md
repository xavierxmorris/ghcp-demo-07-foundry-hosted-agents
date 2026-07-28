---
name: Add an agent tool
about: A well-scoped task suitable for assigning to the GitHub Copilot coding agent
title: 'Add <tool_name> tool to <agent>'
labels: ['enhancement', 'good first issue', 'copilot']
---

<!--
This template is shaped so it can be assigned straight to the Copilot coding
agent. The parts that make that work: a concrete file map, machine-checkable
acceptance criteria, and an explicit out-of-scope section.
See docs/09-coding-agent.md
-->

## What

<!-- One paragraph: what the tool does, what it takes, what it returns. -->

Add a `<tool_name>` tool to the `<agent>` agent that ...

## Where

| Change | File |
| --- | --- |
| Domain logic | `src/<agent>/<triage or retrieval>.py` |
| Tests | `tests/test_<agent>_*.py` |
| Tool wrapper + registration | `src/<agent>/main.py` |
| Eval case | `src/<agent>/datasets/<suite>/<suite>.jsonl` |

## Data available

<!-- Point at the real fixtures so nothing gets invented. -->

- `src/devops-triage/data/services.json` — service catalogue
- `src/devops-triage/data/deployments.json` — deployments, offsets in `hours_ago`
- `src/devops-triage/data/runbooks.json` — runbooks with trigger keywords
- `src/docs-qa/knowledge/*.md` — documentation corpus

## Acceptance criteria

- [ ] Logic lives in the domain module with **no** `agent_framework` or `azure.*`
      imports, and returns a plain `dict`
- [ ] Unknown input returns `found: False` plus the list of valid options —
      never a guess
- [ ] `pytest` passes, including new tests for the success path, the
      unknown-input path, and determinism
- [ ] `@tool` wrapper in `main.py` returns `json.dumps(...)`, has a one-line
      docstring, and `Annotated[..., Field(description=...)]` on every parameter
- [ ] Tool added to the `tools=[...]` list in `build_agent()`
- [ ] `INSTRUCTIONS` updated **only if** the agent's process changes
- [ ] At least one eval case added, with a real `description`
- [ ] No new entries in `requirements.txt`
- [ ] `ruff check src tests` is clean

## Out of scope

<!-- Explicitly listing this is what stops opportunistic refactoring. -->

- Changing the severity matrix or the output format
- Modifying the other agent
- Adding dependencies
- Any change to `azure.yaml` infrastructure
