"""Redundancy detection API endpoints."""

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.api.exceptions import NotFoundError
from src.database import DbSession
from src.services.redundancy import RedundancyService

router = APIRouter(prefix="/redundancy")


# Response Models

class SimilarityScoreResponse(BaseModel):
    """Similarity score breakdown."""

    name_score: float = Field(..., description="Name similarity score (0.0-1.0)")
    schema_score: float = Field(..., description="Schema similarity score (0.0-1.0)")
    lineage_score: float = Field(..., description="Lineage similarity score (0.0-1.0)")
    metadata_score: float = Field(..., description="Metadata similarity score (0.0-1.0)")
    combined_score: float = Field(..., description="Combined weighted score (0.0-1.0)")
    confidence: str = Field(..., description="Confidence level: high, medium, or low")


class SimilarCapsuleResponse(BaseModel):
    """Similar capsule result."""

    capsule_id: str
    capsule_urn: str
    capsule_name: str
    capsule_type: str
    layer: Optional[str] = None
    domain_name: Optional[str] = None
    similarity: SimilarityScoreResponse
    reasons: list[str] = Field(default_factory=list, description="Human-readable reasons")


class SimilarCapsulesResponse(BaseModel):
    """Response for find similar endpoint."""

    target_urn: str
    target_name: str
    threshold: float
    results_count: int
    results: list[SimilarCapsuleResponse]


class ComparisonResponse(BaseModel):
    """Response for comparison endpoint."""

    capsule1: SimilarCapsuleResponse
    capsule2: SimilarCapsuleResponse
    recommendation: str = Field(
        ...,
        description="Recommendation: likely_duplicates, potential_overlap, or distinct"
    )
    explanation: str


class DuplicateCandidateResponse(BaseModel):
    """Duplicate candidate pair."""

    capsule1_urn: str
    capsule1_name: str
    capsule1_layer: Optional[str] = None
    capsule2_urn: str
    capsule2_name: str
    capsule2_layer: Optional[str] = None
    similarity_score: float
    reasons: list[str]


class DuplicateCandidatesResponse(BaseModel):
    """Response for duplicate candidates endpoint."""

    threshold: float
    candidates_count: int
    candidates: list[DuplicateCandidateResponse]


class RedundancyReportResponse(BaseModel):
    """Redundancy report."""

    total_capsules: int
    duplicate_pairs: int
    potential_duplicates: list[DuplicateCandidateResponse]
    by_layer: dict[str, int]
    by_type: dict[str, int]
    savings_estimate: dict


# API Endpoints

@router.get("/capsules/{urn:path}/similar", response_model=SimilarCapsulesResponse)
async def find_similar_capsules(
    urn: str,
    db: DbSession,
    threshold: float = Query(
        0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold (0.0-1.0)"
    ),
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Maximum number of results"
    ),
    same_type_only: bool = Query(
        True,
        description="Only compare capsules of the same type"
    ),
    same_layer_only: bool = Query(
        False,
        description="Only compare capsules in the same layer"
    ),
) -> SimilarCapsulesResponse:
    """
    Find capsules similar to the given URN.

    Uses weighted similarity scoring based on:
    - Name similarity (30%)
    - Schema similarity (35%)
    - Lineage similarity (25%)
    - Metadata similarity (10%)

    Returns results sorted by similarity score (highest first).
    """
    service = RedundancyService(db)

    # Find similar capsules
    results = await service.find_similar(
        urn=urn,
        threshold=threshold,
        limit=limit,
        same_type_only=same_type_only,
        same_layer_only=same_layer_only,
    )

    if not results:
        # Check if target capsule exists
        target = await service.capsule_repo.get_by_urn(urn)
        if not target:
            raise NotFoundError(f"Capsule not found: {urn}")

    # Get target capsule info
    target = await service.capsule_repo.get_by_urn(urn)
    target_name = target.name if target else "Unknown"

    # Convert to response models
    response_results = [
        SimilarCapsuleResponse(
            capsule_id=str(r.capsule_id),
            capsule_urn=r.capsule_urn,
            capsule_name=r.capsule_name,
            capsule_type=r.capsule_type,
            layer=r.layer,
            domain_name=r.domain_name,
            similarity=SimilarityScoreResponse(
                name_score=r.similarity.name_score,
                schema_score=r.similarity.schema_score,
                lineage_score=r.similarity.lineage_score,
                metadata_score=r.similarity.metadata_score,
                combined_score=r.similarity.combined_score,
                confidence=r.similarity.confidence,
            ),
            reasons=r.reasons,
        )
        for r in results
    ]

    return SimilarCapsulesResponse(
        target_urn=urn,
        target_name=target_name,
        threshold=threshold,
        results_count=len(response_results),
        results=response_results,
    )


@router.get("/capsules/{urn:path}/similar/{other_urn:path}", response_model=ComparisonResponse)
async def compare_two_capsules(
    urn: str,
    other_urn: str,
    db: DbSession,
) -> ComparisonResponse:
    """
    Compare two specific capsules for similarity.

    Returns detailed similarity breakdown and recommendation on whether
    the capsules are likely duplicates, have potential overlap, or are distinct.
    """
    service = RedundancyService(db)

    try:
        result1, result2 = await service.compare_capsules(urn, other_urn)
    except ValueError as e:
        raise NotFoundError(str(e))

    # Determine recommendation based on combined score
    score = result1.similarity.combined_score
    if score >= 0.75:
        recommendation = "likely_duplicates"
        explanation = (
            f"High similarity score ({score:.2f}) indicates these are likely duplicate assets. "
            "Consider consolidating them to reduce redundancy."
        )
    elif score >= 0.50:
        recommendation = "potential_overlap"
        explanation = (
            f"Moderate similarity score ({score:.2f}) indicates potential overlap. "
            "Review the differences to determine if consolidation is appropriate."
        )
    else:
        recommendation = "distinct"
        explanation = (
            f"Low similarity score ({score:.2f}) indicates these are distinct assets. "
            "No consolidation recommended."
        )

    # Convert to response models
    capsule1_response = SimilarCapsuleResponse(
        capsule_id=str(result1.capsule_id),
        capsule_urn=result1.capsule_urn,
        capsule_name=result1.capsule_name,
        capsule_type=result1.capsule_type,
        layer=result1.layer,
        domain_name=result1.domain_name,
        similarity=SimilarityScoreResponse(
            name_score=result1.similarity.name_score,
            schema_score=result1.similarity.schema_score,
            lineage_score=result1.similarity.lineage_score,
            metadata_score=result1.similarity.metadata_score,
            combined_score=result1.similarity.combined_score,
            confidence=result1.similarity.confidence,
        ),
        reasons=result1.reasons,
    )

    capsule2_response = SimilarCapsuleResponse(
        capsule_id=str(result2.capsule_id),
        capsule_urn=result2.capsule_urn,
        capsule_name=result2.capsule_name,
        capsule_type=result2.capsule_type,
        layer=result2.layer,
        domain_name=result2.domain_name,
        similarity=SimilarityScoreResponse(
            name_score=result2.similarity.name_score,
            schema_score=result2.similarity.schema_score,
            lineage_score=result2.similarity.lineage_score,
            metadata_score=result2.similarity.metadata_score,
            combined_score=result2.similarity.combined_score,
            confidence=result2.similarity.confidence,
        ),
        reasons=result2.reasons,
    )

    return ComparisonResponse(
        capsule1=capsule1_response,
        capsule2=capsule2_response,
        recommendation=recommendation,
        explanation=explanation,
    )


@router.get("/candidates", response_model=DuplicateCandidatesResponse)
async def get_duplicate_candidates(
    db: DbSession,
    threshold: float = Query(
        0.75,
        ge=0.5,
        le=1.0,
        description="Minimum similarity threshold for duplicates"
    ),
    layer: Optional[str] = Query(None, description="Filter by layer"),
    capsule_type: Optional[str] = Query(None, description="Filter by capsule type"),
) -> DuplicateCandidatesResponse:
    """
    Get high-confidence duplicate candidates.

    Performs pairwise comparison of all capsules (within filters) to identify
    likely duplicates. Use filters to reduce the search space and improve performance.

    Note: This is an O(n²) operation, so it's recommended to use filters for
    large datasets.
    """
    service = RedundancyService(db)

    candidates = await service.find_all_duplicates(
        threshold=threshold,
        capsule_type=capsule_type,
        layer=layer,
    )

    # Convert to response models
    response_candidates = [
        DuplicateCandidateResponse(
            capsule1_urn=c.capsule1_urn,
            capsule1_name=c.capsule1_name,
            capsule1_layer=c.capsule1_layer,
            capsule2_urn=c.capsule2_urn,
            capsule2_name=c.capsule2_name,
            capsule2_layer=c.capsule2_layer,
            similarity_score=c.similarity_score,
            reasons=c.reasons,
        )
        for c in candidates
    ]

    return DuplicateCandidatesResponse(
        threshold=threshold,
        candidates_count=len(response_candidates),
        candidates=response_candidates,
    )


@router.get("/report", response_model=RedundancyReportResponse)
async def get_redundancy_report(
    db: DbSession,
) -> RedundancyReportResponse:
    """
    Get comprehensive redundancy report.

    Analyzes the entire data landscape to identify duplicate and redundant assets,
    providing statistics by layer and type, along with estimated savings from
    consolidation.

    Note: This operation may take some time for large datasets (1000+ capsules).
    """
    service = RedundancyService(db)

    report = await service.get_redundancy_report()

    # Convert potential duplicates to response models
    potential_duplicates = [
        DuplicateCandidateResponse(
            capsule1_urn=c.capsule1_urn,
            capsule1_name=c.capsule1_name,
            capsule1_layer=c.capsule1_layer,
            capsule2_urn=c.capsule2_urn,
            capsule2_name=c.capsule2_name,
            capsule2_layer=c.capsule2_layer,
            similarity_score=c.similarity_score,
            reasons=c.reasons,
        )
        for c in report.potential_duplicates
    ]

    return RedundancyReportResponse(
        total_capsules=report.total_capsules,
        duplicate_pairs=report.duplicate_pairs,
        potential_duplicates=potential_duplicates,
        by_layer=report.by_layer,
        by_type=report.by_type,
        savings_estimate=report.savings_estimate,
    )
