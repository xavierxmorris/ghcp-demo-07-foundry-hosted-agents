# 06 — Evaluate quality

**Time:** ~20 minutes
**Goal:** replace "it looked fine when I tried it" with a number that moves.

## Preflight before using the saved configs

The committed `eval.yaml` files are historical run artifacts, **not portable
defaults**. As inspected on **7 September 2026**:

- Both contain an absolute path from the author's machine.
- Both reference `evaluators\smoke-core`, which is not the shipped rubric folder.
- The docs-qa config names `devops-triage` and references an absent
  `.agent_configs\baseline\metadata.yaml`.

Before spending tokens, create an environment-specific evaluation configuration
using the current tooling. Select the intended agent and deployed version,
resolve the actual dataset and rubric paths, and verify/register the evaluator
in that project. The shipped rubric directories are `triage-core` and
`grounding-core`. Do not copy evaluator version numbers from a different project.

Inspect `azd ai agent eval run --help` and the resulting run's target identity.
The locally inspected `azure.ai.agents` **1.0.0-beta.7** command still lacks an
`--agent` option; this is a version-specific observation, not a claim about
future versions. Prefer an explicitly targeted portal/current-tooling run
over reordering shared deployment configuration to influence target selection.

The examples and scores below document the original July run. See the
[workshop](../WORKSHOP.md) for a repeatable evidence record.

## Two kinds of test, and why you need both

| | Unit tests (`tests/`) | Evals (`src/<agent>/eval.yaml`) |
| --- | --- | --- |
| Tests | Tool logic | Agent behaviour |
| Needs a model? | No | Yes |
| Speed | 0.12s for 55 tests | ~1.5 min for 12 cases |
| Deterministic? | Yes | No — scored by a judge model |
| Catches | "severity matrix is wrong" | "the agent ignored the severity tool" |

Unit tests check that `classify_severity("checkout is down")` returns `SEV2`.
Inspect tool-call traces to establish whether the agent actually called it.
A correct answer or a favorable judge score alone does not prove tool use.

## What's in this repo

Each agent ships an authored suite:

```
src/devops-triage/
  eval.yaml                                  # suite definition
  datasets/triage-core/triage-core.jsonl     # 12 cases
  evaluators/triage-core/rubric_dimensions.json

src/docs-qa/
  eval.yaml
  datasets/grounding-core/grounding-core.jsonl   # 15 cases
  evaluators/grounding-core/rubric_dimensions.json
```

### The dataset format

One JSON object per line:

```json
{
  "id": 7,
  "description": "Unknown service. The critical behaviour: refuse to invent an owner or runbook, and list the services that do exist.",
  "query": "The teleport-gateway service is throwing errors. Who owns it and what do I do?",
  "candidate_response": "I don't have teleport-gateway in the service catalogue, so I can't give you an owner..."
}
```

- `query` — what gets sent to the agent.
- `candidate_response` — the reference answer, used to calibrate the judge.
- `description` — *why this case exists*. Write this properly; it is what tells
  the evaluator generator which dimensions matter.

### Why these cases were authored, not generated

`azd ai agent eval generate` will happily invent a dataset. When we tried it for
`devops-triage`, it produced cases about `auth-service` and `auth-cache` —
services that **do not exist** in this agent's catalogue. Every one of those
cases would score the agent on fabricated ground truth, which makes the most
important question ("did the agent invent a service?") unanswerable.

So the datasets here are hand-written against the real fixtures in
`src/devops-triage/data/` and `src/docs-qa/knowledge/`. Coverage is deliberate:

**`triage-core`** — one case per severity level, alias resolution, a service with
no recent deploys, a tier-3 out-of-hours case that must *not* page, the
safety-critical ledger STOP step, a near-signal-free report, and an unknown
service.

**`grounding-core`** — single-fact lookups, multi-section answers, cross-document
answers, a limitation ("no, BNPL can't be partially refunded"), and **three
out-of-scope cases**, including one that is payments-adjacent and plausible
(processing fees) and one phrased as an instruction rather than a question.

Those three refusal cases are the point of the suite.

### The rubric

`rubric_dimensions.json` is a weighted list of things a judge model scores:

```json
{
  "id": "refuses_when_ungrounded",
  "description": "When the corpus does not contain the answer, the response is exactly the refusal string... Any attempt to answer an ungrounded question scores zero on this dimension.",
  "weight": 10
}
```

Weight the dimension you'd revert a release for the highest. Here that's
`no_fabrication` (triage) and `refuses_when_ungrounded` (docs-qa).

## Running an eval

Custom rubrics must be **registered in the Foundry project** before a run — a
local file is not enough. `azd ai agent eval generate` does the registration, and
accepts your own dataset with `--dataset`:

```bash
# 1. Register: uses OUR dataset, generates + registers a rubric from it
azd ai agent eval generate \
  --agent devops-triage \
  --dataset ./src/devops-triage/datasets/triage-core/triage-core.jsonl \
  --gen-instruction "Triages production incidents... Must never invent a service, team, deployment id, or runbook URL." \
  --reset-defaults --no-prompt

# 2. Run
azd ai agent eval run --config ./src/devops-triage/eval.yaml --name triage-core
```

Real result from this repo:

```
Eval:       eval_02f899e4c73245eab27fb90c07602cb4
Name:       triage-core
Status:     Completed
Agent:      devops-triage v1

Results:    12 total, 6 passed, 6 failed, 0 errored
```

**6 out of 12.** That is a genuine first-run baseline, and it is the honest
starting point of every agent project. The suite has done its job: it found
places where the agent's behaviour and the rubric disagree. Improving that number
is module 06's homework — tighten the instructions, re-deploy, re-run, compare.

The `--gen-instruction` you pass shapes the rubric, so make it describe the
*constraints* you care about, not just the feature.

### Multi-agent gotcha

`azd ai agent eval run` resolves the agent from the **first** `azure.ai.agent`
service in `azure.yaml`, and has no `--agent` flag (unlike `generate`). In this
repo that means it always targets `devops-triage`.

We hit this: running the `docs-qa` suite with `--config src/docs-qa/eval.yaml`
still executed against `devops-triage`, and 14 of 15 cases failed for the obvious
reason. Check the `Agent:` line in the run summary before trusting a score.

This was the behavior observed with the original extension. Check your installed
version rather than assuming it is fixed or permanent. Use an explicitly
selected agent in the Foundry portal/current tooling and verify the run summary.
Do not casually reorder a shared deployment to work around evaluation selection.

## Iterating

```
run eval  →  read the failures  →  change instructions or tools
     ↑                                      ↓
     └──────────  azd deploy  ←─────────────┘
```

Inspect individual results:

```bash
azd ai agent eval list
azd ai agent eval show --run <evalrun-id>
```

Ask Copilot to do the analysis — there's a prompt file for it:
[`.github/prompts/write-eval-cases.prompt.md`](../.github/prompts/write-eval-cases.prompt.md).

## Automatic prompt optimisation

Once you have a suite, Foundry can optimise the instructions against it:

```bash
azd ai agent optimize --optimize-model gpt-5.4-mini
azd ai agent optimize status
azd ai agent optimize apply      # writes the winning prompt locally
azd ai agent deploy
```

This only works if your eval suite is good. A weak suite optimises toward the
wrong thing — which is the real argument for authoring your cases by hand.

---

← [05 — Deploy](05-deploy-to-foundry.md) · Next → [07 — Observability](07-observability.md)
