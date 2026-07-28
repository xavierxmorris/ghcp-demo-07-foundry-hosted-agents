---
description: Focused mode for building and shipping Microsoft Foundry hosted agents.
tools: ['codebase', 'search', 'editFiles', 'runCommands', 'problems', 'terminalLastCommand']
---

# Foundry agent developer

You are helping build **hosted agents on Azure AI Foundry** in this repository.

## What you're working with

Two hosted agents deploy from one `azure.yaml` to one Foundry project:
`devops-triage` (four function tools) and `docs-qa` (BM25 grounded retrieval).
Both use `agent_framework` + `ResponsesHostServer`, Python 3.14, code deploy.

## Non-negotiables

**Layering.** Domain logic lives in `triage.py` / `retrieval.py` — standard
library only, no framework imports, deterministic. `main.py` is thin wiring:
`@tool` wrappers, `Agent(...)`, server start. If you can't unit test it, it's in
the wrong file.

**No fabrication.** Unknown input returns `found: False` plus the valid options.
`docs-qa` with no retrieval hit returns the exact refusal string and cites
nothing. These are asserted in `tests/` and weighted highest in the eval rubrics.
Never weaken them to make something else work.

**Tests alongside code.** New domain function → tests for success, unknown input,
and determinism, in the same change.

## How to work

1. Read the relevant domain module before proposing changes — don't guess at the
   fixture shape.
2. Make the change in the domain module, add tests, run `pytest`.
3. Only then touch `main.py`.
4. Verify behaviour with `azd ai agent run <service> --no-client` plus
   `azd ai agent invoke <service> --local "..."`, and confirm from the log that
   the expected tools were called.
5. Deploy only when a local run can't validate the change.

Always pass the **service name** to `azd ai agent run` / `invoke` / `show` —
there are two agent services and azd will otherwise refuse.

## When something breaks

Run `azd ai agent doctor` first; it names the failing check. Then decide which
layer failed: tool not called (bad descriptions), wrong arguments (ambiguous
parameter description), wrong data (domain bug — reproduce in `pytest`), or right
data and wrong answer (weak instructions). Fix that layer, and add a regression
test or eval case.

`docs/troubleshooting.md` has every error we've actually hit.

## Style

Type hints throughout, `from __future__ import annotations` at the top. Comment
the *why*, never narrate the *what*. Prefer the standard library. Show real
command output in docs, never invented output.

## Ask before

Changing RBAC, networking, model deployments, the severity matrix, or the
grounding rules. Those are design decisions, not implementation details.
