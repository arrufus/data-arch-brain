"""PII compliance service for tracking and analyzing sensitive data."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.capsule import Capsule
from src.models.column import Column
from src.models.lineage import CapsuleLineage, ColumnLineage
from src.repositories.capsule import CapsuleRepository
from src.repositories.column import ColumnRepository


class PIISeverity(str, Enum):
    """Severity levels for PII exposure."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# PII types mapped to severity
PII_SEVERITY_MAP = {
    "ssn": PIISeverity.CRITICAL,
    "national_id": PIISeverity.CRITICAL,
    "passport": PIISeverity.CRITICAL,
    "drivers_license": PIISeverity.CRITICAL,
    "credit_card": PIISeverity.CRITICAL,
    "bank_account": PIISeverity.CRITICAL,
    "biometric": PIISeverity.CRITICAL,
    "health": PIISeverity.CRITICAL,
    "email": PIISeverity.HIGH,
    "phone": PIISeverity.HIGH,
    "address": PIISeverity.HIGH,
    "name": PIISeverity.HIGH,
    "first_name": PIISeverity.HIGH,
    "last_name": PIISeverity.HIGH,
    "date_of_birth": PIISeverity.HIGH,
    "ip_address": PIISeverity.MEDIUM,
    "device_id": PIISeverity.MEDIUM,
    "location": PIISeverity.MEDIUM,
    "age": PIISeverity.MEDIUM,
    "gender": PIISeverity.LOW,
}

# Consumption/Gold layers where PII exposure is a concern
CONSUMPTION_LAYERS = {"gold", "marts", "mart", "consumption", "reporting", "analytics"}


@dataclass
class PIIColumnInfo:
    """Information about a PII column."""

    column_id: UUID
    column_urn: str
    column_name: str
    pii_type: str
    pii_detected_by: Optional[str]
    capsule_id: UUID
    capsule_urn: str
    capsule_name: str
    capsule_layer: Optional[str]
    data_type: Optional[str]
    description: Optional[str]


@dataclass
class PIITypeSummary:
    """Summary of PII for a specific type."""

    pii_type: str
    column_count: int
    capsule_count: int
    layers: list[str]
    columns: list[PIIColumnInfo]


@dataclass
class PIILayerSummary:
    """Summary of PII for a specific layer."""

    layer: str
    column_count: int
    capsule_count: int
    pii_types: list[str]


@dataclass
class PIIInventory:
    """Complete PII inventory."""

    total_pii_columns: int
    capsules_with_pii: int
    pii_types_found: list[str]
    by_pii_type: list[PIITypeSummary]
    by_layer: list[PIILayerSummary]


@dataclass
class PIIExposure:
    """A PII exposure finding."""

    column_id: UUID
    column_urn: str
    column_name: str
    pii_type: str
    capsule_id: UUID
    capsule_urn: str
    capsule_name: str
    layer: str
    severity: PIISeverity
    reason: str
    recommendation: str
    lineage_path: list[str] = field(default_factory=list)


@dataclass
class PIIExposureReport:
    """PII exposure report."""

    exposed_pii_columns: int
    affected_capsules: int
    severity_breakdown: dict[str, int]
    exposures: list[PIIExposure]


@dataclass
class PIITraceNode:
    """A node in the PII trace path."""

    column_urn: str
    column_name: str
    capsule_urn: str
    capsule_name: str
    layer: Optional[str]
    pii_type: Optional[str]
    transformation: Optional[str] = None


@dataclass
class PIITrace:
    """Complete PII trace for a column."""

    column: PIIColumnInfo
    origin: Optional[PIITraceNode]
    propagation_path: list[PIITraceNode]
    terminals: list[PIITraceNode]
    is_masked_at_terminal: bool
    total_downstream_consumers: int


class ComplianceService:
    """Service for PII compliance analysis."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.capsule_repo = CapsuleRepository(session)
        self.column_repo = ColumnRepository(session)

    async def get_pii_inventory(
        self,
        pii_type: Optional[str] = None,
        layer: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> PIIInventory:
        """Get comprehensive PII inventory."""
        # Base query for PII columns with capsule info
        stmt = (
            select(Column)
            .where(Column.pii_type.isnot(None))
            .options(selectinload(Column.capsule))
        )

        if pii_type:
            stmt = stmt.where(Column.pii_type == pii_type)

        result = await self.session.execute(stmt)
        pii_columns = result.scalars().all()

        # Filter by layer if specified
        if layer:
            pii_columns = [
                c for c in pii_columns
                if c.capsule and c.capsule.layer == layer
            ]

        # Filter by domain if specified
        if domain:
            pii_columns = [
                c for c in pii_columns
                if c.capsule and c.capsule.domain and c.capsule.domain.name == domain
            ]

        # Build column info list
        column_infos = []
        for col in pii_columns:
            if col.capsule:
                column_infos.append(PIIColumnInfo(
                    column_id=col.id,
                    column_urn=col.urn,
                    column_name=col.name,
                    pii_type=col.pii_type,
                    pii_detected_by=col.pii_detected_by,
                    capsule_id=col.capsule.id,
                    capsule_urn=col.capsule.urn,
                    capsule_name=col.capsule.name,
                    capsule_layer=col.capsule.layer,
                    data_type=col.data_type,
                    description=col.description,
                ))

        # Group by PII type
        by_pii_type: dict[str, list[PIIColumnInfo]] = {}
        for info in column_infos:
            if info.pii_type not in by_pii_type:
                by_pii_type[info.pii_type] = []
            by_pii_type[info.pii_type].append(info)

        pii_type_summaries = []
        for ptype, cols in sorted(by_pii_type.items()):
            unique_capsules = set(c.capsule_id for c in cols)
            unique_layers = list(set(c.capsule_layer for c in cols if c.capsule_layer))
            pii_type_summaries.append(PIITypeSummary(
                pii_type=ptype,
                column_count=len(cols),
                capsule_count=len(unique_capsules),
                layers=sorted(unique_layers),
                columns=cols,
            ))

        # Group by layer
        by_layer: dict[str, list[PIIColumnInfo]] = {}
        for info in column_infos:
            layer_key = info.capsule_layer or "unknown"
            if layer_key not in by_layer:
                by_layer[layer_key] = []
            by_layer[layer_key].append(info)

        layer_summaries = []
        for lyr, cols in sorted(by_layer.items()):
            unique_capsules = set(c.capsule_id for c in cols)
            unique_pii_types = list(set(c.pii_type for c in cols))
            layer_summaries.append(PIILayerSummary(
                layer=lyr,
                column_count=len(cols),
                capsule_count=len(unique_capsules),
                pii_types=sorted(unique_pii_types),
            ))

        # Summary stats
        unique_capsule_ids = set(c.capsule_id for c in column_infos)
        unique_pii_types = list(set(c.pii_type for c in column_infos))

        return PIIInventory(
            total_pii_columns=len(column_infos),
            capsules_with_pii=len(unique_capsule_ids),
            pii_types_found=sorted(unique_pii_types),
            by_pii_type=pii_type_summaries,
            by_layer=layer_summaries,
        )

    async def detect_pii_exposure(
        self,
        layer: Optional[str] = None,
        severity: Optional[PIISeverity] = None,
    ) -> PIIExposureReport:
        """Detect exposed PII in consumption layers."""
        # Get PII columns in consumption layers
        stmt = (
            select(Column)
            .where(Column.pii_type.isnot(None))
            .options(selectinload(Column.capsule))
        )
        result = await self.session.execute(stmt)
        pii_columns = result.scalars().all()

        # Filter to consumption layers
        target_layers = CONSUMPTION_LAYERS
        if layer:
            target_layers = {layer}

        exposures: list[PIIExposure] = []
        affected_capsule_ids: set[UUID] = set()
        severity_counts: dict[str, int] = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }

        for col in pii_columns:
            if not col.capsule:
                continue

            capsule_layer = (col.capsule.layer or "").lower()
            if capsule_layer not in target_layers:
                continue

            # Check for masking indicators in column meta or name
            is_masked = self._is_column_masked(col)
            if is_masked:
                continue

            # This is an exposed PII column
            pii_severity = PII_SEVERITY_MAP.get(
                col.pii_type.lower() if col.pii_type else "",
                PIISeverity.MEDIUM
            )

            if severity and pii_severity != severity:
                continue

            exposure = PIIExposure(
                column_id=col.id,
                column_urn=col.urn,
                column_name=col.name,
                pii_type=col.pii_type,
                capsule_id=col.capsule.id,
                capsule_urn=col.capsule.urn,
                capsule_name=col.capsule.name,
                layer=capsule_layer,
                severity=pii_severity,
                reason=f"Unmasked {col.pii_type} PII in {capsule_layer} layer",
                recommendation=f"Apply masking, hashing, or encryption to {col.name}",
            )

            exposures.append(exposure)
            affected_capsule_ids.add(col.capsule.id)
            severity_counts[pii_severity.value] += 1

        return PIIExposureReport(
            exposed_pii_columns=len(exposures),
            affected_capsules=len(affected_capsule_ids),
            severity_breakdown=severity_counts,
            exposures=exposures,
        )

    def _is_column_masked(self, column: Column) -> bool:
        """Check if a column has masking/hashing indicators."""
        # Check column name patterns
        name_lower = column.name.lower()
        masking_indicators = [
            "_hash", "_hashed", "_masked", "_encrypted", "_redacted",
            "_anonymized", "_tokenized", "_obfuscated",
            "hash_", "masked_", "encrypted_",
        ]
        if any(ind in name_lower for ind in masking_indicators):
            return True

        # Check meta for masking flags
        meta = column.meta or {}
        if meta.get("masked") or meta.get("hashed") or meta.get("encrypted"):
            return True
        if meta.get("transformation") in ["hash", "mask", "encrypt", "redact"]:
            return True

        return False

    async def trace_pii_column(
        self,
        column_urn: str,
        max_depth: int = 10,
    ) -> Optional[PIITrace]:
        """Trace a PII column through the pipeline."""
        # Get the column
        column = await self.column_repo.get_by_urn(column_urn)
        if not column:
            return None

        # Load the capsule
        stmt = (
            select(Column)
            .where(Column.id == column.id)
            .options(selectinload(Column.capsule))
        )
        result = await self.session.execute(stmt)
        column = result.scalar_one()

        if not column.capsule:
            return None

        column_info = PIIColumnInfo(
            column_id=column.id,
            column_urn=column.urn,
            column_name=column.name,
            pii_type=column.pii_type,
            pii_detected_by=column.pii_detected_by,
            capsule_id=column.capsule.id,
            capsule_urn=column.capsule.urn,
            capsule_name=column.capsule.name,
            capsule_layer=column.capsule.layer,
            data_type=column.data_type,
            description=column.description,
        )

        # Trace upstream to find origin
        origin, upstream_path = await self._trace_upstream(column, max_depth)

        # Trace downstream to find terminals
        terminals, downstream_path = await self._trace_downstream(column, max_depth)

        # Build complete propagation path
        propagation_path = upstream_path + downstream_path

        # Check if masked at any terminal
        is_masked_at_terminal = all(
            self._node_is_masked(t) for t in terminals
        ) if terminals else False

        return PIITrace(
            column=column_info,
            origin=origin,
            propagation_path=propagation_path,
            terminals=terminals,
            is_masked_at_terminal=is_masked_at_terminal,
            total_downstream_consumers=len(terminals),
        )

    async def _trace_upstream(
        self,
        column: Column,
        max_depth: int,
    ) -> tuple[Optional[PIITraceNode], list[PIITraceNode]]:
        """Trace column upstream to find origin."""
        path: list[PIITraceNode] = []
        visited: set[UUID] = {column.id}
        current_id = column.id
        origin: Optional[PIITraceNode] = None

        for _ in range(max_depth):
            # Get upstream column lineage edges
            stmt = select(ColumnLineage).where(
                ColumnLineage.target_column_id == current_id
            )
            result = await self.session.execute(stmt)
            edges = result.scalars().all()

            if not edges:
                # No upstream - this is the origin
                break

            # Follow first upstream edge (could expand to handle multiple)
            edge = edges[0]
            source_col = await self.session.get(Column, edge.source_column_id)
            if not source_col or source_col.id in visited:
                break

            visited.add(source_col.id)

            # Load capsule
            stmt = (
                select(Column)
                .where(Column.id == source_col.id)
                .options(selectinload(Column.capsule))
            )
            result = await self.session.execute(stmt)
            source_col = result.scalar_one()

            node = PIITraceNode(
                column_urn=source_col.urn,
                column_name=source_col.name,
                capsule_urn=source_col.capsule.urn if source_col.capsule else "",
                capsule_name=source_col.capsule.name if source_col.capsule else "",
                layer=source_col.capsule.layer if source_col.capsule else None,
                pii_type=source_col.pii_type,
                transformation=edge.transformation_type,
            )
            path.insert(0, node)
            current_id = source_col.id

        # The origin is the first node in the path
        if path:
            origin = path[0]

        return origin, path

    async def _trace_downstream(
        self,
        column: Column,
        max_depth: int,
    ) -> tuple[list[PIITraceNode], list[PIITraceNode]]:
        """Trace column downstream to find terminals."""
        terminals: list[PIITraceNode] = []
        path: list[PIITraceNode] = []
        visited: set[UUID] = {column.id}
        queue: list[tuple[UUID, int]] = [(column.id, 0)]

        while queue:
            current_id, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            # Get downstream column lineage edges
            stmt = select(ColumnLineage).where(
                ColumnLineage.source_column_id == current_id
            )
            result = await self.session.execute(stmt)
            edges = result.scalars().all()

            if not edges:
                # No downstream - this is a terminal
                col = await self.session.get(Column, current_id)
                if col and col.id != column.id:
                    stmt = (
                        select(Column)
                        .where(Column.id == col.id)
                        .options(selectinload(Column.capsule))
                    )
                    result = await self.session.execute(stmt)
                    col = result.scalar_one()

                    node = PIITraceNode(
                        column_urn=col.urn,
                        column_name=col.name,
                        capsule_urn=col.capsule.urn if col.capsule else "",
                        capsule_name=col.capsule.name if col.capsule else "",
                        layer=col.capsule.layer if col.capsule else None,
                        pii_type=col.pii_type,
                    )
                    terminals.append(node)
                continue

            for edge in edges:
                if edge.target_column_id in visited:
                    continue

                visited.add(edge.target_column_id)
                target_col = await self.session.get(Column, edge.target_column_id)
                if not target_col:
                    continue

                # Load capsule
                stmt = (
                    select(Column)
                    .where(Column.id == target_col.id)
                    .options(selectinload(Column.capsule))
                )
                result = await self.session.execute(stmt)
                target_col = result.scalar_one()

                node = PIITraceNode(
                    column_urn=target_col.urn,
                    column_name=target_col.name,
                    capsule_urn=target_col.capsule.urn if target_col.capsule else "",
                    capsule_name=target_col.capsule.name if target_col.capsule else "",
                    layer=target_col.capsule.layer if target_col.capsule else None,
                    pii_type=target_col.pii_type,
                    transformation=edge.transformation_type,
                )
                path.append(node)
                queue.append((target_col.id, depth + 1))

        return terminals, path

    def _node_is_masked(self, node: PIITraceNode) -> bool:
        """Check if a trace node appears to be masked."""
        name_lower = node.column_name.lower()
        masking_indicators = [
            "_hash", "_hashed", "_masked", "_encrypted", "_redacted",
            "_anonymized", "_tokenized", "_obfuscated",
        ]
        if any(ind in name_lower for ind in masking_indicators):
            return True
        if node.transformation in ["hash", "mask", "encrypt", "redact"]:
            return True
        return False

    async def get_pii_columns_by_capsule(
        self,
        capsule_id: UUID,
    ) -> list[PIIColumnInfo]:
        """Get all PII columns for a specific capsule."""
        stmt = (
            select(Column)
            .where(Column.capsule_id == capsule_id)
            .where(Column.pii_type.isnot(None))
            .options(selectinload(Column.capsule))
        )
        result = await self.session.execute(stmt)
        columns = result.scalars().all()

        return [
            PIIColumnInfo(
                column_id=col.id,
                column_urn=col.urn,
                column_name=col.name,
                pii_type=col.pii_type,
                pii_detected_by=col.pii_detected_by,
                capsule_id=col.capsule.id,
                capsule_urn=col.capsule.urn,
                capsule_name=col.capsule.name,
                capsule_layer=col.capsule.layer,
                data_type=col.data_type,
                description=col.description,
            )
            for col in columns
            if col.capsule
        ]
