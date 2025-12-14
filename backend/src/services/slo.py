"""SLO (Service Level Objectives) compliance checking service.

This module provides functionality for checking data product SLO compliance
including freshness, availability, and quality metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.capsule import Capsule
from src.models.data_product import CapsuleDataProduct, DataProduct
from src.models.violation import Violation, ViolationStatus

if TYPE_CHECKING:
    pass


class SLOCheckStatus(str, Enum):
    """Status of an SLO check."""

    PASSING = "passing"
    WARNING = "warning"
    FAILING = "failing"
    NOT_CONFIGURED = "not_configured"


@dataclass
class SLOCheckResult:
    """Result of an individual SLO check."""

    status: SLOCheckStatus
    target: Optional[float] = None
    actual: Optional[float] = None
    message: str = ""


@dataclass
class SLOStatus:
    """Overall SLO status for a data product."""

    overall_status: SLOCheckStatus
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    freshness: Optional[dict] = None
    availability: Optional[dict] = None
    quality: Optional[dict] = None


class SLOService:
    """Service for checking data product SLO compliance.

    This service evaluates three types of SLOs:
    1. Freshness: How recently the data was updated
    2. Availability: System uptime (requires external metrics)
    3. Quality: Conformance score based on violations
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_slo_status(self, product: DataProduct) -> SLOStatus:
        """Check all SLO metrics for a data product.

        Args:
            product: DataProduct with capsule_associations loaded

        Returns:
            SLOStatus with all metrics evaluated
        """
        freshness_result = await self._check_freshness_slo(product)
        quality_result = await self._check_quality_slo(product)
        availability_result = self._check_availability_slo(product)

        # Determine overall status (worst of all checks)
        statuses = [
            freshness_result.status if freshness_result else SLOCheckStatus.NOT_CONFIGURED,
            quality_result.status if quality_result else SLOCheckStatus.NOT_CONFIGURED,
            availability_result.status if availability_result else SLOCheckStatus.NOT_CONFIGURED,
        ]

        # Filter out NOT_CONFIGURED for overall status calculation
        active_statuses = [s for s in statuses if s != SLOCheckStatus.NOT_CONFIGURED]

        if not active_statuses:
            overall = SLOCheckStatus.NOT_CONFIGURED
        elif SLOCheckStatus.FAILING in active_statuses:
            overall = SLOCheckStatus.FAILING
        elif SLOCheckStatus.WARNING in active_statuses:
            overall = SLOCheckStatus.WARNING
        else:
            overall = SLOCheckStatus.PASSING

        return SLOStatus(
            overall_status=overall,
            checked_at=datetime.now(timezone.utc),
            freshness=self._result_to_dict(freshness_result) if freshness_result else None,
            availability=self._result_to_dict(availability_result) if availability_result else None,
            quality=self._result_to_dict(quality_result) if quality_result else None,
        )

    async def _check_freshness_slo(
        self, product: DataProduct
    ) -> Optional[SLOCheckResult]:
        """Check data freshness SLO.

        Freshness is determined by the most recent updated_at timestamp
        across all capsules in the data product.
        """
        if not product.slo_freshness_hours:
            return None

        if not product.capsule_associations:
            return SLOCheckResult(
                status=SLOCheckStatus.WARNING,
                target=product.slo_freshness_hours,
                actual=None,
                message="No capsules in data product to check freshness",
            )

        # Get capsule IDs
        capsule_ids = [assoc.capsule_id for assoc in product.capsule_associations]

        # Find the most recent update timestamp
        stmt = select(func.max(Capsule.updated_at)).where(Capsule.id.in_(capsule_ids))
        result = await self.session.execute(stmt)
        last_update = result.scalar()

        if not last_update:
            return SLOCheckResult(
                status=SLOCheckStatus.WARNING,
                target=product.slo_freshness_hours,
                actual=None,
                message="Unable to determine last update time",
            )

        # Calculate hours since last update
        now = datetime.now(timezone.utc)
        # Ensure last_update is timezone-aware
        if last_update.tzinfo is None:
            last_update = last_update.replace(tzinfo=timezone.utc)

        hours_since_update = (now - last_update).total_seconds() / 3600

        # Determine status
        target_hours = product.slo_freshness_hours
        warning_threshold = target_hours * 0.8  # 80% of target is warning

        if hours_since_update <= warning_threshold:
            status = SLOCheckStatus.PASSING
            message = f"Data updated {hours_since_update:.1f} hours ago (target: {target_hours}h)"
        elif hours_since_update <= target_hours:
            status = SLOCheckStatus.WARNING
            message = f"Data approaching staleness: {hours_since_update:.1f}h (target: {target_hours}h)"
        else:
            status = SLOCheckStatus.FAILING
            message = f"Data is stale: {hours_since_update:.1f}h exceeds target of {target_hours}h"

        return SLOCheckResult(
            status=status,
            target=float(target_hours),
            actual=round(hours_since_update, 2),
            message=message,
        )

    async def _check_quality_slo(
        self, product: DataProduct
    ) -> Optional[SLOCheckResult]:
        """Check data quality SLO based on violation conformance.

        Quality score is calculated as:
        1.0 - (open_violations / total_possible_violations)

        For simplicity, we use: 1.0 - (open_violations / (capsule_count * 10))
        assuming each capsule could have up to 10 rules checked.
        """
        if not product.slo_quality_threshold:
            return None

        if not product.capsule_associations:
            return SLOCheckResult(
                status=SLOCheckStatus.WARNING,
                target=product.slo_quality_threshold,
                actual=None,
                message="No capsules in data product to check quality",
            )

        capsule_ids = [assoc.capsule_id for assoc in product.capsule_associations]

        # Count open violations for these capsules
        stmt = (
            select(func.count())
            .select_from(Violation)
            .where(
                Violation.capsule_id.in_(capsule_ids),
                Violation.status == ViolationStatus.OPEN,
            )
        )
        result = await self.session.execute(stmt)
        open_violations = result.scalar() or 0

        # Calculate quality score
        # Using a simple formula: higher violations = lower score
        capsule_count = len(capsule_ids)
        max_expected_violations = capsule_count * 10  # Assume 10 rules per capsule

        if max_expected_violations == 0:
            quality_score = 1.0
        else:
            quality_score = max(0.0, 1.0 - (open_violations / max_expected_violations))

        quality_score = round(quality_score, 3)

        # Determine status
        target = product.slo_quality_threshold
        warning_threshold = target + 0.05  # Warning at target + 5%

        if quality_score >= target:
            status = SLOCheckStatus.PASSING
            message = f"Quality score {quality_score:.1%} meets target {target:.1%}"
        elif quality_score >= target - 0.1:
            status = SLOCheckStatus.WARNING
            message = f"Quality score {quality_score:.1%} approaching target {target:.1%}"
        else:
            status = SLOCheckStatus.FAILING
            message = f"Quality score {quality_score:.1%} below target {target:.1%} ({open_violations} open violations)"

        return SLOCheckResult(
            status=status,
            target=target,
            actual=quality_score,
            message=message,
        )

    def _check_availability_slo(
        self, product: DataProduct
    ) -> Optional[SLOCheckResult]:
        """Check availability SLO.

        Note: True availability monitoring requires external metrics
        (e.g., from Prometheus, CloudWatch, etc.). This implementation
        provides a placeholder that always returns PASSING.

        In production, integrate with your observability platform.
        """
        if not product.slo_availability_percent:
            return None

        # Placeholder: Always report as passing
        # In production, integrate with monitoring system
        return SLOCheckResult(
            status=SLOCheckStatus.PASSING,
            target=product.slo_availability_percent,
            actual=99.9,  # Placeholder value
            message=(
                "Availability monitoring requires integration with "
                "external metrics system (placeholder: 99.9%)"
            ),
        )

    def _result_to_dict(self, result: SLOCheckResult) -> dict:
        """Convert SLOCheckResult to dictionary for API response."""
        return {
            "status": result.status.value,
            "target": result.target,
            "actual": result.actual,
            "message": result.message,
        }


async def check_product_slos(
    session: AsyncSession, product_id
) -> SLOStatus:
    """Convenience function to check SLOs for a product by ID.

    Args:
        session: Database session
        product_id: UUID of the data product

    Returns:
        SLOStatus with all metrics

    Raises:
        ValueError: If product not found
    """
    from src.repositories.data_product import DataProductRepository

    repo = DataProductRepository(session)
    product = await repo.get_by_id_with_capsules(product_id)

    if not product:
        raise ValueError(f"DataProduct {product_id} not found")

    service = SLOService(session)
    return await service.check_slo_status(product)
