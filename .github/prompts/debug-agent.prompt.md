---
mode: agent
description: Diagnose a failing hosted-agent deployment or invocation, methodically.
---

# Debug a Foundry agent

Work through this in order. Do not skip to a fix — report what each step showed.

## 1. Always start here

```bash
azd ai agent doctor
```

It checks local config, auth, endpoint reachability, RBAC, and deployment status,
and names the exact failing check. Most problems stop here.

## 2. Match the symptom

| Symptom | Likely cause | Action |
| --- | --- | --- |
| `403` from the endpoint | `az` and `azd` signed in as different accounts, or missing data-plane role | Compare `az ad signed-in-user show` with `azd auth login --check-status`. Owner is **not** enough — needs `Foundry User` on the AI Services account. |
| `multiple azure.ai.agent services found` | Two agent services in `azure.yaml` | Pass the service name positionally |
| `could not connect to localhost:8088` | Invoked before the socket bound, or the server died with its shell | Wait for `Running on http://0.0.0.0:8088`; never background with `&` |
| Model `404` locally, works deployed | Stale `AZURE_AI_MODEL_DEPLOYMENT_NAME` in the azd env overriding `.env` | `azd env get-values`, then `azd env set` the correct value |
| Agent deploys but never becomes active | Import error or missing package | `azd ai agent monitor <service>` |
| `InvalidTemplate` on provision | Stale `infra/` folder conflicting with the `microsoft.foundry` provider | Delete `infra/` |
| `evaluator ... was not found` | Custom rubric not registered in the project | Register via `azd ai agent eval generate --dataset <ours>` |
| Eval scores the wrong agent | `eval run` binds to the first agent service in `azure.yaml` | Check the `Agent:` line in the summary |

Full detail: `docs/troubleshooting.md`.

## 3. If it's a behaviour problem, not an infrastructure problem

Reproduce and keep the Trace ID:

```bash
azd ai agent invoke <agent> "<the failing prompt>"
```

Then determine **which layer** failed:

1. **Did the tool get called?** Check the log stream
   (`azd ai agent monitor <agent>`) or the local server output. No call → the
   model didn't understand the tool applied → fix the docstring and
   `Field(description=...)`.
2. **Were the arguments right?** Wrong arguments → the parameter description is
   ambiguous.
3. **Was the tool's return value correct?** Reproduce it directly in `pytest`
   against `triage.py` / `retrieval.py`. If it's wrong there, it's a domain bug —
   write a failing test first, then fix.
4. **Tool right, answer wrong?** The instructions are weak. Tighten
   `INSTRUCTIONS` and add an eval case.

## 4. Before reporting done

- `pytest` passes
- The specific failing scenario now behaves correctly via `invoke --local`
- A regression test **or** eval case exists for it
- You state which layer was at fault and why

## Never

- Bypass the toolchain with `python main.py` or a raw `curl` to `/responses` —
  those skip the wiring the deployed agent actually uses
- Invent CLI flags. `azd ai agent invoke` has no `--force`
- Change RBAC, networking, or model deployments without telling me first
