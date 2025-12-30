"""Seed finance vertical data capsules with all 7 dimensions, data products, and tags.

This script creates comprehensive example data capsules for the finance domain,
demonstrating all 7 dimensions of the Data Capsule model, data products, and
classification tags.

Usage:
    python -m scripts.seed_finance_capsules
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
    CapsuleDataProduct,
    CapsuleIndex,
    CapsuleLineage,
    CapsuleTag,
    CapsuleVersion,
    Column,
    ColumnBusinessTerm,
    ColumnConstraint,
    ColumnProfile,
    DataPolicy,
    DataProduct,
    Domain,
    MaskingRule,
    Owner,
    QualityRule,
    Tag,
    TransformationCode,
    ValueDomain,
)


async def create_finance_domain_and_owner(db: AsyncSession):
    """Create finance domain and owner."""
    # Create owner
    owner = Owner(
        name="Finance Data Team",
        owner_type="team",
        email="finance-data@company.com",
        slack_channel="#finance-data",
        meta={"department": "finance", "cost_center": "FIN-001"},
    )
    db.add(owner)
    await db.flush()

    # Create domain
    domain = Domain(
        name="finance",
        description="Financial data domain including accounting, revenue, and regulatory reporting",
        owner_id=owner.id,
        meta={
            "compliance_frameworks": ["SOX", "GAAP", "IFRS"],
            "data_classification": "highly_confidential",
        },
    )
    db.add(domain)
    await db.flush()

    return domain, owner


async def create_finance_tags(db: AsyncSession):
    """Create finance-specific tags for classification."""
    tags = []

    # Compliance tags
    sox_tag = Tag(
        name="sox",
        category="compliance",
        description="Sarbanes-Oxley Act compliance requirement",
        color="#FF6B6B",
        sensitivity_level="restricted",
        meta={"framework": "SOX", "requires_audit": True},
    )
    db.add(sox_tag)
    tags.append(sox_tag)

    gaap_tag = Tag(
        name="gaap",
        category="compliance",
        description="Generally Accepted Accounting Principles",
        color="#4ECDC4",
        sensitivity_level="internal",
        meta={"framework": "GAAP", "geography": "US"},
    )
    db.add(gaap_tag)
    tags.append(gaap_tag)

    ifrs_tag = Tag(
        name="ifrs",
        category="compliance",
        description="International Financial Reporting Standards",
        color="#45B7D1",
        sensitivity_level="internal",
        meta={"framework": "IFRS", "geography": "global"},
    )
    db.add(ifrs_tag)
    tags.append(ifrs_tag)

    # Domain tags
    finance_tag = Tag(
        name="finance",
        category="domain",
        description="Financial data and metrics",
        color="#96CEB4",
        meta={"domain": "finance"},
    )
    db.add(finance_tag)
    tags.append(finance_tag)

    revenue_tag = Tag(
        name="revenue",
        category="business_area",
        description="Revenue recognition and tracking",
        color="#FFEAA7",
        meta={"critical_metric": True},
    )
    db.add(revenue_tag)
    tags.append(revenue_tag)

    gl_tag = Tag(
        name="general_ledger",
        category="business_area",
        description="General ledger and accounting entries",
        color="#DFE6E9",
        meta={"system_of_record": True},
    )
    db.add(gl_tag)
    tags.append(gl_tag)

    # Quality tags
    tier1_tag = Tag(
        name="tier-1",
        category="data_quality",
        description="Tier 1 - Mission critical data",
        color="#E17055",
        sensitivity_level="restricted",
        meta={"sla_tier": "critical", "uptime_requirement": "99.99"},
    )
    db.add(tier1_tag)
    tags.append(tier1_tag)

    regulatory_tag = Tag(
        name="regulatory",
        category="compliance",
        description="Subject to regulatory reporting requirements",
        color="#FD79A8",
        sensitivity_level="restricted",
        meta={"audit_retention_years": 7},
    )
    db.add(regulatory_tag)
    tags.append(regulatory_tag)

    await db.flush()
    return tags


async def create_finance_business_terms(db: AsyncSession, domain_id):
    """Create finance business terms."""
    from sqlalchemy import select

    terms = []

    # Check if revenue term already exists
    result = await db.execute(select(BusinessTerm).where(BusinessTerm.term_name == "revenue"))
    revenue_term = result.scalar_one_or_none()

    if not revenue_term:
        revenue_term = BusinessTerm(
            term_name="revenue",
            display_name="Revenue",
            definition="Total income from normal business operations, calculated as the sale price times the number of units sold",
            approval_status="approved",
            domain_id=domain_id,
            category="financial_metric",
            meta={"gaap_reference": "ASC 606", "formula": "price * quantity"},
        )
        db.add(revenue_term)
        await db.flush()
    terms.append(revenue_term)

    # Debit term
    result = await db.execute(select(BusinessTerm).where(BusinessTerm.term_name == "debit"))
    debit_term = result.scalar_one_or_none()
    if not debit_term:
        debit_term = BusinessTerm(
            term_name="debit",
            display_name="Debit",
            definition="An accounting entry that increases asset or expense accounts, or decreases liability or equity accounts",
            approval_status="approved",
            domain_id=domain_id,
            category="accounting_concept",
            meta={"double_entry_side": "left"},
        )
        db.add(debit_term)
    terms.append(debit_term)

    # Credit term
    result = await db.execute(select(BusinessTerm).where(BusinessTerm.term_name == "credit"))
    credit_term = result.scalar_one_or_none()
    if not credit_term:
        credit_term = BusinessTerm(
            term_name="credit",
            display_name="Credit",
            definition="An accounting entry that decreases asset or expense accounts, or increases liability or equity accounts",
            approval_status="approved",
            domain_id=domain_id,
            category="accounting_concept",
            meta={"double_entry_side": "right"},
        )
        db.add(credit_term)
    terms.append(credit_term)

    # Account balance term
    result = await db.execute(select(BusinessTerm).where(BusinessTerm.term_name == "account_balance"))
    balance_term = result.scalar_one_or_none()
    if not balance_term:
        balance_term = BusinessTerm(
            term_name="account_balance",
            display_name="Account Balance",
            definition="The net amount in an account, calculated as the sum of all debits minus the sum of all credits",
            approval_status="approved",
            domain_id=domain_id,
            category="financial_metric",
            meta={"calculation": "SUM(debits) - SUM(credits)"},
        )
        db.add(balance_term)
    terms.append(balance_term)

    # Fiscal period term
    result = await db.execute(select(BusinessTerm).where(BusinessTerm.term_name == "fiscal_period"))
    fiscal_period_term = result.scalar_one_or_none()
    if not fiscal_period_term:
        fiscal_period_term = BusinessTerm(
            term_name="fiscal_period",
            display_name="Fiscal Period",
            definition="A period of time used for calculating financial statements, typically monthly, quarterly, or annually",
            approval_status="approved",
            domain_id=domain_id,
            category="time_dimension",
            meta={"granularity": ["month", "quarter", "year"]},
        )
        db.add(fiscal_period_term)
    terms.append(fiscal_period_term)

    await db.flush()
    return terms


async def create_finance_value_domains(db: AsyncSession):
    """Create value domains for finance data."""
    domains = []

    # Currency amount
    currency_domain = ValueDomain(
        domain_name="currency_usd",
        description="Monetary value in US Dollars with 2 decimal precision",
        domain_type="range",
        min_value="-999999999999.99",
        max_value="999999999999.99",
        pattern_regex=r"^-?\d+\.\d{2}$",
        pattern_description="Currency format with 2 decimal places",
        meta={"currency": "USD", "decimal_places": 2},
    )
    db.add(currency_domain)
    domains.append(currency_domain)

    # Account type enum
    account_type_domain = ValueDomain(
        domain_name="account_type_enum",
        description="Chart of accounts - account types",
        domain_type="enum",
        allowed_values=[
            {"code": "asset", "label": "Asset", "description": "Resources owned by the company"},
            {"code": "liability", "label": "Liability", "description": "Obligations owed by the company"},
            {"code": "equity", "label": "Equity", "description": "Owner's interest in the company"},
            {"code": "revenue", "label": "Revenue", "description": "Income from business operations"},
            {"code": "expense", "label": "Expense", "description": "Costs of business operations"},
        ],
        meta={"source": "chart_of_accounts"},
    )
    db.add(account_type_domain)
    domains.append(account_type_domain)

    # Transaction status enum
    txn_status_domain = ValueDomain(
        domain_name="transaction_status_enum",
        description="Financial transaction processing status",
        domain_type="enum",
        allowed_values=[
            {"code": "pending", "label": "Pending", "description": "Transaction initiated, awaiting approval"},
            {"code": "approved", "label": "Approved", "description": "Transaction approved, ready to post"},
            {"code": "posted", "label": "Posted", "description": "Transaction posted to GL"},
            {"code": "reconciled", "label": "Reconciled", "description": "Transaction reconciled with bank"},
            {"code": "voided", "label": "Voided", "description": "Transaction cancelled/reversed"},
        ],
        meta={},
    )
    db.add(txn_status_domain)
    domains.append(txn_status_domain)

    await db.flush()
    return domains


async def create_chart_of_accounts_capsule(db: AsyncSession, domain_id, owner_id, business_terms, value_domains, tags):
    """Create chart_of_accounts capsule - Master data for GL accounts."""
    # Create capsule
    capsule = Capsule(
        urn="urn:dcs:postgres:table:finance_erp.master:chart_of_accounts",
        name="chart_of_accounts",
        capsule_type="model",
        layer="gold",
        description="Chart of accounts master data defining all GL account codes and hierarchies",
        domain_id=domain_id,
        owner_id=owner_id,
        schema_name="master",
        database_name="finance_erp",
        materialization="table",
        row_count=500,
        table_size_bytes=102400,
        last_analyzed_at=datetime.now(),
        meta={
            "platform": "postgres",
            "system": "NetSuite",
            "refresh_frequency": "daily",
            "business_critical": True,
        },
    )
    db.add(capsule)
    await db.flush()

    # Dimension 1: Identity & Context (done above)

    # Dimension 2: Structural Metadata - Columns
    account_id_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.account_id",
        name="account_id",
        data_type="VARCHAR(20)",
        ordinal_position=1,
        is_nullable=False,
        description="Unique GL account identifier",
        meta={},
    )
    db.add(account_id_col)

    account_name_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.account_name",
        name="account_name",
        data_type="VARCHAR(255)",
        ordinal_position=2,
        is_nullable=False,
        description="Human-readable account name",
        meta={},
    )
    db.add(account_name_col)

    account_type_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.account_type",
        name="account_type",
        data_type="VARCHAR(50)",
        ordinal_position=3,
        is_nullable=False,
        description="Account classification (asset, liability, equity, revenue, expense)",
        value_domain=value_domains[1].domain_name,
        meta={},
    )
    db.add(account_type_col)

    parent_account_id_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.parent_account_id",
        name="parent_account_id",
        data_type="VARCHAR(20)",
        ordinal_position=4,
        is_nullable=True,
        description="Parent account for hierarchical rollups",
        meta={},
    )
    db.add(parent_account_id_col)

    is_active_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.is_active",
        name="is_active",
        data_type="BOOLEAN",
        ordinal_position=5,
        is_nullable=False,
        description="Whether account is active for new transactions",
        meta={},
    )
    db.add(is_active_col)

    await db.flush()

    # Dimension 2: Constraints
    pk_constraint = ColumnConstraint(
        column_id=account_id_col.id,
        constraint_type="primary_key",
        constraint_name="pk_chart_of_accounts",
        is_enforced=True,
        meta={},
    )
    db.add(pk_constraint)

    # Self-referencing FK for hierarchy
    parent_fk = ColumnConstraint(
        column_id=parent_account_id_col.id,
        constraint_type="foreign_key",
        constraint_name="fk_parent_account",
        referenced_table_urn=capsule.urn,
        referenced_column_urn=account_id_col.urn,
        on_delete_action="RESTRICT",
        is_enforced=True,
        meta={},
    )
    db.add(parent_fk)

    # Dimension 2: Indexes
    type_idx = CapsuleIndex(
        capsule_id=capsule.id,
        index_name="idx_account_type",
        index_type="btree",
        column_names=["account_type"],
        is_unique=False,
        meta={},
    )
    db.add(type_idx)

    parent_idx = CapsuleIndex(
        capsule_id=capsule.id,
        index_name="idx_parent_account",
        index_type="btree",
        column_names=["parent_account_id"],
        is_unique=False,
        meta={},
    )
    db.add(parent_idx)

    # Dimension 3: Business Terms
    # Link balance_term to capsule (accounting concept)
    capsule_term = CapsuleBusinessTerm(
        capsule_id=capsule.id,
        business_term_id=business_terms[3].id,  # account_balance
        relationship_type="defines",
        added_by="finance_data_team",
        meta={},
    )
    db.add(capsule_term)

    # Dimension 4: Column Profiles
    account_id_profile = ColumnProfile(
        column_id=account_id_col.id,
        total_count=500,
        null_count=0,
        null_percentage=Decimal("0.00"),
        distinct_count=500,
        unique_percentage=Decimal("100.00"),
        completeness_score=Decimal("100.00"),
        validity_score=Decimal("100.00"),
        uniqueness_score=Decimal("100.00"),
        profiled_at=datetime.now(),
        meta={},
    )
    db.add(account_id_profile)

    # Dimension 4: Quality Rules
    unique_rule = QualityRule(
        column_id=account_id_col.id,
        rule_type="unique",
        rule_name="unique_account_id",
        rule_config={},
        severity="error",
        blocking=True,
        is_enabled=True,
        meta={},
    )
    db.add(unique_rule)

    not_null_rule = QualityRule(
        column_id=account_name_col.id,
        rule_type="not_null",
        rule_name="account_name_required",
        rule_config={},
        severity="error",
        blocking=True,
        is_enabled=True,
        meta={},
    )
    db.add(not_null_rule)

    ref_integrity_rule = QualityRule(
        column_id=parent_account_id_col.id,
        rule_type="referential_integrity",
        rule_name="valid_parent_account",
        rule_config={
            "referenced_table": capsule.urn,
            "referenced_column": "account_id",
        },
        severity="error",
        blocking=True,
        is_enabled=True,
        meta={},
    )
    db.add(ref_integrity_rule)

    # Dimension 5: Data Policies
    policy = DataPolicy(
        capsule_id=capsule.id,
        sensitivity_level="internal",
        classification_tags=["sox", "gaap", "master_data"],
        retention_period=timedelta(days=3650),  # 10 years
        deletion_action="archive",
        requires_masking=False,
        compliance_frameworks=["SOX", "GAAP"],
        audit_log_required=True,
        min_access_level="finance_team",
        allowed_roles=["finance_analyst", "controller", "cfo", "auditor"],
        data_residency="US",
        cross_border_transfer=False,
        meta={
            "policy_name": "master_data_policy",
            "data_steward": "controller@company.com",
        },
    )
    db.add(policy)

    # Dimension 6: Version
    version = CapsuleVersion(
        capsule_id=capsule.id,
        version_number=1,
        version_name="v1.0.0",
        schema_snapshot={"columns": 5, "indexes": 2},
        change_type="created",
        breaking_change=False,
        is_current=True,
        deployed_at=datetime(2024, 1, 1),
        deployed_by="finance_data_team",
        git_commit_sha="abc123",
        git_repository="github.com/company/finance-data",
        meta={},
    )
    db.add(version)

    # Dimension 7: Contract
    contract = CapsuleContract(
        capsule_id=capsule.id,
        contract_version="1.0",
        contract_status="active",
        freshness_sla=timedelta(hours=24),
        freshness_schedule="daily",
        completeness_sla=Decimal("100.00"),
        quality_score_sla=Decimal("100.00"),
        availability_sla=Decimal("99.99"),
        critical_quality_rules=["unique_account_id", "account_name_required"],
        schema_change_policy="backwards_compatible",
        breaking_change_notice_days=90,
        support_level="critical",
        support_contact="finance-data@company.com",
        support_slack_channel="#finance-data",
        deprecation_policy="180_days_notice",
        known_consumers=[
            {"team": "finance_reporting", "contact": "reporting@company.com", "use_case": "Financial statements"},
            {"team": "gl_posting", "contact": "gl@company.com", "use_case": "Transaction posting"},
        ],
        meta={},
    )
    db.add(contract)

    # Tag associations
    for tag in [tags[0], tags[1], tags[5], tags[6]]:  # sox, gaap, gl, tier1
        capsule_tag = CapsuleTag(
            capsule_id=capsule.id,
            tag_id=tag.id,
            added_by="finance_data_team",
            meta={},
        )
        db.add(capsule_tag)

    await db.flush()
    return capsule, account_id_col


async def create_gl_transactions_capsule(
    db: AsyncSession, domain_id, owner_id, business_terms, value_domains, tags, chart_of_accounts_capsule, account_id_col
):
    """Create gl_transactions capsule - Fact table for all GL entries."""
    # Create capsule
    capsule = Capsule(
        urn="urn:dcs:postgres:table:finance_erp.facts:gl_transactions",
        name="gl_transactions",
        capsule_type="model",
        layer="gold",
        description="General ledger transaction fact table containing all accounting entries",
        domain_id=domain_id,
        owner_id=owner_id,
        schema_name="facts",
        database_name="finance_erp",
        materialization="table",
        partition_strategy="range",
        partition_key=["transaction_date"],
        partition_expression="RANGE (transaction_date)",
        storage_format="parquet",
        compression="snappy",
        row_count=50000000,
        table_size_bytes=25000000000,
        last_analyzed_at=datetime.now(),
        meta={
            "platform": "postgres",
            "system": "NetSuite",
            "refresh_frequency": "hourly",
            "business_critical": True,
            "partition_retention_days": 2555,
        },
    )
    db.add(capsule)
    await db.flush()

    # Dimension 2: Structural Metadata - Columns
    transaction_id_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.transaction_id",
        name="transaction_id",
        data_type="UUID",
        ordinal_position=1,
        is_nullable=False,
        description="Unique transaction identifier",
        meta={},
    )
    db.add(transaction_id_col)

    transaction_date_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.transaction_date",
        name="transaction_date",
        data_type="DATE",
        ordinal_position=2,
        is_nullable=False,
        description="Date of transaction posting",
        meta={},
    )
    db.add(transaction_date_col)

    account_id_ref_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.account_id",
        name="account_id",
        data_type="VARCHAR(20)",
        ordinal_position=3,
        is_nullable=False,
        description="Reference to chart of accounts",
        meta={},
    )
    db.add(account_id_ref_col)

    debit_amount_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.debit_amount",
        name="debit_amount",
        data_type="DECIMAL(18,2)",
        ordinal_position=4,
        is_nullable=True,
        description="Debit amount in USD",
        unit_of_measure="USD",
        value_domain=value_domains[0].domain_name,
        meta={},
    )
    db.add(debit_amount_col)

    credit_amount_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.credit_amount",
        name="credit_amount",
        data_type="DECIMAL(18,2)",
        ordinal_position=5,
        is_nullable=True,
        description="Credit amount in USD",
        unit_of_measure="USD",
        value_domain=value_domains[0].domain_name,
        meta={},
    )
    db.add(credit_amount_col)

    transaction_status_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.transaction_status",
        name="transaction_status",
        data_type="VARCHAR(50)",
        ordinal_position=6,
        is_nullable=False,
        description="Current status of the transaction",
        value_domain=value_domains[2].domain_name,
        meta={},
    )
    db.add(transaction_status_col)

    description_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.description",
        name="description",
        data_type="TEXT",
        ordinal_position=7,
        is_nullable=True,
        description="Transaction description or memo",
        meta={},
    )
    db.add(description_col)

    fiscal_period_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.fiscal_period",
        name="fiscal_period",
        data_type="VARCHAR(7)",
        ordinal_position=8,
        is_nullable=False,
        description="Fiscal period in YYYY-MM format",
        meta={"format": "YYYY-MM"},
    )
    db.add(fiscal_period_col)

    created_by_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.created_by",
        name="created_by",
        data_type="VARCHAR(255)",
        ordinal_position=9,
        is_nullable=False,
        description="User who created the transaction",
        semantic_type="pii",
        meta={},
    )
    db.add(created_by_col)

    await db.flush()

    # Dimension 2: Constraints
    pk_constraint = ColumnConstraint(
        column_id=transaction_id_col.id,
        constraint_type="primary_key",
        constraint_name="pk_gl_transactions",
        is_enforced=True,
        meta={},
    )
    db.add(pk_constraint)

    fk_account = ColumnConstraint(
        column_id=account_id_ref_col.id,
        constraint_type="foreign_key",
        constraint_name="fk_gl_account",
        referenced_table_urn=chart_of_accounts_capsule.urn,
        referenced_column_urn=account_id_col.urn,
        on_delete_action="RESTRICT",
        is_enforced=True,
        meta={},
    )
    db.add(fk_account)

    # Double-entry check constraint (table-level, but attached to debit_amount column)
    check_constraint = ColumnConstraint(
        column_id=debit_amount_col.id,
        constraint_type="check",
        constraint_name="chk_debit_or_credit",
        check_expression="(debit_amount IS NOT NULL AND credit_amount IS NULL) OR (debit_amount IS NULL AND credit_amount IS NOT NULL)",
        is_enforced=True,
        meta={"business_rule": "double_entry_accounting"},
    )
    db.add(check_constraint)

    # Dimension 2: Indexes
    date_idx = CapsuleIndex(
        capsule_id=capsule.id,
        index_name="idx_gl_transaction_date",
        index_type="btree",
        column_names=["transaction_date"],
        is_unique=False,
        meta={},
    )
    db.add(date_idx)

    account_idx = CapsuleIndex(
        capsule_id=capsule.id,
        index_name="idx_gl_account",
        index_type="btree",
        column_names=["account_id"],
        is_unique=False,
        meta={},
    )
    db.add(account_idx)

    period_idx = CapsuleIndex(
        capsule_id=capsule.id,
        index_name="idx_gl_fiscal_period",
        index_type="btree",
        column_names=["fiscal_period"],
        is_unique=False,
        meta={},
    )
    db.add(period_idx)

    # Dimension 3: Business Terms
    for term_idx in [1, 2, 4]:  # debit, credit, fiscal_period
        capsule_term = CapsuleBusinessTerm(
            capsule_id=capsule.id,
            business_term_id=business_terms[term_idx].id,
            relationship_type="implements",
            added_by="finance_data_team",
            meta={},
        )
        db.add(capsule_term)

    # Link debit/credit amounts to business terms
    debit_col_term = ColumnBusinessTerm(
        column_id=debit_amount_col.id,
        business_term_id=business_terms[1].id,  # debit
        relationship_type="measures",
        added_by="finance_data_team",
        meta={},
    )
    db.add(debit_col_term)

    credit_col_term = ColumnBusinessTerm(
        column_id=credit_amount_col.id,
        business_term_id=business_terms[2].id,  # credit
        relationship_type="measures",
        added_by="finance_data_team",
        meta={},
    )
    db.add(credit_col_term)

    # Dimension 4: Column Profiles
    txn_id_profile = ColumnProfile(
        column_id=transaction_id_col.id,
        total_count=50000000,
        null_count=0,
        null_percentage=Decimal("0.00"),
        distinct_count=50000000,
        unique_percentage=Decimal("100.00"),
        completeness_score=Decimal("100.00"),
        validity_score=Decimal("100.00"),
        uniqueness_score=Decimal("100.00"),
        profiled_at=datetime.now(),
        meta={},
    )
    db.add(txn_id_profile)

    debit_profile = ColumnProfile(
        column_id=debit_amount_col.id,
        total_count=50000000,
        null_count=25000000,
        null_percentage=Decimal("50.00"),
        min_value=Decimal("0.01"),
        max_value=Decimal("10000000.00"),
        mean_value=Decimal("5420.50"),
        median_value=Decimal("1250.00"),
        completeness_score=Decimal("50.00"),
        validity_score=Decimal("99.99"),
        profiled_at=datetime.now(),
        meta={},
    )
    db.add(debit_profile)

    credit_profile = ColumnProfile(
        column_id=credit_amount_col.id,
        total_count=50000000,
        null_count=25000000,
        null_percentage=Decimal("50.00"),
        min_value=Decimal("0.01"),
        max_value=Decimal("10000000.00"),
        mean_value=Decimal("5420.50"),
        median_value=Decimal("1250.00"),
        completeness_score=Decimal("50.00"),
        validity_score=Decimal("99.99"),
        profiled_at=datetime.now(),
        meta={},
    )
    db.add(credit_profile)

    # Dimension 4: Quality Rules
    unique_txn_rule = QualityRule(
        column_id=transaction_id_col.id,
        rule_type="unique",
        rule_name="unique_transaction_id",
        rule_config={},
        severity="error",
        blocking=True,
        is_enabled=True,
        meta={},
    )
    db.add(unique_txn_rule)

    ref_integrity_rule = QualityRule(
        column_id=account_id_ref_col.id,
        rule_type="referential_integrity",
        rule_name="valid_gl_account",
        rule_config={
            "referenced_table": chart_of_accounts_capsule.urn,
            "referenced_column": "account_id",
        },
        severity="error",
        blocking=True,
        is_enabled=True,
        meta={},
    )
    db.add(ref_integrity_rule)

    # Double-entry balance rule (custom SQL)
    balance_rule = QualityRule(
        capsule_id=capsule.id,
        rule_type="custom_sql",
        rule_name="double_entry_balance",
        rule_config={
            "sql": "SELECT SUM(COALESCE(debit_amount, 0)) - SUM(COALESCE(credit_amount, 0)) as balance FROM gl_transactions WHERE balance <> 0",
        },
        severity="error",
        blocking=False,
        is_enabled=True,
        meta={"description": "Ensure debits equal credits across all transactions"},
    )
    db.add(balance_rule)

    freshness_rule = QualityRule(
        capsule_id=capsule.id,
        rule_type="freshness",
        rule_name="gl_freshness",
        rule_config={"max_age_hours": 1},
        severity="error",
        blocking=False,
        is_enabled=True,
        meta={},
    )
    db.add(freshness_rule)

    # Dimension 5: Data Policies
    policy = DataPolicy(
        capsule_id=capsule.id,
        sensitivity_level="restricted",
        classification_tags=["sox", "gaap", "financial", "audit_trail"],
        retention_period=timedelta(days=2555),  # 7 years
        deletion_action="archive",
        requires_masking=True,
        compliance_frameworks=["SOX", "GAAP"],
        audit_log_required=True,
        min_access_level="finance_team",
        allowed_roles=["finance_analyst", "controller", "cfo", "auditor", "sox_auditor"],
        data_residency="US",
        cross_border_transfer=False,
        allowed_regions=["US"],
        meta={
            "policy_name": "gl_transactions_policy",
            "sox_controls": ["ITGC-01", "FSCA-02"],
            "audit_retention_years": 7,
        },
    )
    db.add(policy)

    # Masking rules
    created_by_mask = MaskingRule(
        column_id=created_by_col.id,
        rule_name="mask_user_identity",
        masking_method="hashing",
        method_config={"algorithm": "sha256"},
        applies_to_roles=["analyst", "external_auditor"],
        meta={},
    )
    db.add(created_by_mask)

    description_mask = MaskingRule(
        column_id=description_col.id,
        rule_name="mask_transaction_description",
        masking_method="partial_redaction",
        method_config={"show_first": 20, "mask_rest": True},
        applies_to_roles=["analyst"],
        meta={},
    )
    db.add(description_mask)

    # Dimension 6: Lineage
    lineage = CapsuleLineage(
        source_urn=chart_of_accounts_capsule.urn,
        target_urn=capsule.urn,
        source_id=chart_of_accounts_capsule.id,
        target_id=capsule.id,
        edge_type="flows_to",
        transformation="foreign_key_join",
        meta={"join_column": "account_id"},
    )
    db.add(lineage)

    # Dimension 6: Transformation Code
    transformation = TransformationCode(
        capsule_id=capsule.id,
        language="sql",
        code_text="""
-- gl_transactions materialization
-- Loads hourly from NetSuite GL API

INSERT INTO facts.gl_transactions (
    transaction_id,
    transaction_date,
    account_id,
    debit_amount,
    credit_amount,
    transaction_status,
    description,
    fiscal_period,
    created_by
)
SELECT
    t.id as transaction_id,
    t.transaction_date,
    t.account_id,
    CASE WHEN t.amount > 0 THEN t.amount ELSE NULL END as debit_amount,
    CASE WHEN t.amount < 0 THEN ABS(t.amount) ELSE NULL END as credit_amount,
    t.status as transaction_status,
    t.memo as description,
    TO_CHAR(t.transaction_date, 'YYYY-MM') as fiscal_period,
    t.created_by
FROM netsuite_api.journal_entries t
WHERE t.posted_date >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
  AND t.status = 'posted'
        """,
        file_path="etl/finance/load_gl_transactions.sql",
        git_commit_sha="def456",
        git_repository="github.com/company/finance-data",
        upstream_references=["netsuite_api.journal_entries"],
        meta={"schedule": "hourly", "incremental": True},
    )
    db.add(transformation)

    # Dimension 6: Version History
    version_1 = CapsuleVersion(
        capsule_id=capsule.id,
        version_number=1,
        version_name="v1.0.0",
        schema_snapshot={"columns": 9, "indexes": 3, "constraints": 3},
        change_type="created",
        breaking_change=False,
        is_current=False,
        deployed_at=datetime(2024, 1, 1),
        deployed_by="finance_data_team",
        git_commit_sha="abc123",
        git_repository="github.com/company/finance-data",
        meta={},
    )
    db.add(version_1)

    version_2 = CapsuleVersion(
        capsule_id=capsule.id,
        version_number=2,
        version_name="v1.1.0",
        schema_snapshot={"columns": 9, "indexes": 3, "constraints": 3},
        change_type="data_change",
        change_summary="Added fiscal_period column for reporting",
        breaking_change=False,
        is_current=True,
        deployed_at=datetime(2024, 6, 1),
        deployed_by="finance_data_team",
        git_commit_sha="def456",
        git_repository="github.com/company/finance-data",
        meta={},
    )
    db.add(version_2)

    # Dimension 7: Contract
    contract = CapsuleContract(
        capsule_id=capsule.id,
        contract_version="1.1",
        contract_status="active",
        freshness_sla=timedelta(hours=1),
        freshness_schedule="hourly",
        completeness_sla=Decimal("99.99"),
        expected_row_count_min=1000000,
        expected_row_count_max=100000000,
        availability_sla=Decimal("99.99"),
        max_downtime=timedelta(minutes=5),
        quality_score_sla=Decimal("99.90"),
        critical_quality_rules=["unique_transaction_id", "valid_gl_account", "double_entry_balance"],
        schema_change_policy="backwards_compatible",
        breaking_change_notice_days=90,
        support_level="critical",
        support_contact="finance-data@company.com",
        support_slack_channel="#finance-data-oncall",
        deprecation_policy="180_days_notice",
        known_consumers=[
            {"team": "financial_reporting", "contact": "reporting@company.com", "use_case": "Monthly close"},
            {"team": "sox_compliance", "contact": "sox@company.com", "use_case": "SOX audit trails"},
            {"team": "treasury", "contact": "treasury@company.com", "use_case": "Cash flow analysis"},
            {"team": "fp_and_a", "contact": "fpa@company.com", "use_case": "Budget variance"},
        ],
        meta={"pagerduty_service": "finance-data-platform"},
    )
    db.add(contract)

    # Tag associations
    for tag in [tags[0], tags[1], tags[3], tags[5], tags[6], tags[7]]:  # sox, gaap, finance, gl, tier1, regulatory
        capsule_tag = CapsuleTag(
            capsule_id=capsule.id,
            tag_id=tag.id,
            added_by="finance_data_team",
            meta={},
        )
        db.add(capsule_tag)

    await db.flush()
    return capsule


async def create_revenue_by_month_capsule(
    db: AsyncSession, domain_id, owner_id, business_terms, value_domains, tags, gl_transactions_capsule
):
    """Create revenue_by_month capsule - Aggregated revenue metrics."""
    # Create capsule
    capsule = Capsule(
        urn="urn:dcs:dbt:model:finance_analytics.marts:revenue_by_month",
        name="revenue_by_month",
        capsule_type="model",
        layer="gold",
        description="Monthly revenue aggregation by account, used for financial reporting and analytics",
        domain_id=domain_id,
        owner_id=owner_id,
        schema_name="marts",
        database_name="finance_analytics",
        materialization="incremental",
        row_count=12000,
        table_size_bytes=512000,
        last_analyzed_at=datetime.now(),
        meta={
            "platform": "dbt",
            "project": "finance_analytics",
            "dbt_model_type": "mart",
            "refresh_frequency": "daily",
        },
    )
    db.add(capsule)
    await db.flush()

    # Dimension 2: Structural Metadata - Columns
    fiscal_period_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.fiscal_period",
        name="fiscal_period",
        data_type="VARCHAR(7)",
        ordinal_position=1,
        is_nullable=False,
        description="Fiscal period (YYYY-MM)",
        meta={},
    )
    db.add(fiscal_period_col)

    account_id_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.account_id",
        name="account_id",
        data_type="VARCHAR(20)",
        ordinal_position=2,
        is_nullable=False,
        description="GL account identifier",
        meta={},
    )
    db.add(account_id_col)

    revenue_amount_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.revenue_amount",
        name="revenue_amount",
        data_type="DECIMAL(18,2)",
        ordinal_position=3,
        is_nullable=False,
        description="Total revenue recognized in the period",
        unit_of_measure="USD",
        value_domain=value_domains[0].domain_name,
        meta={},
    )
    db.add(revenue_amount_col)

    transaction_count_col = Column(
        capsule_id=capsule.id,
        urn=f"{capsule.urn}.transaction_count",
        name="transaction_count",
        data_type="INTEGER",
        ordinal_position=4,
        is_nullable=False,
        description="Number of transactions in the period",
        meta={},
    )
    db.add(transaction_count_col)

    await db.flush()

    # Dimension 2: Constraints
    pk_constraint = ColumnConstraint(
        column_id=fiscal_period_col.id,  # Composite PK, attached to first column
        constraint_type="primary_key",
        constraint_name="pk_revenue_by_month",
        is_enforced=True,
        meta={"columns": ["fiscal_period", "account_id"]},
    )
    db.add(pk_constraint)

    # Dimension 2: Indexes
    period_idx = CapsuleIndex(
        capsule_id=capsule.id,
        index_name="idx_revenue_period",
        index_type="btree",
        column_names=["fiscal_period"],
        is_unique=False,
        meta={},
    )
    db.add(period_idx)

    # Dimension 3: Business Terms
    revenue_capsule_term = CapsuleBusinessTerm(
        capsule_id=capsule.id,
        business_term_id=business_terms[0].id,  # revenue
        relationship_type="measures",
        added_by="finance_data_team",
        meta={},
    )
    db.add(revenue_capsule_term)

    revenue_col_term = ColumnBusinessTerm(
        column_id=revenue_amount_col.id,
        business_term_id=business_terms[0].id,  # revenue
        relationship_type="measures",
        added_by="finance_data_team",
        meta={},
    )
    db.add(revenue_col_term)

    # Dimension 4: Column Profiles
    revenue_profile = ColumnProfile(
        column_id=revenue_amount_col.id,
        total_count=12000,
        null_count=0,
        null_percentage=Decimal("0.00"),
        min_value=Decimal("0.00"),
        max_value=Decimal("5000000.00"),
        mean_value=Decimal("125000.00"),
        median_value=Decimal("87500.00"),
        completeness_score=Decimal("100.00"),
        validity_score=Decimal("100.00"),
        profiled_at=datetime.now(),
        meta={},
    )
    db.add(revenue_profile)

    # Dimension 4: Quality Rules
    not_null_rule = QualityRule(
        column_id=revenue_amount_col.id,
        rule_type="not_null",
        rule_name="revenue_amount_required",
        rule_config={},
        severity="error",
        blocking=True,
        is_enabled=True,
        meta={},
    )
    db.add(not_null_rule)

    range_check_rule = QualityRule(
        column_id=revenue_amount_col.id,
        rule_type="range_check",
        rule_name="revenue_amount_range",
        rule_config={"min": 0, "max": 10000000},
        expected_range_min=Decimal("0"),
        expected_range_max=Decimal("10000000.00"),
        severity="warning",
        is_enabled=True,
        meta={},
    )
    db.add(range_check_rule)

    freshness_rule = QualityRule(
        capsule_id=capsule.id,
        rule_type="freshness",
        rule_name="revenue_freshness",
        rule_config={"max_age_hours": 24},
        severity="warning",
        blocking=False,
        is_enabled=True,
        meta={},
    )
    db.add(freshness_rule)

    # Dimension 5: Data Policies
    policy = DataPolicy(
        capsule_id=capsule.id,
        sensitivity_level="confidential",
        classification_tags=["sox", "gaap", "revenue", "financial"],
        retention_period=timedelta(days=2555),  # 7 years
        deletion_action="archive",
        requires_masking=False,
        compliance_frameworks=["SOX", "GAAP", "ASC 606"],
        audit_log_required=True,
        min_access_level="finance_team",
        allowed_roles=["finance_analyst", "controller", "cfo", "fp_and_a", "sox_auditor"],
        data_residency="US",
        cross_border_transfer=False,
        meta={
            "policy_name": "revenue_reporting_policy",
            "sox_controls": ["FSCA-03"],
        },
    )
    db.add(policy)

    # Dimension 6: Lineage
    lineage = CapsuleLineage(
        source_urn=gl_transactions_capsule.urn,
        target_urn=capsule.urn,
        source_id=gl_transactions_capsule.id,
        target_id=capsule.id,
        edge_type="flows_to",
        transformation="aggregation",
        meta={"aggregation_level": "monthly"},
    )
    db.add(lineage)

    # Dimension 6: Transformation Code
    transformation = TransformationCode(
        capsule_id=capsule.id,
        language="sql",
        code_text="""
-- revenue_by_month.sql
-- Aggregates GL transactions to monthly revenue by account

{{ config(
    materialized='incremental',
    unique_key=['fiscal_period', 'account_id'],
    on_schema_change='fail'
) }}

WITH revenue_accounts AS (
    SELECT account_id
    FROM {{ ref('chart_of_accounts') }}
    WHERE account_type = 'revenue'
      AND is_active = true
),

monthly_revenue AS (
    SELECT
        t.fiscal_period,
        t.account_id,
        SUM(COALESCE(t.credit_amount, 0) - COALESCE(t.debit_amount, 0)) as revenue_amount,
        COUNT(*) as transaction_count
    FROM {{ ref('gl_transactions') }} t
    INNER JOIN revenue_accounts r ON t.account_id = r.account_id
    WHERE t.transaction_status = 'posted'
    {% if is_incremental() %}
      AND t.transaction_date >= (SELECT MAX(fiscal_period) FROM {{ this }})
    {% endif %}
    GROUP BY 1, 2
)

SELECT * FROM monthly_revenue
        """,
        file_path="models/marts/finance/revenue_by_month.sql",
        git_commit_sha="ghi789",
        git_repository="github.com/company/finance-analytics",
        upstream_references=["{{ ref('gl_transactions') }}", "{{ ref('chart_of_accounts') }}"],
        meta={"schedule": "daily", "incremental": True},
    )
    db.add(transformation)

    # Dimension 6: Version
    version = CapsuleVersion(
        capsule_id=capsule.id,
        version_number=1,
        version_name="v1.0.0",
        schema_snapshot={"columns": 4, "indexes": 1},
        change_type="created",
        breaking_change=False,
        is_current=True,
        deployed_at=datetime(2024, 6, 1),
        deployed_by="finance_analytics_team",
        git_commit_sha="ghi789",
        git_repository="github.com/company/finance-analytics",
        meta={},
    )
    db.add(version)

    # Dimension 7: Contract
    contract = CapsuleContract(
        capsule_id=capsule.id,
        contract_version="1.0",
        contract_status="active",
        freshness_sla=timedelta(hours=24),
        freshness_schedule="daily",
        completeness_sla=Decimal("100.00"),
        quality_score_sla=Decimal("99.50"),
        availability_sla=Decimal("99.90"),
        critical_quality_rules=["revenue_amount_required"],
        schema_change_policy="strict",
        breaking_change_notice_days=90,
        support_level="business_hours",
        support_contact="finance-analytics@company.com",
        support_slack_channel="#finance-analytics",
        deprecation_policy="180_days_notice",
        known_consumers=[
            {"team": "financial_reporting", "contact": "reporting@company.com", "use_case": "Monthly revenue reports"},
            {"team": "fp_and_a", "contact": "fpa@company.com", "use_case": "Revenue forecasting"},
            {"team": "executives", "contact": "exec@company.com", "use_case": "Board reporting"},
        ],
        meta={},
    )
    db.add(contract)

    # Tag associations
    for tag in [tags[0], tags[1], tags[3], tags[4], tags[7]]:  # sox, gaap, finance, revenue, regulatory
        capsule_tag = CapsuleTag(
            capsule_id=capsule.id,
            tag_id=tag.id,
            added_by="finance_analytics_team",
            meta={},
        )
        db.add(capsule_tag)

    await db.flush()
    return capsule


async def create_data_products(
    db: AsyncSession,
    domain_id,
    owner_id,
    chart_of_accounts_capsule,
    gl_transactions_capsule,
    revenue_by_month_capsule,
):
    """Create data products containing the finance capsules."""
    products = []

    # Financial Reporting Data Product
    reporting_product = DataProduct(
        name="Financial Reporting Product",
        description="Core financial reporting data product providing GL transactions and revenue metrics for financial statements",
        version="1.0.0",
        status="active",
        domain_id=domain_id,
        owner_id=owner_id,
        slo_freshness_hours=24,
        slo_availability_percent=99.9,
        slo_quality_threshold=0.999,
        output_port_schema={
            "type": "object",
            "properties": {
                "revenue_by_month": {
                    "type": "object",
                    "description": "Monthly revenue aggregations",
                    "schema_ref": revenue_by_month_capsule.urn,
                },
            },
        },
        input_sources=[chart_of_accounts_capsule.urn, gl_transactions_capsule.urn],
        meta={
            "business_owner": "Controller",
            "technical_owner": "Finance Data Team",
            "criticality": "tier-1",
            "compliance": ["SOX", "GAAP"],
        },
        tags=["finance", "reporting", "sox"],
    )
    db.add(reporting_product)
    await db.flush()
    products.append(reporting_product)

    # Associate capsules
    coa_assoc = CapsuleDataProduct(
        capsule_id=chart_of_accounts_capsule.id,
        data_product_id=reporting_product.id,
        role="input",
        meta={"purpose": "Master data for account definitions"},
    )
    db.add(coa_assoc)

    gl_assoc = CapsuleDataProduct(
        capsule_id=gl_transactions_capsule.id,
        data_product_id=reporting_product.id,
        role="member",
        meta={"purpose": "Source transaction data"},
    )
    db.add(gl_assoc)

    revenue_assoc = CapsuleDataProduct(
        capsule_id=revenue_by_month_capsule.id,
        data_product_id=reporting_product.id,
        role="output",
        meta={"purpose": "Published revenue metrics", "output_port": True},
    )
    db.add(revenue_assoc)

    # GL Data Product (for GL transactions only)
    gl_product = DataProduct(
        name="General Ledger Data Product",
        description="Comprehensive general ledger data product providing detailed transaction history and account structure",
        version="1.0.0",
        status="active",
        domain_id=domain_id,
        owner_id=owner_id,
        slo_freshness_hours=1,
        slo_availability_percent=99.99,
        slo_quality_threshold=0.9999,
        output_port_schema={
            "type": "object",
            "properties": {
                "gl_transactions": {
                    "type": "object",
                    "description": "All posted GL transactions",
                    "schema_ref": gl_transactions_capsule.urn,
                },
                "chart_of_accounts": {
                    "type": "object",
                    "description": "Active account definitions",
                    "schema_ref": chart_of_accounts_capsule.urn,
                },
            },
        },
        input_sources=[],
        meta={
            "business_owner": "Controller",
            "technical_owner": "Finance Data Team",
            "criticality": "tier-1",
            "compliance": ["SOX", "GAAP"],
            "system_of_record": "NetSuite",
        },
        tags=["finance", "general_ledger", "sox", "tier-1"],
    )
    db.add(gl_product)
    await db.flush()
    products.append(gl_product)

    # Associate capsules
    coa_gl_assoc = CapsuleDataProduct(
        capsule_id=chart_of_accounts_capsule.id,
        data_product_id=gl_product.id,
        role="output",
        meta={"purpose": "Master data", "output_port": True},
    )
    db.add(coa_gl_assoc)

    gl_gl_assoc = CapsuleDataProduct(
        capsule_id=gl_transactions_capsule.id,
        data_product_id=gl_product.id,
        role="output",
        meta={"purpose": "Transaction detail", "output_port": True},
    )
    db.add(gl_gl_assoc)

    await db.flush()
    return products


async def seed_finance_examples():
    """Main function to seed finance data capsules."""
    async with async_session_maker() as db:
        try:
            print("🌱 Starting to seed finance vertical data capsules...")

            # Create domain and owner
            print("  Creating finance domain and owner...")
            domain, owner = await create_finance_domain_and_owner(db)

            # Create tags
            print("  Creating finance classification tags...")
            tags = await create_finance_tags(db)

            # Create business terms
            print("  Creating finance business terms...")
            business_terms = await create_finance_business_terms(db, domain.id)

            # Create value domains
            print("  Creating finance value domains...")
            value_domains = await create_finance_value_domains(db)

            # Create chart_of_accounts capsule
            print("  Creating chart_of_accounts capsule (master data)...")
            chart_of_accounts, account_id_col = await create_chart_of_accounts_capsule(
                db, domain.id, owner.id, business_terms, value_domains, tags
            )

            # Create gl_transactions capsule
            print("  Creating gl_transactions capsule (fact table)...")
            gl_transactions = await create_gl_transactions_capsule(
                db,
                domain.id,
                owner.id,
                business_terms,
                value_domains,
                tags,
                chart_of_accounts,
                account_id_col,  # account_id column from COA
            )

            # Create revenue_by_month capsule
            print("  Creating revenue_by_month capsule (aggregated mart)...")
            revenue_by_month = await create_revenue_by_month_capsule(
                db, domain.id, owner.id, business_terms, value_domains, tags, gl_transactions
            )

            # Create data products
            print("  Creating data products...")
            data_products = await create_data_products(
                db, domain.id, owner.id, chart_of_accounts, gl_transactions, revenue_by_month
            )

            # Commit all changes
            await db.commit()

            print("✅ Successfully seeded finance vertical data!")
            print("\nCreated capsules (all with 7 dimensions):")
            print(f"  1. {chart_of_accounts.urn} (master data)")
            print(f"  2. {gl_transactions.urn} (fact table)")
            print(f"  3. {revenue_by_month.urn} (aggregated mart)")
            print("\nCreated data products:")
            print(f"  1. {data_products[0].name} (contains all 3 capsules)")
            print(f"  2. {data_products[1].name} (GL-focused product)")
            print("\nCreated tags:")
            print(f"  - {len(tags)} classification tags (sox, gaap, ifrs, finance, revenue, gl, tier-1, regulatory)")
            print("\nAll capsules include:")
            print("  ✓ Dimension 1: Identity & Context")
            print("  ✓ Dimension 2: Structural Metadata (columns, constraints, indexes)")
            print("  ✓ Dimension 3: Business Terms")
            print("  ✓ Dimension 4: Quality & Profiling")
            print("  ✓ Dimension 5: Data Policies (sensitivity, masking)")
            print("  ✓ Dimension 6: Lineage & Transformation")
            print("  ✓ Dimension 7: Operational Contract")

        except Exception as e:
            await db.rollback()
            print(f"❌ Error seeding finance examples: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_finance_examples())
