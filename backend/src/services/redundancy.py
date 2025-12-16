"""Redundancy detection service for identifying duplicate data assets."""

import asyncio
import re
from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.capsule import Capsule
from src.models.column import Column
from src.models.lineage import CapsuleLineage
from src.repositories.capsule import CapsuleRepository
from src.repositories.column import ColumnRepository


@dataclass
class SimilarityScore:
    """Similarity score breakdown."""

    name_score: float
    schema_score: float
    lineage_score: float
    metadata_score: float
    combined_score: float
    confidence: str  # "high", "medium", "low"


@dataclass
class SimilarCapsule:
    """A capsule similar to the target."""

    capsule_id: UUID
    capsule_urn: str
    capsule_name: str
    capsule_type: str
    layer: Optional[str]
    domain_name: Optional[str]
    similarity: SimilarityScore
    reasons: list[str]  # Human-readable reasons for similarity


@dataclass
class DuplicateCandidate:
    """A pair of likely duplicate capsules."""

    capsule1_urn: str
    capsule1_name: str
    capsule1_layer: Optional[str]
    capsule2_urn: str
    capsule2_name: str
    capsule2_layer: Optional[str]
    similarity_score: float
    reasons: list[str]


@dataclass
class RedundancyReport:
    """Full redundancy analysis report."""

    total_capsules: int
    duplicate_pairs: int
    potential_duplicates: list[DuplicateCandidate] = field(default_factory=list)
    by_layer: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)
    savings_estimate: dict = field(default_factory=dict)


class RedundancyService:
    """Service for detecting redundant/duplicate data assets."""

    # Weights for combined similarity score
    WEIGHT_NAME = 0.30
    WEIGHT_SCHEMA = 0.35
    WEIGHT_LINEAGE = 0.25
    WEIGHT_METADATA = 0.10

    # Similarity thresholds
    THRESHOLD_HIGH = 0.75
    THRESHOLD_MEDIUM = 0.50

    def __init__(self, session: AsyncSession):
        """Initialize redundancy service."""
        self.session = session
        self.capsule_repo = CapsuleRepository(session)
        self.column_repo = ColumnRepository(session)

    async def find_similar(
        self,
        urn: str,
        threshold: float = 0.5,
        limit: int = 10,
        same_type_only: bool = True,
        same_layer_only: bool = False,
    ) -> list[SimilarCapsule]:
        """
        Find capsules similar to the given URN.

        Args:
            urn: Target capsule URN
            threshold: Minimum similarity score (0.0-1.0)
            limit: Maximum number of results
            same_type_only: Only compare capsules of the same type
            same_layer_only: Only compare capsules in the same layer

        Returns:
            List of similar capsules, sorted by similarity descending
        """
        # Get target capsule with columns and domain
        target = await self.capsule_repo.get_by_urn_with_columns(urn)
        if not target:
            return []

        # Get upstream lineage for target
        target_upstream = await self._get_upstream_urns(urn)

        # Get candidate capsules (exclude target itself)
        filters = {"exclude_urn": urn}
        if same_type_only:
            filters["capsule_type"] = target.capsule_type
        if same_layer_only and target.layer:
            filters["layer"] = target.layer

        candidates = await self._get_candidate_capsules(filters)

        # Calculate similarity for each candidate
        similar_capsules: list[tuple[float, SimilarCapsule]] = []

        for candidate in candidates:
            # Get candidate columns and lineage
            candidate_upstream = await self._get_upstream_urns(candidate.urn)

            # Calculate all similarity scores
            similarity = await self._calculate_full_similarity(
                target=target,
                target_upstream=target_upstream,
                candidate=candidate,
                candidate_upstream=candidate_upstream,
            )

            # Filter by threshold
            if similarity.combined_score >= threshold:
                reasons = self._generate_reasons(similarity, target, candidate)
                similar_capsule = SimilarCapsule(
                    capsule_id=candidate.id,
                    capsule_urn=candidate.urn,
                    capsule_name=candidate.name,
                    capsule_type=candidate.capsule_type,
                    layer=candidate.layer,
                    domain_name=candidate.domain.name if candidate.domain else None,
                    similarity=similarity,
                    reasons=reasons,
                )
                similar_capsules.append((similarity.combined_score, similar_capsule))

        # Sort by score descending and limit results
        similar_capsules.sort(key=lambda x: x[0], reverse=True)
        return [capsule for _, capsule in similar_capsules[:limit]]

    async def compare_capsules(
        self, urn1: str, urn2: str
    ) -> tuple[SimilarCapsule, SimilarCapsule]:
        """
        Compare two specific capsules.

        Args:
            urn1: First capsule URN
            urn2: Second capsule URN

        Returns:
            Tuple of (capsule1_similarity, capsule2_similarity)
        """
        # Get both capsules
        capsule1 = await self.capsule_repo.get_by_urn_with_columns(urn1)
        capsule2 = await self.capsule_repo.get_by_urn_with_columns(urn2)

        if not capsule1 or not capsule2:
            raise ValueError(f"One or both capsules not found: {urn1}, {urn2}")

        # Get lineage for both
        upstream1 = await self._get_upstream_urns(urn1)
        upstream2 = await self._get_upstream_urns(urn2)

        # Calculate similarity scores
        similarity = await self._calculate_full_similarity(
            target=capsule1,
            target_upstream=upstream1,
            candidate=capsule2,
            candidate_upstream=upstream2,
        )

        reasons = self._generate_reasons(similarity, capsule1, capsule2)

        # Create similar capsule objects for both
        similar1 = SimilarCapsule(
            capsule_id=capsule1.id,
            capsule_urn=capsule1.urn,
            capsule_name=capsule1.name,
            capsule_type=capsule1.capsule_type,
            layer=capsule1.layer,
            domain_name=capsule1.domain.name if capsule1.domain else None,
            similarity=similarity,
            reasons=reasons,
        )

        similar2 = SimilarCapsule(
            capsule_id=capsule2.id,
            capsule_urn=capsule2.urn,
            capsule_name=capsule2.name,
            capsule_type=capsule2.capsule_type,
            layer=capsule2.layer,
            domain_name=capsule2.domain.name if capsule2.domain else None,
            similarity=similarity,
            reasons=reasons,
        )

        return similar1, similar2

    async def find_all_duplicates(
        self,
        threshold: float = 0.75,
        capsule_type: Optional[str] = None,
        layer: Optional[str] = None,
    ) -> list[DuplicateCandidate]:
        """
        Find all high-confidence duplicate pairs.

        Args:
            threshold: Minimum similarity score for duplicates
            capsule_type: Filter by capsule type
            layer: Filter by layer

        Returns:
            List of duplicate candidate pairs
        """
        # Get all capsules with filters
        filters = {}
        if capsule_type:
            filters["capsule_type"] = capsule_type
        if layer:
            filters["layer"] = layer

        capsules = await self._get_candidate_capsules(filters)

        # Track seen pairs to avoid duplicates
        seen_pairs: set[tuple[str, str]] = set()
        duplicate_pairs: list[tuple[float, DuplicateCandidate]] = []

        # Compare each pair (O(n²) - optimize with filters above)
        for i, capsule1 in enumerate(capsules):
            # Get lineage once per capsule
            upstream1 = await self._get_upstream_urns(capsule1.urn)

            for capsule2 in capsules[i + 1 :]:
                # Skip if pair already seen
                pair_key = tuple(sorted([capsule1.urn, capsule2.urn]))
                if pair_key in seen_pairs:
                    continue

                seen_pairs.add(pair_key)

                # Get lineage for capsule2
                upstream2 = await self._get_upstream_urns(capsule2.urn)

                # Calculate similarity
                similarity = await self._calculate_full_similarity(
                    target=capsule1,
                    target_upstream=upstream1,
                    candidate=capsule2,
                    candidate_upstream=upstream2,
                )

                # Filter by threshold
                if similarity.combined_score >= threshold:
                    reasons = self._generate_reasons(similarity, capsule1, capsule2)
                    candidate = DuplicateCandidate(
                        capsule1_urn=capsule1.urn,
                        capsule1_name=capsule1.name,
                        capsule1_layer=capsule1.layer,
                        capsule2_urn=capsule2.urn,
                        capsule2_name=capsule2.name,
                        capsule2_layer=capsule2.layer,
                        similarity_score=similarity.combined_score,
                        reasons=reasons,
                    )
                    duplicate_pairs.append((similarity.combined_score, candidate))

        # Sort by score descending
        duplicate_pairs.sort(key=lambda x: x[0], reverse=True)
        return [candidate for _, candidate in duplicate_pairs]

    async def get_redundancy_report(self) -> RedundancyReport:
        """Generate comprehensive redundancy report."""
        # Get all capsules
        all_capsules = await self._get_candidate_capsules({})

        # Find all duplicates (threshold 0.75)
        duplicates = await self.find_all_duplicates(threshold=self.THRESHOLD_HIGH)

        # Count by layer
        by_layer: dict[str, int] = defaultdict(int)
        for dup in duplicates:
            if dup.capsule1_layer:
                by_layer[dup.capsule1_layer] += 1

        # Count by type
        by_type: dict[str, int] = defaultdict(int)
        capsule_types = [c.capsule_type for c in all_capsules]
        for capsule_type in set(capsule_types):
            type_duplicates = [
                d for d in duplicates
                if await self._capsules_have_type(d.capsule1_urn, d.capsule2_urn, capsule_type)
            ]
            if type_duplicates:
                by_type[capsule_type] = len(type_duplicates)

        # Estimate potential savings
        savings_estimate = {
            "potential_storage_reduction": f"{len(duplicates) * 10}%",
            "potential_compute_reduction": f"{len(duplicates) * 15}%",
            "models_to_review": len(duplicates) * 2,
            "note": "Estimates based on typical redundancy patterns",
        }

        return RedundancyReport(
            total_capsules=len(all_capsules),
            duplicate_pairs=len(duplicates),
            potential_duplicates=duplicates,
            by_layer=dict(by_layer),
            by_type=dict(by_type),
            savings_estimate=savings_estimate,
        )

    # Private helper methods

    async def _get_candidate_capsules(self, filters: dict) -> Sequence[Capsule]:
        """Get candidate capsules with eager loading."""
        stmt = (
            select(Capsule)
            .options(
                selectinload(Capsule.columns),
                selectinload(Capsule.domain),
            )
        )

        # Apply filters
        if "exclude_urn" in filters:
            stmt = stmt.where(Capsule.urn != filters["exclude_urn"])
        if "capsule_type" in filters:
            stmt = stmt.where(Capsule.capsule_type == filters["capsule_type"])
        if "layer" in filters:
            stmt = stmt.where(Capsule.layer == filters["layer"])

        # Limit to reasonable size for performance
        stmt = stmt.limit(1000)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def _get_upstream_urns(self, urn: str) -> set[str]:
        """Get set of upstream URNs for lineage similarity."""
        stmt = (
            select(CapsuleLineage.source_urn)
            .where(CapsuleLineage.target_urn == urn)
            .where(CapsuleLineage.edge_type == "flows_to")
        )
        result = await self.session.execute(stmt)
        return set(result.scalars().all())

    async def _calculate_full_similarity(
        self,
        target: Capsule,
        target_upstream: set[str],
        candidate: Capsule,
        candidate_upstream: set[str],
    ) -> SimilarityScore:
        """Calculate all similarity scores and combine them."""
        # Calculate individual scores
        name_score = self._calculate_name_similarity(target.name, candidate.name)
        schema_score = self._calculate_schema_similarity(target.columns, candidate.columns)
        lineage_score = self._calculate_lineage_similarity(target_upstream, candidate_upstream)
        metadata_score = self._calculate_metadata_similarity(target, candidate)

        # Calculate combined score
        return self._calculate_combined_score(
            name_score, schema_score, lineage_score, metadata_score
        )

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate normalized name similarity using SequenceMatcher.

        Uses Ratcliff/Obershelp pattern matching algorithm.
        """
        # Normalize names (lowercase, strip)
        norm1 = self._normalize_name(name1)
        norm2 = self._normalize_name(name2)

        # Exact match
        if norm1 == norm2:
            return 1.0

        # Use SequenceMatcher for fuzzy matching
        matcher = SequenceMatcher(None, norm1, norm2)
        return matcher.ratio()

    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison."""
        # Convert to lowercase
        name = name.lower()

        # Remove common prefixes/suffixes
        prefixes = ["stg_", "staging_", "int_", "intermediate_", "dim_", "fct_", "rpt_", "raw_"]
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix) :]
                break

        # Remove underscores and dashes
        name = name.replace("_", "").replace("-", "")

        return name.strip()

    def _calculate_schema_similarity(
        self, columns1: Sequence[Column], columns2: Sequence[Column]
    ) -> float:
        """
        Calculate schema similarity using Jaccard index on column names and types.

        Jaccard = |intersection| / |union|
        """
        if not columns1 or not columns2:
            return 0.0

        # Create sets of (name, type) tuples
        schema1 = {(col.name.lower(), col.data_type.lower() if col.data_type else "")
                   for col in columns1}
        schema2 = {(col.name.lower(), col.data_type.lower() if col.data_type else "")
                   for col in columns2}

        # Calculate Jaccard index
        intersection = schema1 & schema2
        union = schema1 | schema2

        if not union:
            return 0.0

        jaccard = len(intersection) / len(union)

        # Also consider column name similarity (type-agnostic)
        names1 = {col.name.lower() for col in columns1}
        names2 = {col.name.lower() for col in columns2}

        name_intersection = names1 & names2
        name_union = names1 | names2

        name_jaccard = len(name_intersection) / len(name_union) if name_union else 0.0

        # Weighted combination (exact match 70%, name-only 30%)
        return 0.7 * jaccard + 0.3 * name_jaccard

    def _calculate_lineage_similarity(self, upstream1: set[str], upstream2: set[str]) -> float:
        """
        Calculate lineage similarity using Jaccard index on upstream sources.
        """
        if not upstream1 and not upstream2:
            return 0.0  # No lineage info, can't compare

        if not upstream1 or not upstream2:
            return 0.0  # One has lineage, other doesn't

        # Calculate Jaccard index
        intersection = upstream1 & upstream2
        union = upstream1 | upstream2

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _calculate_metadata_similarity(self, capsule1: Capsule, capsule2: Capsule) -> float:
        """Calculate metadata similarity (tags, domain, layer, description)."""
        score = 0.0
        components = 0

        # Domain similarity (exact match)
        if capsule1.domain_id and capsule2.domain_id:
            components += 1
            if capsule1.domain_id == capsule2.domain_id:
                score += 0.4  # 40% weight for domain match

        # Layer similarity (exact match)
        if capsule1.layer and capsule2.layer:
            components += 1
            if capsule1.layer == capsule2.layer:
                score += 0.3  # 30% weight for layer match

        # Tags similarity (Jaccard index)
        if capsule1.tags and capsule2.tags:
            components += 1
            tags1 = set(capsule1.tags)
            tags2 = set(capsule2.tags)
            intersection = tags1 & tags2
            union = tags1 | tags2
            if union:
                tag_jaccard = len(intersection) / len(union)
                score += 0.2 * tag_jaccard  # 20% weight for tags

        # Description similarity (optional, low weight)
        if capsule1.description and capsule2.description:
            components += 1
            matcher = SequenceMatcher(
                None,
                capsule1.description.lower(),
                capsule2.description.lower()
            )
            desc_sim = matcher.ratio()
            score += 0.1 * desc_sim  # 10% weight for description

        # Normalize by number of components available
        if components == 0:
            return 0.0

        return score / components if components > 0 else 0.0

    def _calculate_combined_score(
        self, name: float, schema: float, lineage: float, metadata: float
    ) -> SimilarityScore:
        """Calculate weighted combined similarity score."""
        combined = (
            self.WEIGHT_NAME * name
            + self.WEIGHT_SCHEMA * schema
            + self.WEIGHT_LINEAGE * lineage
            + self.WEIGHT_METADATA * metadata
        )

        # Determine confidence level
        if combined >= self.THRESHOLD_HIGH:
            confidence = "high"
        elif combined >= self.THRESHOLD_MEDIUM:
            confidence = "medium"
        else:
            confidence = "low"

        return SimilarityScore(
            name_score=round(name, 3),
            schema_score=round(schema, 3),
            lineage_score=round(lineage, 3),
            metadata_score=round(metadata, 3),
            combined_score=round(combined, 3),
            confidence=confidence,
        )

    def _generate_reasons(
        self, similarity: SimilarityScore, capsule1: Capsule, capsule2: Capsule
    ) -> list[str]:
        """Generate human-readable reasons for similarity."""
        reasons = []

        # Name similarity
        if similarity.name_score >= 0.8:
            reasons.append(f"Very similar names: '{capsule1.name}' vs '{capsule2.name}'")
        elif similarity.name_score >= 0.6:
            reasons.append(f"Similar names: '{capsule1.name}' vs '{capsule2.name}'")

        # Schema similarity
        if similarity.schema_score >= 0.8:
            overlap_pct = int(similarity.schema_score * 100)
            reasons.append(f"High schema overlap: {overlap_pct}% of columns match")
        elif similarity.schema_score >= 0.5:
            overlap_pct = int(similarity.schema_score * 100)
            reasons.append(f"Moderate schema overlap: {overlap_pct}% of columns match")

        # Lineage similarity
        if similarity.lineage_score >= 0.5:
            reasons.append("Share common upstream sources")

        # Metadata similarity
        if capsule1.domain_id == capsule2.domain_id and capsule1.domain:
            reasons.append(f"Same domain: {capsule1.domain.name}")

        if capsule1.layer == capsule2.layer and capsule1.layer:
            reasons.append(f"Same layer: {capsule1.layer}")

        # Overall confidence
        if similarity.confidence == "high":
            reasons.append("High confidence: Likely duplicates")
        elif similarity.confidence == "medium":
            reasons.append("Medium confidence: Potential overlap")

        return reasons

    async def _capsules_have_type(self, urn1: str, urn2: str, capsule_type: str) -> bool:
        """Check if both capsules have the specified type."""
        stmt = select(Capsule.capsule_type).where(
            Capsule.urn.in_([urn1, urn2])
        )
        result = await self.session.execute(stmt)
        types = list(result.scalars().all())
        return all(t == capsule_type for t in types)
