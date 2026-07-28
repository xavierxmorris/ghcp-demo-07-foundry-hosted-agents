# 02 — Anatomy of a hosted agent

**Time:** ~15 minutes
**Goal:** be able to read and edit `azure.yaml` and `main.py` with confidence.

## What "hosted" means

A **hosted agent** is your code running inside Foundry Agent Service. You supply
a repo directory; Foundry supplies the container build, the HTTP surface, managed
identity, versioning, scaling, and tracing.

| You own | Foundry owns |
| --- | --- |
| `main.py`, tools, instructions | Container build and runtime |
| `requirements.txt` | Hosting, scaling, TLS |
| The agent's contract in `azure.yaml` | Identity — no keys in your code |
| Tests and evals | Immutable versioning, rollback |
| | OpenTelemetry tracing to App Insights |

The alternative is a **prompt agent** — instructions plus a model, no code. Use a
hosted agent when you need custom tools, custom retrieval, or custom control flow.
Both agents here need all three.

## `azure.yaml`, field by field

This one file is the entire deployment. Three services: one Foundry project and
two agents.

```yaml
services:
  ai-project:
    host: azure.ai.project
    deployments:
      - name: gpt-5.4-mini          # the Azure deployment resource name
        model:
          format: OpenAI
          name: gpt-5.4-mini
          version: '2026-03-17'
        sku:
          name: GlobalStandard
          capacity: 30              # shared by BOTH agents -- size accordingly
```

`azd provision` reads `services.ai-project.deployments[]` and creates the model
deployment. Never create it with `az cognitiveservices account deployment create`
— that puts it outside the azd lifecycle and `azd down` won't clean it up.

```yaml
  devops-triage:
    host: azure.ai.agent            # <- makes this an agent service
    kind: hosted
    name: devops-triage             # the agent name in Foundry
    description: >-
      Triages production incidents...
    project: src/devops-triage      # directory that gets packaged and shipped
    language: python
    uses:
      - ai-project                  # links agent -> model deployment
    codeConfiguration:
      runtime: python_3_14
      entryPoint: main.py
    protocols:
      - protocol: responses
        version: 2.0.0
    environmentVariables:
      - name: AZURE_AI_MODEL_DEPLOYMENT_NAME
        value: ${AZURE_AI_MODEL_DEPLOYMENT_NAME}   # from the azd env
    container:
      resources:
        cpu: '0.5'
        memory: 1Gi
```

The fields that actually matter:

| Field | Notes |
| --- | --- |
| `uses: [ai-project]` | Without this the agent has no model binding. |
| `codeConfiguration` | Present → **code deploy** (ZIP upload, Foundry builds). Absent → container deploy via ACR. |
| `entryPoint` | Must be a real file in `project:`. Mismatch = deploy failure. |
| `protocols` | `responses` (OpenAI-compatible), `invocations` (A2A), `invocations_ws` (duplex/streaming). Changing this needs a redeploy. |
| `environmentVariables` | `${VAR}` resolves from the azd env. **Not for secrets** — use a connection. |
| `container.resources` | Valid tiers only: `0.25`/`0.5Gi`, `0.5`/`1Gi`, `1`/`2Gi`, `2`/`4Gi`. |
| `description` | Feeds eval generation. Write it properly. |

> **Never** put `FOUNDRY_*` or `AGENT_*` variables in `environmentVariables`.
> The platform injects those at runtime; declaring them causes conflicts.

### camelCase vs snake_case

Local `azure.yaml` uses camelCase (`codeConfiguration`, `entryPoint`). The
*deployed* definition returned by `azd ai agent show` uses snake_case
(`code_configuration`, `entry_point` as an array). Same concept, two spellings —
don't copy one into the other.

## `main.py`, layer by layer

Every hosted agent is the same four moves.

**1 — Chat client bound to the project's model deployment**

```python
client = FoundryChatClient(
    project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
    credential=DefaultAzureCredential(),
)
```

`FOUNDRY_PROJECT_ENDPOINT` is injected by the platform when deployed, and read
from `.env` when local. `DefaultAzureCredential` resolves to the agent's managed
identity in Foundry and to your `az login` identity locally. **The same code runs
in both places** — no branching, no keys.

**2 — Tools**

```python
@tool(approval_mode="never_require")
def lookup_service_owner(
    service: Annotated[str, Field(description="Service name, id, or alias.")],
) -> str:
    """Look up ownership, on-call rotation, tier, SLA, and dependencies."""
    return json.dumps(triage.lookup_service(service))
```

- The **docstring** becomes the tool description the model sees.
- Each `Field(description=...)` is the model's only guide to that parameter.
  Vague descriptions produce wrong tool calls — this is prompt engineering.
- `approval_mode="never_require"` means no human-in-the-loop gate. Use it for
  read-only tools; require approval for anything that writes.

**3 — Agent**

```python
agent = Agent(
    client=client,
    name="devops-triage",
    instructions=INSTRUCTIONS,
    tools=[classify_incident_severity, lookup_service_owner, ...],
    default_options={"store": False},
)
```

`store: False` because the hosting layer already manages conversation history;
storing again duplicates it.

**4 — Serve**

```python
ResponsesHostServer(agent).run()
```

Binds `0.0.0.0:8088` and speaks the Responses protocol. Foundry expects exactly
this.

## The layering rule

```
main.py        @tool wrappers, Agent, server        (framework-aware, thin)
triage.py      severity matrix, catalogue, runbooks (stdlib only, pure)
retrieval.py   BM25 index and search                (stdlib only, pure)
```

Domain modules import **nothing** from `agent_framework`. That's what makes
`pytest` run 55 assertions in 0.12 seconds with no Azure and no model.

Rule of thumb: **if you can't unit-test it, it's in the wrong file.**

## Two agents, two shapes

| | `devops-triage` | `docs-qa` |
| --- | --- | --- |
| Core skill | Multi-step tool orchestration | Grounded retrieval |
| Tools | 4 | 2 |
| Prompt enforces | Fixed markdown output contract | Citations + explicit refusal |
| Fails by | Guessing a service or runbook | Answering without a source |
| Guarded by | `found: False` returns | Empty search results + refusal string |

Both encode the same principle: **the tool layer refuses to invent, and the
prompt refuses to paper over it.**

---

← [01 — Scaffold with Copilot](01-scaffold-with-copilot.md) · Next → [03 — Provision Azure](03-provision-azure.md)
