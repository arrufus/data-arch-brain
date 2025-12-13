"""Unit tests for the conformance service."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.conformance import (
    ConformanceService,
    RuleDefinition,
    RuleSeverity,
    RuleCategory,
    RuleScope,
    ALL_BUILT_IN_RULES,
)


class TestRuleDefinition:
    """Tests for RuleDefinition dataclass."""

    def test_rule_definition_creation(self):
        """Test creating a rule definition."""
        rule = RuleDefinition(
            rule_id="TEST_001",
            name="Test Rule",
            description="A test rule",
            severity=RuleSeverity.WARNING,
            category=RuleCategory.NAMING,
            scope=RuleScope.CAPSULE,
        )

        assert rule.rule_id == "TEST_001"
        assert rule.name == "Test Rule"
        assert rule.severity == RuleSeverity.WARNING
        assert rule.category == RuleCategory.NAMING
        assert rule.scope == RuleScope.CAPSULE
        assert rule.enabled is True

    def test_rule_definition_with_pattern(self):
        """Test rule definition with regex pattern."""
        rule = RuleDefinition(
            rule_id="TEST_002",
            name="Naming Pattern Rule",
            description="Test naming pattern",
            severity=RuleSeverity.ERROR,
            category=RuleCategory.NAMING,
            scope=RuleScope.CAPSULE,
            pattern=r"^(stg_|dim_|fct_)",
        )

        assert rule.pattern == r"^(stg_|dim_|fct_)"


class TestBuiltInRules:
    """Tests for built-in rules."""

    def test_builtin_rules_exist(self):
        """Test that built-in rules are defined."""
        assert len(ALL_BUILT_IN_RULES) > 0

    def test_builtin_rules_have_required_fields(self):
        """Test that all built-in rules have required fields."""
        for rule in ALL_BUILT_IN_RULES:
            assert rule.rule_id is not None
            assert rule.name is not None
            assert rule.description is not None
            assert rule.severity is not None
            assert rule.category is not None
            assert rule.scope is not None

    def test_builtin_rules_have_unique_ids(self):
        """Test that all built-in rules have unique IDs."""
        rule_ids = [rule.rule_id for rule in ALL_BUILT_IN_RULES]
        assert len(rule_ids) == len(set(rule_ids))

    def test_medallion_rules_exist(self):
        """Test that Medallion architecture rules exist."""
        medallion_rules = [r for r in ALL_BUILT_IN_RULES if r.rule_set == "medallion"]
        assert len(medallion_rules) > 0

    def test_dbt_best_practices_rules_exist(self):
        """Test that dbt best practices rules exist."""
        dbt_rules = [r for r in ALL_BUILT_IN_RULES if r.rule_set == "dbt_best_practices"]
        assert len(dbt_rules) > 0

    def test_pii_compliance_rules_exist(self):
        """Test that PII compliance rules exist."""
        pii_rules = [r for r in ALL_BUILT_IN_RULES if r.rule_set == "pii_compliance"]
        assert len(pii_rules) > 0


class TestConformanceServiceRuleManagement:
    """Tests for ConformanceService rule management."""

    def test_get_available_rules(self):
        """Test getting available rules."""
        session_mock = MagicMock()
        service = ConformanceService(session_mock)

        rules = service.get_available_rules()
        assert len(rules) > 0

    def test_get_rules_by_rule_set(self):
        """Test filtering rules by rule set."""
        session_mock = MagicMock()
        service = ConformanceService(session_mock)

        medallion_rules = service.get_available_rules(rule_set="medallion")
        assert all(r.rule_set == "medallion" for r in medallion_rules)

    def test_get_rules_by_category(self):
        """Test filtering rules by category."""
        session_mock = MagicMock()
        service = ConformanceService(session_mock)

        naming_rules = service.get_available_rules(category="naming")
        assert all(r.category == RuleCategory.NAMING for r in naming_rules)

    def test_get_enabled_rules_only(self):
        """Test getting only enabled rules."""
        session_mock = MagicMock()
        service = ConformanceService(session_mock)

        enabled_rules = service.get_available_rules(enabled_only=True)
        assert all(r.enabled for r in enabled_rules)

    def test_get_rule_sets(self):
        """Test getting available rule sets."""
        session_mock = MagicMock()
        service = ConformanceService(session_mock)

        rule_sets = service.get_rule_sets()
        assert "medallion" in rule_sets
        assert "dbt_best_practices" in rule_sets
        assert "pii_compliance" in rule_sets


class TestCustomRuleLoading:
    """Tests for custom rule loading."""

    def test_load_custom_rules_valid_yaml(self):
        """Test loading valid custom rules from YAML."""
        session_mock = MagicMock()
        service = ConformanceService(session_mock)

        yaml_content = """
rules:
  - id: CUSTOM_001
    name: "Custom Test Rule"
    description: "A custom test rule"
    severity: warning
    category: naming
    scope: capsule
    pattern: "^custom_"
    remediation: "Rename to start with custom_"
"""
        rules = service.load_custom_rules(yaml_content, rule_set_name="custom_test")

        assert len(rules) == 1
        assert rules[0].rule_id == "CUSTOM_001"
        assert rules[0].name == "Custom Test Rule"
        assert rules[0].severity == RuleSeverity.WARNING
        assert rules[0].rule_set == "custom_test"

    def test_load_custom_rules_invalid_yaml_missing_rules(self):
        """Test loading invalid YAML without rules key."""
        session_mock = MagicMock()
        service = ConformanceService(session_mock)

        yaml_content = """
some_key: value
"""
        with pytest.raises(ValueError, match="must contain 'rules' key"):
            service.load_custom_rules(yaml_content)

    def test_load_custom_rules_invalid_yaml_missing_required_field(self):
        """Test loading invalid YAML with missing required field."""
        session_mock = MagicMock()
        service = ConformanceService(session_mock)

        yaml_content = """
rules:
  - id: CUSTOM_001
    name: "Incomplete Rule"
    # Missing description, severity, category, scope
"""
        with pytest.raises(ValueError, match="missing required field"):
            service.load_custom_rules(yaml_content)

    def test_load_custom_rules_invalid_severity(self):
        """Test loading rules with invalid severity."""
        session_mock = MagicMock()
        service = ConformanceService(session_mock)

        yaml_content = """
rules:
  - id: CUSTOM_001
    name: "Test Rule"
    description: "Test"
    severity: invalid_severity
    category: naming
    scope: capsule
"""
        with pytest.raises(ValueError, match="Invalid severity"):
            service.load_custom_rules(yaml_content)

    def test_remove_rule(self):
        """Test removing a custom rule."""
        session_mock = MagicMock()
        service = ConformanceService(session_mock)

        # First add a custom rule
        yaml_content = """
rules:
  - id: CUSTOM_TO_REMOVE
    name: "Rule to Remove"
    description: "Will be removed"
    severity: info
    category: naming
    scope: capsule
"""
        service.load_custom_rules(yaml_content)

        # Verify it was added
        rules = service.get_available_rules(enabled_only=False)
        rule_ids = [r.rule_id for r in rules]
        assert "CUSTOM_TO_REMOVE" in rule_ids

        # Remove it
        removed = service.remove_rule("CUSTOM_TO_REMOVE")
        assert removed is True

        # Verify it was removed
        rules = service.get_available_rules(enabled_only=False)
        rule_ids = [r.rule_id for r in rules]
        assert "CUSTOM_TO_REMOVE" not in rule_ids

    def test_remove_nonexistent_rule(self):
        """Test removing a rule that doesn't exist."""
        session_mock = MagicMock()
        service = ConformanceService(session_mock)

        removed = service.remove_rule("NONEXISTENT_RULE")
        assert removed is False

    def test_export_rules_yaml(self):
        """Test exporting rules to YAML format."""
        session_mock = MagicMock()
        service = ConformanceService(session_mock)

        yaml_output = service.export_rules_yaml()

        assert "rules:" in yaml_output
        assert "id:" in yaml_output
        assert "name:" in yaml_output
        assert "severity:" in yaml_output


class TestSeverityWeights:
    """Tests for severity weight calculations."""

    def test_severity_weights(self):
        """Test that severity weights are correctly defined."""
        assert RuleSeverity.CRITICAL.value == "critical"
        assert RuleSeverity.ERROR.value == "error"
        assert RuleSeverity.WARNING.value == "warning"
        assert RuleSeverity.INFO.value == "info"
