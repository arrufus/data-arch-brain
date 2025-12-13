"""Cached service wrappers for performance-critical operations.

Provides caching decorators and wrappers for compliance, conformance, and lineage queries.
"""

import json
from dataclasses import asdict
from typing import Any, Optional
from uuid import UUID

from src.cache import (
    CacheInvalidator,
    get_cache_client,
    make_cache_key,
)
from src.config import get_settings
from src.logging_config import get_logger
from src.metrics import get_metrics, record_pii_counts, record_conformance_scores, record_cache_hit, record_cache_miss

logger = get_logger(__name__)
settings = get_settings()


async def _get_cached_or_compute(
    cache_key: str,
    compute_fn,
    ttl: int,
    cache_type: str = "general",
) -> tuple[Any, bool]:
    """
    Get value from cache or compute it.
    
    Returns:
        Tuple of (result, from_cache)
    """
    client = get_cache_client()
    
    if not client.is_connected or not settings.cache_enabled:
        result = await compute_fn()
        return result, False
    
    # Try cache first
    try:
        cached = await client.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit", key=cache_key, type=cache_type)
            record_cache_hit(cache_type)
            return json.loads(cached), True
    except Exception as e:
        logger.warning("Cache read error", key=cache_key, error=str(e))
    
    # Compute value
    result = await compute_fn()
    
    # Store in cache
    try:
        await client.set(cache_key, json.dumps(result, default=str), ttl=ttl)
        logger.debug("Cache set", key=cache_key, ttl=ttl)
        record_cache_miss(cache_type)
    except Exception as e:
        logger.warning("Cache write error", key=cache_key, error=str(e))
    
    return result, False


async def get_cached_pii_inventory(
    compliance_service,
    pii_type: Optional[str] = None,
    layer: Optional[str] = None,
    domain: Optional[str] = None,
) -> dict:
    """
    Get PII inventory with caching.
    
    Caches the full inventory result for quick repeated access.
    """
    cache_key = make_cache_key(
        "pii_inventory",
        pii_type or "",
        layer or "",
        domain or "",
        prefix="dab:compliance",
    )
    
    async def compute():
        inventory = await compliance_service.get_pii_inventory(
            pii_type=pii_type,
            layer=layer,
            domain=domain,
        )
        # Convert to dict for caching
        result = {
            "total_pii_columns": inventory.total_pii_columns,
            "capsules_with_pii": inventory.capsules_with_pii,
            "pii_types_found": inventory.pii_types_found,
            "by_pii_type": [
                {
                    "pii_type": s.pii_type,
                    "column_count": s.column_count,
                    "capsule_count": s.capsule_count,
                    "layers": s.layers,
                    "columns": [
                        {
                            "column_id": str(c.column_id),
                            "column_urn": c.column_urn,
                            "column_name": c.column_name,
                            "pii_type": c.pii_type,
                            "pii_detected_by": c.pii_detected_by,
                            "capsule_id": str(c.capsule_id),
                            "capsule_urn": c.capsule_urn,
                            "capsule_name": c.capsule_name,
                            "capsule_layer": c.capsule_layer,
                            "data_type": c.data_type,
                            "description": c.description,
                        }
                        for c in s.columns
                    ],
                }
                for s in inventory.by_pii_type
            ],
            "by_layer": [
                {
                    "layer": l.layer,
                    "column_count": l.column_count,
                    "capsule_count": l.capsule_count,
                    "pii_types": l.pii_types,
                }
                for l in inventory.by_layer
            ],
        }
        
        # Update metrics with PII counts
        pii_counts = {s.pii_type: s.column_count for s in inventory.by_pii_type}
        record_pii_counts(pii_counts)
        
        return result
    
    result, _ = await _get_cached_or_compute(
        cache_key,
        compute,
        ttl=settings.cache_pii_ttl,
        cache_type="pii_inventory",
    )
    return result


async def get_cached_conformance_score(
    conformance_service,
    layer: Optional[str] = None,
    capsule_type: Optional[str] = None,
) -> dict:
    """
    Get conformance score with caching.
    
    Caches conformance evaluation results for repeated access.
    """
    cache_key = make_cache_key(
        "conformance_score",
        layer or "",
        capsule_type or "",
        prefix="dab:conformance",
    )
    
    async def compute():
        result = await conformance_service.evaluate(
            layer=layer,
            capsule_type=capsule_type,
        )
        # Convert to dict for caching
        output = {
            "score": result.score,
            "weighted_score": result.weighted_score,
            "total_rules": result.total_rules,
            "passing_rules": result.passing_rules,
            "failing_rules": result.failing_rules,
            "not_applicable": result.not_applicable,
            "by_severity": {
                sev: {"total": d["total"], "passing": d["passing"], "failing": d["failing"]}
                for sev, d in result.by_severity.items()
            },
            "by_category": result.by_category,
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "rule_name": v.rule_name,
                    "severity": v.severity.value if hasattr(v.severity, 'value') else v.severity,
                    "category": v.category.value if hasattr(v.category, 'value') else v.category,
                    "subject_type": v.subject_type,
                    "subject_id": str(v.subject_id),
                    "subject_urn": v.subject_urn,
                    "subject_name": v.subject_name,
                    "message": v.message,
                    "details": v.details,
                    "remediation": v.remediation,
                }
                for v in result.violations
            ],
            "evaluated_at": result.evaluated_at.isoformat() if result.evaluated_at else None,
        }
        
        # Update conformance score metrics
        scores_by_layer = {layer or "all": result.score}
        record_conformance_scores(scores_by_layer)
        
        return output
    
    result, _ = await _get_cached_or_compute(
        cache_key,
        compute,
        ttl=settings.cache_conformance_ttl,
        cache_type="conformance_score",
    )
    return result


async def get_cached_lineage(
    capsule_repo,
    capsule_id: UUID,
    direction: str,
    depth: int = 1,
) -> list[dict]:
    """
    Get capsule lineage with caching.
    
    Caches upstream/downstream lineage queries.
    """
    cache_key = make_cache_key(
        "lineage",
        str(capsule_id),
        direction,
        depth,
        prefix="dab:lineage",
    )
    
    async def compute():
        if direction == "upstream":
            capsules = await capsule_repo.get_upstream(capsule_id, depth)
        else:
            capsules = await capsule_repo.get_downstream(capsule_id, depth)
        
        return [
            {
                "id": str(c.id),
                "urn": c.urn,
                "name": c.name,
                "capsule_type": c.capsule_type,
                "layer": c.layer,
            }
            for c in capsules
        ]
    
    result, _ = await _get_cached_or_compute(
        cache_key,
        compute,
        ttl=settings.cache_lineage_ttl,
        cache_type="lineage",
    )
    return result


async def invalidate_after_ingestion() -> dict[str, int]:
    """
    Invalidate all caches that should be cleared after data ingestion.
    
    Called automatically after successful ingestion.
    """
    invalidator = CacheInvalidator()
    result = await invalidator.on_ingestion_complete()
    logger.info("Caches invalidated after ingestion", **result)
    return result
