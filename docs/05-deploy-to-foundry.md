# 05 — Deploy to Foundry

**Time:** ~10 minutes
**Goal:** publish both agents as immutable versions and invoke them remotely.

## Deploy

```bash
azd deploy
```

`azd deploy` handles every agent service in `azure.yaml` — both agents go out in
one command, in parallel. Real output:

```
  devops-triage: Packaging (Packaging code)
  docs-qa: Packaging (Packaging code)
  devops-triage: Deploying (Deploying hosted agent (code deploy))
  docs-qa: Deploying (Creating agent)
  devops-triage: Deploying (Waiting for agent to become active)
  devops-triage: Done [2m2s]
  docs-qa: Done [2m10s]

SUCCESS: Your application was deployed to Azure in 2 minutes 10 seconds.
```

To deploy just one:

```bash
azd deploy docs-qa
```

### What happens

1. The `project:` directory is zipped, honouring `.azdignore` (which is why
   `datasets/`, `evaluators/`, and `.venv/` don't ship).
2. The ZIP uploads to Foundry.
3. Foundry builds the runtime from `requirements.txt` — no Docker on your machine.
4. A **new immutable agent version** is registered.
5. `AGENT_<SERVICE>_NAME` / `_VERSION` are written back to the azd env.

> With `codeConfiguration` in `azure.yaml` this is **code deploy**. The
> `Dockerfile` in each agent directory is not used — it only comes into play if
> you switch to container deploy (`language: docker`, `docker.remoteBuild: true`).

## Verify

```bash
azd ai agent show devops-triage --output json
```

Look for `"status": "active"` and an `agent_endpoints` map. Then check both:

```bash
azd ai agent doctor
```

```
Remote
   (✓) Foundry project endpoint reachable
   (✓) Developer has required role on Foundry project
   (✓) Hosted agents are active
```

## Invoke the deployed agents

```bash
azd ai agent invoke devops-triage "The ledger service posting queue is backing up and writes are failing. This is blocking all payments."
```

Real response:

```
Agent:        devops-triage (remote)
Trace ID:     5b19729dd9150894bb7d5f7ff53255d0

[devops-triage] **Severity:** SEV2 - Ledger write failures are blocking all payments.
**Service:** Ledger Service (tier-1) - owned by Payments Core
**Page:** payments-core-primary via #payments-core-oncall
**Likely cause:** ldg-881 — high-risk migration to a partitioned posting schema, 9 hours ago
**Next actions:**
1. STOP: never restart the ledger writer without first capturing the pending posting queue depth.
2. Verify the partitioned posting table migration completed on every replica.
3. Check for replication lag on postgres-payments; ledger writes block when lag exceeds 30s.
**Runbook:** https://runbooks.contoso.example/ledger-service/write-failures

Server responded in 27.108s (first byte: 8.357s)
```

Note step 1 — the runbook's blocking safety instruction survived into the answer.
That's not luck; it's an [eval dimension](06-evaluate.md).

Keep that **Trace ID** — module 07 uses it.

> Remote invokes call the model and **cost money**. `invoke` has no `--force`
> flag; if it asks for confirmation, confirm rather than inventing flags.

## Versioning and rollback

Every deploy creates a new immutable version; old versions stay callable:

```bash
azd ai agent show devops-triage --output json      # current version
azd ai agent invoke devops-triage --version 1 "..."  # pin an older version
```

This is the safety net for prompt changes: deploy v2, compare against v1 with the
same eval suite, and keep whichever wins.

## The Playground

`azd deploy` prints a portal link per agent:

```
https://ai.azure.com/nextgen/r/<encoded>/build/agents/devops-triage/build?version=1
```

The Playground is the best demo surface — chat with the agent, expand each tool
call, and see the trace inline. Get the link any time from
`azd ai agent show --output json` (`playground_url`).

## Redeploying after a change

```bash
pytest                              # 1. logic still correct
azd ai agent run docs-qa --no-client  # 2. behaviour still correct locally
azd deploy docs-qa                  # 3. publish
azd ai agent invoke docs-qa "..."   # 4. confirm remotely
```

## Common failures

| Symptom | Fix |
| --- | --- |
| `agent_definition_not_found` | Deployed name doesn't match `azure.yaml`. Deploy from the repo root. |
| postdeploy hook fails on `AZURE_TENANT_ID` | `azd env set AZURE_TENANT_ID $(az account show --query tenantId -o tsv)` and re-deploy. The agent version from the first deploy is still valid. |
| `entryPoint` mismatch | `codeConfiguration.entryPoint` names a file that doesn't exist in `project:`. Fix `azure.yaml`. |
| Agent never becomes active | `azd ai agent monitor` for the log stream — usually an import error or a missing entry in `requirements.txt`. |

---

← [04 — Run locally](04-run-locally.md) · Next → [06 — Evaluate quality](06-evaluate.md)
