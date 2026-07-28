"""Deterministic incident-triage domain logic for the devops-triage agent.

Everything here is pure Python with no network calls, which is deliberate:

* The demo runs identically on every machine, with no extra Azure resources.
* Evaluations are reproducible -- the same alert always yields the same severity.
* Unit tests can assert on the tool layer without invoking a model.

In a real deployment you would swap the JSON fixtures for calls to your CMDB,
PagerDuty, and deployment pipeline, keeping the exact same function signatures.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from functools import cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

# Severity ladder, most severe first. Each rule is evaluated in order and the
# first match wins, so SEV1 conditions take precedence over SEV2 conditions.
SEVERITY_RULES = (
    ("SEV1", "Total outage or data loss affecting most customers"),
    ("SEV2", "Major functionality broken or severe degradation for many customers"),
    ("SEV3", "Partial degradation with a viable workaround"),
    ("SEV4", "Minor or cosmetic issue with no customer impact"),
)

OUTAGE_KEYWORDS = (
    "outage",
    "down",
    "unavailable",
    "data loss",
    "corruption",
    "cannot log in",
    "complete failure",
    "total failure",
)

DEGRADED_KEYWORDS = (
    "timeout",
    "timing out",
    "slow",
    "latency",
    "degraded",
    "elevated errors",
    "5xx",
    "failing",
    "queue backlog",
)


@cache
def _load(name: str) -> dict:
    """Load and cache a JSON fixture from the data directory."""
    with (DATA_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def _services() -> dict:
    return _load("services.json")


def _deployments() -> dict:
    return _load("deployments.json")


def _runbooks() -> dict:
    return _load("runbooks.json")


def normalize_service(service: str) -> str | None:
    """Resolve a free-text service name to a canonical service id.

    Accepts the canonical id, the display name, or any registered alias, all
    case-insensitively. Returns ``None`` when nothing matches so the caller can
    surface a helpful "unknown service" message instead of inventing data.
    """
    if not service:
        return None

    needle = service.strip().lower().replace("_", "-").replace(" ", "-")
    for service_id, record in _services().items():
        candidates = {service_id.lower(), record["display_name"].lower().replace(" ", "-")}
        candidates.update(alias.lower().replace(" ", "-") for alias in record.get("aliases", []))
        if needle in candidates:
            return service_id
    return None


def classify_severity(
    customer_impact: str,
    error_rate_pct: float = 0.0,
    affected_users: int = 0,
    revenue_impacting: bool = False,
) -> dict:
    """Apply the severity matrix to a described incident.

    The rules mirror a typical enterprise severity matrix: signal strength
    (error rate, blast radius) is combined with qualitative impact language so a
    "checkout is completely down" report is never downgraded just because the
    numeric telemetry has not caught up yet.
    """
    text = (customer_impact or "").lower()
    has_outage_language = any(word in text for word in OUTAGE_KEYWORDS)
    has_degraded_language = any(word in text for word in DEGRADED_KEYWORDS)

    signals: list[str] = []

    if has_outage_language:
        signals.append("impact description indicates a hard outage or data loss")
    if has_degraded_language:
        signals.append("impact description indicates degradation")
    if error_rate_pct:
        signals.append(f"error rate {error_rate_pct:.1f}%")
    if affected_users:
        signals.append(f"{affected_users:,} affected users")
    if revenue_impacting:
        signals.append("revenue-impacting")

    if (has_outage_language and (revenue_impacting or affected_users >= 1_000)) or error_rate_pct >= 50:
        severity = "SEV1"
    elif has_outage_language or error_rate_pct >= 10 or affected_users >= 1_000 or revenue_impacting:
        severity = "SEV2"
    elif has_degraded_language or error_rate_pct >= 1 or affected_users >= 50:
        severity = "SEV3"
    else:
        severity = "SEV4"

    definition = dict(SEVERITY_RULES)[severity]
    response_target = {
        "SEV1": "Page on-call immediately, 15 minute response, incident commander required",
        "SEV2": "Page on-call, 30 minute response, status page update required",
        "SEV3": "Notify owning team in business hours, 4 hour response",
        "SEV4": "File a backlog ticket, no paging",
    }[severity]

    return {
        "severity": severity,
        "definition": definition,
        "response_target": response_target,
        "signals": signals or ["no strong impact signals supplied"],
    }


def lookup_service(service: str) -> dict:
    """Return ownership and escalation metadata for a service."""
    service_id = normalize_service(service)
    if service_id is None:
        return {
            "found": False,
            "requested": service,
            "known_services": sorted(_services().keys()),
        }

    record = _services()[service_id]
    return {"found": True, "service_id": service_id, **record}


def recent_deployments(service: str, hours: int = 24) -> dict:
    """Return deployments for a service within the trailing window.

    Deployment timestamps in the fixture are stored as *relative* offsets in
    hours so the demo always looks fresh, no matter when it is run.
    """
    service_id = normalize_service(service)
    if service_id is None:
        return {
            "found": False,
            "requested": service,
            "known_services": sorted(_services().keys()),
        }

    now = datetime.now(UTC)
    window: list[dict] = []
    for entry in _deployments().get(service_id, []):
        age_hours = entry["hours_ago"]
        if age_hours <= hours:
            window.append(
                {
                    "deployment_id": entry["deployment_id"],
                    "deployed_at": (now - timedelta(hours=age_hours)).isoformat(timespec="seconds"),
                    "hours_ago": age_hours,
                    "author": entry["author"],
                    "summary": entry["summary"],
                    "risk": entry["risk"],
                    "rollback_command": f"contoso-deploy rollback {service_id} --to {entry['previous_id']}",
                }
            )

    window.sort(key=lambda item: item["hours_ago"])
    return {
        "found": True,
        "service_id": service_id,
        "window_hours": hours,
        "deployment_count": len(window),
        "deployments": window,
    }


def get_runbook(service: str, symptom: str = "") -> dict:
    """Return the runbook entry that best matches a symptom.

    Matching is intentionally simple keyword overlap: the agent supplies the
    symptom in its own words, and we score each runbook entry by how many of its
    registered trigger keywords appear.
    """
    service_id = normalize_service(service)
    if service_id is None:
        return {
            "found": False,
            "requested": service,
            "known_services": sorted(_services().keys()),
        }

    entries = _runbooks().get(service_id, [])
    if not entries:
        return {"found": False, "service_id": service_id, "reason": "no runbook registered"}

    text = (symptom or "").lower()
    scored = []
    for entry in entries:
        score = sum(1 for keyword in entry["triggers"] if keyword.lower() in text)
        scored.append((score, entry))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    best_score, best = scored[0]

    return {
        "found": True,
        "service_id": service_id,
        "matched_on_symptom": best_score > 0,
        "title": best["title"],
        "url": best["url"],
        "steps": best["steps"],
        "escalate_to": best["escalate_to"],
        "other_runbooks": [entry["title"] for _, entry in scored[1:]],
    }
