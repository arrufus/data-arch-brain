"""SQLAlchemy models for Data Capsule Server."""

from src.models.base import Base, DCSBase, DCS_SCHEMA
from src.models.business_term import (
    ApprovalStatus,
    BusinessTerm,
    CapsuleBusinessTerm,
    ColumnBusinessTerm,
    RelationshipType,
)
from src.models.capsule import ArchitectureLayer, Capsule, CapsuleType
from src.models.capsule_contract import (
    CapsuleContract,
    ContractStatus,
    SchemaChangePolicy,
    SupportLevel,
)
from src.models.capsule_version import CapsuleVersion, ChangeType
from src.models.column import Column, PIIDetectionMethod, PIIType, SemanticType
from src.models.column_profile import ColumnProfile
from src.models.constraint import ColumnConstraint, ConstraintType, OnDeleteAction
from src.models.data_policy import DataPolicy, DeletionAction, PolicyStatus, SensitivityLevel
from src.models.data_product import CapsuleDataProduct, CapsuleRole, DataProduct, DataProductStatus
from src.models.domain import Domain, Owner
from src.models.index import CapsuleIndex, IndexType
from src.models.ingestion import IngestionJob, IngestionStatus
from src.models.lineage import CapsuleLineage, ColumnLineage
from src.models.masking_rule import MaskingMethod, MaskingRule
from src.models.quality_rule import QualityRule, QualityRuleCategory, QualityRuleSeverity, RuleType
from src.models.rule import Rule, RuleCategory, RuleScope, RuleSeverity
from src.models.sla_incident import IncidentSeverity, IncidentStatus, IncidentType, SLAIncident
from src.models.source_system import SourceSystem
from src.models.transformation_code import CodeLanguage, TransformationCode
from src.models.tag import CapsuleTag, ColumnTag, Tag
from src.models.value_domain import DomainType, ValueDomain
from src.models.violation import Violation, ViolationStatus

__all__ = [
    # Base
    "Base",
    "DCSBase",
    "DCS_SCHEMA",
    # Business Term (Phase 2)
    "BusinessTerm",
    "ApprovalStatus",
    "CapsuleBusinessTerm",
    "ColumnBusinessTerm",
    "RelationshipType",
    # Capsule
    "Capsule",
    "CapsuleType",
    "ArchitectureLayer",
    # Capsule Contract (Phase 5-6)
    "CapsuleContract",
    "ContractStatus",
    "SchemaChangePolicy",
    "SupportLevel",
    # Capsule Version (Phase 5-6)
    "CapsuleVersion",
    "ChangeType",
    # Column
    "Column",
    "SemanticType",
    "PIIType",
    "PIIDetectionMethod",
    # Column Profile (Phase 3)
    "ColumnProfile",
    # Constraint (Phase 1)
    "ColumnConstraint",
    "ConstraintType",
    "OnDeleteAction",
    # Data Policy (Phase 4)
    "DataPolicy",
    "SensitivityLevel",
    "DeletionAction",
    "PolicyStatus",
    # Data Product
    "DataProduct",
    "DataProductStatus",
    "CapsuleDataProduct",
    "CapsuleRole",
    # Domain
    "Domain",
    "Owner",
    # Index (Phase 1)
    "CapsuleIndex",
    "IndexType",
    # Ingestion
    "IngestionJob",
    "IngestionStatus",
    # Lineage
    "CapsuleLineage",
    "ColumnLineage",
    # Masking Rule (Phase 4)
    "MaskingRule",
    "MaskingMethod",
    # Quality Rule (Phase 3)
    "QualityRule",
    "RuleType",
    "QualityRuleCategory",
    "QualityRuleSeverity",
    # Rule
    "Rule",
    "RuleSeverity",
    "RuleCategory",
    "RuleScope",
    # SLA Incident (Phase 5-6)
    "SLAIncident",
    "IncidentType",
    "IncidentStatus",
    "IncidentSeverity",
    # Source System
    "SourceSystem",
    # Tag
    "Tag",
    "CapsuleTag",
    "ColumnTag",
    # Transformation Code (Phase 5-6)
    "TransformationCode",
    "CodeLanguage",
    # Value Domain (Phase 2)
    "ValueDomain",
    "DomainType",
    # Violation
    "Violation",
    "ViolationStatus",
]
