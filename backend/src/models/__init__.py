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
from src.models.lineage import CapsuleLineage, ColumnLineage, ColumnVersion, TaskColumnEdge
from src.models.masking_rule import MaskingMethod, MaskingRule
from src.models.orchestration_edge import (
    OrchestrationEdgeType,
    PipelineTriggerEdge,
    TaskDataEdge,
    TaskDependencyEdge,
)
from src.models.pipeline import (
    OperationType,
    Pipeline,
    PipelineRun,
    PipelineTask,
    PipelineType,
    RunStatus,
    TaskRun,
    TaskType,
)
from src.models.quality_rule import QualityRule, QualityRuleCategory, QualityRuleSeverity, RuleType
from src.models.rule import Rule, RuleCategory, RuleScope, RuleSeverity
from src.models.sla_incident import IncidentSeverity, IncidentStatus, IncidentType, SLAIncident
from src.models.source_system import SourceSystem
from src.models.transformation_code import CodeLanguage, TransformationCode
from src.models.tag import CapsuleTag, ColumnTag, Tag
from src.models.task_dependency import TaskDependency
from src.models.impact_history import ImpactHistory
from src.models.impact_alert import ImpactAlert
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
    "ColumnVersion",
    "TaskColumnEdge",
    # Masking Rule (Phase 4)
    "MaskingRule",
    "MaskingMethod",
    # Orchestration Edges (Airflow Integration)
    "TaskDataEdge",
    "TaskDependencyEdge",
    "PipelineTriggerEdge",
    "OrchestrationEdgeType",
    # Pipeline (Airflow Integration)
    "Pipeline",
    "PipelineTask",
    "PipelineRun",
    "TaskRun",
    "PipelineType",
    "TaskType",
    "OperationType",
    "RunStatus",
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
    # Task Dependency (Phase 8)
    "TaskDependency",
    # Impact History (Phase 8)
    "ImpactHistory",
    # Impact Alert (Phase 8)
    "ImpactAlert",
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
