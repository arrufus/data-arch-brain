"""SQLAlchemy models for Data Capsule Server."""

from src.models.base import Base, DCSBase, DCS_SCHEMA
from src.models.capsule import ArchitectureLayer, Capsule, CapsuleType
from src.models.column import Column, PIIDetectionMethod, PIIType, SemanticType
from src.models.data_product import CapsuleDataProduct, CapsuleRole, DataProduct, DataProductStatus
from src.models.domain import Domain, Owner
from src.models.ingestion import IngestionJob, IngestionStatus
from src.models.lineage import CapsuleLineage, ColumnLineage
from src.models.rule import Rule, RuleCategory, RuleScope, RuleSeverity
from src.models.source_system import SourceSystem
from src.models.tag import CapsuleTag, ColumnTag, Tag
from src.models.violation import Violation, ViolationStatus

__all__ = [
    # Base
    "Base",
    "DCSBase",
    "DCS_SCHEMA",
    # Capsule
    "Capsule",
    "CapsuleType",
    "ArchitectureLayer",
    # Column
    "Column",
    "SemanticType",
    "PIIType",
    "PIIDetectionMethod",
    # Data Product
    "DataProduct",
    "DataProductStatus",
    "CapsuleDataProduct",
    "CapsuleRole",
    # Domain
    "Domain",
    "Owner",
    # Ingestion
    "IngestionJob",
    "IngestionStatus",
    # Lineage
    "CapsuleLineage",
    "ColumnLineage",
    # Rule
    "Rule",
    "RuleSeverity",
    "RuleCategory",
    "RuleScope",
    # Source System
    "SourceSystem",
    # Tag
    "Tag",
    "CapsuleTag",
    "ColumnTag",
    # Violation
    "Violation",
    "ViolationStatus",
]
