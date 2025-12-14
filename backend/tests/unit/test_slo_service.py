"""Unit tests for SLO service."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.models.data_product import DataProduct, CapsuleDataProduct
from src.models.capsule import Capsule
from src.services.slo import (
    SLOCheckResult,
    SLOCheckStatus,
    SLOService,
    SLOStatus,
)


class TestSLOCheckStatus:
    """Tests for SLOCheckStatus enum."""

    def test_status_values(self):
        """Test all status values."""
        assert SLOCheckStatus.PASSING == "passing"
        assert SLOCheckStatus.WARNING == "warning"
        assert SLOCheckStatus.FAILING == "failing"
        assert SLOCheckStatus.NOT_CONFIGURED == "not_configured"


class TestSLOCheckResult:
    """Tests for SLOCheckResult dataclass."""

    def test_create_result(self):
        """Test creating an SLO check result."""
        result = SLOCheckResult(
            status=SLOCheckStatus.PASSING,
            target=99.9,
            actual=99.95,
            message="SLO met",
        )

        assert result.status == SLOCheckStatus.PASSING
        assert result.target == 99.9
        assert result.actual == 99.95
        assert result.message == "SLO met"

    def test_result_defaults(self):
        """Test default values."""
        result = SLOCheckResult(status=SLOCheckStatus.NOT_CONFIGURED)

        assert result.target is None
        assert result.actual is None
        assert result.message == ""


class TestSLOStatus:
    """Tests for SLOStatus dataclass."""

    def test_create_status(self):
        """Test creating overall SLO status."""
        status = SLOStatus(
            overall_status=SLOCheckStatus.PASSING,
            freshness={"status": "passing", "actual": 2.5},
            quality={"status": "passing", "actual": 0.98},
        )

        assert status.overall_status == SLOCheckStatus.PASSING
        assert status.freshness is not None
        assert status.quality is not None
        assert status.availability is None

    def test_status_has_timestamp(self):
        """Test that status has checked_at timestamp."""
        status = SLOStatus(overall_status=SLOCheckStatus.PASSING)

        assert status.checked_at is not None
        assert isinstance(status.checked_at, datetime)


class TestSLOServiceFreshness:
    """Tests for SLO service freshness checks."""

    @pytest.mark.asyncio
    async def test_freshness_not_configured(self):
        """Test freshness check when SLO not configured."""
        session = AsyncMock()
        service = SLOService(session)

        product = DataProduct(
            name="Test Product",
            slo_freshness_hours=None,  # Not configured
        )
        product.capsule_associations = []

        result = await service._check_freshness_slo(product)

        assert result is None

    @pytest.mark.asyncio
    async def test_freshness_no_capsules(self):
        """Test freshness check with no capsules."""
        session = AsyncMock()
        service = SLOService(session)

        product = DataProduct(
            name="Test Product",
            slo_freshness_hours=24,
        )
        product.capsule_associations = []

        result = await service._check_freshness_slo(product)

        assert result is not None
        assert result.status == SLOCheckStatus.WARNING
        assert "No capsules" in result.message

    @pytest.mark.asyncio
    async def test_freshness_passing(self):
        """Test freshness check when data is fresh."""
        session = AsyncMock()

        # Mock the query result to return recent timestamp
        recent_time = datetime.now(timezone.utc) - timedelta(hours=2)
        mock_result = MagicMock()
        mock_result.scalar.return_value = recent_time
        session.execute = AsyncMock(return_value=mock_result)

        service = SLOService(session)

        # Create mock associations
        capsule_id = uuid4()
        association = MagicMock()
        association.capsule_id = capsule_id

        product = DataProduct(
            name="Test Product",
            slo_freshness_hours=24,
        )
        product.capsule_associations = [association]

        result = await service._check_freshness_slo(product)

        assert result is not None
        assert result.status == SLOCheckStatus.PASSING
        assert result.target == 24.0
        assert result.actual < 3  # Should be around 2 hours

    @pytest.mark.asyncio
    async def test_freshness_warning(self):
        """Test freshness check when approaching staleness."""
        session = AsyncMock()

        # Mock timestamp at 80% of SLO (e.g., 19 hours for 24 hour SLO)
        stale_time = datetime.now(timezone.utc) - timedelta(hours=20)
        mock_result = MagicMock()
        mock_result.scalar.return_value = stale_time
        session.execute = AsyncMock(return_value=mock_result)

        service = SLOService(session)

        association = MagicMock()
        association.capsule_id = uuid4()

        product = DataProduct(
            name="Test Product",
            slo_freshness_hours=24,
        )
        product.capsule_associations = [association]

        result = await service._check_freshness_slo(product)

        assert result is not None
        assert result.status == SLOCheckStatus.WARNING
        assert "approaching" in result.message.lower()

    @pytest.mark.asyncio
    async def test_freshness_failing(self):
        """Test freshness check when data is stale."""
        session = AsyncMock()

        # Mock timestamp beyond SLO
        stale_time = datetime.now(timezone.utc) - timedelta(hours=48)
        mock_result = MagicMock()
        mock_result.scalar.return_value = stale_time
        session.execute = AsyncMock(return_value=mock_result)

        service = SLOService(session)

        association = MagicMock()
        association.capsule_id = uuid4()

        product = DataProduct(
            name="Test Product",
            slo_freshness_hours=24,
        )
        product.capsule_associations = [association]

        result = await service._check_freshness_slo(product)

        assert result is not None
        assert result.status == SLOCheckStatus.FAILING
        assert "stale" in result.message.lower()


class TestSLOServiceQuality:
    """Tests for SLO service quality checks."""

    @pytest.mark.asyncio
    async def test_quality_not_configured(self):
        """Test quality check when SLO not configured."""
        session = AsyncMock()
        service = SLOService(session)

        product = DataProduct(
            name="Test Product",
            slo_quality_threshold=None,
        )
        product.capsule_associations = []

        result = await service._check_quality_slo(product)

        assert result is None

    @pytest.mark.asyncio
    async def test_quality_passing(self):
        """Test quality check when score meets threshold."""
        session = AsyncMock()

        # Mock zero violations
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        session.execute = AsyncMock(return_value=mock_result)

        service = SLOService(session)

        association = MagicMock()
        association.capsule_id = uuid4()

        product = DataProduct(
            name="Test Product",
            slo_quality_threshold=0.9,
        )
        product.capsule_associations = [association]

        result = await service._check_quality_slo(product)

        assert result is not None
        assert result.status == SLOCheckStatus.PASSING
        assert result.actual == 1.0  # No violations = perfect score


class TestSLOServiceAvailability:
    """Tests for SLO service availability checks."""

    def test_availability_not_configured(self):
        """Test availability check when SLO not configured."""
        session = AsyncMock()
        service = SLOService(session)

        product = DataProduct(
            name="Test Product",
            slo_availability_percent=None,
        )

        result = service._check_availability_slo(product)

        assert result is None

    def test_availability_placeholder(self):
        """Test availability check returns placeholder (not yet integrated with metrics)."""
        session = AsyncMock()
        service = SLOService(session)

        product = DataProduct(
            name="Test Product",
            slo_availability_percent=99.9,
        )

        result = service._check_availability_slo(product)

        assert result is not None
        assert result.status == SLOCheckStatus.PASSING
        assert "placeholder" in result.message.lower()


class TestSLOServiceOverall:
    """Tests for overall SLO status calculation."""

    @pytest.mark.asyncio
    async def test_overall_status_all_passing(self):
        """Test overall status when all checks pass."""
        session = AsyncMock()

        # Mock both queries for freshness and quality
        mock_result = MagicMock()
        mock_result.scalar.side_effect = [
            datetime.now(timezone.utc) - timedelta(hours=1),  # freshness query
            0,  # violations count
        ]
        session.execute = AsyncMock(return_value=mock_result)

        service = SLOService(session)

        association = MagicMock()
        association.capsule_id = uuid4()

        product = DataProduct(
            name="Test Product",
            slo_freshness_hours=24,
            slo_quality_threshold=0.9,
            slo_availability_percent=99.9,
        )
        product.capsule_associations = [association]

        status = await service.check_slo_status(product)

        assert status.overall_status == SLOCheckStatus.PASSING

    @pytest.mark.asyncio
    async def test_overall_status_not_configured(self):
        """Test overall status when no SLOs configured."""
        session = AsyncMock()
        service = SLOService(session)

        product = DataProduct(name="Test Product")
        product.capsule_associations = []

        status = await service.check_slo_status(product)

        assert status.overall_status == SLOCheckStatus.NOT_CONFIGURED

    @pytest.mark.asyncio
    async def test_result_to_dict(self):
        """Test converting result to dictionary."""
        session = AsyncMock()
        service = SLOService(session)

        result = SLOCheckResult(
            status=SLOCheckStatus.PASSING,
            target=99.9,
            actual=99.95,
            message="SLO met",
        )

        result_dict = service._result_to_dict(result)

        assert result_dict["status"] == "passing"
        assert result_dict["target"] == 99.9
        assert result_dict["actual"] == 99.95
        assert result_dict["message"] == "SLO met"
