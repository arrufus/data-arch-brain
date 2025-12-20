"""Seed example data capsules demonstrating all 7 dimensions.

This script creates comprehensive example data capsules based on the
jaffle_shop example from the design document. Each capsule demonstrates
all 7 dimensions of the Data Capsule model.

Usage:
    python -m scripts.seed_example_capsules
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.models import (
    BusinessTerm,
    Capsule,
    CapsuleBusinessTerm,
    CapsuleContract,
    CapsuleIndex,
    CapsuleLineage,
    CapsuleVersion,
    Column,
    ColumnBusinessTerm,
    ColumnConstraint,
    ColumnProfile,
    DataPolicy,
    Domain,
    MaskingRule,
    Owner,
    QualityRule,
    TransformationCode,
    ValueDomain,
)


async def create_domain_and_owner(db: AsyncSession):
    """Create example domain and owner."""
    # Create owner first (domain needs owner_id)
    owner = Owner(
        name="Data Platform Team",
        owner_type="team",
        email="data-platform@company.com",
        slack_channel="#data-platform",
        meta={},
    )
    db.add(owner)
    await db.flush()

    # Create domain
    domain = Domain(
        name="order_management",
        description="Domain for order and customer transaction data",
        owner_id=owner.id,
        meta={},
    )
    db.add(domain)
    await db.flush()

    return domain, owner


async def create_business_terms(db: AsyncSession, domain_id):
    """Create business terms."""
    terms = []

    # Revenue term
    revenue_term = BusinessTerm(
        term_name="revenue",
        display_name="Revenue",
        definition="Total monetary value received from sales transactions",
        approval_status="approved",
        domain_id=domain_id,
        category="financial",
        meta={},
    )
    db.add(revenue_term)
    terms.append(revenue_term)

    # Transaction term
    transaction_term = BusinessTerm(
        term_name="transaction",
        display_name="Transaction",
        definition="A business event representing an exchange of value",
        approval_status="approved",
        domain_id=domain_id,
        category="business_process",
        meta={},
    )
    db.add(transaction_term)
    terms.append(transaction_term)

    # Customer Purchase term
    customer_purchase_term = BusinessTerm(
        term_name="customer_purchase",
        display_name="Customer Purchase",
        definition="An order placed by a customer for products or services",
        approval_status="approved",
        domain_id=domain_id,
        category="business_process",
        meta={},
    )
    db.add(customer_purchase_term)
    terms.append(customer_purchase_term)

    await db.flush()
    return terms


async def create_value_domains(db: AsyncSession):
    """Create value domains."""
    domains = []

    # Currency amount domain
    currency_domain = ValueDomain(
        domain_name="currency_amount",
        description="Monetary value in USD",
        domain_type="range",
        min_value="0.00",
        max_value="999999999.99",
        pattern_regex=r"^\d+\.\d{2}$",
        pattern_description="Currency format with 2 decimal places",
        meta={"currency": "USD", "decimal_places": 2},
    )
    db.add(currency_domain)
    domains.append(currency_domain)

    # Order status enum
    status_domain = ValueDomain(
        domain_name="order_status_enum",
        description="Valid order status values",
        domain_type="enum",
        allowed_values=[
            {"code": "pending", "label": "Pending", "description": "Order placed, awaiting confirmation"},
            {"code": "confirmed", "label": "Confirmed", "description": "Order confirmed, preparing shipment"},
            {"code": "shipped", "label": "Shipped", "description": "Order shipped to customer"},
            {"code": "delivered", "label": "Delivered", "description": "Order delivered successfully"},
            {"code": "cancelled", "label": "Cancelled", "description": "Order cancelled"},
        ],
        meta={},
    )
    db.add(status_domain)
    domains.append(status_domain)

    await db.flush()
    return domains


async def create_stg_customers(db: AsyncSession, domain_id, owner_id):
    """Create stg_customers capsule - Dimension 1 staging layer."""
    # Create capsule
    capsule = Capsule(
        urn="urn:dcs:dbt:model:jaffle_shop.staging:stg_customers",
        name="stg_customers",
        capsule_type="model",
        layer="bronze",
        description="Staged customer master data from source system",
        domain_id=domain_id,
        owner_id=owner_id,
        schema_name="staging",
        materialization="view",
        meta={
            "platform": "dbt",
            "project": "jaffle_shop",
            "dbt_model_type": "staging",
        },
    )
    db.add(capsule)
    await db.flush()

    # Dimension 2: Structural Metadata - Columns
    customer_id_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.customer_id",
        name="customer_id",
        data_type="STRING",
        ordinal_position=1,
        is_nullable=False,
        description="Unique customer identifier",
        meta={},
    )
    db.add(customer_id_col)

    first_name_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.first_name",
        name="first_name",
        data_type="STRING",
        ordinal_position=2,
        is_nullable=False,
        description="Customer first name",
        meta={},
    )
    db.add(first_name_col)

    email_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.email",
        name="email",
        data_type="STRING",
        ordinal_position=3,
        is_nullable=True,
        description="Customer email address",
        meta={},
    )
    db.add(email_col)

    await db.flush()

    # Dimension 2: Constraints
    pk_constraint = ColumnConstraint(
        column_id=customer_id_col.id,
        constraint_type="primary_key",
        constraint_name="pk_stg_customers",
        is_enforced=True,
        meta={},
    )
    db.add(pk_constraint)

    # Dimension 2: Index
    idx = CapsuleIndex(
        capsule_id=capsule.id,
        index_name="idx_customers_email",
        index_type="btree",
        column_names=["email"],
        is_unique=False,
        meta={},
    )
    db.add(idx)

    # Dimension 4: Column profiles
    customer_profile = ColumnProfile(
        column_id=customer_id_col.id,
        total_count=1000,
        null_count=0,
        null_percentage=Decimal("0.00"),
        distinct_count=1000,
        unique_percentage=Decimal("100.00"),
        completeness_score=Decimal("100.00"),
        validity_score=Decimal("100.00"),
        uniqueness_score=Decimal("100.00"),
        profiled_at=datetime.now(),
        meta={},
    )
    db.add(customer_profile)

    # Dimension 4: Quality rules
    unique_rule = QualityRule(
        column_id=customer_id_col.id,
        rule_type="unique",
        rule_name="unique_customer_id",
        rule_config={},
        severity="error",
        blocking=True,
        is_enabled=True,
        meta={},
    )
    db.add(unique_rule)

    # Dimension 5: Data policies
    policy = DataPolicy(
        capsule_id=capsule.id,
        sensitivity_level="confidential",
        classification_tags=["gdpr", "ccpa", "pii"],
        retention_period=timedelta(days=2555),  # 7 years
        deletion_action="archive",
        requires_masking=True,
        compliance_frameworks=["GDPR", "CCPA"],
        audit_log_required=True,
        meta={"policy_name": "customer_data_policy", "classification": "internal"},
    )
    db.add(policy)

    # Dimension 5: Masking rule for email
    masking_rule = MaskingRule(
        column_id=email_col.id,
        rule_name="mask_customer_email",
        masking_method="partial_redaction",
        method_config={"algorithm": "partial", "mask_pattern": "***@***.com"},
        applies_to_roles=["analyst", "external"],
        meta={},
    )
    db.add(masking_rule)

    # Dimension 6: Version
    version = CapsuleVersion(
        capsule_id=capsule.id,
        version_number=1,
        version_name="v1.0.0",
        schema_snapshot={"columns": 3, "indexes": 1},
        change_type="created",
        breaking_change=False,
        is_current=True,
        git_commit_sha="a1b2c3d4",
        git_repository="github.com/org/jaffle_shop",
        meta={},
    )
    db.add(version)

    # Dimension 7: Contract
    contract = CapsuleContract(
        capsule_id=capsule.id,
        contract_version="1.0",
        contract_status="active",
        freshness_sla=timedelta(hours=24),
        completeness_sla=Decimal("99.50"),
        quality_score_sla=Decimal("95.00"),
        support_level="business_hours",
        support_contact="data-platform@company.com",
        support_slack_channel="#data-platform",
        meta={},
    )
    db.add(contract)

    await db.flush()
    return capsule, [customer_id_col, first_name_col, email_col]


async def create_stg_orders(
    db: AsyncSession, domain_id, owner_id, business_terms, value_domains, stg_customers_capsule, customer_id_col
):
    """Create stg_orders capsule - Main example with all 7 dimensions."""
    # Create placeholder source capsules for lineage demonstration
    raw_orders_capsule = Capsule(
        urn="urn:dcs:dbt:source:jaffle_shop.raw:raw_orders",
        name="raw_orders",
        capsule_type="source",
        layer="raw",
        description="Raw orders data from source system",
        domain_id=domain_id,
        owner_id=owner_id,
        meta={"platform": "dbt", "project": "jaffle_shop"},
    )
    db.add(raw_orders_capsule)

    raw_payments_capsule = Capsule(
        urn="urn:dcs:dbt:source:jaffle_shop.raw:raw_payments",
        name="raw_payments",
        capsule_type="source",
        layer="raw",
        description="Raw payments data from source system",
        domain_id=domain_id,
        owner_id=owner_id,
        meta={"platform": "dbt", "project": "jaffle_shop"},
    )
    db.add(raw_payments_capsule)
    await db.flush()

    # Create capsule
    capsule = Capsule(
        urn="urn:dcs:dbt:model:jaffle_shop.staging:stg_orders",
        name="stg_orders",
        capsule_type="model",
        layer="bronze",
        description="Staged order transactions from source system",
        domain_id=domain_id,
        owner_id=owner_id,
        schema_name="staging",
        materialization="table",
        meta={
            "platform": "dbt",
            "project": "jaffle_shop",
            "dbt_model_type": "staging",
        },
    )
    db.add(capsule)
    await db.flush()

    # Dimension 2: Structural Metadata - Columns
    order_id_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.order_id",
        name="order_id",
        data_type="STRING",
        ordinal_position=1,
        is_nullable=False,
        description="Unique order identifier",
        meta={},
    )
    db.add(order_id_col)

    customer_ref_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.customer_id",
        name="customer_id",
        data_type="STRING",
        ordinal_position=2,
        is_nullable=False,
        description="Reference to customer",
        meta={},
    )
    db.add(customer_ref_col)

    order_total_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.order_total",
        name="order_total",
        data_type="DECIMAL(18,2)",
        ordinal_position=3,
        is_nullable=False,
        description="Total order value including tax and shipping",
        unit_of_measure="USD",
        value_domain=value_domains[0].domain_name,  # currency_amount
        meta={},
    )
    db.add(order_total_col)

    order_status_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.order_status",
        name="order_status",
        data_type="STRING",
        ordinal_position=4,
        is_nullable=False,
        description="Current status of the order",
        value_domain=value_domains[1].domain_name,  # order_status_enum
        meta={},
    )
    db.add(order_status_col)

    order_date_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.order_date",
        name="order_date",
        data_type="DATE",
        ordinal_position=5,
        is_nullable=False,
        description="Date when order was placed",
        meta={},
    )
    db.add(order_date_col)

    await db.flush()

    # Dimension 2: Constraints
    pk_constraint = ColumnConstraint(
        column_id=order_id_col.id,
        constraint_type="primary_key",
        constraint_name="pk_stg_orders",
        is_enforced=True,
        meta={},
    )
    db.add(pk_constraint)

    fk_constraint = ColumnConstraint(
        column_id=customer_ref_col.id,
        constraint_type="foreign_key",
        constraint_name="fk_orders_customer",
        referenced_table_urn=stg_customers_capsule.urn,
        referenced_column_urn=customer_id_col.urn,
        on_delete_action="RESTRICT",
        is_enforced=True,
        meta={},
    )
    db.add(fk_constraint)

    check_constraint = ColumnConstraint(
        column_id=order_total_col.id,
        constraint_type="check",
        constraint_name="chk_order_total_positive",
        check_expression="order_total >= 0",
        is_enforced=True,
        meta={},
    )
    db.add(check_constraint)

    # Dimension 2: Indexes
    customer_idx = CapsuleIndex(
        capsule_id=capsule.id,
        index_name="idx_orders_customer",
        index_type="btree",
        column_names=["customer_id"],
        is_unique=False,
        meta={},
    )
    db.add(customer_idx)

    date_idx = CapsuleIndex(
        capsule_id=capsule.id,
        index_name="idx_orders_date",
        index_type="btree",
        column_names=["order_date"],
        is_unique=False,
        meta={},
    )
    db.add(date_idx)

    # Dimension 3: Business Terms
    for term in business_terms:
        capsule_term = CapsuleBusinessTerm(
            capsule_id=capsule.id,
            business_term_id=term.id,
            relationship_type="implements",
            added_by="seed_script",
            meta={},
        )
        db.add(capsule_term)

    # Link order_total to revenue term
    col_term = ColumnBusinessTerm(
        column_id=order_total_col.id,
        business_term_id=business_terms[0].id,  # revenue
        relationship_type="measures",
        added_by="seed_script",
        meta={},
    )
    db.add(col_term)

    # Dimension 4: Column Profiles
    order_id_profile = ColumnProfile(
        column_id=order_id_col.id,
        total_count=50000,
        null_count=0,
        null_percentage=Decimal("0.00"),
        distinct_count=50000,
        unique_percentage=Decimal("100.00"),
        completeness_score=Decimal("100.00"),
        validity_score=Decimal("100.00"),
        uniqueness_score=Decimal("100.00"),
        profiled_at=datetime.now(),
        meta={},
    )
    db.add(order_id_profile)

    order_total_profile = ColumnProfile(
        column_id=order_total_col.id,
        total_count=50000,
        null_count=0,
        null_percentage=Decimal("0.00"),
        min_value=Decimal("5.00"),
        max_value=Decimal("9999.99"),
        mean_value=Decimal("125.50"),
        median_value=Decimal("89.99"),
        completeness_score=Decimal("100.00"),
        validity_score=Decimal("98.50"),
        uniqueness_score=Decimal("85.00"),
        profiled_at=datetime.now(),
        meta={},
    )
    db.add(order_total_profile)

    # Dimension 4: Quality Rules
    unique_order_rule = QualityRule(
        column_id=order_id_col.id,
        rule_type="unique",
        rule_name="unique_order_id",
        rule_config={},
        severity="error",
        blocking=True,
        is_enabled=True,
        meta={},
    )
    db.add(unique_order_rule)

    range_check_rule = QualityRule(
        column_id=order_total_col.id,
        rule_type="range_check",
        rule_name="order_total_range",
        rule_config={"min": 0, "max": 1000000},
        expected_range_min=Decimal("0"),
        expected_range_max=Decimal("1000000.00"),
        severity="warning",
        is_enabled=True,
        meta={},
    )
    db.add(range_check_rule)

    freshness_rule = QualityRule(
        capsule_id=capsule.id,
        rule_type="freshness",
        rule_name="orders_freshness",
        rule_config={"max_age_hours": 4},
        severity="error",
        blocking=False,
        is_enabled=True,
        meta={},
    )
    db.add(freshness_rule)

    ref_integrity_rule = QualityRule(
        column_id=customer_ref_col.id,
        rule_type="referential_integrity",
        rule_name="valid_customer_ref",
        rule_config={
            "referenced_table": stg_customers_capsule.urn,
            "referenced_column": "customer_id",
        },
        severity="error",
        blocking=True,
        is_enabled=True,
        meta={},
    )
    db.add(ref_integrity_rule)

    # Dimension 5: Data Policies
    capsule_policy = DataPolicy(
        capsule_id=capsule.id,
        sensitivity_level="confidential",
        classification_tags=["sox", "gdpr", "financial"],
        retention_period=timedelta(days=2555),  # 7 years
        deletion_action="archive",
        allowed_regions=["US", "CA"],
        data_residency="US",
        cross_border_transfer=False,
        min_access_level="authenticated",
        allowed_roles=["data_analyst", "data_scientist", "finance_team"],
        requires_masking=True,
        compliance_frameworks=["SOX", "GDPR"],
        audit_log_required=True,
        meta={
            "policy_name": "orders_data_policy",
            "classification": "internal",
        },
    )
    db.add(capsule_policy)

    customer_masking = MaskingRule(
        column_id=customer_ref_col.id,
        rule_name="mask_customer_reference",
        masking_method="tokenization",
        method_config={"algorithm": "deterministic"},
        applies_to_roles=["non_production", "analytics_readonly"],
        meta={},
    )
    db.add(customer_masking)

    # Dimension 6: Lineage
    raw_orders_lineage = CapsuleLineage(
        source_urn=raw_orders_capsule.urn,
        target_urn=capsule.urn,
        source_id=raw_orders_capsule.id,
        target_id=capsule.id,
        edge_type="flows_to",
        transformation="sql_join",
        meta={},
    )
    db.add(raw_orders_lineage)

    raw_payments_lineage = CapsuleLineage(
        source_urn=raw_payments_capsule.urn,
        target_urn=capsule.urn,
        source_id=raw_payments_capsule.id,
        target_id=capsule.id,
        edge_type="flows_to",
        transformation="sql_join",
        meta={},
    )
    db.add(raw_payments_lineage)

    # Dimension 6: Transformation Code
    transformation = TransformationCode(
        capsule_id=capsule.id,
        language="sql",
        code_text="""
-- stg_orders.sql
SELECT
    order_id,
    customer_id,
    SUM(amount) as order_total,
    status as order_status,
    order_date
FROM {{ source('raw', 'raw_orders') }} o
LEFT JOIN {{ source('raw', 'raw_payments') }} p ON o.order_id = p.order_id
GROUP BY 1, 2, 4, 5
        """,
        file_path="models/staging/stg_orders.sql",
        git_commit_sha="a1b2c3d4",
        git_repository="github.com/org/jaffle_shop",
        upstream_references=[
            "{{ source('raw', 'raw_orders') }}",
            "{{ source('raw', 'raw_payments') }}",
        ],
        meta={},
    )
    db.add(transformation)

    # Dimension 6: Version History
    version_1 = CapsuleVersion(
        capsule_id=capsule.id,
        version_number=1,
        version_name="v2.0.0",
        schema_snapshot={"columns": 5, "indexes": 2, "constraints": 3},
        change_type="schema_change",
        change_summary="Changed order_status enum values",
        breaking_change=True,
        deployed_at=datetime(2024, 11, 1),
        deployed_by="data_platform_team",
        git_commit_sha="x1y2z3",
        git_repository="github.com/org/jaffle_shop",
        is_current=False,
        meta={},
    )
    db.add(version_1)

    version_2 = CapsuleVersion(
        capsule_id=capsule.id,
        version_number=2,
        version_name="v2.1.0",
        schema_snapshot={"columns": 5, "indexes": 2, "constraints": 3},
        change_type="schema_change",
        change_summary="Added order_total_usd column",
        breaking_change=False,
        deployed_at=datetime(2024, 12, 1),
        deployed_by="data_platform_team",
        git_commit_sha="a1b2c3d4",
        git_repository="github.com/org/jaffle_shop",
        is_current=True,
        meta={},
    )
    db.add(version_2)

    # Dimension 7: Operational Contract
    contract = CapsuleContract(
        capsule_id=capsule.id,
        contract_version="1.0",
        contract_status="active",
        # Freshness SLA
        freshness_sla=timedelta(hours=4),
        freshness_schedule="hourly",
        # Completeness SLA
        completeness_sla=Decimal("99.90"),
        expected_row_count_min=1000,
        expected_row_count_max=1000000,
        # Availability SLA
        availability_sla=Decimal("99.90"),
        max_downtime=timedelta(hours=1),
        # Quality SLA
        quality_score_sla=Decimal("95.00"),
        critical_quality_rules=["unique_order_id", "valid_customer_ref"],
        # Schema change policy
        schema_change_policy="backwards_compatible",
        breaking_change_notice_days=30,
        # Support
        support_level="business_hours",
        support_contact="data-platform-team@company.com",
        support_slack_channel="#data-platform",
        # Deprecation
        deprecation_policy="90_days_notice",
        # Known consumers
        known_consumers=[
            {"team": "analytics", "contact": "analytics@company.com", "use_case": "Daily revenue reporting"},
            {"team": "ml_platform", "contact": "ml@company.com", "use_case": "Order prediction model"},
        ],
        meta={},
    )
    db.add(contract)

    await db.flush()
    return capsule


async def create_orders_fact(db: AsyncSession, domain_id, owner_id, stg_orders_capsule):
    """Create orders_fact capsule - Gold layer downstream consumer."""
    # Create capsule
    capsule = Capsule(
        urn="urn:dcs:dbt:model:jaffle_shop.marts:orders_fact",
        name="orders_fact",
        capsule_type="model",
        layer="gold",
        description="Fact table for order analytics - aggregated and enriched order data",
        domain_id=domain_id,
        owner_id=owner_id,
        schema_name="marts",
        materialization="incremental",
        meta={
            "platform": "dbt",
            "project": "jaffle_shop",
            "dbt_model_type": "fact",
        },
    )
    db.add(capsule)
    await db.flush()

    # Create lineage from stg_orders
    lineage = CapsuleLineage(
        source_urn=stg_orders_capsule.urn,
        target_urn=capsule.urn,
        source_id=stg_orders_capsule.id,
        target_id=capsule.id,
        edge_type="flows_to",
        transformation="aggregation",
        meta={},
    )
    db.add(lineage)

    # Add basic columns
    order_key_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.order_key",
        name="order_key",
        data_type="STRING",
        ordinal_position=1,
        is_nullable=False,
        description="Surrogate key for order fact",
        meta={},
    )
    db.add(order_key_col)

    # Dimension 6: Version
    version = CapsuleVersion(
        capsule_id=capsule.id,
        version_number=1,
        version_name="v1.0.0",
        schema_snapshot={"columns": 1},
        change_type="created",
        breaking_change=False,
        is_current=True,
        git_commit_sha="b2c3d4e5",
        git_repository="github.com/org/jaffle_shop",
        meta={},
    )
    db.add(version)

    # Dimension 7: Contract
    contract = CapsuleContract(
        capsule_id=capsule.id,
        contract_version="1.0",
        contract_status="active",
        freshness_sla=timedelta(hours=6),
        quality_score_sla=Decimal("98.00"),
        support_level="critical",
        support_contact="analytics-team@company.com",
        meta={},
    )
    db.add(contract)

    await db.flush()
    return capsule


async def seed_examples():
    """Main function to seed example capsules."""
    async with async_session_maker() as db:
        try:
            print("🌱 Starting to seed example data capsules...")

            # Create domain and owner
            print("  Creating domain and owner...")
            domain, owner = await create_domain_and_owner(db)

            # Create business terms
            print("  Creating business terms...")
            business_terms = await create_business_terms(db, domain.id)

            # Create value domains
            print("  Creating value domains...")
            value_domains = await create_value_domains(db)

            # Create stg_customers
            print("  Creating stg_customers capsule (bronze layer)...")
            stg_customers, customer_cols = await create_stg_customers(db, domain.id, owner.id)

            # Create stg_orders (main example)
            print("  Creating stg_orders capsule (bronze layer) - Main example with all 7 dimensions...")
            stg_orders = await create_stg_orders(
                db, domain.id, owner.id, business_terms, value_domains, stg_customers, customer_cols[0]
            )

            # Create orders_fact
            print("  Creating orders_fact capsule (gold layer)...")
            orders_fact = await create_orders_fact(db, domain.id, owner.id, stg_orders)

            # Commit all changes
            await db.commit()

            print("✅ Successfully seeded example data capsules!")
            print("\nCreated capsules:")
            print(f"  1. {stg_customers.urn} (bronze layer)")
            print(f"  2. {stg_orders.urn} (bronze layer) ⭐ Full 7-dimension example")
            print(f"  3. {orders_fact.urn} (gold layer)")
            print("\nYou can now view these examples via:")
            print("  - API: GET /api/v1/capsules")
            print("  - Catalog: GET /api/v1/catalog/capsules")
            print("  - Swagger UI: http://localhost:8000/api/v1/docs")

        except Exception as e:
            await db.rollback()
            print(f"❌ Error seeding examples: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_examples())
