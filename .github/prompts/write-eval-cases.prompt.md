---
mode: agent
description: Write or extend evaluation cases for a hosted agent, grounded in the real fixtures.
---

# Write eval cases

Add cases to an agent's evaluation dataset in
`src/<agent>/datasets/<suite>/<suite>.jsonl`.

Ask me which agent and what behaviour I want covered, unless I've said.

## Read the ground truth first

Cases must be grounded in what the agent can actually see:

- `devops-triage` → `src/devops-triage/data/services.json`, `deployments.json`,
  `runbooks.json`
- `docs-qa` → `src/docs-qa/knowledge/*.md`

**Never invent a service, team, deployment id, runbook URL, or documentation
fact.** A case built on fiction scores the agent against fiction, and makes the
question "did the agent fabricate?" unanswerable. This is exactly why these
datasets are hand-authored rather than generated.

## Row format

One JSON object per line, no trailing commas, no blank lines:

```json
{"id": 13, "description": "Why this case exists and what it proves.", "query": "What the user sends.", "candidate_response": "The reference answer."}
```

- `description` — the most important field. It tells the evaluator generator
  which dimension the case targets. Be explicit: *"Tier-3 service out of hours;
  the correct answer is a low severity and explicitly NOT paging."*
- `query` — realistic phrasing. Real users are terse, misspell, and omit context.
- `candidate_response` — what a correct answer looks like, in the agent's actual
  output format, using only facts from the fixtures.

Use the next unused integer `id`.

## Cover these categories

For **any** agent:
1. Happy path
2. Boundary — the exact threshold in the source data
3. Ambiguous input the agent must handle without guessing
4. **Unknown input** — the agent must decline and list valid options
5. Adversarial phrasing — an instruction rather than a question, or a plausible
   but out-of-scope topic

For `devops-triage` specifically: each severity level, alias resolution, a
service with no deployments in the window, and the safety-critical ledger STOP
step.

For `docs-qa` specifically: single-fact, multi-section, cross-document, a
limitation ("no, you can't"), and at least one out-of-scope refusal per batch —
including one that *sounds* in-domain.

## Rubric

If the new cases target a behaviour the rubric doesn't score, add a dimension to
`src/<agent>/evaluators/<suite>/rubric_dimensions.json`:

```json
{"id": "dimension_name", "description": "Precisely what the judge should check, including what scores zero.", "weight": 8}
```

Weight highest the thing you would revert a release for.

## Validate

```bash
python -c "import json,pathlib; [json.loads(l) for l in pathlib.Path('src/<agent>/datasets/<suite>/<suite>.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]" && echo OK
```

To run the suite, remember the rubric must be registered first — see
`docs/06-evaluate.md`, and check the `Agent:` line in the run summary, because
`eval run` binds to the first agent service in `azure.yaml`.
