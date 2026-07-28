# 09 — Hand work to the GitHub Copilot coding agent

**Time:** ~15 minutes
**Goal:** file an issue, assign it to Copilot, review the PR it opens.

Modules 01–08 used Copilot as a pair programmer in your terminal or editor. The
**coding agent** is different: it works asynchronously in GitHub, on its own
branch, and opens a pull request you review like any other.

## Making the repo agent-ready

Three things decide whether the coding agent succeeds here.

### 1. `copilot-setup-steps.yml`

The agent runs in a fresh container. Without setup it can't run your tests, so it
can't verify its own work.

[`.github/workflows/copilot-setup-steps.yml`](../.github/workflows/copilot-setup-steps.yml)
pre-installs Python 3.14, the dev dependencies, and `azd` with the Foundry
extensions. The job **must** be named `copilot-setup-steps`.

```yaml
jobs:
  copilot-setup-steps:        # this exact name is required
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'
      - run: pip install -r requirements-dev.txt
```

Verify it independently — it's a normal workflow:

```bash
gh workflow run copilot-setup-steps.yml
gh run watch
```

### 2. Instructions

[`AGENTS.md`](../AGENTS.md) and
[`.github/copilot-instructions.md`](../.github/copilot-instructions.md) carry the
layering rule, the tool-authoring pattern, and the non-negotiable grounding
behaviour. The coding agent reads these. Without them it will cheerfully put
business logic in a `@tool` function and skip the tests.

### 3. Tests that actually gate

55 unit tests that run in 0.12 seconds with no Azure. The agent runs them, sees
failures, and iterates before opening the PR. **This is the single highest-value
thing you can give a coding agent.** An agent without a fast test signal is
guessing.

## Writing an issue it can succeed at

Bad:

> Make the triage agent better

Good — and this is a real issue in
[`.github/ISSUE_TEMPLATE/`](../.github/ISSUE_TEMPLATE/):

> **Add a `check_dependency_health` tool to devops-triage**
>
> **What:** a tool that takes a service name, walks `depends_on` from
> `data/services.json`, and returns each dependency with its tier and whether it
> had a medium- or high-risk deploy in the last 12 hours.
>
> **Where:** logic in `src/devops-triage/triage.py`, thin `@tool` wrapper in
> `src/devops-triage/main.py`.
>
> **Acceptance criteria:**
> - `pytest` passes, including new tests for: a service with dependencies, a
>   service with none (`postgres-payments`), an unknown service, and the
>   external `feature-store` dependency that isn't in the catalogue
> - Unknown service returns `found: False` with `known_services`, never a guess
> - The tool appears in the agent's `tools=[...]` list and `INSTRUCTIONS`
>   mentions when to use it
> - No new dependencies in `requirements.txt`
>
> **Out of scope:** changing severity classification or the output format.

What makes it work: **a concrete file map, machine-checkable acceptance criteria,
and an explicit out-of-scope section.** The out-of-scope line is what stops an
agent from opportunistically rewriting things you didn't ask about.

## Assign it

```bash
gh issue create --title "Add check_dependency_health tool" --body-file issue.md
# then assign to Copilot in the GitHub UI, or:
gh issue edit <n> --add-assignee "@copilot"
```

Copilot pushes a branch, opens a draft PR, and reports progress in the PR
timeline. You review it exactly like a human contribution.

## Reviewing the PR

Domain-specific things to check here:

- [ ] Logic is in `triage.py` / `retrieval.py`, **not** inside the `@tool` wrapper
- [ ] Every tool parameter has `Annotated[..., Field(description=...)]`
- [ ] The tool returns `json.dumps(...)` of a plain dict
- [ ] Unknown input returns `found: False` plus valid options — no fabrication
- [ ] Tests cover success, unknown input, and determinism
- [ ] No new runtime dependency unless genuinely required
- [ ] `INSTRUCTIONS` updated if the agent's process changed

Ask for changes in review comments; Copilot iterates on the same PR.

## Copilot code review

[`.github/workflows/`](../.github/workflows/) can also request an automatic
Copilot review on every PR, which catches the mechanical issues before you look.
Combined with `ci.yml`, a PR arrives already linted, tested, and reviewed.

## Where the boundary is

| Good fit for the coding agent | Keep for yourself |
| --- | --- |
| Add a tool following an existing pattern | Design the agent's core contract |
| Extend the docs corpus, add eval cases | Decide what "correct" means |
| Improve test coverage | Change the severity matrix |
| Fix a reproducible bug with a failing test | Anything touching production RBAC or cost |

The agent is excellent at *more of the same, done carefully*. Judgement calls
about what the agent should do stay with you.

---

← [08 — CI/CD](08-cicd.md) · Back to [README](../README.md)
