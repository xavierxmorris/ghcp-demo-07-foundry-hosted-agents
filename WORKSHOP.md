# Workshop: distinguish correct tools from a reliable agent

**Audience:** developers and AI platform engineers. **Time:** 60 minutes offline,
plus a separately budgeted cloud session.
**Outcome:** a tool contract, an agent-evaluation matrix, and an evidence-backed
release decision. A good sample response is not the release gate.

## 1. Choose the evidence level - 8 minutes

| Level | Needs | Establishes | Does not establish |
| --- | --- | --- | --- |
| Domain tests | Python and development requirements | Deterministic tool behavior | Model compliance or Azure health |
| Local agent plus model | Provisioned project, model access, agent dependencies | Tool selection and response behavior locally | Hosted identity/network/runtime |
| Deployed agent | Approved Azure resources and budget | A named deployed version responds | Quality across the evaluation set |
| Evaluation plus traces | Correct agent, dataset, evaluator, model budget | Measured behavior for specified cases | Exhaustive correctness |

Local domain tests are offline. A locally running **agent** still calls a cloud
model in this project; do not label it offline inference.

The original runtime declares **Python 3.14**, Responses **2.0.0**, and
`gpt-5.4-mini` model version **2026-03-17** in [azure.yaml](azure.yaml).
SDK dependencies are ranges, not a lock. Record resolved versions.

## 2. Follow one tool end to end - 12 minutes

| Layer | Triage agent | Documentation agent |
| --- | --- | --- |
| Domain logic | [triage.py](src/devops-triage/triage.py) | [retrieval.py](src/docs-qa/retrieval.py) |
| Model-facing wrappers | [main.py](src/devops-triage/main.py) | [main.py](src/docs-qa/main.py) |
| Ground truth | [data/](src/devops-triage/data/) | [knowledge/](src/docs-qa/knowledge/) |
| Local tests | [test_devops_triage_tools.py](tests/test_devops_triage_tools.py) | [test_docs_qa_retrieval.py](tests/test_docs_qa_retrieval.py) |

Follow the README's isolated-environment setup, then run:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

On macOS/Linux, use `.venv/bin/python -m pytest`. These commands use the
environment created by the README without relying on shell activation.

The domain suite contains 55 tests. It does not import the hosting framework
to run a real model. Trace an alias through `normalize_service`, an ownership
lookup, a JSON tool result, and the instructions that consume that result.

```text
Map the incident-triage path from the user request to tool wrappers, plain
Python functions, and fixtures. Identify which assertions can run offline
and which require an agent trace. Do not deploy or invoke a model.
```

**Checkpoint:** explain why `found: false` with known options is preferable
to a fabricated service owner. Also note that deployment ages are synthetic
relative fixtures: fresh-looking timestamps are not live operational evidence.

## 3. Exercise a negative result - 12 minutes

| Case | Domain expectation | Agent expectation to evaluate later |
| --- | --- | --- |
| Known service alias | Resolves to the catalog ID | Uses returned owner/runbook |
| `teleport-gateway` | Unknown, with known-service options | No invented ownership or rollback |
| Low-signal incident | Conservative matrix result | Does not manufacture telemetry |
| Relevant refund question | Retrieval returns supporting chunks | Answer is supported and cites them |
| Out-of-corpus question | No useful evidence | Exact documented refusal |
| Plausible but unsupported payments detail | Not established by the corpus | Does not fill the gap from general knowledge |

Retrieval is BM25 over bundled Markdown, not an Azure AI Search deployment.
Positive token overlap is not proof that a chunk answers the question.
Read the returned passage and check every factual claim against it.

```text
Propose one new negative regression case for the existing retrieval tests.
Use only the fictional corpus. Explain what false positive it catches.
Keep domain logic independent of the hosting framework and network.
```

If you implement the exercise, run the corresponding existing test file.
Do not weaken refusal behavior merely to improve answer coverage.

## 4. Prepare evaluation without spending tokens - 12 minutes

Read [docs/06-evaluate.md](docs/06-evaluate.md#preflight-before-using-the-saved-configs).
The saved eval configs contain author-machine paths, missing rubric references,
and a docs-qa config that names the wrong agent. Treat them as historical
artifacts, not portable instructions to execute blindly.

Record these fields in a fresh environment-specific evaluation plan:

| Field | Required evidence |
| --- | --- |
| Agent name/version | Actual deployed target, not the first service in a file |
| Dataset | Resolved local path, version/hash, and known source for each expected answer |
| Evaluator | Exists in this project; correct name/version and rubric |
| Judge/model | Selected model and configuration |
| Run identity | Run ID, time, and target in the returned summary |
| Failure categories | Tool logic, retrieval, instruction following, evaluator error, or environment |

On 2026-09-07, local azd **1.28.0** with installed `azure.ai.agents`
**1.0.0-beta.7** still showed no `--agent` on `eval run`. The tool also advertised
azd **1.33.0** as available; that does not mean this lab was executed with it.
Record `installedVersion`, not the catalog's `version`.

The historical **6/12** triage score is a useful failure baseline, not a release
success. A docs-qa score against devops-triage is invalid evidence, not a
quality regression to optimize away.

## 5. Optional cloud session - separately scheduled

Follow [prerequisites](docs/00-prerequisites.md) only after approving a dedicated
environment, region/model capacity, identities, and budget. Use the same intended
account for `az` and `azd`; control-plane ownership does not automatically give
the agent all required data-plane access.

Use [local-run guidance](docs/04-run-locally.md) and explicitly name the service.
Wait for readiness before invoking it. Capture a grounded response, an unknown
service, and a refusal in fresh sessions so prior conversation cannot supply
the missing answer.

Inspect the tool trace: inputs, result, agent response, citations, and target
version. Do not execute fictional rollback strings or turn lookup tools into
production incident actions during this workshop.

Change one thing at a time, rerun the same cases, and retain failures.
Evaluate on cases not used to tune the prompt as well as the training examples.

## 6. Cost, cleanup, and production boundaries - 8 minutes

Budget for hosted CPU/memory across active sessions, model calls, evaluator
calls, telemetry, and supporting resources. A session can remain billable
through its idle timeout; "the last request finished" is not a cost boundary.

Before `azd down --purge`, confirm the selected environment, subscription,
resource group, and ownership of every resource being removed. Never use a
shared environment as a disposable workshop environment.

| Limitation | Production work still needed |
| --- | --- |
| Fixture CMDB/deployments | Authorized, reliable integrations and failure handling |
| Bundled corpus | Content ownership, freshness, access control, and retrieval evaluation |
| Prompt-level constraints | Tool permissions and deterministic enforcement where possible |
| Small authored dataset | Broader coverage, held-out cases, and release thresholds |
| Unlocked runtime dependencies | Reproducible dependency and deployment strategy |

## Troubleshooting and evidence

A 403 calls for identity, tenant, role, and network diagnosis, not broad new
permissions. No citations calls for retrieval/trace inspection, not a stronger
claim in the answer. A suspicious score calls for checking the target and
evaluator before prompt tuning.

Keep local test output separately from cloud run IDs and traces. No cloud run
means no cloud-quality or deployment claim. Do not commit endpoints, credentials,
or raw sensitive telemetry.

## Current sources

Checked **2026-09-07**:
[hosted agents and consumption billing](https://learn.microsoft.com/azure/foundry/agents/concepts/hosted-agents),
[deploying from source](https://learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent-code),
[azd releases](https://github.com/Azure/azure-dev/releases).
The original module outputs remain dated examples; confirm current CLI help
before running version-sensitive operations.
