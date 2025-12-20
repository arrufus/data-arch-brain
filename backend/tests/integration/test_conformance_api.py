"""Integration tests for Conformance API endpoints."""

import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
class TestConformanceRulesAPI:
    """Integration tests for conformance rules endpoints."""

    async def test_list_rules(self, client: AsyncClient):
        """Test listing conformance rules."""
        response = await client.get("/api/v1/conformance/rules")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "rule_sets" in data
        assert isinstance(data["data"], list)
        assert isinstance(data["rule_sets"], list)

        # Should have rules (built-in rules)
        assert len(data["data"]) > 0

    async def test_list_rules_by_rule_set(self, client: AsyncClient):
        """Test filtering rules by rule set."""
        response = await client.get("/api/v1/conformance/rules?rule_set=medallion")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

        # All returned rules should be from medallion rule set
        for rule in data["data"]:
            assert rule["rule_set"] == "medallion"

    async def test_list_rules_by_category(self, client: AsyncClient):
        """Test filtering rules by category."""
        response = await client.get("/api/v1/conformance/rules?category=naming")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

        # All returned rules should be naming category
        for rule in data["data"]:
            assert rule["category"] == "naming"

    async def test_list_rules_filter_enabled(self, client: AsyncClient):
        """Test filtering rules by enabled status."""
        response = await client.get("/api/v1/conformance/rules?enabled=true")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

        # All returned rules should be enabled
        for rule in data["data"]:
            assert rule["enabled"] is True

    async def test_get_rule_by_id(self, client: AsyncClient):
        """Test getting a specific rule by ID."""
        # First get the list to find a valid rule ID
        list_response = await client.get("/api/v1/conformance/rules")
        rules = list_response.json()["data"]

        if not rules:
            pytest.skip("No rules available to test")

        rule_id = rules[0]["rule_id"]

        # Get the specific rule
        response = await client.get(f"/api/v1/conformance/rules/{rule_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["rule_id"] == rule_id
        assert "name" in data
        assert "description" in data
        assert "severity" in data
        assert "category" in data
        assert "scope" in data
        assert "enabled" in data

    async def test_get_rule_not_found(self, client: AsyncClient):
        """Test getting non-existent rule returns 404."""
        response = await client.get("/api/v1/conformance/rules/NONEXISTENT_RULE")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestUpdateRuleAPI:
    """Integration tests for PATCH /conformance/rules/{rule_id} endpoint."""

    async def test_update_rule_enable(self, client: AsyncClient):
        """Test enabling a rule."""
        # Get a rule ID
        list_response = await client.get("/api/v1/conformance/rules?enabled=false")
        rules = list_response.json()["data"]

        if not rules:
            pytest.skip("No disabled rules available to test")

        rule_id = rules[0]["rule_id"]

        # Enable the rule
        response = await client.patch(
            f"/api/v1/conformance/rules/{rule_id}",
            json={"enabled": True},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["rule_id"] == rule_id
        assert data["enabled"] is True

    async def test_update_rule_disable(self, client: AsyncClient):
        """Test disabling a rule."""
        # Get an enabled rule
        list_response = await client.get("/api/v1/conformance/rules?enabled=true")
        rules = list_response.json()["data"]

        if not rules:
            pytest.skip("No enabled rules available to test")

        rule_id = rules[0]["rule_id"]

        # Disable the rule
        response = await client.patch(
            f"/api/v1/conformance/rules/{rule_id}",
            json={"enabled": False},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["rule_id"] == rule_id
        assert data["enabled"] is False

        # Re-enable it for future tests
        await client.patch(
            f"/api/v1/conformance/rules/{rule_id}",
            json={"enabled": True},
        )

    async def test_update_rule_not_found(self, client: AsyncClient):
        """Test updating non-existent rule returns 404."""
        response = await client.patch(
            "/api/v1/conformance/rules/NONEXISTENT_RULE",
            json={"enabled": True},
        )

        assert response.status_code == 404

    async def test_update_rule_invalid_body(self, client: AsyncClient):
        """Test updating rule with invalid body."""
        # Get a rule ID
        list_response = await client.get("/api/v1/conformance/rules")
        rules = list_response.json()["data"]

        if not rules:
            pytest.skip("No rules available to test")

        rule_id = rules[0]["rule_id"]

        # Send invalid body (missing enabled field)
        response = await client.patch(
            f"/api/v1/conformance/rules/{rule_id}",
            json={},
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
class TestTestRuleAPI:
    """Integration tests for POST /conformance/rules/{rule_id}/test endpoint."""

    async def test_test_rule_without_capsules(self, client: AsyncClient):
        """Test testing a rule without specifying capsules (tests all)."""
        # Get a rule ID
        list_response = await client.get("/api/v1/conformance/rules")
        rules = list_response.json()["data"]

        if not rules:
            pytest.skip("No rules available to test")

        rule_id = rules[0]["rule_id"]

        # Test the rule
        response = await client.post(
            f"/api/v1/conformance/rules/{rule_id}/test",
            json={},
        )

        assert response.status_code == 200
        data = response.json()

        assert "score" in data
        assert "weighted_score" in data
        assert "summary" in data
        assert "by_severity" in data
        assert "by_category" in data
        assert "violation_count" in data
        assert "violations" in data
        assert "computed_at" in data

        # Summary should have correct fields
        assert "total_rules" in data["summary"]
        assert "passing_rules" in data["summary"]
        assert "failing_rules" in data["summary"]
        assert "not_applicable" in data["summary"]

        # Should be testing only one rule
        assert data["summary"]["total_rules"] == 1

    async def test_test_rule_with_specific_capsules(self, client: AsyncClient):
        """Test testing a rule with specific capsule URNs."""
        # Get a rule ID
        list_response = await client.get("/api/v1/conformance/rules")
        rules = list_response.json()["data"]

        if not rules:
            pytest.skip("No rules available to test")

        rule_id = rules[0]["rule_id"]

        # Test with specific (non-existent) capsule URNs
        # This should still return 200 but with no violations
        response = await client.post(
            f"/api/v1/conformance/rules/{rule_id}/test",
            json={
                "capsule_urns": [
                    "urn:dcs:capsule:test:test_table",
                    "urn:dcs:capsule:test:test_table2",
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "violations" in data
        assert isinstance(data["violations"], list)

    async def test_test_rule_not_found(self, client: AsyncClient):
        """Test testing non-existent rule returns 404."""
        response = await client.post(
            "/api/v1/conformance/rules/NONEXISTENT_RULE/test",
            json={},
        )

        assert response.status_code == 404

    async def test_test_rule_response_structure(self, client: AsyncClient):
        """Test that test rule response has correct structure."""
        # Get a rule ID
        list_response = await client.get("/api/v1/conformance/rules")
        rules = list_response.json()["data"]

        if not rules:
            pytest.skip("No rules available to test")

        rule_id = rules[0]["rule_id"]

        # Test the rule
        response = await client.post(
            f"/api/v1/conformance/rules/{rule_id}/test",
            json={},
        )

        assert response.status_code == 200
        data = response.json()

        # Check score fields
        assert isinstance(data["score"], (int, float))
        assert isinstance(data["weighted_score"], (int, float))
        assert 0 <= data["score"] <= 100
        assert 0 <= data["weighted_score"] <= 100

        # Check summary structure
        summary = data["summary"]
        assert summary["total_rules"] == 1
        assert isinstance(summary["passing_rules"], int)
        assert isinstance(summary["failing_rules"], int)
        assert summary["passing_rules"] + summary["failing_rules"] <= 1

        # Check by_severity structure
        assert isinstance(data["by_severity"], dict)
        for sev_key, sev_data in data["by_severity"].items():
            assert "total" in sev_data
            assert "passing" in sev_data
            assert "failing" in sev_data

        # Check by_category structure
        assert isinstance(data["by_category"], dict)
        for cat_key, cat_data in data["by_category"].items():
            assert "total" in cat_data
            assert "pass" in cat_data
            assert "fail" in cat_data

        # Check violations structure
        assert isinstance(data["violations"], list)
        if data["violations"]:
            violation = data["violations"][0]
            assert "rule_id" in violation
            assert "rule_name" in violation
            assert "severity" in violation
            assert "category" in violation
            assert "subject_type" in violation
            assert "subject_id" in violation
            assert "subject_urn" in violation
            assert "subject_name" in violation
            assert "message" in violation
            assert "details" in violation


@pytest.mark.asyncio
class TestConformanceEvaluateAPI:
    """Integration tests for conformance evaluation endpoints."""

    async def test_get_conformance_score(self, client: AsyncClient):
        """Test getting conformance score."""
        response = await client.get("/api/v1/conformance/score")

        assert response.status_code == 200
        data = response.json()

        assert "scope" in data
        assert "score" in data
        assert "weighted_score" in data
        assert "summary" in data
        assert "by_severity" in data
        assert "by_category" in data
        assert "computed_at" in data

    async def test_run_conformance_evaluation(self, client: AsyncClient):
        """Test running conformance evaluation."""
        response = await client.post(
            "/api/v1/conformance/evaluate",
            json={},
        )

        assert response.status_code == 200
        data = response.json()

        assert "score" in data
        assert "summary" in data
        assert "violations" in data
        assert "violation_count" in data

    async def test_run_conformance_evaluation_with_rule_sets(self, client: AsyncClient):
        """Test running conformance evaluation with specific rule sets."""
        response = await client.post(
            "/api/v1/conformance/evaluate",
            json={"rule_sets": ["medallion", "dbt_best_practices"]},
        )

        assert response.status_code == 200
        data = response.json()

        assert "violations" in data
        assert isinstance(data["violations"], list)

        # All violations should be from specified rule sets
        for violation in data["violations"]:
            # Note: We'd need to map violation to rule set to verify this
            # For now, just check the structure
            assert "rule_id" in violation

    async def test_list_violations(self, client: AsyncClient):
        """Test listing violations."""
        response = await client.get("/api/v1/conformance/violations")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_violations_with_filters(self, client: AsyncClient):
        """Test listing violations with filters."""
        response = await client.get(
            "/api/v1/conformance/violations?severity=error&limit=10"
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) <= 10

        # All violations should be error severity
        for violation in data["data"]:
            assert violation["severity"] == "error"
