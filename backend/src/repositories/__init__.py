"""Repository layer for data access."""

from src.repositories.base import BaseRepository
from src.repositories.business_term import (
    BusinessTermRepository,
    CapsuleBusinessTermRepository,
    ColumnBusinessTermRepository,
)
from src.repositories.capsule import CapsuleRepository
from src.repositories.column import ColumnRepository
from src.repositories.column_profile import ColumnProfileRepository
from src.repositories.constraint import ColumnConstraintRepository
from src.repositories.data_policy import DataPolicyRepository
from src.repositories.data_product import CapsuleDataProductRepository, DataProductRepository
from src.repositories.domain import DomainRepository, OwnerRepository
from src.repositories.index import CapsuleIndexRepository
from src.repositories.ingestion import IngestionJobRepository
from src.repositories.lineage import CapsuleLineageRepository, ColumnLineageRepository
from src.repositories.masking_rule import MaskingRuleRepository
from src.repositories.quality_rule import QualityRuleRepository
from src.repositories.rule import RuleRepository
from src.repositories.source_system import SourceSystemRepository
from src.repositories.tag import CapsuleTagRepository, ColumnTagRepository, TagRepository
from src.repositories.value_domain import ValueDomainRepository
from src.repositories.violation import ViolationRepository

__all__ = [
    "BaseRepository",
    # Phase 2: Business Term repositories
    "BusinessTermRepository",
    "CapsuleBusinessTermRepository",
    "ColumnBusinessTermRepository",
    "CapsuleRepository",
    "ColumnRepository",
    # Phase 3: Column Profile repository
    "ColumnProfileRepository",
    # Phase 1: Constraint repository
    "ColumnConstraintRepository",
    # Phase 4: Data Policy repository
    "DataPolicyRepository",
    "CapsuleDataProductRepository",
    "DataProductRepository",
    "DomainRepository",
    "OwnerRepository",
    # Phase 1: Index repository
    "CapsuleIndexRepository",
    "IngestionJobRepository",
    "CapsuleLineageRepository",
    "ColumnLineageRepository",
    # Phase 4: Masking Rule repository
    "MaskingRuleRepository",
    # Phase 3: Quality Rule repository
    "QualityRuleRepository",
    "RuleRepository",
    "SourceSystemRepository",
    "TagRepository",
    "CapsuleTagRepository",
    "ColumnTagRepository",
    # Phase 2: Value Domain repository
    "ValueDomainRepository",
    "ViolationRepository",
]
