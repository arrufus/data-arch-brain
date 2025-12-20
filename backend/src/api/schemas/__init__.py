"""Pydantic schemas for API request/response validation."""

from src.api.schemas.business_term import (
    BusinessTermCreate,
    BusinessTermDetail,
    BusinessTermSummary,
    BusinessTermUpdate,
    CapsuleBusinessTermCreate,
    ColumnBusinessTermCreate,
)
from src.api.schemas.capsule_contract import (
    CapsuleContractCreate,
    CapsuleContractDetail,
    CapsuleContractSummary,
    CapsuleContractUpdate,
)
from src.api.schemas.capsule_version import (
    CapsuleVersionCreate,
    CapsuleVersionDetail,
    CapsuleVersionSummary,
    CapsuleVersionUpdate,
)
from src.api.schemas.column_profile import (
    ColumnProfileCreate,
    ColumnProfileDetail,
    ColumnProfileSummary,
)
from src.api.schemas.constraint import (
    ColumnConstraintCreate,
    ColumnConstraintDetail,
    ColumnConstraintSummary,
    ColumnConstraintUpdate,
)
from src.api.schemas.data_policy import (
    DataPolicyCreate,
    DataPolicyDetail,
    DataPolicySummary,
    DataPolicyUpdate,
)
from src.api.schemas.index import (
    CapsuleIndexCreate,
    CapsuleIndexDetail,
    CapsuleIndexSummary,
    CapsuleIndexUpdate,
)
from src.api.schemas.masking_rule import (
    MaskingRuleCreate,
    MaskingRuleDetail,
    MaskingRuleSummary,
    MaskingRuleUpdate,
)
from src.api.schemas.quality_rule import (
    QualityRuleCreate,
    QualityRuleDetail,
    QualityRuleSummary,
    QualityRuleUpdate,
)
from src.api.schemas.sla_incident import (
    SLAIncidentCreate,
    SLAIncidentDetail,
    SLAIncidentSummary,
    SLAIncidentUpdate,
)
from src.api.schemas.transformation_code import (
    TransformationCodeCreate,
    TransformationCodeDetail,
    TransformationCodeSummary,
    TransformationCodeUpdate,
)
from src.api.schemas.value_domain import (
    ValueDomainCreate,
    ValueDomainDetail,
    ValueDomainSummary,
    ValueDomainUpdate,
)

__all__ = [
    # Business term schemas (Phase 2)
    "BusinessTermCreate",
    "BusinessTermDetail",
    "BusinessTermSummary",
    "BusinessTermUpdate",
    "CapsuleBusinessTermCreate",
    "ColumnBusinessTermCreate",
    # Capsule contract schemas (Phase 5-6)
    "CapsuleContractCreate",
    "CapsuleContractDetail",
    "CapsuleContractSummary",
    "CapsuleContractUpdate",
    # Capsule version schemas (Phase 5-6)
    "CapsuleVersionCreate",
    "CapsuleVersionDetail",
    "CapsuleVersionSummary",
    "CapsuleVersionUpdate",
    # Column profile schemas (Phase 3)
    "ColumnProfileCreate",
    "ColumnProfileDetail",
    "ColumnProfileSummary",
    # Constraint schemas (Phase 1)
    "ColumnConstraintCreate",
    "ColumnConstraintDetail",
    "ColumnConstraintSummary",
    "ColumnConstraintUpdate",
    # Data policy schemas (Phase 4)
    "DataPolicyCreate",
    "DataPolicyDetail",
    "DataPolicySummary",
    "DataPolicyUpdate",
    # Index schemas (Phase 1)
    "CapsuleIndexCreate",
    "CapsuleIndexDetail",
    "CapsuleIndexSummary",
    "CapsuleIndexUpdate",
    # Masking rule schemas (Phase 4)
    "MaskingRuleCreate",
    "MaskingRuleDetail",
    "MaskingRuleSummary",
    "MaskingRuleUpdate",
    # Quality rule schemas (Phase 3)
    "QualityRuleCreate",
    "QualityRuleDetail",
    "QualityRuleSummary",
    "QualityRuleUpdate",
    # SLA incident schemas (Phase 5-6)
    "SLAIncidentCreate",
    "SLAIncidentDetail",
    "SLAIncidentSummary",
    "SLAIncidentUpdate",
    # Transformation code schemas (Phase 5-6)
    "TransformationCodeCreate",
    "TransformationCodeDetail",
    "TransformationCodeSummary",
    "TransformationCodeUpdate",
    # Value domain schemas (Phase 2)
    "ValueDomainCreate",
    "ValueDomainDetail",
    "ValueDomainSummary",
    "ValueDomainUpdate",
]
