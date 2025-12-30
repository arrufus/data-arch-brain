"""Conformance rule engine for architecture validation."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional, Sequence
from uuid import UUID

import yaml
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.capsule import Capsule
from src.models.column import Column
from src.repositories.capsule import CapsuleRepository

if TYPE_CHECKING:
    from src.models.violation import Violation
    from src.repositories.rule import RuleRepository
    from src.repositories.violation import ViolationRepository


class RuleSeverity(str, Enum):
    """Severity levels for rules."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class RuleCategory(str, Enum):
    """Categories of conformance rules."""

    NAMING = "naming"
    LINEAGE = "lineage"
    PII = "pii"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    ARCHITECTURE = "architecture"
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    QUALITY = "quality"
    POLICY = "policy"
    PROVENANCE = "provenance"
    OPERATIONAL = "operational"


class RuleScope(str, Enum):
    """Scope that a rule applies to."""

    CAPSULE = "capsule"
    COLUMN = "column"
    LINEAGE = "lineage"


# Severity weights for scoring
SEVERITY_WEIGHTS = {
    RuleSeverity.CRITICAL: 10,
    RuleSeverity.ERROR: 5,
    RuleSeverity.WARNING: 2,
    RuleSeverity.INFO: 1,
}


@dataclass
class RuleDefinition:
    """Definition of a conformance rule."""

    rule_id: str
    name: str
    description: str
    severity: RuleSeverity
    category: RuleCategory
    scope: RuleScope
    rule_set: Optional[str] = None
    enabled: bool = True
    # For pattern rules
    pattern: Optional[str] = None
    pattern_type: str = "regex"  # regex, glob
    # For condition rules
    condition: Optional[dict] = None
    # Remediation guidance
    remediation: Optional[str] = None


@dataclass
class ViolationInfo:
    """Information about a rule violation."""

    rule_id: str
    rule_name: str
    severity: RuleSeverity
    category: RuleCategory
    subject_type: str  # capsule, column
    subject_id: UUID
    subject_urn: str
    subject_name: str
    message: str
    details: dict = field(default_factory=dict)
    remediation: Optional[str] = None


@dataclass
class ConformanceResult:
    """Result of conformance evaluation."""

    total_rules: int
    passing_rules: int
    failing_rules: int
    not_applicable: int
    score: float  # 0-100
    weighted_score: float  # 0-100
    by_severity: dict[str, dict[str, int]]
    by_category: dict[str, dict[str, int]]
    violations: list[ViolationInfo]


# Built-in rule definitions
MEDALLION_RULES: list[RuleDefinition] = [
    RuleDefinition(
        rule_id="MED_001",
        name="Gold sources Silver only",
        description="Gold/Mart layer models should only source from Silver/Intermediate layers",
        severity=RuleSeverity.ERROR,
        category=RuleCategory.LINEAGE,
        scope=RuleScope.CAPSULE,
        rule_set="medallion",
        condition={
            "if": {"layer": ["gold", "marts", "mart"]},
            "then": {"upstream_layers": ["silver", "intermediate", "int"]},
        },
        remediation="Refactor to source from Silver/Intermediate layer instead of Bronze/Raw",
    ),
    RuleDefinition(
        rule_id="MED_002",
        name="Silver sources Bronze only",
        description="Silver/Intermediate models should only source from Bronze/Raw or other Silver",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.LINEAGE,
        scope=RuleScope.CAPSULE,
        rule_set="medallion",
        condition={
            "if": {"layer": ["silver", "intermediate", "int"]},
            "then": {"upstream_layers": ["bronze", "raw", "silver", "intermediate", "int", "staging", "stg"]},
        },
        remediation="Ensure Silver models source from Bronze/Raw or other Silver models",
    ),
    RuleDefinition(
        rule_id="MED_003",
        name="Bronze naming convention",
        description="Bronze/Raw layer models should follow naming convention",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.NAMING,
        scope=RuleScope.CAPSULE,
        rule_set="medallion",
        pattern=r"^(raw_|bronze_|stg_|src_)",
        condition={"if": {"layer": ["bronze", "raw", "staging"]}},
        remediation="Rename model to start with raw_, bronze_, stg_, or src_",
    ),
    RuleDefinition(
        rule_id="MED_004",
        name="Silver naming convention",
        description="Silver/Intermediate models should follow naming convention",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.NAMING,
        scope=RuleScope.CAPSULE,
        rule_set="medallion",
        pattern=r"^(int_|silver_|stg_)",
        condition={"if": {"layer": ["silver", "intermediate"]}},
        remediation="Rename model to start with int_, silver_, or stg_",
    ),
    RuleDefinition(
        rule_id="MED_005",
        name="Gold naming convention",
        description="Gold/Mart models should follow naming convention",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.NAMING,
        scope=RuleScope.CAPSULE,
        rule_set="medallion",
        pattern=r"^(dim_|fct_|fact_|mart_|rpt_|gold_)",
        condition={"if": {"layer": ["gold", "marts", "mart"]}},
        remediation="Rename model to start with dim_, fct_, fact_, mart_, rpt_, or gold_",
    ),
]

DBT_BEST_PRACTICES_RULES: list[RuleDefinition] = [
    RuleDefinition(
        rule_id="DBT_001",
        name="Model has description",
        description="All models should have a description",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.DOCUMENTATION,
        scope=RuleScope.CAPSULE,
        rule_set="dbt_best_practices",
        condition={"requires": "description"},
        remediation="Add a description in the schema.yml file",
    ),
    RuleDefinition(
        rule_id="DBT_002",
        name="Model has tests",
        description="All models should have at least one test",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.TESTING,
        scope=RuleScope.CAPSULE,
        rule_set="dbt_best_practices",
        condition={"requires": "tests"},
        remediation="Add at least one test (unique, not_null, etc.) in schema.yml",
    ),
    RuleDefinition(
        rule_id="DBT_003",
        name="Model naming snake_case",
        description="Model names should be in snake_case",
        severity=RuleSeverity.INFO,
        category=RuleCategory.NAMING,
        scope=RuleScope.CAPSULE,
        rule_set="dbt_best_practices",
        pattern=r"^[a-z][a-z0-9_]*$",
        remediation="Rename model to use snake_case (lowercase with underscores)",
    ),
    RuleDefinition(
        rule_id="DBT_004",
        name="Column has description",
        description="Columns should have descriptions",
        severity=RuleSeverity.INFO,
        category=RuleCategory.DOCUMENTATION,
        scope=RuleScope.COLUMN,
        rule_set="dbt_best_practices",
        condition={"requires": "description"},
        remediation="Add a description for this column in schema.yml",
    ),
]

PII_COMPLIANCE_RULES: list[RuleDefinition] = [
    RuleDefinition(
        rule_id="PII_001",
        name="PII in Gold must be masked",
        description="PII columns in Gold/Mart layer should be masked, hashed, or encrypted",
        severity=RuleSeverity.CRITICAL,
        category=RuleCategory.PII,
        scope=RuleScope.COLUMN,
        rule_set="pii_compliance",
        condition={
            "if": {"layer": ["gold", "marts", "mart"], "has_pii": True},
            "then": {"is_masked": True},
        },
        remediation="Apply masking, hashing, or encryption to this PII column",
    ),
    RuleDefinition(
        rule_id="PII_002",
        name="PII columns must be tagged",
        description="Columns containing PII should have explicit PII tags",
        severity=RuleSeverity.ERROR,
        category=RuleCategory.PII,
        scope=RuleScope.COLUMN,
        rule_set="pii_compliance",
        condition={
            "if": {"name_matches_pii_pattern": True},
            "then": {"has_pii_tag": True},
        },
        remediation="Add PII tag via meta: {pii: true, pii_type: ...} in schema.yml",
    ),
    RuleDefinition(
        rule_id="PII_003",
        name="PII type should be specified",
        description="PII columns should have specific PII type classification",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.PII,
        scope=RuleScope.COLUMN,
        rule_set="pii_compliance",
        condition={
            "if": {"has_pii": True},
            "then": {"has_pii_type": True},
        },
        remediation="Specify PII type (email, phone, ssn, etc.) in meta",
    ),
]

# Dimension 2: Structural Metadata Rules
STRUCTURAL_METADATA_RULES: list[RuleDefinition] = [
    RuleDefinition(
        rule_id="DIM2_001",
        name="Primary key constraint naming",
        description="Primary key constraints should follow naming convention: pk_{table}_({columns})",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.STRUCTURAL,
        scope=RuleScope.CAPSULE,
        rule_set="structural_metadata",
        condition={"check": "primary_key_naming_convention"},
        remediation="Rename primary key constraint to follow pk_{table}_({columns}) pattern",
    ),
    RuleDefinition(
        rule_id="DIM2_002",
        name="Foreign key constraint naming",
        description="Foreign key constraints should follow naming convention: fk_{source}_{target}",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.STRUCTURAL,
        scope=RuleScope.CAPSULE,
        rule_set="structural_metadata",
        condition={"check": "foreign_key_naming_convention"},
        remediation="Rename foreign key constraint to follow fk_{source}_{target} pattern",
    ),
    RuleDefinition(
        rule_id="DIM2_003",
        name="Unique constraint naming",
        description="Unique constraints should follow naming convention: uq_{table}_{columns}",
        severity=RuleSeverity.INFO,
        category=RuleCategory.STRUCTURAL,
        scope=RuleScope.CAPSULE,
        rule_set="structural_metadata",
        condition={"check": "unique_constraint_naming_convention"},
        remediation="Rename unique constraint to follow uq_{table}_{columns} pattern",
    ),
    RuleDefinition(
        rule_id="DIM2_004",
        name="Check constraint naming",
        description="Check constraints should follow naming convention: chk_{table}_{condition}",
        severity=RuleSeverity.INFO,
        category=RuleCategory.STRUCTURAL,
        scope=RuleScope.CAPSULE,
        rule_set="structural_metadata",
        condition={"check": "check_constraint_naming_convention"},
        remediation="Rename check constraint to follow chk_{table}_{condition} pattern",
    ),
    RuleDefinition(
        rule_id="DIM2_005",
        name="Index naming convention",
        description="Indexes should follow naming convention: idx_{table}_{columns}",
        severity=RuleSeverity.INFO,
        category=RuleCategory.STRUCTURAL,
        scope=RuleScope.CAPSULE,
        rule_set="structural_metadata",
        condition={"check": "index_naming_convention"},
        remediation="Rename index to follow idx_{table}_{columns} pattern",
    ),
    RuleDefinition(
        rule_id="DIM2_006",
        name="Tables should have primary key",
        description="Every table should have a primary key defined for data integrity",
        severity=RuleSeverity.ERROR,
        category=RuleCategory.STRUCTURAL,
        scope=RuleScope.CAPSULE,
        rule_set="structural_metadata",
        condition={"requires": "has_primary_key"},
        remediation="Add a primary key constraint to this table",
    ),
    RuleDefinition(
        rule_id="DIM2_007",
        name="Foreign keys should have indexes",
        description="Foreign key columns should have indexes for query performance",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.STRUCTURAL,
        scope=RuleScope.CAPSULE,
        rule_set="structural_metadata",
        condition={"check": "foreign_keys_have_indexes"},
        remediation="Add indexes on foreign key columns",
    ),
    RuleDefinition(
        rule_id="DIM2_008",
        name="Composite indexes should be selective",
        description="Composite indexes should have selective columns first for efficiency",
        severity=RuleSeverity.INFO,
        category=RuleCategory.STRUCTURAL,
        scope=RuleScope.CAPSULE,
        rule_set="structural_metadata",
        condition={"check": "composite_index_selectivity"},
        remediation="Reorder composite index to put most selective columns first",
    ),
]

# Dimension 3: Semantic Metadata Rules
SEMANTIC_METADATA_RULES: list[RuleDefinition] = [
    RuleDefinition(
        rule_id="DIM3_001",
        name="Key business columns should have business terms",
        description="Columns with 'id', 'name', 'amount', 'date' should have business terms linked",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.SEMANTIC,
        scope=RuleScope.COLUMN,
        rule_set="semantic_metadata",
        condition={"check": "key_columns_have_business_terms"},
        remediation="Link business terms to clarify semantic meaning",
    ),
    RuleDefinition(
        rule_id="DIM3_002",
        name="Enumerated columns should use value domains",
        description="Columns with limited value sets should reference value domains",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.SEMANTIC,
        scope=RuleScope.COLUMN,
        rule_set="semantic_metadata",
        condition={"check": "enum_columns_have_value_domains"},
        remediation="Create and link a value domain for this enumerated column",
    ),
    RuleDefinition(
        rule_id="DIM3_003",
        name="Code/status columns should have value domains",
        description="Columns ending with '_code' or '_status' should reference value domains",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.SEMANTIC,
        scope=RuleScope.COLUMN,
        rule_set="semantic_metadata",
        condition={"check": "code_status_columns_have_value_domains"},
        remediation="Create and link a value domain for this code/status column",
    ),
    RuleDefinition(
        rule_id="DIM3_004",
        name="Business-critical tables should be tagged",
        description="Tables in Gold layer should have business domain tags",
        severity=RuleSeverity.INFO,
        category=RuleCategory.SEMANTIC,
        scope=RuleScope.CAPSULE,
        rule_set="semantic_metadata",
        condition={
            "if": {"layer": ["gold", "marts", "mart"]},
            "then": {"has_tags": True},
        },
        remediation="Add business domain tags to categorize this table",
    ),
    RuleDefinition(
        rule_id="DIM3_005",
        name="Tables should have ownership",
        description="Every table should have an assigned owner for accountability",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.SEMANTIC,
        scope=RuleScope.CAPSULE,
        rule_set="semantic_metadata",
        condition={"requires": "has_owner"},
        remediation="Assign an owner (team or individual) to this table",
    ),
    RuleDefinition(
        rule_id="DIM3_006",
        name="Tables should belong to domain",
        description="Every table should be assigned to a business domain",
        severity=RuleSeverity.INFO,
        category=RuleCategory.SEMANTIC,
        scope=RuleScope.CAPSULE,
        rule_set="semantic_metadata",
        condition={"requires": "has_domain"},
        remediation="Assign this table to a business domain",
    ),
]

# Dimension 4: Quality Expectations Rules
QUALITY_EXPECTATIONS_RULES: list[RuleDefinition] = [
    RuleDefinition(
        rule_id="DIM4_001",
        name="Gold tables should have quality rules",
        description="Production tables should have data quality rules defined",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.QUALITY,
        scope=RuleScope.CAPSULE,
        rule_set="quality_expectations",
        condition={
            "if": {"layer": ["gold", "marts", "mart"]},
            "then": {"has_quality_rules": True},
        },
        remediation="Add quality rules to validate data in this production table",
    ),
    RuleDefinition(
        rule_id="DIM4_002",
        name="Primary keys should have uniqueness rules",
        description="Primary key columns must have uniqueness quality rules",
        severity=RuleSeverity.ERROR,
        category=RuleCategory.QUALITY,
        scope=RuleScope.CAPSULE,
        rule_set="quality_expectations",
        condition={"check": "primary_keys_have_uniqueness_rules"},
        remediation="Add uniqueness quality rule for primary key column(s)",
    ),
    RuleDefinition(
        rule_id="DIM4_003",
        name="Critical columns should have completeness rules",
        description="Non-nullable business-critical columns should have completeness > 99%",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.QUALITY,
        scope=RuleScope.COLUMN,
        rule_set="quality_expectations",
        condition={"check": "critical_columns_have_completeness_rules"},
        remediation="Add completeness quality rule with threshold >= 99%",
    ),
    RuleDefinition(
        rule_id="DIM4_004",
        name="Foreign keys should have referential integrity rules",
        description="Foreign key columns should validate referential integrity",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.QUALITY,
        scope=RuleScope.CAPSULE,
        rule_set="quality_expectations",
        condition={"check": "foreign_keys_have_referential_integrity_rules"},
        remediation="Add referential integrity quality rule for foreign key(s)",
    ),
    RuleDefinition(
        rule_id="DIM4_005",
        name="Enumerated columns should have validity rules",
        description="Columns with value domains should have validity/accepted values rules",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.QUALITY,
        scope=RuleScope.COLUMN,
        rule_set="quality_expectations",
        condition={"check": "enum_columns_have_validity_rules"},
        remediation="Add accepted_values quality rule for this column",
    ),
    RuleDefinition(
        rule_id="DIM4_006",
        name="NOT NULL columns need 100% completeness",
        description="Columns with NOT NULL constraint must have completeness threshold of 100%",
        severity=RuleSeverity.ERROR,
        category=RuleCategory.QUALITY,
        scope=RuleScope.COLUMN,
        rule_set="quality_expectations",
        condition={"check": "not_null_columns_100_percent_complete"},
        remediation="Add completeness rule with 100% threshold for NOT NULL column",
    ),
    RuleDefinition(
        rule_id="DIM4_007",
        name="Foreign keys need referential integrity rules",
        description="Every foreign key must have a relationships quality rule",
        severity=RuleSeverity.ERROR,
        category=RuleCategory.QUALITY,
        scope=RuleScope.COLUMN,
        rule_set="quality_expectations",
        condition={"check": "foreign_keys_need_relationships_rules"},
        remediation="Add relationships quality rule for this foreign key",
    ),
    RuleDefinition(
        rule_id="DIM4_008",
        name="Column profiles should be fresh",
        description="Column profiles should be updated within last 7 days for active tables",
        severity=RuleSeverity.INFO,
        category=RuleCategory.QUALITY,
        scope=RuleScope.CAPSULE,
        rule_set="quality_expectations",
        condition={"check": "column_profiles_are_fresh"},
        remediation="Run profiling job to update column statistics",
    ),
    RuleDefinition(
        rule_id="DIM4_009",
        name="Gold tables should have high quality scores",
        description="Production tables should maintain average quality score >= 90%",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.QUALITY,
        scope=RuleScope.CAPSULE,
        rule_set="quality_expectations",
        condition={
            "if": {"layer": ["gold", "marts", "mart"]},
            "then": {"quality_score_threshold": 90.0},
        },
        remediation="Improve data quality to meet production standards",
    ),
    RuleDefinition(
        rule_id="DIM4_010",
        name="Quality rules should be enabled",
        description="At least 80% of defined quality rules should be enabled",
        severity=RuleSeverity.INFO,
        category=RuleCategory.QUALITY,
        scope=RuleScope.CAPSULE,
        rule_set="quality_expectations",
        condition={"check": "quality_rules_mostly_enabled"},
        remediation="Review and enable disabled quality rules or remove obsolete ones",
    ),
]

# Dimension 5: Policy & Governance Rules
POLICY_GOVERNANCE_RULES: list[RuleDefinition] = [
    RuleDefinition(
        rule_id="DIM5_001",
        name="PII tables must have data policies",
        description="Tables containing PII must have explicit data policies defined",
        severity=RuleSeverity.CRITICAL,
        category=RuleCategory.POLICY,
        scope=RuleScope.CAPSULE,
        rule_set="policy_governance",
        condition={"check": "pii_tables_have_data_policies"},
        remediation="Create data policy defining retention, access control, and compliance requirements",
    ),
    RuleDefinition(
        rule_id="DIM5_002",
        name="PII columns must have policies",
        description="Columns tagged as PII must have associated data policies",
        severity=RuleSeverity.CRITICAL,
        category=RuleCategory.POLICY,
        scope=RuleScope.COLUMN,
        rule_set="policy_governance",
        condition={"check": "pii_columns_have_policies"},
        remediation="Create or link data policy for this PII column",
    ),
    RuleDefinition(
        rule_id="DIM5_003",
        name="PII in Gold requires masking rules",
        description="PII columns in Gold layer must have masking rules configured",
        severity=RuleSeverity.CRITICAL,
        category=RuleCategory.POLICY,
        scope=RuleScope.COLUMN,
        rule_set="policy_governance",
        condition={
            "if": {"layer": ["gold", "marts", "mart"], "has_pii": True},
            "then": {"has_masking_rules": True},
        },
        remediation="Configure masking rules (hash, encrypt, tokenize, redact) for this PII column",
    ),
    RuleDefinition(
        rule_id="DIM5_004",
        name="Gold tables should have retention policies",
        description="Production tables should have explicit retention policies",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.POLICY,
        scope=RuleScope.CAPSULE,
        rule_set="policy_governance",
        condition={
            "if": {"layer": ["gold", "marts", "mart"]},
            "then": {"has_retention_policy": True},
        },
        remediation="Define retention policy (duration, archival strategy) for this table",
    ),
    RuleDefinition(
        rule_id="DIM5_005",
        name="Sensitive data needs access controls",
        description="Tables with HIGH or CRITICAL sensitivity must have access controls defined",
        severity=RuleSeverity.ERROR,
        category=RuleCategory.POLICY,
        scope=RuleScope.CAPSULE,
        rule_set="policy_governance",
        condition={"check": "sensitive_data_has_access_controls"},
        remediation="Define access control policy specifying authorized roles/users",
    ),
    RuleDefinition(
        rule_id="DIM5_006",
        name="Compliance frameworks should be documented",
        description="Tables under regulatory compliance should have frameworks documented (GDPR, CCPA, HIPAA, etc.)",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.POLICY,
        scope=RuleScope.CAPSULE,
        rule_set="policy_governance",
        condition={"check": "compliance_frameworks_documented"},
        remediation="Document applicable compliance frameworks in data policy metadata",
    ),
    RuleDefinition(
        rule_id="DIM5_007",
        name="Geographic restrictions should be defined",
        description="Tables with geo-restricted data should have geographic policies",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.POLICY,
        scope=RuleScope.CAPSULE,
        rule_set="policy_governance",
        condition={"check": "geographic_restrictions_defined"},
        remediation="Define geographic restrictions (allowed/blocked regions) in data policy",
    ),
    RuleDefinition(
        rule_id="DIM5_008",
        name="Restricted data requires encryption",
        description="Tables with RESTRICTED or CONFIDENTIAL data must specify encryption requirements",
        severity=RuleSeverity.CRITICAL,
        category=RuleCategory.POLICY,
        scope=RuleScope.CAPSULE,
        rule_set="policy_governance",
        condition={"check": "restricted_data_requires_encryption"},
        remediation="Configure encryption-at-rest and encryption-in-transit requirements in data policy",
    ),
]

# Dimension 6: Provenance & Lineage Rules
PROVENANCE_LINEAGE_RULES: list[RuleDefinition] = [
    RuleDefinition(
        rule_id="DIM6_001",
        name="Gold tables should have version history",
        description="Production tables should track schema version history",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.PROVENANCE,
        scope=RuleScope.CAPSULE,
        rule_set="provenance_lineage",
        condition={
            "if": {"layer": ["gold", "marts", "mart"]},
            "then": {"has_version_history": True},
        },
        remediation="Enable schema versioning to track changes over time",
    ),
    RuleDefinition(
        rule_id="DIM6_002",
        name="Version changes should have descriptions",
        description="Schema version changes should include descriptive change summaries",
        severity=RuleSeverity.INFO,
        category=RuleCategory.PROVENANCE,
        scope=RuleScope.CAPSULE,
        rule_set="provenance_lineage",
        condition={"check": "version_changes_have_descriptions"},
        remediation="Add change summary descriptions when creating new versions",
    ),
    RuleDefinition(
        rule_id="DIM6_003",
        name="Transformation code should be documented",
        description="Tables with transformations should have associated transformation code",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.PROVENANCE,
        scope=RuleScope.CAPSULE,
        rule_set="provenance_lineage",
        condition={
            "if": {"capsule_type": ["model"]},
            "then": {"has_transformation_code": True},
        },
        remediation="Link transformation code (SQL, Python, etc.) to document data logic",
    ),
    RuleDefinition(
        rule_id="DIM6_004",
        name="Breaking changes must be documented",
        description="Schema changes marked as breaking must have detailed documentation",
        severity=RuleSeverity.ERROR,
        category=RuleCategory.PROVENANCE,
        scope=RuleScope.CAPSULE,
        rule_set="provenance_lineage",
        condition={"check": "breaking_changes_documented"},
        remediation="Document breaking changes with migration guide and impact analysis",
    ),
    RuleDefinition(
        rule_id="DIM6_005",
        name="Git integration for version tracking",
        description="Schema versions should be linked to git commits for traceability",
        severity=RuleSeverity.INFO,
        category=RuleCategory.PROVENANCE,
        scope=RuleScope.CAPSULE,
        rule_set="provenance_lineage",
        condition={"check": "versions_linked_to_git"},
        remediation="Configure git integration to track commit SHA with schema versions",
    ),
    RuleDefinition(
        rule_id="DIM6_006",
        name="Deprecated tables should be marked",
        description="Tables scheduled for deprecation should have deprecation metadata",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.PROVENANCE,
        scope=RuleScope.CAPSULE,
        rule_set="provenance_lineage",
        condition={"check": "deprecated_tables_marked"},
        remediation="Add deprecation notice with sunset date and migration path",
    ),
    RuleDefinition(
        rule_id="DIM6_007",
        name="Lineage should be complete",
        description="Tables should have upstream lineage documented for Bronze/Silver, downstream for Gold",
        severity=RuleSeverity.INFO,
        category=RuleCategory.PROVENANCE,
        scope=RuleScope.CAPSULE,
        rule_set="provenance_lineage",
        condition={"check": "lineage_complete_for_layer"},
        remediation="Document data lineage to show data flow and dependencies",
    ),
    RuleDefinition(
        rule_id="DIM6_008",
        name="Column-level lineage for critical columns",
        description="Key business columns should have column-level lineage tracked",
        severity=RuleSeverity.INFO,
        category=RuleCategory.PROVENANCE,
        scope=RuleScope.COLUMN,
        rule_set="provenance_lineage",
        condition={"check": "critical_columns_have_column_lineage"},
        remediation="Enable column-level lineage tracking for this business-critical column",
    ),
]

# Dimension 7: Operational Contract Rules
OPERATIONAL_CONTRACT_RULES: list[RuleDefinition] = [
    RuleDefinition(
        rule_id="DIM7_001",
        name="Gold tables should have contracts",
        description="Production tables should have explicit data contracts defined",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.OPERATIONAL,
        scope=RuleScope.CAPSULE,
        rule_set="operational_contract",
        condition={
            "if": {"layer": ["gold", "marts", "mart"]},
            "then": {"has_contract": True},
        },
        remediation="Create data contract defining SLAs, support, and expectations",
    ),
    RuleDefinition(
        rule_id="DIM7_002",
        name="Contracts should define freshness SLA",
        description="Data contracts must specify freshness/update frequency SLA",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.OPERATIONAL,
        scope=RuleScope.CAPSULE,
        rule_set="operational_contract",
        condition={"check": "contracts_have_freshness_sla"},
        remediation="Add freshness SLA (e.g., updated daily, hourly, real-time) to contract",
    ),
    RuleDefinition(
        rule_id="DIM7_003",
        name="Contracts should define completeness SLA",
        description="Data contracts should specify expected completeness percentage",
        severity=RuleSeverity.INFO,
        category=RuleCategory.OPERATIONAL,
        scope=RuleScope.CAPSULE,
        rule_set="operational_contract",
        condition={"check": "contracts_have_completeness_sla"},
        remediation="Add completeness SLA (e.g., >= 95% complete) to contract",
    ),
    RuleDefinition(
        rule_id="DIM7_004",
        name="Contracts should define quality SLA",
        description="Data contracts should specify minimum quality score thresholds",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.OPERATIONAL,
        scope=RuleScope.CAPSULE,
        rule_set="operational_contract",
        condition={"check": "contracts_have_quality_sla"},
        remediation="Add quality SLA (e.g., quality score >= 90%) to contract",
    ),
    RuleDefinition(
        rule_id="DIM7_005",
        name="Open incidents must be acknowledged within 24h",
        description="SLA incidents must be acknowledged within 24 hours",
        severity=RuleSeverity.ERROR,
        category=RuleCategory.OPERATIONAL,
        scope=RuleScope.CAPSULE,
        rule_set="operational_contract",
        condition={"check": "incidents_acknowledged_within_sla"},
        remediation="Acknowledge open incidents and provide estimated resolution time",
    ),
    RuleDefinition(
        rule_id="DIM7_006",
        name="Critical incidents should be resolved quickly",
        description="Critical SLA incidents should be resolved within 4 hours",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.OPERATIONAL,
        scope=RuleScope.CAPSULE,
        rule_set="operational_contract",
        condition={"check": "critical_incidents_resolved_quickly"},
        remediation="Prioritize and resolve critical incidents to restore service levels",
    ),
    RuleDefinition(
        rule_id="DIM7_007",
        name="Contracts should list support contacts",
        description="Data contracts must specify technical and business support contacts",
        severity=RuleSeverity.INFO,
        category=RuleCategory.OPERATIONAL,
        scope=RuleScope.CAPSULE,
        rule_set="operational_contract",
        condition={"check": "contracts_have_support_contacts"},
        remediation="Add support contact information (technical owner, business owner) to contract",
    ),
    RuleDefinition(
        rule_id="DIM7_008",
        name="Capsule must meet freshness SLA",
        description="Table updates must meet contracted freshness SLA",
        severity=RuleSeverity.ERROR,
        category=RuleCategory.OPERATIONAL,
        scope=RuleScope.CAPSULE,
        rule_set="operational_contract",
        condition={"check": "capsule_meets_freshness_sla"},
        remediation="Investigate and fix data pipeline delays causing SLA violations",
    ),
]

# All built-in rules
ALL_BUILT_IN_RULES = (
    MEDALLION_RULES
    + DBT_BEST_PRACTICES_RULES
    + PII_COMPLIANCE_RULES
    + STRUCTURAL_METADATA_RULES
    + SEMANTIC_METADATA_RULES
    + QUALITY_EXPECTATIONS_RULES
    + POLICY_GOVERNANCE_RULES
    + PROVENANCE_LINEAGE_RULES
    + OPERATIONAL_CONTRACT_RULES
)


class ConformanceService:
    """Service for architecture conformance checking."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.capsule_repo = CapsuleRepository(session)
        self._rules: dict[str, RuleDefinition] = {r.rule_id: r for r in ALL_BUILT_IN_RULES}
        # Lazy-loaded repositories for persistence
        self._rule_repo: Optional["RuleRepository"] = None
        self._violation_repo: Optional["ViolationRepository"] = None
        self._rule_id_cache: dict[str, UUID] = {}  # Maps rule_id str -> DB UUID

    @property
    def rule_repo(self) -> "RuleRepository":
        """Lazy-load rule repository."""
        if self._rule_repo is None:
            from src.repositories.rule import RuleRepository
            self._rule_repo = RuleRepository(self.session)
        return self._rule_repo

    @property
    def violation_repo(self) -> "ViolationRepository":
        """Lazy-load violation repository."""
        if self._violation_repo is None:
            from src.repositories.violation import ViolationRepository
            self._violation_repo = ViolationRepository(self.session)
        return self._violation_repo

    async def sync_rules_to_db(self) -> dict[str, int]:
        """
        Sync in-memory rule definitions to the database.
        Returns counts of created/updated rules.
        """
        from src.models.rule import Rule
        
        db_rules = []
        for rule_def in self._rules.values():
            db_rule = Rule(
                rule_id=rule_def.rule_id,
                name=rule_def.name,
                description=rule_def.description,
                severity=rule_def.severity.value,
                category=rule_def.category.value,
                rule_set=rule_def.rule_set,
                scope=rule_def.scope.value,
                definition={
                    "pattern": rule_def.pattern,
                    "pattern_type": rule_def.pattern_type,
                    "condition": rule_def.condition,
                    "remediation": rule_def.remediation,
                },
                enabled=rule_def.enabled,
                meta={},
            )
            db_rules.append(db_rule)
        
        result = await self.rule_repo.sync_rules(db_rules)
        
        # Update cache with DB UUIDs
        for rule_def in self._rules.values():
            db_rule = await self.rule_repo.get_by_rule_id(rule_def.rule_id)
            if db_rule:
                self._rule_id_cache[rule_def.rule_id] = db_rule.id
        
        return result

    async def _ensure_rules_synced(self) -> None:
        """Ensure rules are synced to DB and cache is populated."""
        if not self._rule_id_cache:
            await self.sync_rules_to_db()

    async def _get_rule_db_id(self, rule_id: str) -> Optional[UUID]:
        """Get the database UUID for a rule_id string."""
        if rule_id not in self._rule_id_cache:
            db_rule = await self.rule_repo.get_by_rule_id(rule_id)
            if db_rule:
                self._rule_id_cache[rule_id] = db_rule.id
        return self._rule_id_cache.get(rule_id)

    def get_available_rules(
        self,
        rule_set: Optional[str] = None,
        category: Optional[str] = None,
        enabled_only: bool = True,
    ) -> list[RuleDefinition]:
        """Get available conformance rules."""
        rules = list(self._rules.values())

        if rule_set:
            rules = [r for r in rules if r.rule_set == rule_set]
        if category:
            rules = [r for r in rules if r.category.value == category]
        if enabled_only:
            rules = [r for r in rules if r.enabled]

        return rules

    def get_rule_sets(self) -> list[str]:
        """Get available rule sets."""
        return list(set(r.rule_set for r in self._rules.values() if r.rule_set))

    async def evaluate(
        self,
        rule_sets: Optional[list[str]] = None,
        categories: Optional[list[str]] = None,
        capsule_urns: Optional[list[str]] = None,
        persist_violations: bool = False,
        ingestion_id: Optional[UUID] = None,
    ) -> ConformanceResult:
        """
        Evaluate conformance against rules.
        
        Args:
            rule_sets: Optional list of rule sets to evaluate
            categories: Optional list of categories to filter
            capsule_urns: Optional list of capsule URNs to evaluate
            persist_violations: If True, save violations to database
            ingestion_id: Optional ingestion job ID to associate with violations
        """
        # Ensure rules are synced to DB if we need to persist
        if persist_violations:
            await self._ensure_rules_synced()
        
        # Get rules to evaluate
        rules = list(self._rules.values())
        if rule_sets:
            rules = [r for r in rules if r.rule_set in rule_sets]
        if categories:
            rules = [r for r in rules if r.category.value in categories]
        rules = [r for r in rules if r.enabled]

        # Get capsules to evaluate
        if capsule_urns:
            capsules = []
            for urn in capsule_urns:
                c = await self.capsule_repo.get_by_urn(urn)
                if c:
                    capsules.append(c)
        else:
            capsules = await self._get_all_capsules_with_relations()

        # Evaluate rules
        violations: list[ViolationInfo] = []
        rule_results: dict[str, dict[str, int]] = {}  # rule_id -> {pass, fail, na}

        for rule in rules:
            rule_results[rule.rule_id] = {"pass": 0, "fail": 0, "na": 0}

            if rule.scope == RuleScope.CAPSULE:
                for capsule in capsules:
                    result, violation = await self._evaluate_capsule_rule(rule, capsule)
                    rule_results[rule.rule_id][result] += 1
                    if violation:
                        violations.append(violation)

            elif rule.scope == RuleScope.COLUMN:
                for capsule in capsules:
                    for column in capsule.columns:
                        result, violation = await self._evaluate_column_rule(rule, column, capsule)
                        rule_results[rule.rule_id][result] += 1
                        if violation:
                            violations.append(violation)

        # Persist violations if requested
        persisted_violation_ids: set[UUID] = set()
        if persist_violations and violations:
            persisted_violation_ids = await self._persist_violations(violations, ingestion_id)

        # Calculate scores
        total_pass = sum(r["pass"] for r in rule_results.values())
        total_fail = sum(r["fail"] for r in rule_results.values())
        total_na = sum(r["na"] for r in rule_results.values())
        total_applicable = total_pass + total_fail

        score = (total_pass / total_applicable * 100) if total_applicable > 0 else 100.0

        # Calculate weighted score
        weighted_pass = 0.0
        weighted_total = 0.0
        for rule_id, results in rule_results.items():
            rule = self._rules[rule_id]
            weight = SEVERITY_WEIGHTS[rule.severity]
            weighted_pass += results["pass"] * weight
            weighted_total += (results["pass"] + results["fail"]) * weight

        weighted_score = (weighted_pass / weighted_total * 100) if weighted_total > 0 else 100.0

        # Group by severity
        by_severity: dict[str, dict[str, int]] = {}
        for sev in RuleSeverity:
            by_severity[sev.value] = {"total": 0, "pass": 0, "fail": 0}

        for rule_id, results in rule_results.items():
            rule = self._rules[rule_id]
            by_severity[rule.severity.value]["total"] += results["pass"] + results["fail"]
            by_severity[rule.severity.value]["pass"] += results["pass"]
            by_severity[rule.severity.value]["fail"] += results["fail"]

        # Group by category
        by_category: dict[str, dict[str, int]] = {}
        for cat in RuleCategory:
            by_category[cat.value] = {"total": 0, "pass": 0, "fail": 0}

        for rule_id, results in rule_results.items():
            rule = self._rules[rule_id]
            by_category[rule.category.value]["total"] += results["pass"] + results["fail"]
            by_category[rule.category.value]["pass"] += results["pass"]
            by_category[rule.category.value]["fail"] += results["fail"]

        return ConformanceResult(
            total_rules=len(rules),
            passing_rules=sum(1 for r in rule_results.values() if r["fail"] == 0),
            failing_rules=sum(1 for r in rule_results.values() if r["fail"] > 0),
            not_applicable=total_na,
            score=round(score, 2),
            weighted_score=round(weighted_score, 2),
            by_severity=by_severity,
            by_category=by_category,
            violations=violations,
        )

    async def _persist_violations(
        self,
        violations: list[ViolationInfo],
        ingestion_id: Optional[UUID] = None,
    ) -> set[UUID]:
        """
        Persist violations to the database.
        Uses upsert to avoid duplicates for the same rule/subject combo.
        Returns set of persisted violation IDs.
        """
        from src.models.violation import Violation
        
        persisted_ids: set[UUID] = set()
        
        for v_info in violations:
            # Get the database UUID for the rule
            rule_db_id = await self._get_rule_db_id(v_info.rule_id)
            if not rule_db_id:
                continue  # Skip if rule not in DB
            
            # Determine subject IDs
            capsule_id = v_info.subject_id if v_info.subject_type == "capsule" else None
            column_id = v_info.subject_id if v_info.subject_type == "column" else None
            
            # For column violations, we also need the capsule_id
            if v_info.subject_type == "column":
                # Get the column to find its capsule
                from src.repositories.column import ColumnRepository
                column_repo = ColumnRepository(self.session)
                column = await column_repo.get_by_id(v_info.subject_id)
                if column:
                    capsule_id = column.capsule_id
            
            violation = Violation(
                rule_id=rule_db_id,
                capsule_id=capsule_id,
                column_id=column_id,
                severity=v_info.severity.value,
                message=v_info.message,
                details=v_info.details,
                ingestion_id=ingestion_id,
            )
            
            persisted, _ = await self.violation_repo.upsert(violation)
            persisted_ids.add(persisted.id)
        
        return persisted_ids

    async def get_violation_history(
        self,
        capsule_id: Optional[UUID] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence["Violation"]:
        """Get violation history with optional filters."""
        from src.models.violation import Violation
        return await self.violation_repo.list_violations(
            status=status,
            severity=severity,
            capsule_id=capsule_id,
            limit=limit,
            offset=offset,
        )

    async def get_violation_summary(self) -> dict[str, Any]:
        """Get summary statistics about violations."""
        open_count = await self.violation_repo.count_violations(status="open")
        by_severity = await self.violation_repo.count_by_severity(status="open")
        by_category = await self.violation_repo.count_by_category(status="open")
        
        return {
            "open_violations": open_count,
            "by_severity": by_severity,
            "by_category": by_category,
        }

    async def _get_all_capsules_with_relations(self) -> Sequence[Capsule]:
        """Get all capsules with columns and lineage loaded."""
        stmt = (
            select(Capsule)
            .options(
                selectinload(Capsule.columns).selectinload(Column.constraints),
                selectinload(Capsule.columns).selectinload(Column.business_term_associations),
                selectinload(Capsule.columns).selectinload(Column.masking_rules),
                selectinload(Capsule.upstream_edges),
                selectinload(Capsule.domain),
                selectinload(Capsule.owner),
                selectinload(Capsule.quality_rules),
                selectinload(Capsule.contracts),
                selectinload(Capsule.tag_associations),
                selectinload(Capsule.versions),
                selectinload(Capsule.transformation_codes),
                selectinload(Capsule.data_policies),
                selectinload(Capsule.sla_incidents),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def _evaluate_capsule_rule(
        self,
        rule: RuleDefinition,
        capsule: Capsule,
    ) -> tuple[str, Optional[ViolationInfo]]:
        """Evaluate a capsule-scope rule. Returns (result, violation)."""
        # Check if rule applies to this capsule
        if rule.condition and "if" in rule.condition:
            if not self._matches_condition(capsule, rule.condition["if"]):
                return "na", None

        violation_info = None

        # Pattern-based rules
        if rule.pattern:
            if not re.match(rule.pattern, capsule.name, re.IGNORECASE):
                violation_info = ViolationInfo(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    category=rule.category,
                    subject_type="capsule",
                    subject_id=capsule.id,
                    subject_urn=capsule.urn,
                    subject_name=capsule.name,
                    message=f"Name '{capsule.name}' does not match pattern '{rule.pattern}'",
                    details={"pattern": rule.pattern, "actual": capsule.name},
                    remediation=rule.remediation,
                )
                return "fail", violation_info
            return "pass", None

        # Condition-based rules
        if rule.condition:
            if "requires" in rule.condition:
                req = rule.condition["requires"]
                if req == "description" and not capsule.description:
                    violation_info = ViolationInfo(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        subject_type="capsule",
                        subject_id=capsule.id,
                        subject_urn=capsule.urn,
                        subject_name=capsule.name,
                        message=f"Model '{capsule.name}' is missing a description",
                        remediation=rule.remediation,
                    )
                    return "fail", violation_info
                elif req == "tests" and not capsule.has_tests:
                    violation_info = ViolationInfo(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        subject_type="capsule",
                        subject_id=capsule.id,
                        subject_urn=capsule.urn,
                        subject_name=capsule.name,
                        message=f"Model '{capsule.name}' has no tests",
                        remediation=rule.remediation,
                    )
                    return "fail", violation_info
                elif req == "has_primary_key":
                    if not any(col.is_primary_key for col in capsule.columns):
                        violation_info = ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="capsule",
                            subject_id=capsule.id,
                            subject_urn=capsule.urn,
                            subject_name=capsule.name,
                            message=f"Table '{capsule.name}' has no primary key",
                            remediation=rule.remediation,
                        )
                        return "fail", violation_info
                elif req == "has_owner":
                    if not capsule.owner_id:
                        violation_info = ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="capsule",
                            subject_id=capsule.id,
                            subject_urn=capsule.urn,
                            subject_name=capsule.name,
                            message=f"Table '{capsule.name}' has no assigned owner",
                            remediation=rule.remediation,
                        )
                        return "fail", violation_info
                elif req == "has_domain":
                    if not capsule.domain_id:
                        violation_info = ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="capsule",
                            subject_id=capsule.id,
                            subject_urn=capsule.urn,
                            subject_name=capsule.name,
                            message=f"Table '{capsule.name}' is not assigned to a business domain",
                            remediation=rule.remediation,
                        )
                        return "fail", violation_info

            # Complex check conditions
            if "check" in rule.condition:
                check = rule.condition["check"]
                violation_info = await self._evaluate_check_condition(rule, capsule, check)
                if violation_info:
                    return "fail", violation_info

            if "then" in rule.condition:
                then = rule.condition["then"]

                # Check upstream layers constraint
                if "upstream_layers" in then:
                    allowed_layers = [l.lower() for l in then["upstream_layers"]]
                    for edge in capsule.upstream_edges:
                        # Get source capsule
                        source = await self.session.get(Capsule, edge.source_id)
                        if source:
                            source_layer = (source.layer or "").lower()
                            if source_layer and source_layer not in allowed_layers:
                                violation_info = ViolationInfo(
                                    rule_id=rule.rule_id,
                                    rule_name=rule.name,
                                    severity=rule.severity,
                                    category=rule.category,
                                    subject_type="capsule",
                                    subject_id=capsule.id,
                                    subject_urn=capsule.urn,
                                    subject_name=capsule.name,
                                    message=f"Model '{capsule.name}' ({capsule.layer}) sources from '{source.name}' ({source_layer}), which violates layer hierarchy",
                                    details={
                                        "source": source.name,
                                        "source_layer": source_layer,
                                        "allowed_layers": allowed_layers,
                                    },
                                    remediation=rule.remediation,
                                )
                                return "fail", violation_info

                # Check has_quality_rules constraint
                if "has_quality_rules" in then and then["has_quality_rules"]:
                    if not capsule.quality_rules:
                        violation_info = ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="capsule",
                            subject_id=capsule.id,
                            subject_urn=capsule.urn,
                            subject_name=capsule.name,
                            message=f"Table '{capsule.name}' has no quality rules defined",
                            remediation=rule.remediation,
                        )
                        return "fail", violation_info

                # Check has_contract constraint
                if "has_contract" in then and then["has_contract"]:
                    if not capsule.contracts:
                        violation_info = ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="capsule",
                            subject_id=capsule.id,
                            subject_urn=capsule.urn,
                            subject_name=capsule.name,
                            message=f"Table '{capsule.name}' has no data contract defined",
                            remediation=rule.remediation,
                        )
                        return "fail", violation_info

                # Check has_tags constraint
                if "has_tags" in then and then["has_tags"]:
                    if not capsule.tag_associations:
                        violation_info = ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="capsule",
                            subject_id=capsule.id,
                            subject_urn=capsule.urn,
                            subject_name=capsule.name,
                            message=f"Table '{capsule.name}' has no business domain tags",
                            remediation=rule.remediation,
                        )
                        return "fail", violation_info

                # Check has_version_history constraint
                if "has_version_history" in then and then["has_version_history"]:
                    if not capsule.versions:
                        violation_info = ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="capsule",
                            subject_id=capsule.id,
                            subject_urn=capsule.urn,
                            subject_name=capsule.name,
                            message=f"Table '{capsule.name}' has no schema version history",
                            remediation=rule.remediation,
                        )
                        return "fail", violation_info

                # Check has_transformation_code constraint
                if "has_transformation_code" in then and then["has_transformation_code"]:
                    if not capsule.transformation_codes:
                        violation_info = ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="capsule",
                            subject_id=capsule.id,
                            subject_urn=capsule.urn,
                            subject_name=capsule.name,
                            message=f"Model '{capsule.name}' has no transformation code documented",
                            remediation=rule.remediation,
                        )
                        return "fail", violation_info

                # Check has_retention_policy constraint
                if "has_retention_policy" in then and then["has_retention_policy"]:
                    has_retention = any(
                        p.retention_period is not None for p in capsule.data_policies
                    ) if capsule.data_policies else False
                    if not has_retention:
                        violation_info = ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="capsule",
                            subject_id=capsule.id,
                            subject_urn=capsule.urn,
                            subject_name=capsule.name,
                            message=f"Table '{capsule.name}' has no retention policy defined",
                            remediation=rule.remediation,
                        )
                        return "fail", violation_info

                # Check quality_score_threshold constraint
                if "quality_score_threshold" in then:
                    threshold = then["quality_score_threshold"]
                    # Calculate average quality score from quality rules
                    if capsule.quality_rules:
                        # This is simplified - in production would need actual quality scores
                        avg_score = sum(
                            getattr(qr, "last_score", 0) for qr in capsule.quality_rules
                        ) / len(capsule.quality_rules) if capsule.quality_rules else 0
                        if avg_score < threshold:
                            violation_info = ViolationInfo(
                                rule_id=rule.rule_id,
                                rule_name=rule.name,
                                severity=rule.severity,
                                category=rule.category,
                                subject_type="capsule",
                                subject_id=capsule.id,
                                subject_urn=capsule.urn,
                                subject_name=capsule.name,
                                message=f"Table '{capsule.name}' quality score ({avg_score:.1f}%) below threshold ({threshold}%)",
                                details={"avg_score": avg_score, "threshold": threshold},
                                remediation=rule.remediation,
                            )
                            return "fail", violation_info

        return "pass", None

    async def _evaluate_column_rule(
        self,
        rule: RuleDefinition,
        column: Column,
        capsule: Capsule,
    ) -> tuple[str, Optional[ViolationInfo]]:
        """Evaluate a column-scope rule. Returns (result, violation)."""
        # Check if rule applies
        if rule.condition and "if" in rule.condition:
            if_cond = rule.condition["if"]

            # Layer filter
            if "layer" in if_cond:
                capsule_layer = (capsule.layer or "").lower()
                if capsule_layer not in [l.lower() for l in if_cond["layer"]]:
                    return "na", None

            # PII filter
            if "has_pii" in if_cond and if_cond["has_pii"]:
                if not column.pii_type:
                    return "na", None

            # Pattern match filter
            if "name_matches_pii_pattern" in if_cond and if_cond["name_matches_pii_pattern"]:
                pii_patterns = [
                    r"(email|e_mail)",
                    r"(phone|telephone|mobile)",
                    r"(ssn|social_security)",
                    r"(address|street|city|zip|postal)",
                    r"(first_name|last_name|full_name)",
                    r"(dob|date_of_birth|birth_date)",
                    r"(credit_card|card_number)",
                ]
                name_lower = column.name.lower()
                if not any(re.search(p, name_lower) for p in pii_patterns):
                    return "na", None

        violation_info = None

        # Condition-based rules
        if rule.condition:
            if "requires" in rule.condition:
                req = rule.condition["requires"]
                if req == "description" and not column.description:
                    violation_info = ViolationInfo(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        subject_type="column",
                        subject_id=column.id,
                        subject_urn=column.urn,
                        subject_name=f"{capsule.name}.{column.name}",
                        message=f"Column '{column.name}' in '{capsule.name}' is missing description",
                        remediation=rule.remediation,
                    )
                    return "fail", violation_info

            if "then" in rule.condition:
                then = rule.condition["then"]

                # Check masking requirement
                if "is_masked" in then and then["is_masked"]:
                    if not self._is_column_masked(column):
                        violation_info = ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="column",
                            subject_id=column.id,
                            subject_urn=column.urn,
                            subject_name=f"{capsule.name}.{column.name}",
                            message=f"PII column '{column.name}' in Gold layer is not masked",
                            details={"pii_type": column.pii_type, "layer": capsule.layer},
                            remediation=rule.remediation,
                        )
                        return "fail", violation_info

                # Check PII tag requirement
                if "has_pii_tag" in then and then["has_pii_tag"]:
                    if not column.pii_type:
                        violation_info = ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="column",
                            subject_id=column.id,
                            subject_urn=column.urn,
                            subject_name=f"{capsule.name}.{column.name}",
                            message=f"Column '{column.name}' appears to contain PII but is not tagged",
                            remediation=rule.remediation,
                        )
                        return "fail", violation_info

                # Check PII type specification
                if "has_pii_type" in then and then["has_pii_type"]:
                    if column.pii_type in ["unknown", "pii", None]:
                        violation_info = ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="column",
                            subject_id=column.id,
                            subject_urn=column.urn,
                            subject_name=f"{capsule.name}.{column.name}",
                            message=f"PII column '{column.name}' does not have specific PII type",
                            details={"current_pii_type": column.pii_type},
                            remediation=rule.remediation,
                        )
                        return "fail", violation_info

                # Check has_masking_rules constraint
                if "has_masking_rules" in then and then["has_masking_rules"]:
                    # Check if column has masking rules configured
                    has_masking = bool(getattr(column, "masking_rules", None))
                    if not has_masking:
                        violation_info = ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="column",
                            subject_id=column.id,
                            subject_urn=column.urn,
                            subject_name=f"{capsule.name}.{column.name}",
                            message=f"PII column '{column.name}' in Gold layer has no masking rules",
                            details={"pii_type": column.pii_type},
                            remediation=rule.remediation,
                        )
                        return "fail", violation_info

            # Complex check conditions for columns
            if "check" in rule.condition:
                check = rule.condition["check"]
                violation_info = await self._evaluate_column_check_condition(rule, column, capsule, check)
                if violation_info:
                    return "fail", violation_info

        return "pass", None

    async def _evaluate_check_condition(
        self,
        rule: RuleDefinition,
        capsule: Capsule,
        check: str,
    ) -> Optional[ViolationInfo]:
        """Evaluate complex check conditions. Returns violation_info if check fails, None if passes."""
        # For simplicity, many checks return None (pass) for now - will be implemented as needed

        # Structural metadata checks (naming conventions require actual constraint/index data)
        if check in [
            "primary_key_naming_convention",
            "foreign_key_naming_convention",
            "unique_constraint_naming_convention",
            "check_constraint_naming_convention",
            "index_naming_convention",
            "foreign_keys_have_indexes",
            "composite_index_selectivity",
        ]:
            # These would require querying constraint/index models
            # For now, return None (pass) - to be implemented with full constraint support
            return None

        # PII policy checks
        if check == "pii_tables_have_data_policies":
            if capsule.has_pii and not capsule.data_policies:
                return ViolationInfo(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    category=rule.category,
                    subject_type="capsule",
                    subject_id=capsule.id,
                    subject_urn=capsule.urn,
                    subject_name=capsule.name,
                    message=f"Table '{capsule.name}' contains PII but has no data policies",
                    details={"pii_column_count": capsule.pii_column_count},
                    remediation=rule.remediation,
                )

        # Quality rule checks
        if check == "primary_keys_have_uniqueness_rules":
            pk_columns = [col for col in capsule.columns if col.is_primary_key]
            if pk_columns:
                # Check if there are uniqueness quality rules for PK columns
                # Simplified check - would need to query quality_rules properly
                if not capsule.quality_rules:
                    return ViolationInfo(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        subject_type="capsule",
                        subject_id=capsule.id,
                        subject_urn=capsule.urn,
                        subject_name=capsule.name,
                        message=f"Table '{capsule.name}' has primary key but no uniqueness quality rules",
                        details={"pk_columns": [col.name for col in pk_columns]},
                        remediation=rule.remediation,
                    )

        if check == "quality_rules_mostly_enabled":
            if capsule.quality_rules:
                total = len(capsule.quality_rules)
                enabled = sum(1 for qr in capsule.quality_rules if qr.is_enabled)
                if total > 0 and (enabled / total) < 0.8:
                    return ViolationInfo(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        subject_type="capsule",
                        subject_id=capsule.id,
                        subject_urn=capsule.urn,
                        subject_name=capsule.name,
                        message=f"Table '{capsule.name}' has {enabled}/{total} quality rules enabled ({enabled/total*100:.0f}% < 80%)",
                        details={"enabled": enabled, "total": total},
                        remediation=rule.remediation,
                    )

        if check == "column_profiles_are_fresh":
            if capsule.last_analyzed_at:
                from datetime import timedelta
                stale_threshold = datetime.now(timezone.utc) - timedelta(days=7)
                if capsule.last_analyzed_at < stale_threshold:
                    days_old = (datetime.now(timezone.utc) - capsule.last_analyzed_at).days
                    return ViolationInfo(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        subject_type="capsule",
                        subject_id=capsule.id,
                        subject_urn=capsule.urn,
                        subject_name=capsule.name,
                        message=f"Table '{capsule.name}' column profiles are {days_old} days old (> 7 days)",
                        details={"last_analyzed_at": capsule.last_analyzed_at.isoformat(), "days_old": days_old},
                        remediation=rule.remediation,
                    )

        # Policy checks
        if check == "sensitive_data_has_access_controls":
            if capsule.data_policies:
                for policy in capsule.data_policies:
                    sensitivity = getattr(policy, "sensitivity_level", "").lower()
                    if sensitivity in ["high", "critical"]:
                        access_controls = getattr(policy, "access_controls", None)
                        if not access_controls:
                            return ViolationInfo(
                                rule_id=rule.rule_id,
                                rule_name=rule.name,
                                severity=rule.severity,
                                category=rule.category,
                                subject_type="capsule",
                                subject_id=capsule.id,
                                subject_urn=capsule.urn,
                                subject_name=capsule.name,
                                message=f"Table '{capsule.name}' has {sensitivity} sensitivity but no access controls",
                                details={"sensitivity": sensitivity},
                                remediation=rule.remediation,
                            )

        # Contract checks
        if check == "contracts_have_freshness_sla":
            if capsule.contracts:
                contract = capsule.contracts[0]
                if not getattr(contract, "freshness_sla_minutes", None):
                    return ViolationInfo(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        subject_type="capsule",
                        subject_id=capsule.id,
                        subject_urn=capsule.urn,
                        subject_name=capsule.name,
                        message=f"Contract for '{capsule.name}' has no freshness SLA defined",
                        remediation=rule.remediation,
                    )

        if check == "contracts_have_completeness_sla":
            if capsule.contracts:
                contract = capsule.contracts[0]
                if not getattr(contract, "completeness_threshold", None):
                    return ViolationInfo(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        subject_type="capsule",
                        subject_id=capsule.id,
                        subject_urn=capsule.urn,
                        subject_name=capsule.name,
                        message=f"Contract for '{capsule.name}' has no completeness SLA defined",
                        remediation=rule.remediation,
                    )

        if check == "contracts_have_quality_sla":
            if capsule.contracts:
                contract = capsule.contracts[0]
                if not getattr(contract, "quality_threshold", None):
                    return ViolationInfo(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        subject_type="capsule",
                        subject_id=capsule.id,
                        subject_urn=capsule.urn,
                        subject_name=capsule.name,
                        message=f"Contract for '{capsule.name}' has no quality SLA defined",
                        remediation=rule.remediation,
                    )

        if check == "contracts_have_support_contacts":
            if capsule.contracts:
                contract = capsule.contracts[0]
                support_contact = getattr(contract, "support_contact", None)
                if not support_contact:
                    return ViolationInfo(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        subject_type="capsule",
                        subject_id=capsule.id,
                        subject_urn=capsule.urn,
                        subject_name=capsule.name,
                        message=f"Contract for '{capsule.name}' has no support contacts defined",
                        remediation=rule.remediation,
                    )

        if check == "incidents_acknowledged_within_sla":
            if capsule.sla_incidents:
                from datetime import timedelta
                sla_hours = 24
                cutoff = datetime.now(timezone.utc) - timedelta(hours=sla_hours)
                for incident in capsule.sla_incidents:
                    if incident.status == "open" and incident.created_at < cutoff:
                        if not incident.acknowledged_at:
                            hours_old = (datetime.now(timezone.utc) - incident.created_at).total_seconds() / 3600
                            return ViolationInfo(
                                rule_id=rule.rule_id,
                                rule_name=rule.name,
                                severity=rule.severity,
                                category=rule.category,
                                subject_type="capsule",
                                subject_id=capsule.id,
                                subject_urn=capsule.urn,
                                subject_name=capsule.name,
                                message=f"SLA incident for '{capsule.name}' not acknowledged within 24h ({hours_old:.1f}h old)",
                                details={"incident_id": str(incident.id), "hours_old": hours_old},
                                remediation=rule.remediation,
                            )

        if check == "critical_incidents_resolved_quickly":
            if capsule.sla_incidents:
                from datetime import timedelta
                sla_hours = 4
                cutoff = datetime.now(timezone.utc) - timedelta(hours=sla_hours)
                for incident in capsule.sla_incidents:
                    if incident.severity == "critical" and incident.status == "open" and incident.created_at < cutoff:
                        hours_old = (datetime.now(timezone.utc) - incident.created_at).total_seconds() / 3600
                        return ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="capsule",
                            subject_id=capsule.id,
                            subject_urn=capsule.urn,
                            subject_name=capsule.name,
                            message=f"Critical SLA incident for '{capsule.name}' not resolved within 4h ({hours_old:.1f}h old)",
                            details={"incident_id": str(incident.id), "hours_old": hours_old},
                            remediation=rule.remediation,
                        )

        if check == "capsule_meets_freshness_sla":
            if capsule.contracts and capsule.last_analyzed_at:
                contract = capsule.contracts[0]
                freshness_sla_minutes = getattr(contract, "freshness_sla_minutes", None)
                if freshness_sla_minutes:
                    from datetime import timedelta
                    sla_cutoff = datetime.now(timezone.utc) - timedelta(minutes=freshness_sla_minutes)
                    if capsule.last_analyzed_at < sla_cutoff:
                        minutes_old = (datetime.now(timezone.utc) - capsule.last_analyzed_at).total_seconds() / 60
                        return ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="capsule",
                            subject_id=capsule.id,
                            subject_urn=capsule.urn,
                            subject_name=capsule.name,
                            message=f"Table '{capsule.name}' last updated {minutes_old:.0f}m ago (SLA: {freshness_sla_minutes}m)",
                            details={"minutes_old": minutes_old, "sla_minutes": freshness_sla_minutes},
                            remediation=rule.remediation,
                        )

        # Provenance checks
        if check == "version_changes_have_descriptions":
            if capsule.versions:
                for version in capsule.versions:
                    if not getattr(version, "change_summary", None):
                        return ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="capsule",
                            subject_id=capsule.id,
                            subject_urn=capsule.urn,
                            subject_name=capsule.name,
                            message=f"Schema version for '{capsule.name}' missing change summary",
                            details={"version_id": str(version.id)},
                            remediation=rule.remediation,
                        )

        # Default: pass
        return None

    async def _evaluate_column_check_condition(
        self,
        rule: RuleDefinition,
        column: Column,
        capsule: Capsule,
        check: str,
    ) -> Optional[ViolationInfo]:
        """Evaluate complex column-level check conditions. Returns violation_info if check fails, None if passes."""

        # Semantic checks
        if check == "key_columns_have_business_terms":
            key_patterns = [r"_id$", r"^id$", r"name", r"amount", r"date", r"_date$"]
            column_name_lower = column.name.lower()
            if any(re.search(p, column_name_lower) for p in key_patterns):
                # Check if column has business term associations
                has_business_terms = bool(getattr(column, "business_term_associations", None))
                if not has_business_terms:
                    return ViolationInfo(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        subject_type="column",
                        subject_id=column.id,
                        subject_urn=column.urn,
                        subject_name=f"{capsule.name}.{column.name}",
                        message=f"Key business column '{column.name}' has no linked business terms",
                        remediation=rule.remediation,
                    )

        if check in ["enum_columns_have_value_domains", "code_status_columns_have_value_domains"]:
            column_name_lower = column.name.lower()
            is_enum_candidate = False

            if check == "code_status_columns_have_value_domains":
                is_enum_candidate = column_name_lower.endswith("_code") or column_name_lower.endswith("_status")
            else:
                # Check if column looks like an enumeration (small cardinality, string type)
                is_enum_candidate = column.data_type in ["VARCHAR", "TEXT", "CHAR", "STRING"]

            if is_enum_candidate:
                has_value_domain = bool(getattr(column, "value_domain_id", None))
                if not has_value_domain:
                    return ViolationInfo(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        subject_type="column",
                        subject_id=column.id,
                        subject_urn=column.urn,
                        subject_name=f"{capsule.name}.{column.name}",
                        message=f"Enumerated column '{column.name}' has no value domain",
                        remediation=rule.remediation,
                    )

        # Policy checks
        if check == "pii_columns_have_policies":
            if column.pii_type:
                # Check if column has associated policies via capsule.data_policies
                # or via column-specific policy associations
                has_policies = bool(capsule.data_policies)
                if not has_policies:
                    return ViolationInfo(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        subject_type="column",
                        subject_id=column.id,
                        subject_urn=column.urn,
                        subject_name=f"{capsule.name}.{column.name}",
                        message=f"PII column '{column.name}' has no associated data policies",
                        details={"pii_type": column.pii_type},
                        remediation=rule.remediation,
                    )

        # Quality checks
        if check in [
            "critical_columns_have_completeness_rules",
            "not_null_columns_100_percent_complete",
            "foreign_keys_need_relationships_rules",
            "enum_columns_have_validity_rules",
        ]:
            # These would require querying quality_rules for specific column
            # Simplified check - returns None (pass) for now
            return None

        # Default: pass
        return None

    def _matches_condition(self, capsule: Capsule, condition: dict) -> bool:
        """Check if a capsule matches a condition."""
        if "layer" in condition:
            capsule_layer = (capsule.layer or "").lower()
            allowed_layers = [l.lower() for l in condition["layer"]]
            if capsule_layer not in allowed_layers:
                return False
        if "capsule_type" in condition:
            capsule_type = (capsule.capsule_type or "").lower()
            allowed_types = [t.lower() for t in condition["capsule_type"]]
            if capsule_type not in allowed_types:
                return False
        return True

    def _is_column_masked(self, column: Column) -> bool:
        """Check if a column appears to be masked."""
        name_lower = column.name.lower()
        masking_indicators = [
            "_hash", "_hashed", "_masked", "_encrypted", "_redacted",
            "_anonymized", "_tokenized", "_obfuscated",
            "hash_", "masked_", "encrypted_",
        ]
        if any(ind in name_lower for ind in masking_indicators):
            return True

        meta = column.meta or {}
        if meta.get("masked") or meta.get("hashed") or meta.get("encrypted"):
            return True
        if meta.get("transformation") in ["hash", "mask", "encrypt", "redact"]:
            return True

        return False

    async def get_violations(
        self,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        rule_set: Optional[str] = None,
        capsule_urn: Optional[str] = None,
        limit: int = 100,
    ) -> list[ViolationInfo]:
        """Get violations from the latest evaluation."""
        # Run evaluation and filter violations
        result = await self.evaluate(
            rule_sets=[rule_set] if rule_set else None,
            categories=[category] if category else None,
            capsule_urns=[capsule_urn] if capsule_urn else None,
        )

        violations = result.violations

        if severity:
            violations = [v for v in violations if v.severity.value == severity]

        return violations[:limit]

    def load_custom_rules(self, yaml_content: str, rule_set_name: Optional[str] = None) -> list[RuleDefinition]:
        """Load custom rules from YAML content.

        YAML Format:
        ```yaml
        rules:
          - id: CUSTOM_001
            name: "Custom rule name"
            description: "Rule description"
            severity: warning  # critical, error, warning, info
            category: naming   # naming, lineage, pii, documentation, testing, architecture
            scope: capsule     # capsule, column
            pattern: "^(prefix_).*"  # optional regex pattern
            condition:         # optional conditions
              if:
                layer: [gold, silver]
              then:
                requires: description
            remediation: "How to fix this violation"
        ```
        """
        parsed = yaml.safe_load(yaml_content)
        if not parsed or "rules" not in parsed:
            raise ValueError("Invalid YAML: must contain 'rules' key")

        loaded_rules: list[RuleDefinition] = []
        rules_data = parsed["rules"]

        if not isinstance(rules_data, list):
            raise ValueError("Invalid YAML: 'rules' must be a list")

        for rule_data in rules_data:
            try:
                # Validate required fields
                required_fields = ["id", "name", "description", "severity", "category", "scope"]
                for field in required_fields:
                    if field not in rule_data:
                        raise ValueError(f"Rule missing required field: {field}")

                # Parse severity
                severity_str = rule_data["severity"].lower()
                try:
                    severity = RuleSeverity(severity_str)
                except ValueError:
                    raise ValueError(f"Invalid severity: {severity_str}. Must be one of: critical, error, warning, info")

                # Parse category
                category_str = rule_data["category"].lower()
                try:
                    category = RuleCategory(category_str)
                except ValueError:
                    raise ValueError(f"Invalid category: {category_str}")

                # Parse scope
                scope_str = rule_data["scope"].lower()
                try:
                    scope = RuleScope(scope_str)
                except ValueError:
                    raise ValueError(f"Invalid scope: {scope_str}. Must be one of: capsule, column, lineage")

                rule = RuleDefinition(
                    rule_id=rule_data["id"],
                    name=rule_data["name"],
                    description=rule_data["description"],
                    severity=severity,
                    category=category,
                    scope=scope,
                    rule_set=rule_set_name or rule_data.get("rule_set", "custom"),
                    enabled=rule_data.get("enabled", True),
                    pattern=rule_data.get("pattern"),
                    pattern_type=rule_data.get("pattern_type", "regex"),
                    condition=rule_data.get("condition"),
                    remediation=rule_data.get("remediation"),
                )

                loaded_rules.append(rule)
                # Add to internal rules dict
                self._rules[rule.rule_id] = rule

            except Exception as e:
                raise ValueError(f"Error parsing rule {rule_data.get('id', 'unknown')}: {str(e)}")

        return loaded_rules

    def load_rules_from_file(self, file_path: str, rule_set_name: Optional[str] = None) -> list[RuleDefinition]:
        """Load custom rules from a YAML file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Rules file not found: {file_path}")

        yaml_content = path.read_text()
        return self.load_custom_rules(yaml_content, rule_set_name)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID. Returns True if removed."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def clear_custom_rules(self) -> int:
        """Remove all custom rules (non-builtin). Returns count removed."""
        builtin_ids = {r.rule_id for r in ALL_BUILT_IN_RULES}
        custom_ids = [rid for rid in self._rules.keys() if rid not in builtin_ids]
        for rid in custom_ids:
            del self._rules[rid]
        return len(custom_ids)

    def export_rules_yaml(self, rule_set: Optional[str] = None) -> str:
        """Export rules to YAML format."""
        rules = self.get_available_rules(rule_set=rule_set, enabled_only=False)

        rules_data = {
            "rules": [
                {
                    "id": r.rule_id,
                    "name": r.name,
                    "description": r.description,
                    "severity": r.severity.value,
                    "category": r.category.value,
                    "scope": r.scope.value,
                    "rule_set": r.rule_set,
                    "enabled": r.enabled,
                    "pattern": r.pattern,
                    "condition": r.condition,
                    "remediation": r.remediation,
                }
                for r in rules
            ]
        }

        return yaml.dump(rules_data, default_flow_style=False, sort_keys=False)

    async def update_rule(self, rule_id: str, enabled: bool) -> bool:
        """Update a rule's enabled status.

        Args:
            rule_id: The rule ID to update.
            enabled: Whether the rule should be enabled.

        Returns:
            True if the rule was updated, False if not found.
        """
        if rule_id not in self._rules:
            return False

        # Update in-memory rule
        rule = self._rules[rule_id]
        self._rules[rule_id] = RuleDefinition(
            rule_id=rule.rule_id,
            name=rule.name,
            description=rule.description,
            severity=rule.severity,
            category=rule.category,
            scope=rule.scope,
            rule_set=rule.rule_set,
            enabled=enabled,
            pattern=rule.pattern,
            pattern_type=rule.pattern_type,
            condition=rule.condition,
            remediation=rule.remediation,
        )

        # Sync to database
        db_rule = await self.rule_repo.get_by_rule_id(rule_id)
        if db_rule:
            db_rule.enabled = enabled
            await self.session.commit()

        return True

    async def test_rule(
        self,
        rule_id: str,
        capsule_urns: Optional[list[str]] = None,
    ) -> ConformanceResult:
        """Test a single rule against specific capsules.

        Args:
            rule_id: The rule ID to test.
            capsule_urns: Optional list of capsule URNs to test against.
                         If None, tests against all capsules.

        Returns:
            EvaluationResult with violations for this rule only.

        Raises:
            ValueError: If rule_id is not found.
        """
        if rule_id not in self._rules:
            raise ValueError(f"Rule not found: {rule_id}")

        rule = self._rules[rule_id]

        # Get capsules to test
        if capsule_urns:
            capsules = []
            for urn in capsule_urns:
                capsule = await self.capsule_repo.get_by_urn(urn)
                if capsule:
                    capsules.append(capsule)
        else:
            # Get all capsules
            capsules = await self.capsule_repo.get_all()

        # Evaluate the single rule
        violations: list[ViolationInfo] = []
        rules_checked = 0

        for capsule in capsules:
            if rule.scope == RuleScope.CAPSULE:
                status, violation_info = await self._evaluate_capsule_rule(rule, capsule)
                rules_checked += 1
                if status == "fail" and violation_info:
                    violations.append(violation_info)
            elif rule.scope == RuleScope.COLUMN:
                for column in capsule.columns:
                    status, violation_info = await self._evaluate_column_rule(rule, column, capsule)
                    rules_checked += 1
                    if status == "fail" and violation_info:
                        violations.append(violation_info)

        # Calculate score
        passing_rules = rules_checked - len(violations)
        score = (passing_rules / rules_checked * 100) if rules_checked > 0 else 100.0

        # Create result with single rule category
        by_severity = {}
        by_category = {}

        severity_key = rule.severity.value
        by_severity[severity_key] = {
            "total": rules_checked,
            "pass": passing_rules,
            "fail": len(violations),
        }

        category_key = rule.category.value
        by_category[category_key] = {
            "total": rules_checked,
            "pass": passing_rules,
            "fail": len(violations),
        }

        return ConformanceResult(
            score=score,
            weighted_score=score,  # Same as score for single rule
            total_rules=1,  # Only one rule tested
            passing_rules=1 if len(violations) == 0 else 0,
            failing_rules=1 if len(violations) > 0 else 0,
            not_applicable=0,
            by_severity=by_severity,
            by_category=by_category,
            violations=violations,
        )
