# Fix Summary: Domains Page Error

**Date**: 2025-12-19
**Status**: ✅ Issue Resolved

## Overview
Fixed MissingGreenlet error preventing the Domains page from loading correctly.

---

## Issue Description

When navigating to the Domains page (`/domains`), the frontend displayed:
```
[API] Server error: {}
```

The backend returned a 503 Service Unavailable error with `MissingGreenlet` exception.

---

## Root Cause

The domains API endpoint (`GET /api/v1/domains`) was accessing the lazy-loaded `owner` relationship on Domain objects in an async context:

```python
# Line 95 in domains.py
owner_name=d.owner.name if d.owner else None,
```

This triggered SQLAlchemy to attempt lazy loading within an async session, which is not allowed and causes the `MissingGreenlet` error.

---

## Solution

Added eager loading for the `owner` relationship in all domain repository query methods.

### Changes Made

**File**: `backend/src/repositories/domain.py`

#### 1. Added Import
```python
from sqlalchemy.orm import selectinload
```

#### 2. Overridden `get_all()` Method
```python
async def get_all(
    self,
    offset: int = 0,
    limit: int = 100,
) -> Sequence[Domain]:
    """Get all domains with owner relationship loaded."""
    stmt = (
        select(Domain)
        .options(selectinload(Domain.owner))
        .offset(offset)
        .limit(limit)
    )
    result = await self.session.execute(stmt)
    return result.scalars().all()
```

#### 3. Updated `get_root_domains()` Method
```python
async def get_root_domains(self) -> Sequence[Domain]:
    """Get all root-level domains (no parent)."""
    stmt = (
        select(Domain)
        .options(selectinload(Domain.owner))
        .where(Domain.parent_id.is_(None))
    )
    result = await self.session.execute(stmt)
    return result.scalars().all()
```

#### 4. Updated `get_children()` Method
```python
async def get_children(self, parent_id: UUID) -> Sequence[Domain]:
    """Get child domains of a parent."""
    stmt = (
        select(Domain)
        .options(selectinload(Domain.owner))
        .where(Domain.parent_id == parent_id)
    )
    result = await self.session.execute(stmt)
    return result.scalars().all()
```

#### 5. Updated `search()` Method
```python
async def search(
    self,
    query: str,
    offset: int = 0,
    limit: int = 100,
) -> Sequence[Domain]:
    """Search domains by name or description."""
    # Sanitize search query to prevent SQL injection
    safe_query = sanitize_search_query(query)
    if not safe_query:
        return []

    search_pattern = f"%{safe_query}%"
    stmt = (
        select(Domain)
        .options(selectinload(Domain.owner))
        .where(
            Domain.name.ilike(search_pattern)
            | Domain.description.ilike(search_pattern)
        )
        .offset(offset)
        .limit(limit)
    )
    result = await self.session.execute(stmt)
    return result.scalars().all()
```

---

## Verification Tests

All domain endpoints tested and working correctly:

### 1. List Domains Endpoint
```bash
$ curl http://localhost:8002/api/v1/domains
{
    "data": [
        {
            "id": "a7dd3501-6780-433c-a8d3-0881bda935c1",
            "name": "categorystrategy",
            "description": null,
            "parent_id": null,
            "owner_name": null,
            "capsule_count": 3
        },
        ...
    ],
    "pagination": {
        "total": 20,
        "offset": 0,
        "limit": 50,
        "has_more": false
    }
}
```

### 2. Domain Stats Endpoint
```bash
$ curl http://localhost:8002/api/v1/domains/stats
{
    "total_domains": 20,
    "root_domains": 20,
    "capsules_by_domain": {
        "categorystrategy": 3,
        "common": 22,
        ...
    }
}
```

### 3. Domain Detail Endpoint
```bash
$ curl http://localhost:8002/api/v1/domains/common
{
    "id": "6b995cec-da9c-489a-b98e-9a8c67febfef",
    "name": "common",
    "description": null,
    "parent_id": null,
    "owner_name": null,
    "capsule_count": 22,
    ...
}
```

### 4. Domain Capsules Endpoint
```bash
$ curl "http://localhost:8002/api/v1/domains/common/capsules?limit=5"
{
    "domain": {
        "id": "6b995cec-da9c-489a-b98e-9a8c67febfef",
        "name": "common",
        ...
    },
    "capsules": [
        {
            "id": "2c6e14d6-9bc0-4d91-bb8f-7a0556bc176d",
            "urn": "urn:dab:dbt:model:...:stg_common_applicability_count",
            "name": "stg_common_applicability_count",
            "capsule_type": "model",
            "layer": "silver",
            "has_pii": false
        },
        ...
    ]
}
```

---

## Impact Summary

### Before Fix
- ❌ Domains page: 503 Server Error (MissingGreenlet)
- ❌ Cannot browse business domains
- ❌ Cannot view domain details or capsules
- ❌ Console error displayed to user

### After Fix
- ✅ Domains page: Loads successfully
- ✅ Can browse all domains with search and filters
- ✅ Can view domain details and statistics
- ✅ Can view capsules within each domain
- ✅ No console errors

---

## Related Issues Checked

Also verified that similar endpoints are not affected:

### Capsules Endpoint
- ✅ `get_by_urn_with_columns()` already has eager loading for `owner`, `domain`, and `source_system`
- ✅ Capsule detail endpoint working correctly

---

## Lessons Learned

1. **Repository Pattern**: When adding eager loading, ensure ALL query methods that will access relationships include the appropriate `selectinload()` options.

2. **Search Methods**: Don't forget search and filter methods - they're just as likely to access relationships as standard get methods.

3. **Inherited Methods**: If a repository inherits from a base class, override methods that need eager loading rather than relying on the base implementation.

4. **Consistent Patterns**: When one endpoint has MissingGreenlet errors, check similar endpoints for the same pattern to prevent future issues.

---

## Files Modified

### Backend (1 file)
1. `backend/src/repositories/domain.py`
   - Lines 1-12: Added `selectinload` import
   - Lines 45-58: Overridden `get_all()` with eager loading
   - Lines 60-68: Updated `get_root_domains()` with eager loading
   - Lines 70-78: Updated `get_children()` with eager loading
   - Lines 80-104: Updated `search()` with eager loading

---

## Next Steps

1. ✅ Monitor Domains page in production
2. ⏭️ Review other repository methods for similar lazy-loading patterns
3. ⏭️ Add integration tests for domains endpoints
4. ⏭️ Consider adding a linter rule to detect relationship access without eager loading
