"""Unit tests for QualityRule model."""

import pytest
from decimal import Decimal
from uuid import uuid4

from src.models.quality_rule import (
    QualityRule,
    QualityRuleCategory,
    QualityRuleSeverity,
    RuleType,
)


class TestQualityRuleModel:
    """Tests for the QualityRule model."""

    def test_create_capsule_level_rule(self):
        """Test creating a capsule-level quality rule."""
        capsule_id = uuid4()
        rule = QualityRule(
            capsule_id=capsule_id,
            rule_name="Completeness Check",
            rule_type=RuleType.COMPLETENESS_THRESHOLD,
            rule_category=QualityRuleCategory.COMPLETENESS,
            rule_config={"threshold": 0.95},
            threshold_percent=Decimal("95.0"),
            severity=QualityRuleSeverity.WARNING,
            is_enabled=True,
        )

        assert rule.capsule_id == capsule_id
        assert rule.column_id is None
        assert rule.rule_name == "Completeness Check"
        assert rule.rule_type == RuleType.COMPLETENESS_THRESHOLD
        assert rule.rule_category == QualityRuleCategory.COMPLETENESS
        assert rule.threshold_percent == Decimal("95.0")
        assert rule.severity == QualityRuleSeverity.WARNING
        assert rule.is_enabled is True

    def test_create_column_level_rule(self):
        """Test creating a column-level quality rule."""
        column_id = uuid4()
        rule = QualityRule(
            column_id=column_id,
            rule_name="Not Null Check",
            rule_type=RuleType.NOT_NULL,
            rule_category=QualityRuleCategory.COMPLETENESS,
            rule_config={},
            severity=QualityRuleSeverity.ERROR,
            blocking=True,
            is_enabled=True,
        )

        assert rule.column_id == column_id
        assert rule.capsule_id is None
        assert rule.rule_type == RuleType.NOT_NULL
        assert rule.blocking is True

    def test_is_capsule_rule_property(self):
        """Test is_capsule_rule property."""
        capsule_rule = QualityRule(
            capsule_id=uuid4(),
            rule_name="Test",
            rule_type=RuleType.FRESHNESS,
            rule_config={},
        )
        column_rule = QualityRule(
            column_id=uuid4(),
            rule_name="Test",
            rule_type=RuleType.NOT_NULL,
            rule_config={},
        )

        assert capsule_rule.is_capsule_rule is True
        assert capsule_rule.is_column_rule is False
        assert column_rule.is_capsule_rule is False
        assert column_rule.is_column_rule is True

    def test_pattern_match_rule(self):
        """Test pattern match rule with expected pattern."""
        column_id = uuid4()
        rule = QualityRule(
            column_id=column_id,
            rule_name="Email Format Check",
            rule_type=RuleType.PATTERN_MATCH,
            rule_category=QualityRuleCategory.VALIDITY,
            rule_config={"pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$"},
            expected_pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$",
            severity=QualityRuleSeverity.ERROR,
            is_enabled=True,
        )

        assert rule.rule_type == RuleType.PATTERN_MATCH
        assert rule.expected_pattern is not None
        assert "@" in rule.expected_pattern

    def test_range_check_rule(self):
        """Test range check rule with min/max values."""
        column_id = uuid4()
        rule = QualityRule(
            column_id=column_id,
            rule_name="Age Range Check",
            rule_type=RuleType.RANGE_CHECK,
            rule_category=QualityRuleCategory.VALIDITY,
            rule_config={"min": 0, "max": 120},
            expected_range_min=Decimal("0"),
            expected_range_max=Decimal("120"),
            severity=QualityRuleSeverity.WARNING,
            is_enabled=True,
        )

        assert rule.rule_type == RuleType.RANGE_CHECK
        assert rule.expected_range_min == Decimal("0")
        assert rule.expected_range_max == Decimal("120")

    def test_critical_blocking_rule(self):
        """Test critical severity blocking rule."""
        column_id = uuid4()
        rule = QualityRule(
            column_id=column_id,
            rule_name="Primary Key Uniqueness",
            rule_type=RuleType.UNIQUE,
            rule_category=QualityRuleCategory.UNIQUENESS,
            rule_config={},
            severity=QualityRuleSeverity.CRITICAL,
            blocking=True,
            is_enabled=True,
        )

        assert rule.severity == QualityRuleSeverity.CRITICAL
        assert rule.blocking is True

    def test_subject_type_property(self):
        """Test subject_type property."""
        capsule_rule = QualityRule(
            capsule_id=uuid4(),
            rule_name="Test",
            rule_type=RuleType.FRESHNESS,
            rule_config={},
        )
        column_rule = QualityRule(
            column_id=uuid4(),
            rule_name="Test",
            rule_type=RuleType.NOT_NULL,
            rule_config={},
        )

        assert capsule_rule.subject_type == "capsule"
        assert column_rule.subject_type == "column"

    def test_custom_sql_rule(self):
        """Test custom SQL rule."""
        capsule_id = uuid4()
        rule = QualityRule(
            capsule_id=capsule_id,
            rule_name="Custom Business Logic",
            rule_type=RuleType.CUSTOM_SQL,
            rule_category=QualityRuleCategory.CONSISTENCY,
            rule_config={
                "sql": "SELECT COUNT(*) FROM table WHERE condition",
                "expected_result": 0,
            },
            severity=QualityRuleSeverity.ERROR,
            is_enabled=True,
        )

        assert rule.rule_type == RuleType.CUSTOM_SQL
        assert "sql" in rule.rule_config

    def test_value_in_set_rule(self):
        """Test value in set validation rule."""
        column_id = uuid4()
        rule = QualityRule(
            column_id=column_id,
            rule_name="Status Valid Values",
            rule_type=RuleType.VALUE_IN_SET,
            rule_category=QualityRuleCategory.VALIDITY,
            rule_config={"allowed_values": ["active", "inactive", "pending"]},
            severity=QualityRuleSeverity.ERROR,
            is_enabled=True,
        )

        assert rule.rule_type == RuleType.VALUE_IN_SET
        assert "allowed_values" in rule.rule_config
        assert len(rule.rule_config["allowed_values"]) == 3
