"""Unit tests for BusinessTerm models."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.models.business_term import (
    ApprovalStatus,
    BusinessTerm,
    CapsuleBusinessTerm,
    ColumnBusinessTerm,
    RelationshipType,
)


class TestBusinessTermModel:
    """Tests for the BusinessTerm model."""

    def test_create_business_term_minimal(self):
        """Test creating a business term with minimal fields."""
        term = BusinessTerm(
            term_name="customer_lifetime_value",
            display_name="Customer Lifetime Value",
            definition="The total revenue a customer generates over their lifetime",
            approval_status=ApprovalStatus.DRAFT,  # server_default only applies in DB
        )

        assert term.term_name == "customer_lifetime_value"
        assert term.display_name == "Customer Lifetime Value"
        assert "total revenue" in term.definition
        assert term.approval_status == ApprovalStatus.DRAFT
        assert term.abbreviation is None
        # Note: default=list only applies in DB, not Python object creation
        assert term.synonyms is None or term.synonyms == []

    def test_create_business_term_full(self):
        """Test creating a business term with all fields."""
        domain_id = uuid4()
        owner_id = uuid4()

        term = BusinessTerm(
            term_name="annual_recurring_revenue",
            display_name="Annual Recurring Revenue",
            definition="The yearly value of recurring subscription revenue",
            abbreviation="ARR",
            synonyms=["yearly_recurring_revenue", "annual_subscription_revenue"],
            domain_id=domain_id,
            category="financial_metrics",
            owner_id=owner_id,
            steward_email="finance-team@example.com",
            approval_status=ApprovalStatus.APPROVED,
            approved_by="Jane Smith",
            approved_at=datetime.now(timezone.utc),
            tags=["finance", "saas", "kpi"],
        )

        assert term.term_name == "annual_recurring_revenue"
        assert term.abbreviation == "ARR"
        assert len(term.synonyms) == 2
        assert "yearly_recurring_revenue" in term.synonyms
        assert term.domain_id == domain_id
        assert term.category == "financial_metrics"
        assert term.steward_email == "finance-team@example.com"
        assert term.approval_status == ApprovalStatus.APPROVED
        assert term.approved_by == "Jane Smith"
        assert "saas" in term.tags

    def test_business_term_approval_workflow(self):
        """Test business term approval status transitions."""
        term = BusinessTerm(
            term_name="churn_rate",
            display_name="Churn Rate",
            definition="Percentage of customers who stop subscribing",
            approval_status=ApprovalStatus.DRAFT,
        )

        # Start as draft
        assert term.approval_status == ApprovalStatus.DRAFT
        assert term.approved_by is None
        assert term.approved_at is None

        # Move to under review
        term.approval_status = ApprovalStatus.UNDER_REVIEW
        assert term.approval_status == ApprovalStatus.UNDER_REVIEW

        # Approve
        term.approval_status = ApprovalStatus.APPROVED
        term.approved_by = "John Doe"
        term.approved_at = datetime.now(timezone.utc)

        assert term.approval_status == ApprovalStatus.APPROVED
        assert term.approved_by == "John Doe"
        assert term.approved_at is not None

    def test_business_term_with_metadata(self):
        """Test business term with additional metadata."""
        term = BusinessTerm(
            term_name="monthly_active_users",
            display_name="Monthly Active Users",
            definition="Count of unique users active in a month",
            abbreviation="MAU",
            meta={
                "calculation_method": "COUNT(DISTINCT user_id)",
                "data_sources": ["events", "user_sessions"],
                "update_frequency": "daily",
                "owner_team": "product_analytics",
            },
        )

        assert term.meta["calculation_method"] == "COUNT(DISTINCT user_id)"
        assert "events" in term.meta["data_sources"]
        assert term.meta["update_frequency"] == "daily"

    def test_deprecated_business_term(self):
        """Test marking a business term as deprecated."""
        term = BusinessTerm(
            term_name="legacy_customer_score",
            display_name="Legacy Customer Score",
            definition="Old scoring algorithm (deprecated)",
            approval_status=ApprovalStatus.DEPRECATED,
            meta={
                "deprecated_date": "2024-01-01",
                "replacement_term": "customer_health_score",
                "deprecation_reason": "Replaced by improved algorithm",
            },
        )

        assert term.approval_status == ApprovalStatus.DEPRECATED
        assert "replacement_term" in term.meta
        assert term.meta["replacement_term"] == "customer_health_score"

    def test_approval_status_enum_values(self):
        """Test that approval status enum has expected values."""
        assert ApprovalStatus.DRAFT == "draft"
        assert ApprovalStatus.UNDER_REVIEW == "under_review"
        assert ApprovalStatus.APPROVED == "approved"
        assert ApprovalStatus.DEPRECATED == "deprecated"


class TestCapsuleBusinessTermModel:
    """Tests for the CapsuleBusinessTerm association model."""

    def test_create_capsule_term_association(self):
        """Test creating a capsule-business term association."""
        capsule_id = uuid4()
        term_id = uuid4()

        association = CapsuleBusinessTerm(
            capsule_id=capsule_id,
            business_term_id=term_id,
            relationship_type=RelationshipType.IMPLEMENTS,
            added_by="data_steward@example.com",
        )

        assert association.capsule_id == capsule_id
        assert association.business_term_id == term_id
        assert association.relationship_type == RelationshipType.IMPLEMENTS
        assert association.added_by == "data_steward@example.com"

    def test_capsule_term_implements_relationship(self):
        """Test capsule implementing a business term."""
        capsule_id = uuid4()
        term_id = uuid4()

        association = CapsuleBusinessTerm(
            capsule_id=capsule_id,
            business_term_id=term_id,
            relationship_type=RelationshipType.IMPLEMENTS,
            added_by="analyst@example.com",
            meta={
                "confidence": "high",
                "verification_date": "2024-12-18",
            },
        )

        assert association.relationship_type == RelationshipType.IMPLEMENTS
        assert association.meta["confidence"] == "high"

    def test_capsule_term_related_relationship(self):
        """Test capsule related to a business term."""
        capsule_id = uuid4()
        term_id = uuid4()

        association = CapsuleBusinessTerm(
            capsule_id=capsule_id,
            business_term_id=term_id,
            relationship_type=RelationshipType.RELATED_TO,
            added_by="data_engineer@example.com",
        )

        assert association.relationship_type == RelationshipType.RELATED_TO

    def test_capsule_term_association_with_metadata(self):
        """Test association with additional metadata."""
        capsule_id = uuid4()
        term_id = uuid4()

        association = CapsuleBusinessTerm(
            capsule_id=capsule_id,
            business_term_id=term_id,
            relationship_type=RelationshipType.IMPLEMENTS,
            added_by="steward@example.com",
            meta={
                "verification_method": "manual_review",
                "notes": "Confirmed with finance team",
                "last_reviewed": "2024-12-15",
            },
        )

        assert association.meta["verification_method"] == "manual_review"
        assert "finance team" in association.meta["notes"]


class TestColumnBusinessTermModel:
    """Tests for the ColumnBusinessTerm association model."""

    def test_create_column_term_association(self):
        """Test creating a column-business term association."""
        column_id = uuid4()
        term_id = uuid4()

        association = ColumnBusinessTerm(
            column_id=column_id,
            business_term_id=term_id,
            relationship_type=RelationshipType.IMPLEMENTS,
            added_by="data_steward@example.com",
        )

        assert association.column_id == column_id
        assert association.business_term_id == term_id
        assert association.relationship_type == RelationshipType.IMPLEMENTS
        assert association.added_by == "data_steward@example.com"

    def test_column_term_implements_relationship(self):
        """Test column implementing a business term."""
        column_id = uuid4()
        term_id = uuid4()

        association = ColumnBusinessTerm(
            column_id=column_id,
            business_term_id=term_id,
            relationship_type=RelationshipType.IMPLEMENTS,
            added_by="analyst@example.com",
            meta={
                "match_score": 0.95,
                "match_method": "semantic_similarity",
            },
        )

        assert association.relationship_type == RelationshipType.IMPLEMENTS
        assert association.meta["match_score"] == 0.95

    def test_column_term_partial_implementation(self):
        """Test column partially implementing a business term."""
        column_id = uuid4()
        term_id = uuid4()

        association = ColumnBusinessTerm(
            column_id=column_id,
            business_term_id=term_id,
            relationship_type=RelationshipType.IMPLEMENTS,
            added_by="steward@example.com",
            meta={
                "implementation_status": "partial",
                "missing_attributes": ["time_zone", "currency"],
            },
        )

        assert association.meta["implementation_status"] == "partial"
        assert "time_zone" in association.meta["missing_attributes"]

    def test_relationship_type_enum_values(self):
        """Test that relationship type enum has expected values."""
        assert RelationshipType.IMPLEMENTS == "implements"
        assert RelationshipType.RELATED_TO == "related_to"
        assert RelationshipType.DERIVED_FROM == "derived_from"
        assert RelationshipType.EXAMPLE_OF == "example_of"
        assert RelationshipType.MEASURES == "measures"
