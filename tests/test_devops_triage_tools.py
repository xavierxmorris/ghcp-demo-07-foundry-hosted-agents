"""Tests for the devops-triage tool layer.

These run with no Azure resources and no model calls -- they assert on the
deterministic domain logic the agent's tools wrap. That separation is the point:
tool logic is unit-testable, agent behaviour is eval-testable.
"""

from __future__ import annotations

import pytest

import triage


class TestSeverityClassification:
    def test_total_outage_with_revenue_impact_is_sev1(self):
        result = triage.classify_severity(
            customer_impact="Checkout is completely down, nobody can pay",
            revenue_impacting=True,
        )
        assert result["severity"] == "SEV1"

    def test_massive_error_rate_alone_is_sev1(self):
        result = triage.classify_severity(customer_impact="errors", error_rate_pct=72.0)
        assert result["severity"] == "SEV1"

    def test_outage_language_without_scale_is_sev2(self):
        result = triage.classify_severity(customer_impact="The ledger service is down")
        assert result["severity"] == "SEV2"

    def test_moderate_error_rate_is_sev2(self):
        result = triage.classify_severity(customer_impact="some requests fail", error_rate_pct=12.0)
        assert result["severity"] == "SEV2"

    def test_degradation_is_sev3(self):
        result = triage.classify_severity(customer_impact="Checkout is slow, p99 latency doubled")
        assert result["severity"] == "SEV3"

    def test_cosmetic_issue_is_sev4(self):
        result = triage.classify_severity(customer_impact="The receipt logo is misaligned")
        assert result["severity"] == "SEV4"

    def test_every_severity_carries_a_response_target(self):
        for impact in ("total outage", "slow", "misaligned logo"):
            result = triage.classify_severity(customer_impact=impact)
            assert result["response_target"]
            assert result["definition"]

    def test_signals_are_reported_for_explainability(self):
        result = triage.classify_severity(
            customer_impact="elevated errors",
            error_rate_pct=4.0,
            affected_users=120,
        )
        assert any("4.0%" in signal for signal in result["signals"])
        assert any("120" in signal for signal in result["signals"])

    def test_classification_is_deterministic(self):
        first = triage.classify_severity(customer_impact="checkout down", revenue_impacting=True)
        second = triage.classify_severity(customer_impact="checkout down", revenue_impacting=True)
        assert first == second


class TestServiceLookup:
    @pytest.mark.parametrize(
        "given",
        ["checkout-api", "checkout", "Checkout API", "CHECKOUT", "payments-checkout"],
    )
    def test_aliases_and_casing_resolve(self, given):
        result = triage.lookup_service(given)
        assert result["found"] is True
        assert result["service_id"] == "checkout-api"

    def test_unknown_service_is_reported_not_invented(self):
        result = triage.lookup_service("teleport-service")
        assert result["found"] is False
        assert "checkout-api" in result["known_services"]

    def test_lookup_exposes_escalation_metadata(self):
        result = triage.lookup_service("ledger")
        assert result["owning_team"] == "Payments Core"
        assert result["slack_channel"].startswith("#")
        assert result["tier"] == "tier-1"


class TestRecentDeployments:
    def test_window_filters_older_deploys(self):
        result = triage.recent_deployments("checkout", hours=4)
        assert result["deployment_count"] == 1
        assert result["deployments"][0]["deployment_id"] == "chk-2291"

    def test_wider_window_includes_more(self):
        result = triage.recent_deployments("checkout", hours=48)
        assert result["deployment_count"] == 2

    def test_results_are_ordered_most_recent_first(self):
        result = triage.recent_deployments("checkout", hours=72)
        ages = [item["hours_ago"] for item in result["deployments"]]
        assert ages == sorted(ages)

    def test_every_deployment_offers_a_rollback_command(self):
        result = triage.recent_deployments("checkout", hours=72)
        for deployment in result["deployments"]:
            assert deployment["rollback_command"].startswith("contoso-deploy rollback")

    def test_service_with_no_deploys_returns_empty_not_error(self):
        result = triage.recent_deployments("postgres", hours=720)
        assert result["found"] is True
        assert result["deployment_count"] == 0

    def test_unknown_service_is_reported(self):
        result = triage.recent_deployments("nope", hours=24)
        assert result["found"] is False


class TestRunbooks:
    def test_symptom_selects_the_matching_runbook(self):
        result = triage.get_runbook("checkout", symptom="we are seeing a surge of 5xx errors")
        assert result["matched_on_symptom"] is True
        assert "5xx" in result["title"]

    def test_latency_symptom_selects_the_latency_runbook(self):
        result = triage.get_runbook("checkout", symptom="p99 latency is way up and requests time out")
        assert "atency" in result["title"]

    def test_runbook_returns_actionable_steps_and_url(self):
        result = triage.get_runbook("ledger", symptom="posting backlog growing")
        assert len(result["steps"]) >= 3
        assert result["url"].startswith("https://")
        assert result["escalate_to"]

    def test_no_symptom_still_returns_a_default_runbook(self):
        result = triage.get_runbook("fraud-scoring")
        assert result["found"] is True
        assert result["matched_on_symptom"] is False

    def test_unknown_service_is_reported(self):
        result = triage.get_runbook("does-not-exist", symptom="down")
        assert result["found"] is False


class TestDataIntegrity:
    def test_every_service_has_a_runbook(self):
        services = set(triage._services())
        runbooks = set(triage._runbooks())
        assert services == runbooks, "every service needs at least one runbook entry"

    def test_dependencies_reference_known_services_or_are_documented_gaps(self):
        services = triage._services()
        known = set(services)
        # feature-store is intentionally external to this catalogue.
        external = {"feature-store"}
        for record in services.values():
            for dependency in record["depends_on"]:
                assert dependency in known or dependency in external
