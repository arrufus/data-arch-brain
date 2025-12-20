"""Unit tests for DataPolicy model."""

import pytest
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from src.models.data_policy import (
    DataPolicy,
    DeletionAction,
    PolicyStatus,
    SensitivityLevel,
)


class TestDataPolicyModel:
    """Tests for the DataPolicy model."""

    def test_create_capsule_level_policy(self):
        """Test creating a capsule-level data policy."""
        capsule_id = uuid4()
        policy = DataPolicy(
            capsule_id=capsule_id,
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
            classification_tags=["GDPR", "PII"],
            policy_status=PolicyStatus.ACTIVE,
        )

        assert policy.capsule_id == capsule_id
        assert policy.column_id is None
        assert policy.sensitivity_level == SensitivityLevel.CONFIDENTIAL
        assert "GDPR" in policy.classification_tags
        assert policy.policy_status == PolicyStatus.ACTIVE

    def test_create_column_level_policy(self):
        """Test creating a column-level data policy."""
        column_id = uuid4()
        policy = DataPolicy(
            column_id=column_id,
            sensitivity_level=SensitivityLevel.RESTRICTED,
            classification_tags=["PII", "PHI"],
            requires_masking=True,
            encryption_required=True,
            policy_status=PolicyStatus.ACTIVE,
        )

        assert policy.column_id == column_id
        assert policy.capsule_id is None
        assert policy.sensitivity_level == SensitivityLevel.RESTRICTED
        assert policy.requires_masking is True
        assert policy.encryption_required is True

    def test_subject_type_property(self):
        """Test subject_type property."""
        capsule_policy = DataPolicy(
            capsule_id=uuid4(),
            sensitivity_level=SensitivityLevel.INTERNAL,
        )
        column_policy = DataPolicy(
            column_id=uuid4(),
            sensitivity_level=SensitivityLevel.PUBLIC,
        )

        assert capsule_policy.subject_type == "capsule"
        assert column_policy.subject_type == "column"

    def test_retention_policy(self):
        """Test retention policy configuration."""
        column_id = uuid4()
        policy = DataPolicy(
            column_id=column_id,
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
            retention_period=timedelta(days=365),
            retention_start="ingestion",
            deletion_action=DeletionAction.HARD_DELETE,
            legal_hold=False,
        )

        assert policy.retention_period == timedelta(days=365)
        assert policy.retention_start == "ingestion"
        assert policy.deletion_action == DeletionAction.HARD_DELETE
        assert policy.legal_hold is False

    def test_geographic_restrictions(self):
        """Test geographic restriction configuration."""
        capsule_id = uuid4()
        policy = DataPolicy(
            capsule_id=capsule_id,
            sensitivity_level=SensitivityLevel.RESTRICTED,
            allowed_regions=["EU", "UK"],
            restricted_regions=["CN", "RU"],
            data_residency="EU",
            cross_border_transfer=False,
        )

        assert "EU" in policy.allowed_regions
        assert "CN" in policy.restricted_regions
        assert policy.data_residency == "EU"
        assert policy.cross_border_transfer is False

    def test_access_control(self):
        """Test access control configuration."""
        column_id = uuid4()
        policy = DataPolicy(
            column_id=column_id,
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
            min_access_level="privileged",
            allowed_roles=["data_scientist", "analyst"],
            denied_roles=["intern"],
        )

        assert policy.min_access_level == "privileged"
        assert "data_scientist" in policy.allowed_roles
        assert "intern" in policy.denied_roles

    def test_approved_purposes(self):
        """Test approved and prohibited purposes."""
        column_id = uuid4()
        policy = DataPolicy(
            column_id=column_id,
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
            approved_purposes=["analytics", "reporting"],
            prohibited_purposes=["marketing", "profiling"],
        )

        assert "analytics" in policy.approved_purposes
        assert "marketing" in policy.prohibited_purposes

    def test_masking_configuration(self):
        """Test masking configuration."""
        column_id = uuid4()
        policy = DataPolicy(
            column_id=column_id,
            sensitivity_level=SensitivityLevel.RESTRICTED,
            requires_masking=True,
            masking_method="tokenization",
            masking_conditions={"role": "analyst"},
        )

        assert policy.requires_masking is True
        assert policy.masking_method == "tokenization"
        assert policy.masking_conditions["role"] == "analyst"

    def test_encryption_configuration(self):
        """Test encryption configuration."""
        capsule_id = uuid4()
        policy = DataPolicy(
            capsule_id=capsule_id,
            sensitivity_level=SensitivityLevel.SECRET,
            encryption_required=True,
            encryption_method="aes256",
            encryption_at_rest=True,
            encryption_in_transit=True,
        )

        assert policy.encryption_required is True
        assert policy.encryption_method == "aes256"
        assert policy.encryption_at_rest is True
        assert policy.encryption_in_transit is True

    def test_compliance_frameworks(self):
        """Test compliance framework configuration."""
        column_id = uuid4()
        policy = DataPolicy(
            column_id=column_id,
            sensitivity_level=SensitivityLevel.RESTRICTED,
            compliance_frameworks=["GDPR", "CCPA", "HIPAA"],
            consent_required=True,
            right_to_erasure=True,
        )

        assert "GDPR" in policy.compliance_frameworks
        assert "HIPAA" in policy.compliance_frameworks
        assert policy.consent_required is True
        assert policy.right_to_erasure is True

    def test_audit_requirements(self):
        """Test audit requirement configuration."""
        capsule_id = uuid4()
        policy = DataPolicy(
            capsule_id=capsule_id,
            sensitivity_level=SensitivityLevel.RESTRICTED,
            audit_log_required=True,
            audit_retention_period=timedelta(days=2555),  # 7 years
        )

        assert policy.audit_log_required is True
        assert policy.audit_retention_period == timedelta(days=2555)

    def test_governance_metadata(self):
        """Test governance metadata fields."""
        owner_id = uuid4()
        column_id = uuid4()
        policy = DataPolicy(
            column_id=column_id,
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
            policy_owner_id=owner_id,
            approved_by="John Doe",
            approved_at=datetime.now(timezone.utc),
            review_frequency=timedelta(days=365),
            next_review_date=date.today() + timedelta(days=365),
        )

        assert policy.policy_owner_id == owner_id
        assert policy.approved_by == "John Doe"
        assert policy.approved_at is not None
        assert policy.review_frequency == timedelta(days=365)

    def test_is_active_property(self):
        """Test is_active property logic."""
        today = date.today()

        # Active policy within effective dates
        active_policy = DataPolicy(
            column_id=uuid4(),
            sensitivity_level=SensitivityLevel.INTERNAL,
            policy_status=PolicyStatus.ACTIVE,
            effective_from=today - timedelta(days=30),
            effective_to=today + timedelta(days=30),
        )

        # Policy not yet effective
        future_policy = DataPolicy(
            column_id=uuid4(),
            sensitivity_level=SensitivityLevel.INTERNAL,
            policy_status=PolicyStatus.ACTIVE,
            effective_from=today + timedelta(days=30),
        )

        # Expired policy
        expired_policy = DataPolicy(
            column_id=uuid4(),
            sensitivity_level=SensitivityLevel.INTERNAL,
            policy_status=PolicyStatus.ACTIVE,
            effective_to=today - timedelta(days=1),
        )

        # Draft policy
        draft_policy = DataPolicy(
            column_id=uuid4(),
            sensitivity_level=SensitivityLevel.INTERNAL,
            policy_status=PolicyStatus.DRAFT,
        )

        assert active_policy.is_active is True
        assert future_policy.is_active is False
        assert expired_policy.is_active is False
        assert draft_policy.is_active is False

    def test_requires_review_property(self):
        """Test requires_review property logic."""
        today = date.today()

        # Policy requiring review
        needs_review = DataPolicy(
            column_id=uuid4(),
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
            next_review_date=today - timedelta(days=1),
        )

        # Policy not due for review
        no_review = DataPolicy(
            column_id=uuid4(),
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
            next_review_date=today + timedelta(days=30),
        )

        # Policy without review date
        no_date = DataPolicy(
            column_id=uuid4(),
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
        )

        assert needs_review.requires_review is True
        assert no_review.requires_review is False
        assert no_date.requires_review is False

    def test_is_pii_policy_property(self):
        """Test is_pii_policy property logic."""
        pii_policy = DataPolicy(
            column_id=uuid4(),
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
            classification_tags=["GDPR", "PII"],
        )

        ccpa_policy = DataPolicy(
            column_id=uuid4(),
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
            classification_tags=["CCPA", "personal_data"],
        )

        non_pii_policy = DataPolicy(
            column_id=uuid4(),
            sensitivity_level=SensitivityLevel.INTERNAL,
            classification_tags=["financial", "business"],
        )

        assert pii_policy.is_pii_policy is True
        assert ccpa_policy.is_pii_policy is True
        assert non_pii_policy.is_pii_policy is False

    def test_is_regulated_property(self):
        """Test is_regulated property logic."""
        regulated_policy = DataPolicy(
            column_id=uuid4(),
            sensitivity_level=SensitivityLevel.RESTRICTED,
            compliance_frameworks=["HIPAA", "PCI-DSS"],
        )

        unregulated_policy = DataPolicy(
            column_id=uuid4(),
            sensitivity_level=SensitivityLevel.INTERNAL,
            compliance_frameworks=[],
        )

        assert regulated_policy.is_regulated is True
        assert unregulated_policy.is_regulated is False
