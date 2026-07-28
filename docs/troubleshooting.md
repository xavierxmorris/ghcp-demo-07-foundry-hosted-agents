# Troubleshooting

Every error in this document was hit while building this repo. The fixes are the
ones that actually worked.

---

## 403 from the Foundry endpoint

```
(x) Foundry project endpoint reachable
    Foundry returned HTTP 403 (wrong tenant or insufficient RBAC).
```

**Two causes, usually together.**

### Cause 1 — `az` and `azd` are different accounts

```bash
az ad signed-in-user show --query userPrincipalName -o tsv
azd auth login --check-status
```

If those differ, `azd provision` granted the Foundry role to one identity and
your `azd ai agent` commands are running as the other.

```bash
azd auth login --use-device-code    # sign in as the same account az uses
```

### Cause 2 — Owner is not enough

Subscription `Owner` is a **control-plane** role. Calling a Foundry project
endpoint is a **data-plane** operation and needs `Foundry User` or
`Azure AI Developer` on the AI Services account.

```bash
SCOPE=$(az cognitiveservices account show -n <account> -g <rg> --query id -o tsv)
OID=$(az ad user show --id <your-upn> --query id -o tsv)

az role assignment create \
  --assignee-object-id "$OID" \
  --assignee-principal-type User \
  --role "Foundry User" \
  --scope "$SCOPE"
```

Wait 30–60 seconds for propagation, then `azd ai agent doctor`.

Confirm what's assigned:

```bash
az role assignment list --scope "$SCOPE" \
  --query "[].{role:roleDefinitionName, principal:principalName}" -o table
```

---

## `InvalidTemplate` during `azd provision`

```
Deployment template validation failed: 'The following parameters were supplied,
but do not correspond to any parameters defined in the template:
'foundryProjectName, tags'.
```

**Cause.** A leftover `infra/` folder from an older starter template. With
`infra: provider: microsoft.foundry` in `azure.yaml`, the Foundry provider
supplies its own ARM template — but an on-disk `infra/main.bicep` gets compiled
and used instead, and the parameter names have since diverged.

**Fix.** Delete `infra/`. This repo intentionally ships without one.

```bash
rm -rf infra/
azd provision --no-state --no-prompt
```

---

## `multiple azure.ai.agent services found`

```
ERROR: could not resolve agent service in azd project:
multiple azure.ai.agent services found in azure.yaml: devops-triage, docs-qa
```

**Fix.** Pass the service name positionally:

```bash
azd ai agent run devops-triage --no-client
azd ai agent invoke devops-triage --local "..."
azd ai agent show docs-qa
```

`azd deploy` is the exception — it handles all services at once, and takes an
optional service name to narrow it.

---

## `azd ai agent eval run` evaluates the wrong agent

The run summary says `Agent: devops-triage` even though you passed
`--config src/docs-qa/eval.yaml`, and nearly every case fails.

**Cause.** `eval run` resolves the agent from the **first** `azure.ai.agent`
service in `azure.yaml`. Unlike `eval generate`, it has no `--agent` flag, and
`-C` does not change the resolution.

**Fix.** Check the `Agent:` line in the summary before trusting a score. Until
the flag exists: reorder `azure.yaml`, run the eval from the portal, or keep one
agent per azd project.

---

## `The evaluator <name> was not found` (404)

```
ERROR: failed to create eval: ... "The evaluator triage-core was not found"
```

**Cause.** Custom rubrics must be **registered in the Foundry project**. A local
`rubric_dimensions.json` referenced by `eval.yaml` is not enough, and
`azd ai agent eval update` does not create a new evaluator from scratch.

**Fix.** Register via `eval generate`, passing your own dataset so your authored
cases are preserved:

```bash
azd ai agent eval generate \
  --agent devops-triage \
  --dataset ./src/devops-triage/datasets/triage-core/triage-core.jsonl \
  --gen-instruction "<what the agent does and what it must never do>" \
  --reset-defaults --no-prompt
```

---

## `--runtime must be one of: python_3_13, python_3_14, dotnet_10`

You passed a bare `python`. Use the full runtime token.

---

## `--entry-point is required` / entry point mismatch

`codeConfiguration.entryPoint` must name a real file inside the service's
`project:` directory. A wrong value scaffolds fine and then fails at local run
and deploy. Fix it directly in `azure.yaml`; no re-init needed.

---

## `could not connect to localhost:8088`

**Cause 1 — invoked too early.** `Starting agent on http://localhost:8088` prints
*before* the socket is bound. Wait for:

```
[INFO] Running on http://0.0.0.0:8088 (CTRL + C to quit)
```

**Cause 2 — the server died with its parent shell.** Don't background it with
`&`, `nohup`, or a popped window. Run it in a terminal you keep open, or a
managed background session you can poll and stop.

**Cause 3 — port in use.** A previous run is still holding 8088. Stop it, or use
`--port 8089` on both `run` and `invoke --local`.

---

## Model `404` on local run but the deployed agent works

**Cause.** `azd ai agent run` injects azd env values into the process *before*
Python loads `.env`, and `load_dotenv()` does not override existing process
variables. A stale `AZURE_AI_MODEL_DEPLOYMENT_NAME` in the azd env therefore
wins.

**Fix.** Keep both in sync:

```bash
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME gpt-5.4-mini
azd env get-values
```

---

## `ConnectionError: 169.254.169.254 ... unreachable network`

Harmless. That's the Azure instance-metadata probe failing because you're not
running on an Azure VM. It appears as an OpenTelemetry span with an error status
during local runs. Ignore it.

---

## `--no-inspector has been deprecated`

Use `--no-client`.

---

## Deploy postdeploy hook fails on `AZURE_TENANT_ID`

```bash
azd env set AZURE_TENANT_ID $(az account show --query tenantId -o tsv)
azd deploy --no-prompt
```

The agent version from the first deploy is still valid — the hook only registers
env vars.

---

## Agent deploys but never becomes active

```bash
azd ai agent monitor <service>
```

Almost always an import error or a package missing from that agent's
`requirements.txt`. The domain modules use only the standard library precisely so
this can't happen for tool logic.

---

## `azd down` leaves the name reserved

Use `azd down --purge`. Without it the AI Services account is soft-deleted and
the name stays taken for the retention period.

---

## Still stuck

```bash
azd ai agent doctor
```

It names the exact failing check and a suggested fix. Run it before anything
else — it would have short-circuited most of the entries on this page.
