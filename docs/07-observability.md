# 07 — Observability and tracing

**Time:** ~15 minutes
**Goal:** answer "why did the agent say that?" from telemetry instead of guesswork.

## You already have tracing

`azd provision` created Log Analytics and Application Insights, and the Foundry
runtime emits OpenTelemetry spans automatically. There is no instrumentation code
in either agent — the `logger.info(...)` lines in `main.py` are the only thing
added, and those exist so tool calls are legible in the log stream.

You saw the hook in module 05:

```
Trace ID:     5b19729dd9150894bb7d5f7ff53255d0
```

Every remote invoke returns one. It is the join key for everything below.

## The live log stream

```bash
azd ai agent monitor devops-triage
```

A server-sent-events stream of the agent's logs, per session. This is the first
place to look when an agent won't start or a tool throws.

Locally you get the same detail on stdout:

```
INFO:devops-triage:starting devops-triage hosted agent
INFO:devops-triage:classify_incident_severity -> SEV2
INFO:devops-triage:lookup_service_owner(checkout) -> found=True
INFO:devops-triage:list_recent_deployments(checkout, 24h)
INFO:devops-triage:get_service_runbook(checkout, 'elevated 5xx')
```

That sequence *is* the agent's reasoning: four tools, in the order the
instructions prescribe. If a tool is missing from the sequence, the model skipped
it — an instructions problem, not a code problem.

## Querying traces with KQL

Get the connection details:

```bash
azd env get-values | grep APPLICATIONINSIGHTS
```

Then in the Azure portal → Application Insights → **Logs**.

**Every agent turn in the last hour, slowest first**

```kusto
dependencies
| where timestamp > ago(1h)
| where cloud_RoleName has "agent"
| project timestamp, name, duration, success, operation_Id
| order by duration desc
| take 50
```

**Follow one invocation end to end** — paste the Trace ID from `invoke`:

```kusto
union traces, dependencies, customEvents, exceptions
| where operation_Id == "5b19729dd9150894bb7d5f7ff53255d0"
| project timestamp, itemType, name, message, duration
| order by timestamp asc
```

This shows the model call, each tool call with its duration, and the final
response — the whole causal chain.

**Which tools are actually being used?**

```kusto
dependencies
| where timestamp > ago(24h)
| where name has_any ("classify_incident_severity", "lookup_service_owner",
                      "list_recent_deployments", "get_service_runbook",
                      "search_documentation", "fetch_document")
| summarize calls = count(), p50 = percentile(duration, 50),
            p95 = percentile(duration, 95), failures = countif(success == false)
        by name
| order by calls desc
```

A tool with near-zero calls is usually a tool with a bad description — the model
never understood when to reach for it. Fix the `Field(description=...)`, not the
code.

**Token usage and cost drivers**

```kusto
customEvents
| where timestamp > ago(24h)
| where name has "completion" or name has "chat"
| extend prompt = toint(customMeasurements["promptTokens"]),
         completion = toint(customMeasurements["completionTokens"])
| summarize turns = count(), prompt_tokens = sum(prompt),
            completion_tokens = sum(completion)
        by bin(timestamp, 1h)
| order by timestamp desc
```

**Error rate over time**

```kusto
requests
| where timestamp > ago(24h)
| summarize total = count(), failed = countif(success == false) by bin(timestamp, 15m)
| extend error_rate = todouble(failed) / todouble(total) * 100
| render timechart
```

## Debugging a bad answer: the workflow

1. **Reproduce.** `azd ai agent invoke <agent> "<the question>"` and keep the Trace ID.
2. **Read the tool sequence.** Union query above. Ask: did it call the tools at all?
3. **Classify the failure:**

| Observation | Root cause | Fix |
| --- | --- | --- |
| Tool never called | Model didn't know it applied | Improve the docstring and `Field` descriptions |
| Tool called with wrong arguments | Parameter description is ambiguous | Rewrite the description; add an example |
| Tool returned correct data, answer still wrong | Instructions are weak | Tighten `INSTRUCTIONS`, add an eval case |
| Tool returned wrong data | Domain-logic bug | Write a failing unit test, fix `triage.py` / `retrieval.py` |

That last row is why the [layering rule](02-anatomy-of-a-hosted-agent.md#the-layering-rule)
matters — a data bug is reproducible in `pytest` in milliseconds.

4. **Add an eval case** for the failure before you fix it, so it can't come back.

## Continuous evaluation

Batch evals (module 06) score a fixed dataset. **Continuous evaluation** samples
real production traffic and scores it on a schedule, which catches drift that a
static dataset never will:

```bash
azd ai agent eval list      # eval runs, including scheduled ones
```

Configure sampling rate and evaluators in the Foundry portal under your project's
evaluation settings. Start at a low sampling rate — every scored response costs
judge-model tokens.

## Costs to watch

| Source | Control |
| --- | --- |
| Log Analytics ingestion | Set a daily cap on the workspace |
| Judge-model tokens (continuous eval) | Lower the sampling rate |
| Trace volume | Raise `LOG_LEVEL` from `INFO` to `WARNING` in `azure.yaml` env vars |

---

← [06 — Evaluate](06-evaluate.md) · Next → [08 — CI/CD](08-cicd.md)
