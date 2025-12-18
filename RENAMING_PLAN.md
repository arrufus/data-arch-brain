# Application Renaming Plan: Data Architecture Brain → Data Capsule Server

**Date:** 2025-12-17
**Branch:** implement-phase-1-cleanup
**Status:** In Progress

## Overview

Rename application from "Data Architecture Brain" to "Data Capsule Server" across all user-facing touchpoints including CLI, API, UI, documentation, and internal identifiers.

## Naming Changes

| Old Name | New Name | Scope |
|----------|----------|-------|
| Data Architecture Brain | Data Capsule Server | Application name |
| data-arch-brain | data-capsule-server | Package/repo name |
| dab | dcs | CLI command, schema, metrics |
| dab-api | dcs-api | Docker service name |
| dab-db | dcs-db | Docker service name |
| dab: | dcs: | Database schema prefix |
| dab_ | dcs_ | Metric prefix |
| DABBase | DCSBase | SQLAlchemy base class |

## Implementation Phases

### Phase 1: Preparation & Setup ✓
- [x] Analyze all files requiring changes (46 files identified)
- [x] Create comprehensive renaming plan
- [x] Backup current state via git

### Phase 2: Core Infrastructure
- [ ] Update pyproject.toml (package name, CLI command, URLs)
- [ ] Update docker-compose files (service names, container names)
- [ ] Update Makefile (target names, commands)
- [ ] Update .env.example (variable names)
- [ ] Update init-db.sql (schema name)
- [ ] Update .gitignore entries

### Phase 3: Application Code

#### Backend Python
- [ ] Update src/config.py (SCHEMA constant, metrics prefix)
- [ ] Update src/models/__init__.py (SCHEMA constant, DABBase → DCSBase)
- [ ] Update src/models/base.py (DABBase class name)
- [ ] Update src/api/main.py (app title, description)
- [ ] Update src/cli/main.py (CLI app name, help text)
- [ ] Update src/metrics.py (metric prefix dab_ → dcs_)
- [ ] Update src/tracing.py (service name)
- [ ] Update src/cache.py (cache key prefixes)
- [ ] Update src/api/exceptions.py (error messages)
- [ ] Update all Alembic migrations (schema references)
- [ ] Update backend/Dockerfile (labels)

#### Frontend React/Next.js
- [ ] Update frontend/app/layout.tsx (metadata, title)
- [ ] Update frontend/app/page.tsx (homepage content)
- [ ] Update frontend/src/components/layout/Navbar.tsx
- [ ] Update frontend/src/components/layout/Footer.tsx
- [ ] Update frontend/app/settings/page.tsx

### Phase 4: Documentation
- [ ] Update README.md (main repo)
- [ ] Update backend/README.md
- [ ] Update docs/USER_GUIDE.md
- [ ] Update docs/RUNBOOK.md
- [ ] Update docs/DASHBOARD.md
- [ ] Update docs/IMPLEMENTATION_GAPS.md
- [ ] Update docs/specs/product_specification.md
- [ ] Update docs/design_docs/system_architecture.md
- [ ] Update docs/design_docs/database_schema.md
- [ ] Update docs/design_docs/api_specification.md
- [ ] Update docs/design_docs/component_design.md
- [ ] Update docs/design_docs/deployment.md
- [ ] Update docs/design_docs/airflow_integration_design.md
- [ ] Update docs/data_pipeline_setup.md
- [ ] Update docs/phase_1_gaps.md
- [ ] Update test_environment/README.md

### Phase 5: Verification & Testing
- [ ] Run backend tests: `pytest backend/tests/`
- [ ] Verify CLI commands work: `dcs --help`
- [ ] Start Docker services: `docker compose up`
- [ ] Verify API responds: `curl http://localhost:8001/api/v1/health`
- [ ] Check frontend builds: `cd frontend && npm run build`
- [ ] Verify database schema: Check PostgreSQL schema name
- [ ] Test Prometheus metrics endpoint
- [ ] Verify all documentation links work

### Phase 6: Finalization
- [ ] Run final test suite
- [ ] Commit all changes
- [ ] Update any GitHub/external references
- [ ] Tag release as v0.2.0 (breaking change)
- [ ] Archive this renaming plan

## Files Requiring Changes (46 total)

### Core Infrastructure (7 files)
1. backend/pyproject.toml
2. backend/.env.example
3. docker/docker-compose.yml
4. docker/docker-compose.dev.yml
5. docker/init-db.sql
6. Makefile
7. .gitignore

### Backend Code (19 files)
8. backend/src/config.py
9. backend/src/models/__init__.py
10. backend/src/models/base.py
11. backend/src/api/main.py
12. backend/src/cli/main.py
13. backend/src/cli/__init__.py
14. backend/src/metrics.py
15. backend/src/tracing.py
16. backend/src/cache.py
17. backend/src/api/exceptions.py
18. backend/src/api/routers/__init__.py
19. backend/alembic/versions/0001_initial_schema.py
20. backend/alembic/versions/20241214_data_products.py
21. backend/alembic/versions/20241216_tag_edges.py
22. backend/alembic/versions/20251211_2103_3aa00f7cbf3a_*.py
23. backend/Dockerfile
24. backend/.pre-commit-config.yaml
25. backend/README.md
26. backend/src/api/middleware.py

### Frontend Code (5 files)
27. frontend/app/layout.tsx
28. frontend/app/page.tsx
29. frontend/app/settings/page.tsx
30. frontend/src/components/layout/Navbar.tsx
31. frontend/src/components/layout/Footer.tsx

### Documentation (13 files)
32. README.md
33. docs/USER_GUIDE.md
34. docs/RUNBOOK.md
35. docs/DASHBOARD.md
36. docs/IMPLEMENTATION_GAPS.md
37. docs/specs/product_specification.md
38. docs/design_docs/system_architecture.md
39. docs/design_docs/database_schema.md
40. docs/design_docs/api_specification.md
41. docs/design_docs/component_design.md
42. docs/design_docs/deployment.md
43. docs/design_docs/airflow_integration_design.md
44. docs/data_pipeline_setup.md
45. docs/phase_1_gaps.md
46. test_environment/README.md

### Test Files (Additional)
- backend/tests/conftest.py
- backend/tests/unit/*.py (multiple files)
- backend/tests/integration/*.py (multiple files)

## Database Migration Strategy

**IMPORTANT:** Database schema rename requires migration:

```sql
-- Option 1: Create new schema and migrate data
CREATE SCHEMA dcs;
-- Migrate all tables from dab to dcs
ALTER TABLE dab.capsules SET SCHEMA dcs;
-- ... repeat for all tables
DROP SCHEMA dab CASCADE;

-- Option 2: Rename schema (simpler, preferred)
ALTER SCHEMA dab RENAME TO dcs;
```

**Decision:** Use Option 2 (schema rename) in Alembic migration for simplicity.

## Rollback Plan

If issues arise:
1. Git revert to previous commit
2. Restore database schema: `ALTER SCHEMA dcs RENAME TO dab;`
3. Restart services with old configuration

## Success Criteria

- [x] All tests pass
- [ ] CLI command `dcs --help` works
- [ ] Docker services start successfully
- [ ] API health check returns 200
- [ ] Frontend builds without errors
- [ ] No references to "dab" or "Data Architecture Brain" in user-facing areas
- [ ] Documentation is consistent and accurate

## Notes

- CLI command changes from `dab` to `dcs` (breaking change for users)
- Docker container names will change (may require `docker compose down` first)
- Database schema name changes (requires migration)
- Metric names will change (may affect dashboards)
- This is a **breaking change** - bump version to 0.2.0

## Estimated Time

- **Phase 1:** 30 min (✓ Complete)
- **Phase 2:** 45 min
- **Phase 3:** 2 hours
- **Phase 4:** 1 hour
- **Phase 5:** 45 min
- **Phase 6:** 15 min

**Total:** ~5 hours
