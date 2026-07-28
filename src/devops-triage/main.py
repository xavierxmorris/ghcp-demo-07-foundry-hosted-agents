"""DevOps incident triage agent -- a Microsoft Foundry *hosted* agent.

Shape of a hosted agent:

1. Build a chat client pointed at the Foundry project's model deployment.
2. Build an ``Agent`` with instructions plus a set of ``@tool`` functions.
3. Wrap it in ``ResponsesHostServer`` and call ``run()``.

Foundry supplies ``FOUNDRY_PROJECT_ENDPOINT`` and the managed identity at
runtime. Locally, ``DefaultAzureCredential`` falls back to your ``az login``
identity and ``.env`` supplies the endpoint, so the same file runs in both
places with no branching.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Annotated

from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import Field

import triage

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("devops-triage")

INSTRUCTIONS = """
You are the Contoso Payments incident triage assistant. You help the on-call
engineer move fast during a live production incident.

Follow this process for every incident report:

1. Call `classify_incident_severity` to get the severity. Never assign a
   severity yourself and never override the tool's answer.
2. Call `lookup_service_owner` to find the owning team, on-call rotation, and
   escalation channel.
3. Call `list_recent_deployments` to see whether a recent deploy is a likely
   culprit. A deploy is suspicious when it landed shortly before the incident
   began and its risk is medium or high.
4. Call `get_service_runbook` to retrieve the authoritative remediation steps.

Then reply with exactly this structure, in markdown:

**Severity:** <SEV level> - <one line justification citing the signals>
**Service:** <display name> (<tier>) - owned by <team>
**Page:** <on-call rotation> via <slack channel>
**Likely cause:** <deployment id and summary, or "no recent deploy correlates">
**Next actions:**
1. <first runbook step>
2. <second runbook step>
3. <third runbook step>
**Runbook:** <url>

Rules you must not break:
- Only use facts returned by the tools. Never invent a service, team, deployment
  id, runbook URL, or metric.
- If `lookup_service_owner` reports the service is unknown, say so plainly and
  list the services you do know about. Do not guess an owner.
- Keep the whole response under 200 words. The reader is mid-incident.
- Never recommend restarting the ledger writer before the runbook's capture step.
"""


@tool(approval_mode="never_require")
def classify_incident_severity(
    customer_impact: Annotated[
        str, Field(description="Plain-language description of what customers are experiencing.")
    ],
    error_rate_pct: Annotated[
        float, Field(description="Observed error rate as a percentage, 0 if unknown.")
    ] = 0.0,
    affected_users: Annotated[
        int, Field(description="Approximate number of affected users, 0 if unknown.")
    ] = 0,
    revenue_impacting: Annotated[
        bool, Field(description="True when the incident blocks payments or revenue.")
    ] = False,
) -> str:
    """Assign a SEV1-SEV4 severity using the Contoso severity matrix."""
    result = triage.classify_severity(
        customer_impact=customer_impact,
        error_rate_pct=error_rate_pct,
        affected_users=affected_users,
        revenue_impacting=revenue_impacting,
    )
    logger.info("classify_incident_severity -> %s", result["severity"])
    return json.dumps(result)


@tool(approval_mode="never_require")
def lookup_service_owner(
    service: Annotated[str, Field(description="Service name, id, or alias, e.g. 'checkout'.")],
) -> str:
    """Look up ownership, on-call rotation, tier, SLA, and dependencies."""
    result = triage.lookup_service(service)
    logger.info("lookup_service_owner(%s) -> found=%s", service, result["found"])
    return json.dumps(result)


@tool(approval_mode="never_require")
def list_recent_deployments(
    service: Annotated[str, Field(description="Service name, id, or alias.")],
    hours: Annotated[int, Field(description="Trailing window in hours to search.")] = 24,
) -> str:
    """List deployments for a service inside a trailing time window."""
    result = triage.recent_deployments(service, hours=hours)
    logger.info("list_recent_deployments(%s, %sh)", service, hours)
    return json.dumps(result)


@tool(approval_mode="never_require")
def get_service_runbook(
    service: Annotated[str, Field(description="Service name, id, or alias.")],
    symptom: Annotated[
        str, Field(description="Symptom in your own words, e.g. 'elevated 5xx and timeouts'.")
    ] = "",
) -> str:
    """Retrieve the runbook entry that best matches a symptom."""
    result = triage.get_runbook(service, symptom=symptom)
    logger.info("get_service_runbook(%s, %r)", service, symptom)
    return json.dumps(result)


def build_agent() -> Agent:
    """Construct the agent. Split out so tests can build it without serving."""
    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    return Agent(
        client=client,
        name="devops-triage",
        instructions=INSTRUCTIONS,
        tools=[
            classify_incident_severity,
            lookup_service_owner,
            list_recent_deployments,
            get_service_runbook,
        ],
        # The hosting layer owns conversation history, so the model API does not
        # need to persist it as well.
        default_options={"store": False},
    )


def main() -> None:
    logger.info("starting devops-triage hosted agent")
    ResponsesHostServer(build_agent()).run()


if __name__ == "__main__":
    main()
