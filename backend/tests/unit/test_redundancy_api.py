"""Unit tests for redundancy API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.api.main import create_app
from src.services.redundancy import (
    SimilarityScore,
    SimilarCapsule,
    DuplicateCandidate,
    RedundancyReport,
)


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_similar_capsule():
    """Create sample similar capsule for mocking."""
    return SimilarCapsule(
        capsule_id=uuid4(),
        capsule_urn="urn:dab:dbt:model:staging:stg_customers_v2",
        capsule_name="stg_customers_v2",
        capsule_type="model",
        layer="silver",
        domain_name="customer",
        similarity=SimilarityScore(
            name_score=0.85,
            schema_score=0.90,
            lineage_score=0.75,
            metadata_score=0.80,
            combined_score=0.84,
            confidence="high",
        ),
        reasons=[
            "Very similar names: 'stg_customers' vs 'stg_customers_v2'",
            "High schema overlap: 90% of columns match",
            "Same domain: customer",
        ],
    )


@pytest.fixture
def sample_duplicate_candidate():
    """Create sample duplicate candidate for mocking."""
    return DuplicateCandidate(
        capsule1_urn="urn:dab:dbt:model:staging:stg_customers",
        capsule1_name="stg_customers",
        capsule1_layer="silver",
        capsule2_urn="urn:dab:dbt:model:staging:staging_customers",
        capsule2_name="staging_customers",
        capsule2_layer="silver",
        similarity_score=0.88,
        reasons=[
            "Very similar names",
            "High schema overlap: 88% of columns match",
            "Same layer: silver",
        ],
    )


@pytest.fixture
def sample_redundancy_report():
    """Create sample redundancy report for mocking."""
    return RedundancyReport(
        total_capsules=150,
        duplicate_pairs=12,
        potential_duplicates=[],
        by_layer={"silver": 8, "gold": 4},
        by_type={"model": 10, "source": 2},
        savings_estimate={
            "potential_storage_reduction": "120%",
            "potential_compute_reduction": "180%",
            "models_to_review": 24,
        },
    )


# Test find_similar_capsules endpoint

@patch("src.api.routers.redundancy.RedundancyService")
def test_find_similar_capsules_success(mock_service_class, client, sample_similar_capsule):
    """Test find similar capsules endpoint returns results."""
    # Mock service
    mock_service = AsyncMock()
    mock_service.find_similar.return_value = [sample_similar_capsule]
    mock_service.capsule_repo.get_by_urn.return_value = AsyncMock(
        urn="urn:dab:dbt:model:staging:stg_customers",
        name="stg_customers",
    )
    mock_service_class.return_value = mock_service

    # Make request
    response = client.get(
        "/api/v1/redundancy/capsules/urn:dab:dbt:model:staging:stg_customers/similar",
        params={"threshold": 0.5, "limit": 10},
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["target_urn"] == "urn:dab:dbt:model:staging:stg_customers"
    assert data["threshold"] == 0.5
    assert data["results_count"] == 1
    assert len(data["results"]) == 1

    result = data["results"][0]
    assert result["capsule_urn"] == "urn:dab:dbt:model:staging:stg_customers_v2"
    assert result["similarity"]["combined_score"] == 0.84
    assert result["similarity"]["confidence"] == "high"


@patch("src.api.routers.redundancy.RedundancyService")
def test_find_similar_capsules_with_filters(mock_service_class, client):
    """Test find similar capsules with filters."""
    mock_service = AsyncMock()
    mock_service.find_similar.return_value = []
    mock_service.capsule_repo.get_by_urn.return_value = AsyncMock(name="test")
    mock_service_class.return_value = mock_service

    response = client.get(
        "/api/v1/redundancy/capsules/urn:test/similar",
        params={
            "threshold": 0.75,
            "limit": 5,
            "same_type_only": True,
            "same_layer_only": True,
        },
    )

    assert response.status_code == 200
    # Verify service was called with correct parameters
    mock_service.find_similar.assert_called_once()
    call_kwargs = mock_service.find_similar.call_args.kwargs
    assert call_kwargs["threshold"] == 0.75
    assert call_kwargs["limit"] == 5
    assert call_kwargs["same_type_only"] is True
    assert call_kwargs["same_layer_only"] is True


@patch("src.api.routers.redundancy.RedundancyService")
def test_find_similar_capsules_not_found(mock_service_class, client):
    """Test find similar capsules when target not found."""
    mock_service = AsyncMock()
    mock_service.find_similar.return_value = []
    mock_service.capsule_repo.get_by_urn.return_value = None
    mock_service_class.return_value = mock_service

    response = client.get(
        "/api/v1/redundancy/capsules/urn:missing/similar"
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_find_similar_threshold_validation(client):
    """Test threshold parameter validation."""
    # Threshold > 1.0
    response = client.get(
        "/api/v1/redundancy/capsules/urn:test/similar",
        params={"threshold": 1.5},
    )
    assert response.status_code == 422

    # Threshold < 0.0
    response = client.get(
        "/api/v1/redundancy/capsules/urn:test/similar",
        params={"threshold": -0.5},
    )
    assert response.status_code == 422


def test_find_similar_limit_validation(client):
    """Test limit parameter validation."""
    # Limit > 100
    response = client.get(
        "/api/v1/redundancy/capsules/urn:test/similar",
        params={"limit": 150},
    )
    assert response.status_code == 422

    # Limit < 1
    response = client.get(
        "/api/v1/redundancy/capsules/urn:test/similar",
        params={"limit": 0},
    )
    assert response.status_code == 422


# Test compare_two_capsules endpoint

@patch("src.api.routers.redundancy.RedundancyService")
def test_compare_two_capsules_success(mock_service_class, client, sample_similar_capsule):
    """Test compare two capsules endpoint."""
    # Create second capsule
    capsule2 = SimilarCapsule(
        capsule_id=uuid4(),
        capsule_urn="urn:dab:dbt:model:staging:stg_customers",
        capsule_name="stg_customers",
        capsule_type="model",
        layer="silver",
        domain_name="customer",
        similarity=sample_similar_capsule.similarity,
        reasons=sample_similar_capsule.reasons,
    )

    mock_service = AsyncMock()
    mock_service.compare_capsules.return_value = (capsule2, sample_similar_capsule)
    mock_service_class.return_value = mock_service

    response = client.get(
        "/api/v1/redundancy/capsules/urn:dab:dbt:model:staging:stg_customers/similar/urn:dab:dbt:model:staging:stg_customers_v2"
    )

    assert response.status_code == 200
    data = response.json()
    assert "capsule1" in data
    assert "capsule2" in data
    assert "recommendation" in data
    assert "explanation" in data
    assert data["recommendation"] == "likely_duplicates"  # Score 0.84 > 0.75


@patch("src.api.routers.redundancy.RedundancyService")
def test_compare_two_capsules_medium_similarity(mock_service_class, client):
    """Test comparison with medium similarity."""
    capsule1 = SimilarCapsule(
        capsule_id=uuid4(),
        capsule_urn="urn:test1",
        capsule_name="test1",
        capsule_type="model",
        layer="silver",
        domain_name=None,
        similarity=SimilarityScore(
            name_score=0.6,
            schema_score=0.6,
            lineage_score=0.6,
            metadata_score=0.6,
            combined_score=0.6,
            confidence="medium",
        ),
        reasons=["Moderate similarity"],
    )
    capsule2 = SimilarCapsule(
        capsule_id=uuid4(),
        capsule_urn="urn:test2",
        capsule_name="test2",
        capsule_type="model",
        layer="silver",
        domain_name=None,
        similarity=capsule1.similarity,
        reasons=["Moderate similarity"],
    )

    mock_service = AsyncMock()
    mock_service.compare_capsules.return_value = (capsule1, capsule2)
    mock_service_class.return_value = mock_service

    response = client.get(
        "/api/v1/redundancy/capsules/urn:test1/similar/urn:test2"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"] == "potential_overlap"  # 0.5 <= 0.6 < 0.75


@patch("src.api.routers.redundancy.RedundancyService")
def test_compare_two_capsules_not_found(mock_service_class, client):
    """Test comparison when capsule not found."""
    mock_service = AsyncMock()
    mock_service.compare_capsules.side_effect = ValueError("Capsule not found")
    mock_service_class.return_value = mock_service

    response = client.get(
        "/api/v1/redundancy/capsules/urn:missing1/similar/urn:missing2"
    )

    assert response.status_code == 404


# Test get_duplicate_candidates endpoint

@patch("src.api.routers.redundancy.RedundancyService")
def test_get_duplicate_candidates_success(mock_service_class, client, sample_duplicate_candidate):
    """Test get duplicate candidates endpoint."""
    mock_service = AsyncMock()
    mock_service.find_all_duplicates.return_value = [sample_duplicate_candidate]
    mock_service_class.return_value = mock_service

    response = client.get(
        "/api/v1/redundancy/candidates",
        params={"threshold": 0.75},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["threshold"] == 0.75
    assert data["candidates_count"] == 1
    assert len(data["candidates"]) == 1

    candidate = data["candidates"][0]
    assert candidate["capsule1_urn"] == "urn:dab:dbt:model:staging:stg_customers"
    assert candidate["capsule2_urn"] == "urn:dab:dbt:model:staging:staging_customers"
    assert candidate["similarity_score"] == 0.88


@patch("src.api.routers.redundancy.RedundancyService")
def test_get_duplicate_candidates_with_filters(mock_service_class, client):
    """Test duplicate candidates with layer and type filters."""
    mock_service = AsyncMock()
    mock_service.find_all_duplicates.return_value = []
    mock_service_class.return_value = mock_service

    response = client.get(
        "/api/v1/redundancy/candidates",
        params={
            "threshold": 0.8,
            "layer": "gold",
            "capsule_type": "model",
        },
    )

    assert response.status_code == 200
    mock_service.find_all_duplicates.assert_called_once()
    call_kwargs = mock_service.find_all_duplicates.call_args.kwargs
    assert call_kwargs["threshold"] == 0.8
    assert call_kwargs["capsule_type"] == "model"
    assert call_kwargs["layer"] == "gold"


def test_get_duplicate_candidates_threshold_validation(client):
    """Test candidates threshold validation."""
    # Threshold < 0.5
    response = client.get(
        "/api/v1/redundancy/candidates",
        params={"threshold": 0.3},
    )
    assert response.status_code == 422

    # Threshold > 1.0
    response = client.get(
        "/api/v1/redundancy/candidates",
        params={"threshold": 1.5},
    )
    assert response.status_code == 422


# Test get_redundancy_report endpoint

@patch("src.api.routers.redundancy.RedundancyService")
def test_get_redundancy_report_success(mock_service_class, client, sample_redundancy_report, sample_duplicate_candidate):
    """Test redundancy report endpoint."""
    sample_redundancy_report.potential_duplicates = [sample_duplicate_candidate]

    mock_service = AsyncMock()
    mock_service.get_redundancy_report.return_value = sample_redundancy_report
    mock_service_class.return_value = mock_service

    response = client.get("/api/v1/redundancy/report")

    assert response.status_code == 200
    data = response.json()
    assert data["total_capsules"] == 150
    assert data["duplicate_pairs"] == 12
    assert len(data["potential_duplicates"]) == 1
    assert "by_layer" in data
    assert "by_type" in data
    assert "savings_estimate" in data
    assert data["by_layer"]["silver"] == 8
    assert data["by_type"]["model"] == 10


@patch("src.api.routers.redundancy.RedundancyService")
def test_get_redundancy_report_empty(mock_service_class, client):
    """Test redundancy report with no duplicates."""
    mock_service = AsyncMock()
    mock_service.get_redundancy_report.return_value = RedundancyReport(
        total_capsules=50,
        duplicate_pairs=0,
        potential_duplicates=[],
        by_layer={},
        by_type={},
        savings_estimate={},
    )
    mock_service_class.return_value = mock_service

    response = client.get("/api/v1/redundancy/report")

    assert response.status_code == 200
    data = response.json()
    assert data["total_capsules"] == 50
    assert data["duplicate_pairs"] == 0
    assert len(data["potential_duplicates"]) == 0


# Test response model validation

def test_similarity_score_response_model():
    """Test SimilarityScoreResponse model structure."""
    from src.api.routers.redundancy import SimilarityScoreResponse

    score = SimilarityScoreResponse(
        name_score=0.8,
        schema_score=0.9,
        lineage_score=0.7,
        metadata_score=0.6,
        combined_score=0.8,
        confidence="high",
    )

    assert score.name_score == 0.8
    assert score.combined_score == 0.8
    assert score.confidence == "high"


def test_similar_capsule_response_model():
    """Test SimilarCapsuleResponse model structure."""
    from src.api.routers.redundancy import SimilarCapsuleResponse, SimilarityScoreResponse

    capsule = SimilarCapsuleResponse(
        capsule_id=str(uuid4()),
        capsule_urn="urn:test",
        capsule_name="test",
        capsule_type="model",
        layer="silver",
        domain_name="customer",
        similarity=SimilarityScoreResponse(
            name_score=0.5,
            schema_score=0.5,
            lineage_score=0.5,
            metadata_score=0.5,
            combined_score=0.5,
            confidence="medium",
        ),
        reasons=["Test reason"],
    )

    assert capsule.capsule_name == "test"
    assert capsule.layer == "silver"
    assert len(capsule.reasons) == 1
