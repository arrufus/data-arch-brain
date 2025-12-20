"""Unit tests for MaskingRule model."""

import pytest
from uuid import uuid4

from src.models.masking_rule import MaskingMethod, MaskingRule


class TestMaskingRuleModel:
    """Tests for the MaskingRule model."""

    def test_create_basic_masking_rule(self):
        """Test creating a basic masking rule."""
        column_id = uuid4()
        rule = MaskingRule(
            column_id=column_id,
            rule_name="Email Redaction",
            masking_method=MaskingMethod.REDACTION,
            method_config={"replacement": "***@***.***"},
            is_enabled=True,
        )

        assert rule.column_id == column_id
        assert rule.rule_name == "Email Redaction"
        assert rule.masking_method == MaskingMethod.REDACTION
        assert rule.method_config["replacement"] == "***@***.***"
        assert rule.is_enabled is True

    def test_partial_redaction_rule(self):
        """Test partial redaction masking rule."""
        column_id = uuid4()
        rule = MaskingRule(
            column_id=column_id,
            rule_name="Phone Partial Mask",
            masking_method=MaskingMethod.PARTIAL_REDACTION,
            method_config={
                "show_first": 3,
                "show_last": 4,
                "mask_char": "*",
            },
            preserve_length=True,
            preserve_format=True,
            is_enabled=True,
        )

        assert rule.masking_method == MaskingMethod.PARTIAL_REDACTION
        assert rule.preserve_length is True
        assert rule.preserve_format is True

    def test_tokenization_rule(self):
        """Test tokenization masking rule with reversibility."""
        column_id = uuid4()
        rule = MaskingRule(
            column_id=column_id,
            rule_name="SSN Tokenization",
            masking_method=MaskingMethod.TOKENIZATION,
            method_config={"algorithm": "FPE", "key_id": "key-123"},
            is_reversible=True,
            tokenization_vault="vault-prod-01",
            is_enabled=True,
        )

        assert rule.masking_method == MaskingMethod.TOKENIZATION
        assert rule.is_reversible is True
        assert rule.tokenization_vault == "vault-prod-01"

    def test_hashing_rule(self):
        """Test hashing masking rule (irreversible)."""
        column_id = uuid4()
        rule = MaskingRule(
            column_id=column_id,
            rule_name="User ID Hash",
            masking_method=MaskingMethod.HASHING,
            method_config={
                "algorithm": "SHA256",
                "salt": "random-salt",
            },
            is_reversible=False,
            preserve_type=True,
            is_enabled=True,
        )

        assert rule.masking_method == MaskingMethod.HASHING
        assert rule.is_reversible is False
        assert "algorithm" in rule.method_config

    def test_encryption_rule(self):
        """Test encryption masking rule."""
        column_id = uuid4()
        rule = MaskingRule(
            column_id=column_id,
            rule_name="Credit Card Encryption",
            masking_method=MaskingMethod.ENCRYPTION,
            method_config={
                "algorithm": "AES-256-GCM",
                "key_id": "encryption-key-prod",
            },
            is_reversible=True,
            preserve_null=True,
            is_enabled=True,
        )

        assert rule.masking_method == MaskingMethod.ENCRYPTION
        assert rule.is_reversible is True

    def test_role_based_masking(self):
        """Test role-based masking configuration."""
        column_id = uuid4()
        rule = MaskingRule(
            column_id=column_id,
            rule_name="Salary Masking for Non-HR",
            masking_method=MaskingMethod.GENERALIZATION,
            method_config={"bucket_size": 10000},
            applies_to_roles=["analyst", "developer", "manager"],
            exempt_roles=["hr_admin", "payroll"],
            is_enabled=True,
        )

        assert "analyst" in rule.applies_to_roles
        assert "hr_admin" in rule.exempt_roles

    def test_conditional_masking(self):
        """Test conditional masking with SQL condition."""
        column_id = uuid4()
        rule = MaskingRule(
            column_id=column_id,
            rule_name="Conditional PII Mask",
            masking_method=MaskingMethod.REDACTION,
            method_config={"replacement": "***"},
            apply_condition="country_code NOT IN ('US', 'CA')",
            is_enabled=True,
        )

        assert rule.apply_condition is not None
        assert "country_code" in rule.apply_condition

    def test_is_role_based_property(self):
        """Test is_role_based property logic."""
        role_based_rule = MaskingRule(
            column_id=uuid4(),
            rule_name="Test",
            masking_method=MaskingMethod.REDACTION,
            method_config={},
            applies_to_roles=["analyst"],
        )

        exempt_based_rule = MaskingRule(
            column_id=uuid4(),
            rule_name="Test",
            masking_method=MaskingMethod.REDACTION,
            method_config={},
            exempt_roles=["admin"],
        )

        no_role_rule = MaskingRule(
            column_id=uuid4(),
            rule_name="Test",
            masking_method=MaskingMethod.REDACTION,
            method_config={},
        )

        assert role_based_rule.is_role_based is True
        assert exempt_based_rule.is_role_based is True
        assert no_role_rule.is_role_based is False

    def test_is_conditional_property(self):
        """Test is_conditional property logic."""
        conditional_rule = MaskingRule(
            column_id=uuid4(),
            rule_name="Test",
            masking_method=MaskingMethod.REDACTION,
            method_config={},
            apply_condition="status = 'active'",
        )

        unconditional_rule = MaskingRule(
            column_id=uuid4(),
            rule_name="Test",
            masking_method=MaskingMethod.REDACTION,
            method_config={},
        )

        assert conditional_rule.is_conditional is True
        assert unconditional_rule.is_conditional is False

    def test_preserves_data_characteristics_property(self):
        """Test preserves_data_characteristics property logic."""
        preserving_rule = MaskingRule(
            column_id=uuid4(),
            rule_name="Test",
            masking_method=MaskingMethod.PARTIAL_REDACTION,
            method_config={},
            preserve_length=True,
            preserve_format=True,
        )

        non_preserving_rule = MaskingRule(
            column_id=uuid4(),
            rule_name="Test",
            masking_method=MaskingMethod.HASHING,
            method_config={},
        )

        assert preserving_rule.preserves_data_characteristics is True
        assert non_preserving_rule.preserves_data_characteristics is False

    def test_applies_to_role_method(self):
        """Test applies_to_role method logic."""
        rule = MaskingRule(
            column_id=uuid4(),
            rule_name="Test",
            masking_method=MaskingMethod.REDACTION,
            method_config={},
            applies_to_roles=["analyst", "developer"],
            exempt_roles=["admin"],
        )

        # Applies to specified roles
        assert rule.applies_to_role("analyst") is True
        assert rule.applies_to_role("developer") is True

        # Does not apply to exempt roles
        assert rule.applies_to_role("admin") is False

        # Does not apply to unspecified roles
        assert rule.applies_to_role("manager") is False

    def test_applies_to_role_no_restrictions(self):
        """Test applies_to_role when no roles specified (applies to all)."""
        rule = MaskingRule(
            column_id=uuid4(),
            rule_name="Test",
            masking_method=MaskingMethod.REDACTION,
            method_config={},
            applies_to_roles=[],
            exempt_roles=[],
        )

        # Should apply to all roles when no restrictions
        assert rule.applies_to_role("analyst") is True
        assert rule.applies_to_role("admin") is True
        assert rule.applies_to_role("anyone") is True

    def test_pseudonymization_rule(self):
        """Test pseudonymization masking rule."""
        column_id = uuid4()
        rule = MaskingRule(
            column_id=column_id,
            rule_name="Name Pseudonymization",
            masking_method=MaskingMethod.PSEUDONYMIZATION,
            method_config={
                "algorithm": "deterministic",
                "seed": "project-seed",
            },
            preserve_format=True,
            is_reversible=False,
            is_enabled=True,
        )

        assert rule.masking_method == MaskingMethod.PSEUDONYMIZATION
        assert rule.preserve_format is True

    def test_format_preserving_encryption_rule(self):
        """Test format-preserving encryption rule."""
        column_id = uuid4()
        rule = MaskingRule(
            column_id=column_id,
            rule_name="Credit Card FPE",
            masking_method=MaskingMethod.FORMAT_PRESERVING_ENCRYPTION,
            method_config={
                "algorithm": "FF3-1",
                "key_id": "fpe-key-01",
            },
            preserve_length=True,
            preserve_format=True,
            preserve_type=True,
            is_reversible=True,
            is_enabled=True,
        )

        assert rule.masking_method == MaskingMethod.FORMAT_PRESERVING_ENCRYPTION
        assert rule.preserve_length is True
        assert rule.preserve_format is True
        assert rule.preserve_type is True
