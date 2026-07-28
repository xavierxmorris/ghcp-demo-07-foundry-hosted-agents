# 04 — Run and debug locally

**Time:** ~15 minutes
**Goal:** iterate on agent code in seconds instead of minutes.

Local run does **not** need a deployed agent. Your code runs on your machine and
calls the Foundry model endpoint directly with your own credentials. You only
need a provisioned project (module 03) and a `.env`.

## Set up the virtual environment — in the right place

```bash
cd src/devops-triage          # NOT the repo root
python -m venv .venv
# Windows:        .\.venv\Scripts\Activate.ps1
# macOS / Linux:  source .venv/bin/activate
python -m pip install uv
```

Two rules that are easy to get wrong:

1. **The venv must live next to `requirements.txt`**, inside the agent's source
   directory. `azd ai agent run` resolves the venv relative to that directory. A
   venv at the repo root is silently ignored and azd creates a second one.
2. **Install `uv` into it, and leave it activated.** `azd ai agent run` installs
   `requirements.txt` itself, and uses `uv` from the active environment when it
   can — seconds instead of minutes. Do **not** `pip install -r requirements.txt`
   yourself.

## Start the agent

From the repo root, with that venv still active:

```bash
azd ai agent run devops-triage --no-client
```

Because this repo has two agent services, **the service name is required**.
Without it:

```
ERROR: could not resolve agent service in azd project:
multiple azure.ai.agent services found in azure.yaml: devops-triage, docs-qa
```

Wait for the readiness line before invoking anything:

```
[2026-07-28 10:17:27 +1000] [15272] [INFO] Running on http://0.0.0.0:8088 (CTRL + C to quit)
```

`Starting agent on http://localhost:8088` is printed *before* the socket is
bound — invoking then gives a misleading `could not connect`.

> **Harmless noise.** You'll see a `ConnectionError` trace for
> `169.254.169.254/metadata/instance/compute`. That's the Azure instance-metadata
> probe failing because you're not on an Azure VM. Ignore it.

Drop `--no-client` to open the **Agent Inspector**, a browser UI that shows each
turn, every tool call with its arguments and return value, and token usage. It is
the fastest way to see *why* the model chose a tool.

## Invoke it

In a second terminal:

```bash
azd ai agent invoke devops-triage --local "Checkout is returning 5xx for about 12% of requests, ~3000 users affected."
```

Real output:

```
Target:       localhost:8088 (local)
[local] **Severity:** SEV2 - Major functionality broken with 12% 5xxs...
**Service:** Checkout API (tier-1) - owned by Payments Core
**Page:** payments-core-primary via #payments-core-oncall
**Likely cause:** chk-2291 — high-risk deploy 2 hours ago...

Server responded in 15.361s
```

Useful flags:

| Flag | Purpose |
| --- | --- |
| `--new-session` | Discard saved conversation state and start clean |
| `--port <n>` | Match a non-default `run --port` |
| `-f request.json` | Send a file body instead of a string |
| `--protocol invocations` | Test the A2A protocol instead of Responses |

## Try the docs-qa agent

Stop the first agent (both use port 8088), then:

```bash
cd src/docs-qa && python -m venv .venv && .\.venv\Scripts\Activate.ps1
python -m pip install uv && cd ../..
azd ai agent run docs-qa --no-client
```

Then run the two invocations that define this agent:

```bash
# In the corpus -- expect a cited answer
azd ai agent invoke docs-qa --local "How long do I have to submit evidence for a Mastercard chargeback?"

# Not in the corpus -- expect a refusal
azd ai agent invoke docs-qa --local --new-session "What is the capital of Australia?"
```

```
[local] You have **21 days** to submit evidence for a **Mastercard** chargeback...
Sources: chargebacks-and-disputes#Response deadlines, chargebacks-and-disputes#Evidence that wins

[local] I don't have that in the Contoso Payments documentation.
```

The refusal takes ~1s versus ~9s for the grounded answer — retrieval returns
nothing, so the model has nothing to summarise and declines immediately.

## The inner loop

```
edit triage.py / retrieval.py
      ↓
pytest                     ← milliseconds, no Azure, no model
      ↓
edit main.py instructions
      ↓
azd ai agent run + invoke --local     ← seconds, real model
      ↓
azd deploy                            ← ~2 min, only when needed
```

Stay in the top half. Push a deploy only when you change something a local run
can't validate.

## When local isn't enough

Deploy when you've changed:

- `protocols`, `container.resources`, or `environmentVariables` in `azure.yaml`
- the model deployment
- anything needing a real Foundry connection (AI Search, Bing, MCP, A2A)
- or you're ready to publish an immutable version

**Always stop the local server before deploying** — a live process holds files in
the project directory.

---

← [03 — Provision](03-provision-azure.md) · Next → [05 — Deploy to Foundry](05-deploy-to-foundry.md)
