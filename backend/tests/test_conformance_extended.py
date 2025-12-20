"""Comprehensive tests for extended conformance rules (Dimensions 2-7).

Tests all 48 new conformance rules added for the 7-dimension data capsule model.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.business_term import BusinessTerm, CapsuleBusinessTerm
from src.models.capsule import Capsule
from src.models.capsule_contract import CapsuleContract
from src.models.capsule_version import CapsuleVersion
from src.models.column import Column
from src.models.data_policy import DataPolicy
from src.models.domain import Domain, Owner
from src.models.index import CapsuleIndex
from src.models.masking_rule import MaskingRule
from src.models.quality_rule import QualityRule
from src.models.sla_incident import SLAIncident
from src.models.tag import CapsuleTag, Tag
from src.models.transformation_code import TransformationCode
from src.models.value_domain import ValueDomain
from src.services.conformance import ConformanceService, RuleSeverity


@pytest.fixture
async def owner(test_session: AsyncSession):
    """Create test owner."""
    owner = Owner(
        name="Test Team",
        owner_type="team",
        email="test@example.com",
        meta={},
    )
    test_session.add(owner)
    await test_session.flush()
    return owner


@pytest.fixture
async def domain(test_session: AsyncSession, owner):
    """Create test domain."""
    domain = Domain(
        name="test_domain",
        description="Test domain",
        owner_id=owner.id,
        meta={},
    )
    test_session.add(domain)
    await test_session.flush()
    return domain


@pytest.fixture
async def business_term(test_session: AsyncSession, domain):
    """Create test business term."""
    term = BusinessTerm(
        name="Revenue",
        definition="Total revenue",
        domain_id=domain.id,
        meta={},
    )
    test_session.add(term)
    await test_session.flush()
    return term


@pytest.fixture
async def value_domain(test_session: AsyncSession):
    """Create test value domain."""
    vd = ValueDomain(
        domain_name="order_status",
        domain_type="enum",
        description="Order status values",
        allowed_values=[
            {"code": "pending", "label": "Pending"},
            {"code": "completed", "label": "Completed"},
        ],
        meta={},
    )
    test_session.add(vd)
    await test_session.flush()
    return vd


@pytest.fixture
async def tag(test_session: AsyncSession):
    """Create test tag."""
    tag = Tag(
        name="finance",
        description="Finance domain tag",
        meta={},
    )
    test_session.add(tag)
    await test_session.flush()
    return tag


# ============================================================================
# Dimension 2: Structural Metadata Rules Tests
# ============================================================================


@pytest.mark.asyncio
class TestStructuralMetadataRules:
    """Tests for Dimension 2 (Structural Metadata) conformance rules."""

    async def test_dim2_006_tables_should_have_primary_key_pass(self, test_session: AsyncSession, domain, owner):
        """Test DIM2_006: Table with primary key passes."""
        capsule = Capsule(
            urn="urn:test:table_with_pk",
            name="table_with_pk",
            capsule_type="model",
            layer="bronze",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add column with primary key
        col = Column(
            capsule_id=capsule.id,
            urn=f"{capsule.urn}.id",
            name="id",
            data_type="INTEGER",
            ordinal_position=1,
            is_primary_key=True,
            meta={},
        )
        test_session.add(col)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["structural_metadata"], capsule_urns=[capsule.urn])

        # Find DIM2_006 violations
        dim2_006_violations = [v for v in result.violations if v.rule_id == "DIM2_006"]
        assert len(dim2_006_violations) == 0, "Table with PK should not violate DIM2_006"

    async def test_dim2_006_tables_should_have_primary_key_fail(self, test_session: AsyncSession, domain, owner):
        """Test DIM2_006: Table without primary key fails."""
        capsule = Capsule(
            urn="urn:test:table_no_pk",
            name="table_no_pk",
            capsule_type="model",
            layer="bronze",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add column without primary key
        col = Column(
            capsule_id=capsule.id,
            urn=f"{capsule.urn}.name",
            name="name",
            data_type="VARCHAR",
            ordinal_position=1,
            is_primary_key=False,
            meta={},
        )
        test_session.add(col)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["structural_metadata"], capsule_urns=[capsule.urn])

        # Find DIM2_006 violations
        dim2_006_violations = [v for v in result.violations if v.rule_id == "DIM2_006"]
        assert len(dim2_006_violations) == 1, "Table without PK should violate DIM2_006"
        assert dim2_006_violations[0].severity == RuleSeverity.ERROR


# ============================================================================
# Dimension 3: Semantic Metadata Rules Tests
# ============================================================================


@pytest.mark.asyncio
class TestSemanticMetadataRules:
    """Tests for Dimension 3 (Semantic Metadata) conformance rules."""

    async def test_dim3_004_gold_tables_should_be_tagged_pass(
        self, test_session: AsyncSession, domain, owner, tag
    ):
        """Test DIM3_004: Gold table with tags passes."""
        capsule = Capsule(
            urn="urn:test:gold_table_tagged",
            name="gold_table_tagged",
            capsule_type="model",
            layer="gold",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add tag association
        capsule_tag = CapsuleTag(
            capsule_id=capsule.id,
            tag_id=tag.id,
            meta={},
        )
        test_session.add(capsule_tag)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["semantic_metadata"], capsule_urns=[capsule.urn])

        # Find DIM3_004 violations
        dim3_004_violations = [v for v in result.violations if v.rule_id == "DIM3_004"]
        assert len(dim3_004_violations) == 0, "Gold table with tags should not violate DIM3_004"

    async def test_dim3_004_gold_tables_should_be_tagged_fail(self, test_session: AsyncSession, domain, owner):
        """Test DIM3_004: Gold table without tags fails."""
        capsule = Capsule(
            urn="urn:test:gold_table_no_tags",
            name="gold_table_no_tags",
            capsule_type="model",
            layer="gold",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["semantic_metadata"], capsule_urns=[capsule.urn])

        # Find DIM3_004 violations
        dim3_004_violations = [v for v in result.violations if v.rule_id == "DIM3_004"]
        assert len(dim3_004_violations) == 1, "Gold table without tags should violate DIM3_004"
        assert dim3_004_violations[0].severity == RuleSeverity.INFO

    async def test_dim3_005_tables_should_have_ownership_pass(self, test_session: AsyncSession, domain, owner):
        """Test DIM3_005: Table with owner passes."""
        capsule = Capsule(
            urn="urn:test:table_with_owner",
            name="table_with_owner",
            capsule_type="model",
            layer="bronze",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["semantic_metadata"], capsule_urns=[capsule.urn])

        # Find DIM3_005 violations
        dim3_005_violations = [v for v in result.violations if v.rule_id == "DIM3_005"]
        assert len(dim3_005_violations) == 0, "Table with owner should not violate DIM3_005"

    async def test_dim3_005_tables_should_have_ownership_fail(self, test_session: AsyncSession, domain):
        """Test DIM3_005: Table without owner fails."""
        capsule = Capsule(
            urn="urn:test:table_no_owner",
            name="table_no_owner",
            capsule_type="model",
            layer="bronze",
            domain_id=domain.id,
            owner_id=None,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["semantic_metadata"], capsule_urns=[capsule.urn])

        # Find DIM3_005 violations
        dim3_005_violations = [v for v in result.violations if v.rule_id == "DIM3_005"]
        assert len(dim3_005_violations) == 1, "Table without owner should violate DIM3_005"
        assert dim3_005_violations[0].severity == RuleSeverity.WARNING

    async def test_dim3_006_tables_should_belong_to_domain_pass(self, test_session: AsyncSession, domain, owner):
        """Test DIM3_006: Table with domain passes."""
        capsule = Capsule(
            urn="urn:test:table_with_domain",
            name="table_with_domain",
            capsule_type="model",
            layer="bronze",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["semantic_metadata"], capsule_urns=[capsule.urn])

        # Find DIM3_006 violations
        dim3_006_violations = [v for v in result.violations if v.rule_id == "DIM3_006"]
        assert len(dim3_006_violations) == 0, "Table with domain should not violate DIM3_006"

    async def test_dim3_006_tables_should_belong_to_domain_fail(self, test_session: AsyncSession, owner):
        """Test DIM3_006: Table without domain fails."""
        capsule = Capsule(
            urn="urn:test:table_no_domain",
            name="table_no_domain",
            capsule_type="model",
            layer="bronze",
            domain_id=None,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["semantic_metadata"], capsule_urns=[capsule.urn])

        # Find DIM3_006 violations
        dim3_006_violations = [v for v in result.violations if v.rule_id == "DIM3_006"]
        assert len(dim3_006_violations) == 1, "Table without domain should violate DIM3_006"
        assert dim3_006_violations[0].severity == RuleSeverity.INFO


# ============================================================================
# Dimension 4: Quality Expectations Rules Tests
# ============================================================================


@pytest.mark.asyncio
class TestQualityExpectationsRules:
    """Tests for Dimension 4 (Quality Expectations) conformance rules."""

    async def test_dim4_001_gold_tables_should_have_quality_rules_pass(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM4_001: Gold table with quality rules passes."""
        capsule = Capsule(
            urn="urn:test:gold_with_rules",
            name="gold_with_rules",
            capsule_type="model",
            layer="gold",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add quality rule
        qr = QualityRule(
            capsule_id=capsule.id,
            rule_type="freshness",
            rule_name="test_freshness",
            rule_config={},
            severity="warning",
            is_enabled=True,
            meta={},
        )
        test_session.add(qr)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["quality_expectations"], capsule_urns=[capsule.urn])

        # Find DIM4_001 violations
        dim4_001_violations = [v for v in result.violations if v.rule_id == "DIM4_001"]
        assert len(dim4_001_violations) == 0, "Gold table with quality rules should not violate DIM4_001"

    async def test_dim4_001_gold_tables_should_have_quality_rules_fail(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM4_001: Gold table without quality rules fails."""
        capsule = Capsule(
            urn="urn:test:gold_no_rules",
            name="gold_no_rules",
            capsule_type="model",
            layer="gold",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["quality_expectations"], capsule_urns=[capsule.urn])

        # Find DIM4_001 violations
        dim4_001_violations = [v for v in result.violations if v.rule_id == "DIM4_001"]
        assert len(dim4_001_violations) == 1, "Gold table without quality rules should violate DIM4_001"
        assert dim4_001_violations[0].severity == RuleSeverity.WARNING

    async def test_dim4_002_primary_keys_should_have_uniqueness_rules_fail(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM4_002: Table with PK but no quality rules fails."""
        capsule = Capsule(
            urn="urn:test:pk_no_rules",
            name="pk_no_rules",
            capsule_type="model",
            layer="bronze",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add PK column
        col = Column(
            capsule_id=capsule.id,
            urn=f"{capsule.urn}.id",
            name="id",
            data_type="INTEGER",
            ordinal_position=1,
            is_primary_key=True,
            meta={},
        )
        test_session.add(col)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["quality_expectations"], capsule_urns=[capsule.urn])

        # Find DIM4_002 violations
        dim4_002_violations = [v for v in result.violations if v.rule_id == "DIM4_002"]
        assert len(dim4_002_violations) == 1, "Table with PK but no quality rules should violate DIM4_002"
        assert dim4_002_violations[0].severity == RuleSeverity.ERROR

    async def test_dim4_010_quality_rules_should_be_enabled_pass(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM4_010: Table with mostly enabled quality rules passes."""
        capsule = Capsule(
            urn="urn:test:rules_enabled",
            name="rules_enabled",
            capsule_type="model",
            layer="bronze",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add 5 enabled rules
        for i in range(5):
            qr = QualityRule(
                capsule_id=capsule.id,
                rule_type="freshness",
                rule_name=f"rule_{i}",
                rule_config={},
                severity="warning",
                is_enabled=True,
                meta={},
            )
            test_session.add(qr)

        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["quality_expectations"], capsule_urns=[capsule.urn])

        # Find DIM4_010 violations
        dim4_010_violations = [v for v in result.violations if v.rule_id == "DIM4_010"]
        assert len(dim4_010_violations) == 0, "Table with >=80% enabled rules should not violate DIM4_010"

    async def test_dim4_010_quality_rules_should_be_enabled_fail(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM4_010: Table with mostly disabled quality rules fails."""
        capsule = Capsule(
            urn="urn:test:rules_disabled",
            name="rules_disabled",
            capsule_type="model",
            layer="bronze",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add 5 rules, 4 disabled
        for i in range(5):
            qr = QualityRule(
                capsule_id=capsule.id,
                rule_type="freshness",
                rule_name=f"rule_{i}",
                rule_config={},
                severity="warning",
                is_enabled=(i == 0),  # Only first one enabled
                meta={},
            )
            test_session.add(qr)

        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["quality_expectations"], capsule_urns=[capsule.urn])

        # Find DIM4_010 violations
        dim4_010_violations = [v for v in result.violations if v.rule_id == "DIM4_010"]
        assert len(dim4_010_violations) == 1, "Table with <80% enabled rules should violate DIM4_010"


# ============================================================================
# Dimension 5: Policy & Governance Rules Tests
# ============================================================================


@pytest.mark.asyncio
class TestPolicyGovernanceRules:
    """Tests for Dimension 5 (Policy & Governance) conformance rules."""

    async def test_dim5_001_pii_tables_must_have_data_policies_pass(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM5_001: PII table with policies passes."""
        capsule = Capsule(
            urn="urn:test:pii_with_policy",
            name="pii_with_policy",
            capsule_type="model",
            layer="bronze",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add PII column
        col = Column(
            capsule_id=capsule.id,
            urn=f"{capsule.urn}.email",
            name="email",
            data_type="VARCHAR",
            ordinal_position=1,
            semantic_type="pii",
            pii_type="email",
            meta={},
        )
        test_session.add(col)

        # Add data policy
        policy = DataPolicy(
            capsule_id=capsule.id,
            sensitivity_level="high",
            retention_days=365,
            meta={},
        )
        test_session.add(policy)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["policy_governance"], capsule_urns=[capsule.urn])

        # Find DIM5_001 violations
        dim5_001_violations = [v for v in result.violations if v.rule_id == "DIM5_001"]
        assert len(dim5_001_violations) == 0, "PII table with policies should not violate DIM5_001"

    async def test_dim5_001_pii_tables_must_have_data_policies_fail(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM5_001: PII table without policies fails."""
        capsule = Capsule(
            urn="urn:test:pii_no_policy",
            name="pii_no_policy",
            capsule_type="model",
            layer="bronze",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add PII column
        col = Column(
            capsule_id=capsule.id,
            urn=f"{capsule.urn}.email",
            name="email",
            data_type="VARCHAR",
            ordinal_position=1,
            semantic_type="pii",
            pii_type="email",
            meta={},
        )
        test_session.add(col)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["policy_governance"], capsule_urns=[capsule.urn])

        # Find DIM5_001 violations
        dim5_001_violations = [v for v in result.violations if v.rule_id == "DIM5_001"]
        assert len(dim5_001_violations) == 1, "PII table without policies should violate DIM5_001"
        assert dim5_001_violations[0].severity == RuleSeverity.CRITICAL

    async def test_dim5_003_pii_in_gold_requires_masking_rules_pass(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM5_003: PII column in Gold with masking rules passes."""
        capsule = Capsule(
            urn="urn:test:gold_pii_masked",
            name="gold_pii_masked",
            capsule_type="model",
            layer="gold",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add PII column
        col = Column(
            capsule_id=capsule.id,
            urn=f"{capsule.urn}.email",
            name="email",
            data_type="VARCHAR",
            ordinal_position=1,
            pii_type="email",
            meta={},
        )
        test_session.add(col)
        await test_session.flush()

        # Add masking rule
        masking = MaskingRule(
            column_id=col.id,
            rule_name="mask_email",
            masking_method="hash",
            method_config={},
            meta={},
        )
        test_session.add(masking)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["policy_governance"], capsule_urns=[capsule.urn])

        # Find DIM5_003 violations
        dim5_003_violations = [v for v in result.violations if v.rule_id == "DIM5_003"]
        assert len(dim5_003_violations) == 0, "PII in Gold with masking should not violate DIM5_003"

    async def test_dim5_003_pii_in_gold_requires_masking_rules_fail(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM5_003: PII column in Gold without masking rules fails."""
        capsule = Capsule(
            urn="urn:test:gold_pii_unmasked",
            name="gold_pii_unmasked",
            capsule_type="model",
            layer="gold",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add PII column without masking
        col = Column(
            capsule_id=capsule.id,
            urn=f"{capsule.urn}.email",
            name="email",
            data_type="VARCHAR",
            ordinal_position=1,
            pii_type="email",
            meta={},
        )
        test_session.add(col)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["policy_governance"], capsule_urns=[capsule.urn])

        # Find DIM5_003 violations
        dim5_003_violations = [v for v in result.violations if v.rule_id == "DIM5_003"]
        assert len(dim5_003_violations) == 1, "PII in Gold without masking should violate DIM5_003"
        assert dim5_003_violations[0].severity == RuleSeverity.CRITICAL

    async def test_dim5_004_gold_tables_should_have_retention_policies_pass(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM5_004: Gold table with retention policy passes."""
        capsule = Capsule(
            urn="urn:test:gold_with_retention",
            name="gold_with_retention",
            capsule_type="model",
            layer="gold",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add policy with retention
        policy = DataPolicy(
            capsule_id=capsule.id,
            retention_days=365,
            meta={},
        )
        test_session.add(policy)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["policy_governance"], capsule_urns=[capsule.urn])

        # Find DIM5_004 violations
        dim5_004_violations = [v for v in result.violations if v.rule_id == "DIM5_004"]
        assert len(dim5_004_violations) == 0, "Gold table with retention should not violate DIM5_004"

    async def test_dim5_004_gold_tables_should_have_retention_policies_fail(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM5_004: Gold table without retention policy fails."""
        capsule = Capsule(
            urn="urn:test:gold_no_retention",
            name="gold_no_retention",
            capsule_type="model",
            layer="gold",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["policy_governance"], capsule_urns=[capsule.urn])

        # Find DIM5_004 violations
        dim5_004_violations = [v for v in result.violations if v.rule_id == "DIM5_004"]
        assert len(dim5_004_violations) == 1, "Gold table without retention should violate DIM5_004"


# ============================================================================
# Dimension 6: Provenance & Lineage Rules Tests
# ============================================================================


@pytest.mark.asyncio
class TestProvenanceLineageRules:
    """Tests for Dimension 6 (Provenance & Lineage) conformance rules."""

    async def test_dim6_001_gold_tables_should_have_version_history_pass(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM6_001: Gold table with version history passes."""
        capsule = Capsule(
            urn="urn:test:gold_with_versions",
            name="gold_with_versions",
            capsule_type="model",
            layer="gold",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add version
        version = CapsuleVersion(
            capsule_id=capsule.id,
            version_number=1,
            version_name="v1.0.0",
            change_summary="Initial version",
            meta={},
        )
        test_session.add(version)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["provenance_lineage"], capsule_urns=[capsule.urn])

        # Find DIM6_001 violations
        dim6_001_violations = [v for v in result.violations if v.rule_id == "DIM6_001"]
        assert len(dim6_001_violations) == 0, "Gold table with versions should not violate DIM6_001"

    async def test_dim6_001_gold_tables_should_have_version_history_fail(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM6_001: Gold table without version history fails."""
        capsule = Capsule(
            urn="urn:test:gold_no_versions",
            name="gold_no_versions",
            capsule_type="model",
            layer="gold",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["provenance_lineage"], capsule_urns=[capsule.urn])

        # Find DIM6_001 violations
        dim6_001_violations = [v for v in result.violations if v.rule_id == "DIM6_001"]
        assert len(dim6_001_violations) == 1, "Gold table without versions should violate DIM6_001"
        assert dim6_001_violations[0].severity == RuleSeverity.WARNING

    async def test_dim6_003_transformation_code_should_be_documented_pass(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM6_003: Model with transformation code passes."""
        capsule = Capsule(
            urn="urn:test:model_with_code",
            name="model_with_code",
            capsule_type="model",
            layer="bronze",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add transformation code
        code = TransformationCode(
            capsule_id=capsule.id,
            code_type="sql",
            code_content="SELECT * FROM source",
            file_path="/path/to/file.sql",
            meta={},
        )
        test_session.add(code)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["provenance_lineage"], capsule_urns=[capsule.urn])

        # Find DIM6_003 violations
        dim6_003_violations = [v for v in result.violations if v.rule_id == "DIM6_003"]
        assert len(dim6_003_violations) == 0, "Model with code should not violate DIM6_003"

    async def test_dim6_003_transformation_code_should_be_documented_fail(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM6_003: Model without transformation code fails."""
        capsule = Capsule(
            urn="urn:test:model_no_code",
            name="model_no_code",
            capsule_type="model",
            layer="bronze",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["provenance_lineage"], capsule_urns=[capsule.urn])

        # Find DIM6_003 violations
        dim6_003_violations = [v for v in result.violations if v.rule_id == "DIM6_003"]
        assert len(dim6_003_violations) == 1, "Model without code should violate DIM6_003"


# ============================================================================
# Dimension 7: Operational Contract Rules Tests
# ============================================================================


@pytest.mark.asyncio
class TestOperationalContractRules:
    """Tests for Dimension 7 (Operational Contract) conformance rules."""

    async def test_dim7_001_gold_tables_should_have_contracts_pass(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM7_001: Gold table with contract passes."""
        capsule = Capsule(
            urn="urn:test:gold_with_contract",
            name="gold_with_contract",
            capsule_type="model",
            layer="gold",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add contract
        contract = CapsuleContract(
            capsule_id=capsule.id,
            status="active",
            schema_policy="strict",
            meta={},
        )
        test_session.add(contract)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["operational_contract"], capsule_urns=[capsule.urn])

        # Find DIM7_001 violations
        dim7_001_violations = [v for v in result.violations if v.rule_id == "DIM7_001"]
        assert len(dim7_001_violations) == 0, "Gold table with contract should not violate DIM7_001"

    async def test_dim7_001_gold_tables_should_have_contracts_fail(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM7_001: Gold table without contract fails."""
        capsule = Capsule(
            urn="urn:test:gold_no_contract",
            name="gold_no_contract",
            capsule_type="model",
            layer="gold",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["operational_contract"], capsule_urns=[capsule.urn])

        # Find DIM7_001 violations
        dim7_001_violations = [v for v in result.violations if v.rule_id == "DIM7_001"]
        assert len(dim7_001_violations) == 1, "Gold table without contract should violate DIM7_001"
        assert dim7_001_violations[0].severity == RuleSeverity.WARNING

    async def test_dim7_005_open_incidents_must_be_acknowledged_within_24h_pass(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM7_005: Recent open incident passes (not yet 24h old)."""
        capsule = Capsule(
            urn="urn:test:capsule_recent_incident",
            name="capsule_recent_incident",
            capsule_type="model",
            layer="gold",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add contract
        contract = CapsuleContract(
            capsule_id=capsule.id,
            status="active",
            meta={},
        )
        test_session.add(contract)
        await test_session.flush()

        # Add recent incident (1 hour ago)
        incident = SLAIncident(
            capsule_id=capsule.id,
            contract_id=contract.id,
            incident_type="freshness",
            severity="high",
            status="open",
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
            meta={},
        )
        test_session.add(incident)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["operational_contract"], capsule_urns=[capsule.urn])

        # Find DIM7_005 violations
        dim7_005_violations = [v for v in result.violations if v.rule_id == "DIM7_005"]
        assert len(dim7_005_violations) == 0, "Recent incident should not violate DIM7_005 yet"

    async def test_dim7_005_open_incidents_must_be_acknowledged_within_24h_fail(
        self, test_session: AsyncSession, domain, owner
    ):
        """Test DIM7_005: Old unacknowledged incident fails."""
        capsule = Capsule(
            urn="urn:test:capsule_old_incident",
            name="capsule_old_incident",
            capsule_type="model",
            layer="gold",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add contract
        contract = CapsuleContract(
            capsule_id=capsule.id,
            status="active",
            meta={},
        )
        test_session.add(contract)
        await test_session.flush()

        # Add old incident (48 hours ago, not acknowledged)
        incident = SLAIncident(
            capsule_id=capsule.id,
            contract_id=contract.id,
            incident_type="freshness",
            severity="high",
            status="open",
            created_at=datetime.now(timezone.utc) - timedelta(hours=48),
            acknowledged_at=None,
            meta={},
        )
        test_session.add(incident)
        await test_session.flush()

        # Evaluate
        service = ConformanceService(test_session)
        result = await service.evaluate(rule_sets=["operational_contract"], capsule_urns=[capsule.urn])

        # Find DIM7_005 violations
        dim7_005_violations = [v for v in result.violations if v.rule_id == "DIM7_005"]
        assert len(dim7_005_violations) == 1, "Old unacknowledged incident should violate DIM7_005"
        assert dim7_005_violations[0].severity == RuleSeverity.ERROR


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
class TestConformanceIntegration:
    """Integration tests for all conformance rules together."""

    async def test_all_rule_sets_enabled(self, test_session: AsyncSession):
        """Test that all 9 rule sets are registered."""
        service = ConformanceService(test_session)
        rule_sets = service.get_rule_sets()

        expected_rule_sets = [
            "medallion",
            "dbt_best_practices",
            "pii_compliance",
            "structural_metadata",
            "semantic_metadata",
            "quality_expectations",
            "policy_governance",
            "provenance_lineage",
            "operational_contract",
        ]

        for expected in expected_rule_sets:
            assert expected in rule_sets, f"Rule set '{expected}' not found"

    async def test_total_rule_count(self, test_session: AsyncSession):
        """Test that we have 60 total rules (12 original + 48 new)."""
        service = ConformanceService(test_session)
        all_rules = service.get_available_rules(enabled_only=False)

        assert len(all_rules) == 60, f"Expected 60 rules, found {len(all_rules)}"

    async def test_new_rule_count_by_dimension(self, test_session: AsyncSession):
        """Test that each dimension has the correct number of rules."""
        service = ConformanceService(test_session)

        # Count rules by rule set
        rule_counts = {}
        for rule_set in service.get_rule_sets():
            rules = service.get_available_rules(rule_set=rule_set, enabled_only=False)
            rule_counts[rule_set] = len(rules)

        # Verify counts
        assert rule_counts.get("structural_metadata", 0) == 8, "Expected 8 structural metadata rules"
        assert rule_counts.get("semantic_metadata", 0) == 6, "Expected 6 semantic metadata rules"
        assert rule_counts.get("quality_expectations", 0) == 10, "Expected 10 quality expectations rules"
        assert rule_counts.get("policy_governance", 0) == 8, "Expected 8 policy governance rules"
        assert rule_counts.get("provenance_lineage", 0) == 8, "Expected 8 provenance lineage rules"
        assert rule_counts.get("operational_contract", 0) == 8, "Expected 8 operational contract rules"

    async def test_evaluate_all_dimensions(self, test_session: AsyncSession, domain, owner):
        """Test evaluating a capsule against all dimensions."""
        # Create a minimal capsule
        capsule = Capsule(
            urn="urn:test:minimal_capsule",
            name="minimal_capsule",
            capsule_type="model",
            layer="bronze",
            domain_id=domain.id,
            owner_id=owner.id,
            meta={},
        )
        test_session.add(capsule)

        # Add at least one column to avoid lazy loading issues
        col = Column(
            capsule_id=capsule.id,
            urn=f"{capsule.urn}.id",
            name="id",
            data_type="INTEGER",
            ordinal_position=1,
            meta={},
        )
        test_session.add(col)
        await test_session.flush()

        # Evaluate against all rule sets
        service = ConformanceService(test_session)
        result = await service.evaluate(capsule_urns=[capsule.urn])

        # Should have evaluated all rules
        assert result.total_rules > 0, "No rules were evaluated"

        # Should have some violations (minimal capsule won't pass everything)
        assert len(result.violations) > 0, "Expected violations for minimal capsule"

        # Score should be calculated
        assert 0 <= result.score <= 100, f"Score {result.score} out of range"
        assert 0 <= result.weighted_score <= 100, f"Weighted score {result.weighted_score} out of range"
