# Architecture

Why this repo is shaped the way it is.

## The layering rule

```
┌──────────────────────────────────────────────────────────┐
│  main.py                                                  │
│  ├─ @tool wrappers        (framework-aware, no logic)     │
│  ├─ INSTRUCTIONS          (the agent's contract)          │
│  ├─ Agent(...)            (client + tools + instructions) │
│  └─ ResponsesHostServer   (HTTP surface Foundry expects)  │
└───────────────────────────┬──────────────────────────────┘
                            │ calls
┌───────────────────────────▼──────────────────────────────┐
│  triage.py / retrieval.py                                 │
│  Pure Python. Standard library only.                      │
│  No agent_framework, no azure.*, no network.              │
│  Deterministic in, deterministic out.                     │
└───────────────────────────┬──────────────────────────────┘
                            │ reads
┌───────────────────────────▼──────────────────────────────┐
│  data/*.json  ·  knowledge/*.md                           │
│  Fixtures standing in for a CMDB / doc store.             │
└──────────────────────────────────────────────────────────┘
```

Four things fall out of this, and they're the reason the rule exists:

1. **Tests run in 0.12 seconds.** 55 assertions, no Azure, no model, no network.
2. **CI needs no cloud credentials.** `ci.yml` is just `ruff` and `pytest`.
3. **Bugs are reproducible.** "The agent gave the wrong runbook" becomes a
   failing unit test in one step.
4. **The Copilot coding agent can actually verify itself.** A fast, honest test
   signal is what separates a useful agent PR from a plausible-looking one.

The inverse rule: **if you can't unit test it, it's in the wrong file.**

## Request lifecycle

```
azd ai agent invoke devops-triage "checkout is throwing 5xx"
        │
        ▼
  Foundry Agent Service          ← auth via managed identity, routing, versioning
        │
        ▼
  Your container  ──►  ResponsesHostServer  ──►  Agent
                                                  │
                          ┌───────────────────────┤
                          ▼                       ▼
                   FoundryChatClient          @tool functions
                   (gpt-5.4-mini)                  │
                          │                        ▼
                          │                 triage.py / retrieval.py
                          │                        │
                          ◄────── tool results ────┘
                          │
                          ▼
                    final response  ──►  OpenTelemetry ──► App Insights
```

The model decides *which* tools to call and in what order. The instructions
prescribe the process; the tool descriptions tell it what each one is for. Both
are prompt engineering, and both are what the eval suite actually measures.

## Two agents, two failure modes

Choosing two dissimilar agents was deliberate — they break differently, so they
need different defences.

| | `devops-triage` | `docs-qa` |
| --- | --- | --- |
| Pattern | Multi-step tool orchestration | Retrieval-augmented generation |
| Tools | 4 | 2 |
| State | Stateless per request | Stateless; index built once per process |
| Fails by | Inventing a service, owner, deploy, or runbook | Answering from world knowledge instead of the corpus |
| Tool-layer defence | `found: False` + `known_services` | Empty result list, no padding |
| Prompt-layer defence | "Only use facts returned by the tools" | Exact refusal string + mandatory `Sources:` |
| Eval dimension | `no_fabrication` (weight 10) | `refuses_when_ungrounded` (weight 10) |

The pattern generalises: **make the tool layer physically unable to fabricate,
then make the prompt refuse to paper over the gap, then measure both.**

## Retrieval design (`docs-qa`)

Hand-rolled BM25, standard library only.

```
knowledge/*.md
   │  split on ## / ### headings
   ▼
chunks (doc_id, section, text)
   │  tokenize → stopword removal → crude stemming
   ▼
term frequencies + document frequencies
   │  BM25 (k1=1.5, b=0.75)
   ▼
ranked hits, filtered by MIN_TERM_COVERAGE
```

Three choices worth calling out:

**Chunking on headings** gives every chunk a natural citation label
(`refunds-policy#Insufficient balance`) and keeps it semantically coherent.

**Crude stemming** — strip `ing`/`ed`/`es`/`s` above a length floor — so
"refunded", "refunds", and "refund" match. Not a Porter stemmer; the corpus is
small and a handful of rules removes most mismatches without a dependency.

**`MIN_TERM_COVERAGE = 2`** is the important one. Without it, *"who won the 1998
world cup"* scores a hit on the disputes document purely on the word "won"
(`dispute.won`), because a rare term has high IDF. The agent then cites a
document that cannot answer the question. Requiring overlap on at least two
distinct query terms is what makes an out-of-scope question return **nothing** —
which is what lets the agent decline honestly.

That single constant is the difference between a grounded agent and a
confident-sounding one. It's covered by
`test_off_topic_query_returns_nothing`.

**Swapping in Azure AI Search** means rewriting `retrieval.py` behind the same
two functions. `main.py`, the instructions, the tests' intent, and the evals all
stay put.

## Deployment model

```
azure.yaml
   ├─ services.ai-project      ──► azd provision ──► Foundry project + model deployment
   ├─ services.devops-triage   ──┐
   └─ services.docs-qa         ──┴► azd deploy   ──► ZIP → Foundry build → immutable version
```

**Code deploy** (`codeConfiguration` present): the `project:` directory is zipped
honouring `.azdignore`, uploaded, and built by Foundry from `requirements.txt`.
No Docker locally, no registry to manage.

**Container deploy** (the alternative): `language: docker`,
`docker.remoteBuild: true`, and the `Dockerfile` each agent still carries. Choose
it when you need system packages or a base image the runtimes don't offer.

Versions are immutable. Rollback is pinning `--version`, not redeploying.

## Configuration flow

```
azure.yaml  ──►  ${AZURE_AI_MODEL_DEPLOYMENT_NAME}
                          │
                    azd env (.azure/<env>/.env)
                          │
        ┌─────────────────┴─────────────────┐
        ▼                                   ▼
  local: injected into the process    deployed: agent env var
  BEFORE .env is read                 + FOUNDRY_* injected by platform
```

The ordering is the trap: `azd ai agent run` sets process variables before
Python's `load_dotenv()` runs, and `load_dotenv` doesn't override existing
values. A stale azd env value therefore beats a correct `.env`, and surfaces as a
model `404`. Keep both in sync.

Secrets never live in `environmentVariables` — use a Foundry connection.

## Identity

`DefaultAzureCredential` everywhere:

| Context | Resolves to |
| --- | --- |
| Local | Your `az login` / VS Code identity |
| Foundry | The agent's managed identity |
| CI | The federated OIDC service principal |

No keys, no connection strings, no rotation, one code path.

Data-plane access to a Foundry project needs `Foundry User` or
`Azure AI Developer` — subscription `Owner` alone is not sufficient. That
distinction accounts for most first-run failures; see
[troubleshooting](troubleshooting.md#403-from-the-foundry-endpoint).

## What's deliberately missing

| Not here | Why | Where it'd go |
| --- | --- | --- |
| Azure AI Search | Cost + non-determinism in a demo | `retrieval.py` |
| Private networking | Adds ~20 min of setup | `azure.yaml` network mode |
| Content-safety guardrails | Separate concern, own demo | Foundry guardrails API |
| Multi-turn memory | Both agents are single-turn by design | Foundry memory tool |
| A real CMDB / PagerDuty | Fixtures keep evals reproducible | `data/*.json` → API calls |

Each is a one-module change precisely because of the layering rule.
