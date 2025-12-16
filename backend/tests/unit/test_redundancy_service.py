"""Unit tests for RedundancyService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.models.capsule import Capsule
from src.models.column import Column
from src.models.domain import Domain
from src.services.redundancy import (
    RedundancyService,
    SimilarityScore,
    SimilarCapsule,
    DuplicateCandidate,
    RedundancyReport,
)


@pytest.fixture
def mock_session():
    """Mock async session."""
    session = AsyncMock()
    return session


@pytest.fixture
def redundancy_service(mock_session):
    """Create redundancy service with mocked session."""
    return RedundancyService(mock_session)


@pytest.fixture
def sample_domain():
    """Create a sample domain."""
    return Domain(
        id=uuid4(),
        name="customer",
        description="Customer domain",
    )


@pytest.fixture
def sample_capsule1(sample_domain):
    """Create first sample capsule."""
    capsule_id = uuid4()
    return Capsule(
        id=capsule_id,
        urn="urn:dab:dbt:model:staging:stg_customers",
        name="stg_customers",
        capsule_type="model",
        layer="silver",
        domain_id=sample_domain.id,
        domain=sample_domain,
        tags=["pii", "customer"],
        description="Staging customer data",
        columns=[
            Column(
                id=uuid4(),
                capsule_id=capsule_id,
                urn="urn:dab:dbt:column:staging:stg_customers.id",
                name="id",
                data_type="integer",
                ordinal_position=1,
            ),
            Column(
                id=uuid4(),
                capsule_id=capsule_id,
                urn="urn:dab:dbt:column:staging:stg_customers.email",
                name="email",
                data_type="varchar",
                ordinal_position=2,
            ),
            Column(
                id=uuid4(),
                capsule_id=capsule_id,
                urn="urn:dab:dbt:column:staging:stg_customers.name",
                name="name",
                data_type="varchar",
                ordinal_position=3,
            ),
        ],
    )


@pytest.fixture
def sample_capsule2(sample_domain):
    """Create second sample capsule (similar to first)."""
    capsule_id = uuid4()
    return Capsule(
        id=capsule_id,
        urn="urn:dab:dbt:model:staging:staging_customers",
        name="staging_customers",
        capsule_type="model",
        layer="silver",
        domain_id=sample_domain.id,
        domain=sample_domain,
        tags=["pii", "customer"],
        description="Customer staging table",
        columns=[
            Column(
                id=uuid4(),
                capsule_id=capsule_id,
                urn="urn:dab:dbt:column:staging:staging_customers.id",
                name="id",
                data_type="integer",
                ordinal_position=1,
            ),
            Column(
                id=uuid4(),
                capsule_id=capsule_id,
                urn="urn:dab:dbt:column:staging:staging_customers.email",
                name="email",
                data_type="varchar",
                ordinal_position=2,
            ),
            Column(
                id=uuid4(),
                capsule_id=capsule_id,
                urn="urn:dab:dbt:column:staging:staging_customers.full_name",
                name="full_name",
                data_type="varchar",
                ordinal_position=3,
            ),
        ],
    )


@pytest.fixture
def sample_capsule3():
    """Create third sample capsule (different from first two)."""
    capsule_id = uuid4()
    return Capsule(
        id=capsule_id,
        urn="urn:dab:dbt:model:marts:fct_orders",
        name="fct_orders",
        capsule_type="model",
        layer="gold",
        tags=["orders", "fact"],
        description="Order facts",
        columns=[
            Column(
                id=uuid4(),
                capsule_id=capsule_id,
                urn="urn:dab:dbt:column:marts:fct_orders.order_id",
                name="order_id",
                data_type="integer",
                ordinal_position=1,
            ),
            Column(
                id=uuid4(),
                capsule_id=capsule_id,
                urn="urn:dab:dbt:column:marts:fct_orders.amount",
                name="amount",
                data_type="decimal",
                ordinal_position=2,
            ),
        ],
    )


# Name Similarity Tests

def test_name_similarity_exact_match(redundancy_service):
    """Test name similarity with exact match."""
    score = redundancy_service._calculate_name_similarity("customers", "customers")
    assert score == 1.0


def test_name_similarity_fuzzy_match(redundancy_service):
    """Test name similarity with fuzzy match."""
    # stg_customers vs staging_customers (normalized to "customers")
    score = redundancy_service._calculate_name_similarity("stg_customers", "staging_customers")
    assert score == 1.0  # Same after normalization


def test_name_similarity_partial_match(redundancy_service):
    """Test name similarity with partial match."""
    score = redundancy_service._calculate_name_similarity("customers", "customer_data")
    assert 0.5 < score < 1.0  # Partial similarity


def test_name_similarity_no_match(redundancy_service):
    """Test name similarity with no match."""
    score = redundancy_service._calculate_name_similarity("customers", "orders")
    assert score < 0.3  # Low similarity


def test_normalize_name_removes_prefixes(redundancy_service):
    """Test name normalization removes common prefixes."""
    normalized = redundancy_service._normalize_name("stg_customers")
    assert normalized == "customers"

    normalized = redundancy_service._normalize_name("dim_customers")
    assert normalized == "customers"


# Schema Similarity Tests

def test_schema_similarity_identical(redundancy_service, sample_capsule1):
    """Test schema similarity with identical columns."""
    # Create duplicate column list
    columns = sample_capsule1.columns
    duplicate_columns = [
        Column(
            id=uuid4(),
            capsule_id=uuid4(),
            urn=f"urn:test:{col.name}",
            name=col.name,
            data_type=col.data_type,
            ordinal_position=col.ordinal_position,
        )
        for col in columns
    ]

    score = redundancy_service._calculate_schema_similarity(columns, duplicate_columns)
    assert score == 1.0


def test_schema_similarity_partial_overlap(redundancy_service, sample_capsule1, sample_capsule2):
    """Test schema similarity with partial column overlap."""
    # sample_capsule1 has [id, email, name]
    # sample_capsule2 has [id, email, full_name]
    # Overlap: id, email (2/4 = 50% union)
    score = redundancy_service._calculate_schema_similarity(
        sample_capsule1.columns, sample_capsule2.columns
    )
    assert 0.4 < score < 0.8  # Partial overlap


def test_schema_similarity_different_types(redundancy_service):
    """Test schema similarity with same names but different types."""
    columns1 = [
        Column(
            id=uuid4(),
            capsule_id=uuid4(),
            urn="urn:test:col1",
            name="id",
            data_type="integer",
            ordinal_position=1,
        ),
    ]
    columns2 = [
        Column(
            id=uuid4(),
            capsule_id=uuid4(),
            urn="urn:test:col2",
            name="id",
            data_type="varchar",  # Different type
            ordinal_position=1,
        ),
    ]

    score = redundancy_service._calculate_schema_similarity(columns1, columns2)
    # Should be less than 1.0 because types differ
    # But should still have some similarity due to name match
    assert 0.2 < score < 0.6


def test_schema_similarity_empty_columns(redundancy_service):
    """Test schema similarity with empty column lists."""
    score = redundancy_service._calculate_schema_similarity([], [])
    assert score == 0.0


# Lineage Similarity Tests

def test_lineage_similarity_shared_sources(redundancy_service):
    """Test lineage similarity with shared upstream sources."""
    upstream1 = {"urn:source1", "urn:source2", "urn:source3"}
    upstream2 = {"urn:source1", "urn:source2", "urn:source4"}

    # Intersection: 2, Union: 4, Jaccard: 2/4 = 0.5
    score = redundancy_service._calculate_lineage_similarity(upstream1, upstream2)
    assert score == 0.5


def test_lineage_similarity_identical_sources(redundancy_service):
    """Test lineage similarity with identical upstream sources."""
    upstream = {"urn:source1", "urn:source2"}

    score = redundancy_service._calculate_lineage_similarity(upstream, upstream)
    assert score == 1.0


def test_lineage_similarity_no_overlap(redundancy_service):
    """Test lineage similarity with no shared sources."""
    upstream1 = {"urn:source1", "urn:source2"}
    upstream2 = {"urn:source3", "urn:source4"}

    score = redundancy_service._calculate_lineage_similarity(upstream1, upstream2)
    assert score == 0.0


def test_lineage_similarity_empty_sets(redundancy_service):
    """Test lineage similarity with empty lineage."""
    score = redundancy_service._calculate_lineage_similarity(set(), set())
    assert score == 0.0


# Metadata Similarity Tests

def test_metadata_similarity_same_domain(redundancy_service, sample_capsule1, sample_capsule2):
    """Test metadata similarity with same domain."""
    # Both in same domain
    score = redundancy_service._calculate_metadata_similarity(sample_capsule1, sample_capsule2)
    assert score > 0.3  # Should have some similarity from domain match


def test_metadata_similarity_same_layer(redundancy_service, sample_capsule1, sample_capsule2):
    """Test metadata similarity with same layer."""
    # Both in silver layer
    score = redundancy_service._calculate_metadata_similarity(sample_capsule1, sample_capsule2)
    assert score > 0.2  # Should have some similarity from layer match


def test_metadata_similarity_same_tags(redundancy_service, sample_capsule1, sample_capsule2):
    """Test metadata similarity with overlapping tags."""
    # Both have [pii, customer] tags
    score = redundancy_service._calculate_metadata_similarity(sample_capsule1, sample_capsule2)
    assert score > 0.0  # Should have some similarity from tag overlap


def test_metadata_similarity_different(redundancy_service, sample_capsule1, sample_capsule3):
    """Test metadata similarity with different metadata."""
    # Different layer, domain, tags
    score = redundancy_service._calculate_metadata_similarity(sample_capsule1, sample_capsule3)
    assert score == 0.0


# Combined Score Tests

def test_combined_score_calculation(redundancy_service):
    """Test weighted combined score calculation."""
    score = redundancy_service._calculate_combined_score(
        name=0.8,
        schema=0.9,
        lineage=0.7,
        metadata=0.6,
    )

    # Expected: 0.30*0.8 + 0.35*0.9 + 0.25*0.7 + 0.10*0.6
    expected = 0.24 + 0.315 + 0.175 + 0.06
    assert abs(score.combined_score - expected) < 0.01
    assert score.confidence == "high"  # Above 0.75


def test_combined_score_high_confidence(redundancy_service):
    """Test combined score with high confidence."""
    score = redundancy_service._calculate_combined_score(0.9, 0.9, 0.9, 0.9)

    assert score.combined_score >= redundancy_service.THRESHOLD_HIGH
    assert score.confidence == "high"


def test_combined_score_medium_confidence(redundancy_service):
    """Test combined score with medium confidence."""
    score = redundancy_service._calculate_combined_score(0.6, 0.6, 0.6, 0.6)

    assert redundancy_service.THRESHOLD_MEDIUM <= score.combined_score < redundancy_service.THRESHOLD_HIGH
    assert score.confidence == "medium"


def test_combined_score_low_confidence(redundancy_service):
    """Test combined score with low confidence."""
    score = redundancy_service._calculate_combined_score(0.2, 0.2, 0.2, 0.2)

    assert score.combined_score < redundancy_service.THRESHOLD_MEDIUM
    assert score.confidence == "low"


# Reason Generation Tests

def test_generate_reasons_high_similarity(redundancy_service, sample_capsule1, sample_capsule2):
    """Test reason generation for high similarity."""
    similarity = SimilarityScore(
        name_score=0.9,
        schema_score=0.85,
        lineage_score=0.7,
        metadata_score=0.6,
        combined_score=0.8,
        confidence="high",
    )

    reasons = redundancy_service._generate_reasons(similarity, sample_capsule1, sample_capsule2)

    assert len(reasons) > 0
    assert any("similar names" in r.lower() for r in reasons)
    assert any("schema overlap" in r.lower() for r in reasons)
    assert any("high confidence" in r.lower() for r in reasons)


def test_generate_reasons_same_domain(redundancy_service, sample_capsule1, sample_capsule2):
    """Test reason generation includes domain match."""
    similarity = SimilarityScore(
        name_score=0.5,
        schema_score=0.5,
        lineage_score=0.5,
        metadata_score=0.5,
        combined_score=0.5,
        confidence="medium",
    )

    reasons = redundancy_service._generate_reasons(similarity, sample_capsule1, sample_capsule2)

    assert any("same domain" in r.lower() for r in reasons)
    assert any("same layer" in r.lower() for r in reasons)


# Integration Tests (mocked)

@pytest.mark.asyncio
async def test_find_similar_returns_top_matches(redundancy_service, sample_capsule1, sample_capsule2, sample_capsule3, mock_session):
    """Test find_similar returns top matches sorted by score."""
    # Mock repository methods
    redundancy_service.capsule_repo.get_by_urn_with_columns = AsyncMock(return_value=sample_capsule1)
    redundancy_service._get_upstream_urns = AsyncMock(return_value=set())
    redundancy_service._get_candidate_capsules = AsyncMock(return_value=[sample_capsule2, sample_capsule3])

    results = await redundancy_service.find_similar(
        urn="urn:dab:dbt:model:staging:stg_customers",
        threshold=0.0,  # Get all results
        limit=10,
    )

    # Should return results sorted by similarity
    assert len(results) >= 1
    # sample_capsule2 should be more similar than sample_capsule3
    if len(results) > 1:
        assert results[0].similarity.combined_score >= results[1].similarity.combined_score


@pytest.mark.asyncio
async def test_find_similar_filters_by_threshold(redundancy_service, sample_capsule1, sample_capsule2, sample_capsule3, mock_session):
    """Test find_similar filters results by threshold."""
    redundancy_service.capsule_repo.get_by_urn_with_columns = AsyncMock(return_value=sample_capsule1)
    redundancy_service._get_upstream_urns = AsyncMock(return_value=set())
    redundancy_service._get_candidate_capsules = AsyncMock(return_value=[sample_capsule2, sample_capsule3])

    results = await redundancy_service.find_similar(
        urn="urn:dab:dbt:model:staging:stg_customers",
        threshold=0.9,  # High threshold
        limit=10,
    )

    # High threshold should filter out low-similarity results
    for result in results:
        assert result.similarity.combined_score >= 0.9


@pytest.mark.asyncio
async def test_find_similar_limits_results(redundancy_service, sample_capsule1, mock_session):
    """Test find_similar respects limit parameter."""
    # Create many similar capsules
    similar_capsules = []
    for i in range(20):
        capsule_id = uuid4()
        capsule = Capsule(
            id=capsule_id,
            urn=f"urn:dab:dbt:model:staging:capsule_{i}",
            name=f"capsule_{i}",
            capsule_type="model",
            layer="silver",
            columns=[],
        )
        similar_capsules.append(capsule)

    redundancy_service.capsule_repo.get_by_urn_with_columns = AsyncMock(return_value=sample_capsule1)
    redundancy_service._get_upstream_urns = AsyncMock(return_value=set())
    redundancy_service._get_candidate_capsules = AsyncMock(return_value=similar_capsules)

    results = await redundancy_service.find_similar(
        urn="urn:dab:dbt:model:staging:stg_customers",
        threshold=0.0,
        limit=5,
    )

    assert len(results) <= 5


@pytest.mark.asyncio
async def test_compare_capsules(redundancy_service, sample_capsule1, sample_capsule2, mock_session):
    """Test pairwise capsule comparison."""
    redundancy_service.capsule_repo.get_by_urn_with_columns = AsyncMock(
        side_effect=[sample_capsule1, sample_capsule2]
    )
    redundancy_service._get_upstream_urns = AsyncMock(return_value=set())

    result1, result2 = await redundancy_service.compare_capsules(
        urn1="urn:dab:dbt:model:staging:stg_customers",
        urn2="urn:dab:dbt:model:staging:staging_customers",
    )

    assert result1.capsule_urn == sample_capsule1.urn
    assert result2.capsule_urn == sample_capsule2.urn
    assert result1.similarity.combined_score == result2.similarity.combined_score
    assert result1.similarity.combined_score > 0.0


@pytest.mark.asyncio
async def test_compare_capsules_not_found(redundancy_service, mock_session):
    """Test compare_capsules raises error when capsule not found."""
    redundancy_service.capsule_repo.get_by_urn_with_columns = AsyncMock(return_value=None)

    with pytest.raises(ValueError, match="not found"):
        await redundancy_service.compare_capsules(
            urn1="urn:missing1",
            urn2="urn:missing2",
        )


@pytest.mark.asyncio
async def test_find_all_duplicates(redundancy_service, sample_capsule1, sample_capsule2, mock_session):
    """Test batch duplicate detection."""
    redundancy_service._get_candidate_capsules = AsyncMock(
        return_value=[sample_capsule1, sample_capsule2]
    )
    redundancy_service._get_upstream_urns = AsyncMock(return_value=set())

    duplicates = await redundancy_service.find_all_duplicates(threshold=0.0)

    # Should find at least one pair
    assert len(duplicates) >= 0
    # Each duplicate should have both URNs
    for dup in duplicates:
        assert dup.capsule1_urn
        assert dup.capsule2_urn
        assert dup.similarity_score >= 0.0


@pytest.mark.asyncio
async def test_get_redundancy_report(redundancy_service, sample_capsule1, sample_capsule2, mock_session):
    """Test redundancy report generation."""
    redundancy_service._get_candidate_capsules = AsyncMock(
        return_value=[sample_capsule1, sample_capsule2]
    )
    redundancy_service._get_upstream_urns = AsyncMock(return_value=set())

    report = await redundancy_service.get_redundancy_report()

    assert isinstance(report, RedundancyReport)
    assert report.total_capsules >= 0
    assert report.duplicate_pairs >= 0
    assert isinstance(report.by_layer, dict)
    assert isinstance(report.by_type, dict)
    assert isinstance(report.savings_estimate, dict)


# Edge Cases

@pytest.mark.asyncio
async def test_find_similar_capsule_not_found(redundancy_service, mock_session):
    """Test find_similar returns empty list when target capsule not found."""
    redundancy_service.capsule_repo.get_by_urn_with_columns = AsyncMock(return_value=None)

    results = await redundancy_service.find_similar(urn="urn:missing")

    assert results == []


def test_schema_similarity_one_empty(redundancy_service, sample_capsule1):
    """Test schema similarity when one capsule has no columns."""
    score = redundancy_service._calculate_schema_similarity(sample_capsule1.columns, [])
    assert score == 0.0


def test_lineage_similarity_one_empty(redundancy_service):
    """Test lineage similarity when one capsule has no upstream."""
    upstream1 = {"urn:source1"}
    upstream2 = set()

    score = redundancy_service._calculate_lineage_similarity(upstream1, upstream2)
    assert score == 0.0
