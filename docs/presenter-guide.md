# Presenter guide

Everything you need to run this as a live demo, including what to say, what will
go wrong, and how to reset.

---

## Before you start

Run this **the day before**, not five minutes before:

```bash
azd auth login && az login          # same account for both
azd provision                        # ~2 min
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME gpt-5.4-mini
azd deploy                           # ~2 min
azd ai agent doctor                  # everything green
```

Then pre-warm both agents so the first live invoke isn't a cold start:

```bash
azd ai agent invoke devops-triage "warmup"
azd ai agent invoke docs-qa "warmup"
```

Set up per-agent venvs if you plan to demo the local loop
([module 04](04-run-locally.md)).

**Terminal setup:** large font, two panes. Left pane at the repo root for
commands, right pane free for `azd ai agent run`.

**Browser tabs, pre-opened and pre-authenticated:**
1. The repo on GitHub
2. Foundry Playground for `devops-triage`
3. Application Insights → Logs
4. An issue assigned to the Copilot coding agent (started earlier — it takes
   minutes to produce a PR)

---

## Timing options

| Slot | Modules to run |
| --- | --- |
| **10 min** | Beat 1, 2, 5 |
| **25 min** | Beats 1–6 |
| **45 min** | All beats, with the local loop and eval discussion |
| **Workshop** | Attendees work through `docs/00`–`09` themselves |

---

## Beat 1 — The problem (2 min, no terminal)

> "Most agent demos show one `main.py` and stop. Then you try to ship it and hit
> the real questions: how do I know it isn't making things up? What happens when
> I change the prompt? Who deploys it? This repo is the whole loop, and every
> command in it has actually been run."

Show the README architecture diagram. Land the shape: **your code, running inside
Foundry, with the platform handling container build, identity, versioning, and
tracing.**

---

## Beat 2 — One file describes everything (3 min)

Open `azure.yaml`. Scroll slowly.

> "Three services. One is the Foundry project and the model deployment. Two are
> agents. `uses: ai-project` is the link. `codeConfiguration` means Foundry
> builds the runtime for me — there's a Dockerfile in the repo but it isn't used."

Then `src/devops-triage/main.py`:

> "Four moves, every time. A client bound to the model. Tools. An Agent with
> instructions. A server. The `DefaultAzureCredential` line is the same code
> locally and in Foundry — my `az login` identity here, managed identity there.
> No keys anywhere."

---

## Beat 3 — The layering rule (2 min)

Open `triage.py`, then `tests/`:

```bash
pytest
```

```
55 passed in 0.12s
```

> "No Azure. No model. No network. That's because the domain logic imports
> nothing from the agent framework — `main.py` is only wiring. If you can't unit
> test it, it's in the wrong file. This is also what makes the Copilot coding
> agent effective later: it has a fast, honest signal."

---

## Beat 4 — Local loop (5 min, optional)

```bash
azd ai agent run devops-triage --no-client
```

While it boots, explain the venv-next-to-`requirements.txt` rule. Then in the
other pane:

```bash
azd ai agent invoke devops-triage --local "Checkout is returning 5xx for about 12% of requests, ~3000 users affected."
```

Point at the server log:

```
classify_incident_severity -> SEV2
lookup_service_owner(checkout) -> found=True
list_recent_deployments(checkout, 24h)
get_service_runbook(checkout, 'elevated 5xx')
```

> "That's the agent's reasoning, in order. Four tools, exactly as the
> instructions prescribe."

Drop `--no-client` if you'd rather show the Agent Inspector UI.

---

## Beat 5 — The deployed agents (6 min) ★ the money beat

```bash
azd ai agent invoke devops-triage "The ledger service posting queue is backing up and writes are failing. This is blocking all payments."
```

When the answer lands, point at **next action 1**:

> "STOP: never restart the ledger writer without first capturing the queue depth.
> That's a safety-critical instruction from the runbook, and it survived into the
> answer. That's not luck — it's a weighted dimension in the eval suite."

Then the pair that sells grounding:

```bash
azd ai agent invoke docs-qa "If my merchant balance is too low to cover a refund, what happens?"
azd ai agent invoke docs-qa "What is the capital of Australia?"
```

```
...refund is queued with status `pending_funds` for up to 7 days...
Sources: refunds-policy#Insufficient balance

I don't have that in the Contoso Payments documentation.
```

> "Everyone can build the first one. The second one is the hard part — and notice
> it came back in about a second, because retrieval returned nothing so there was
> nothing to summarise. That refusal is an automated eval case, not a hope."

**Then show the unknown-service case**, which is the same idea in the other agent:

```bash
azd ai agent invoke devops-triage "The teleport-gateway service is throwing errors. Who owns it?"
```

---

## Beat 6 — Measuring it (4 min)

Open `src/devops-triage/datasets/triage-core/triage-core.jsonl`.

> "Twelve hand-written cases. One per severity, alias resolution, a tier-3
> service that must *not* be paged at 2am, and an unknown service. I wrote these
> by hand because when I let the tool generate them, it invented services that
> don't exist in this agent's catalogue — and then you're scoring the agent
> against fiction."

Show the real result:

```
Results:    12 total, 6 passed, 6 failed, 0 errored
```

> "Six out of twelve. That's a real first-run baseline, and I'm showing it on
> purpose. The suite did its job — it found the gap between what the agent does
> and what I said it should do. That number is the thing you move."

---

## Beat 7 — Copilot did the work (4 min)

Show `.github/copilot-instructions.md` and `AGENTS.md`.

> "The layering rule, the tool pattern, the never-fabricate rules — they're
> written down where Copilot reads them. That's why a one-line prompt produces
> code in the house style."

Live prompt in Copilot CLI:

> *Add a `check_dependency_health` tool to the devops-triage agent that walks the
> dependency graph and flags any dependency with a high-risk deploy in the last
> 12 hours. Follow the existing patterns and add tests.*

Then switch to the pre-started coding-agent PR:

> "Same idea, asynchronous. I filed an issue with acceptance criteria and
> assigned it to Copilot before this session. Here's the PR it opened — it ran
> the tests before asking for my review."

---

## Beat 8 — Close (1 min)

> "Scaffold, run, deploy, evaluate, observe, automate. Two agents, one
> `azure.yaml`, 55 tests, an eval suite with a real score, and CI that deploys
> with no secrets. Repo's public — the lab in `docs/` is exactly what I just did."

```bash
azd down --purge
```

Do this on screen. It's a good habit to model.

---

## When it goes wrong

| Symptom | On-stage recovery |
| --- | --- |
| Invoke is slow (>30s) | Talk over it — first byte is ~8s, that's the model. Have a pre-warm ready. |
| `403` | You're in the account-mismatch trap. Switch to the pre-recorded output; fix later. Don't debug RBAC live. |
| `multiple azure.ai.agent services found` | You forgot the service name. Own it — it's a real thing attendees will hit. |
| Local server won't start | Skip to the deployed agents. Beat 5 doesn't need beat 4. |
| Eval run picks the wrong agent | This is a genuine CLI limitation; call it out honestly. It lands better than pretending. |

**Rule:** never debug live for more than 30 seconds. Move to the next beat and
come back.

---

## Reset between sessions

```bash
./scripts/reset-demo.ps1     # Windows
./scripts/reset-demo.sh      # macOS / Linux
```

Removes local venvs, caches, and generated eval artifacts, and re-runs
`azd ai agent doctor`. It does **not** touch Azure resources — deployed agents
stay warm between back-to-back sessions.

Full teardown:

```bash
azd down --purge
```

---

## Questions you will get

**"Why not Azure AI Search for the docs agent?"**
Deliberate. BM25 in the standard library keeps the demo free, deterministic, and
reproducible. The tool contract is identical, so swapping in AI Search is a
change to `retrieval.py` only — `main.py` doesn't move.

**"Is this production-ready?"**
The shape is. You'd add: a real service catalogue instead of JSON fixtures,
private networking, a higher eval pass rate with a CI gate, and content-safety
guardrails.

**"How much does it cost?"**
Infrastructure is ~free at idle. You pay for model tokens and Log Analytics
ingestion. A full lab run is under a dollar.

**"Can I use my own model?"**
Change `services.ai-project.deployments[]` in `azure.yaml` and re-run
`azd provision`. Check regional availability first.

**"Why two agents?"**
They fail differently. One can invent a service; the other can answer without a
source. Different failure modes need different guardrails and different evals.
