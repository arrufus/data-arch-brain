"""Repository layer for data access."""

from src.repositories.base import BaseRepository
from src.repositories.capsule import CapsuleRepository
from src.repositories.column import ColumnRepository
from src.repositories.data_product import CapsuleDataProductRepository, DataProductRepository
from src.repositories.domain import DomainRepository, OwnerRepository
from src.repositories.ingestion import IngestionJobRepository
from src.repositories.lineage import CapsuleLineageRepository, ColumnLineageRepository
from src.repositories.rule import RuleRepository
from src.repositories.source_system import SourceSystemRepository
from src.repositories.tag import CapsuleTagRepository, ColumnTagRepository, TagRepository
from src.repositories.violation import ViolationRepository

__all__ = [
    "BaseRepository",
    "CapsuleRepository",
    "ColumnRepository",
    "CapsuleDataProductRepository",
    "DataProductRepository",
    "DomainRepository",
    "OwnerRepository",
    "IngestionJobRepository",
    "CapsuleLineageRepository",
    "ColumnLineageRepository",
    "RuleRepository",
    "SourceSystemRepository",
    "TagRepository",
    "CapsuleTagRepository",
    "ColumnTagRepository",
    "ViolationRepository",
]
