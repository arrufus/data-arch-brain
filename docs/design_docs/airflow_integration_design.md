# Airflow Integration Design (P2)

## 1. Context and Goals

### 1.1 Why this exists
The product specification calls out **Airflow (P2)** as a future integration source with the scope:

- **Source:** Airflow
- **Metadata type:** DAG definitions
- **Output:** Pipeline metadata

This document provides a design that fits the current Data Capsule Server (DAB) implementation patterns (parser → ingestion orchestrator → persistence in the property graph → API/CLI query).

### 1.2 Goals (what we will deliver)
1. **Ingest Airflow DAG + task metadata** into the existing DAB graph store.
2. **Represent DAG structure and task dependencies** as graph nodes/edges.
3. Support **re-ingestion** (idempotent upserts + optional orphan cleanup) using the existing ingestion flow.
4. Expose the ingested DAGs and tasks through existing **capsules** and **graph export** capabilities with minimal API surface area.

### 1.3 Non-goals (explicitly out of scope for this phase)
- Runtime lineage from Airflow task executions (DAG runs / task instances) beyond minimal “last run” fields.
- Full SQL parsing from task definitions to infer reads/writes to data assets.
- OpenLineage integration (listed separately in the product spec) except for future-proofing.
- Writing Airflow plugins, modifying Airflow itself, or pushing metadata back into Airflow.

### 1.4 Design constraints (from product direction + current code)
- DAB is **read-only by design**.
- **No credentials stored in graph** (product spec). This is important because the current ingestion job model stores `config` verbatim.
- Prefer reusing existing models:
  - `Capsule` as the primary node type.
  - `CapsuleLineage` for relationships.
  - `SourceSystem` for identifying the origin of metadata.

---

## 2. Deep Review of Current Implementation (as-built)

This section summarizes what exists today and what patterns the Airflow integration must follow.

### 2.1 Ingestion architecture (current)
- **Parser abstraction:** `src/parsers/base.py`
  - `MetadataParser.parse(config) -> ParseResult` (async)
  - `MetadataParser.validate_config(config) -> list[str]`
  - `ParseResult` contains:
    - `capsules`, `columns`, `edges`, `column_edges`, `domains`, `tags`, `errors`
    - `source_type`, `source_name`, `source_version`
- **Parser registry:** `src/parsers/__init__.py`
  - `default_registry.register("dbt", DbtParser)`
  - `get_parser(source_type)` used by ingestion orchestrator
- **Ingestion orchestrator:** `src/services/ingestion.py`
  - `ingest(source_type, config, cleanup_orphans=False)`:
    1. Creates `IngestionJob` with stored `config`
    2. Validates config via parser
    3. Calls `parse()`
    4. Persists `ParseResult` into DB
    5. Optionally deletes orphans scoped to `source_system_id`

### 2.2 Persistence and graph model (current)
- **Node storage:** `Capsule` table is the general-purpose node.
  - `capsule_type` is a string, not DB-enforced to enum values.
  - `meta` is JSON(B) (Postgres) / JSON-in-TEXT (SQLite tests).
- **Lineage storage:** `CapsuleLineage` table stores directed edges with:
  - `edge_type` (string, default `flows_to`)
  - `meta` (JSON)
- **URN uniqueness:** enforced via `URNMixin` (`unique=True`)

This is compatible with representing *pipelines* (Airflow DAGs and tasks) without creating new tables.

### 2.3 Query surfaces (current)
- **API:** FastAPI routers for capsules, columns, conformance, compliance, ingestion, graph export.
  - Capsules and lineage endpoints do not enforce a strict set of capsule types.
  - Graph export uses `capsule.capsule_type` as the exported `node_type`.
- **CLI:** `dcs ingest dbt ...` is implemented; other source types currently produce an “Unknown source type” message.

### 2.4 Key gaps relevant to Airflow
1. **Secret handling:** ingestion job `config` is stored verbatim. This is safe for dbt file-path configs but not safe for Airflow tokens/passwords.
2. **Non-dbt ingestion support:** API and CLI have dbt-specific request models/flags.
3. **Tags/domains ingestion:** parser base supports tags/domains, but ingestion persistence currently only creates domains; tags are not persisted from `ParseResult.tags`.

Airflow integration should not worsen these gaps; it should explicitly address the secret-handling risk.

---

## 3. Proposed Airflow Integration (P2) — Functional Design

### 3.1 What metadata we ingest
Minimum metadata to qualify as “DAG definitions / pipeline metadata”:

**DAG-level**
- `dag_id`
- `description`
- `owners`
- `tags`
- `fileloc` / `file_token` if available
- `schedule_interval` / timetable summary
- `is_paused`, `is_active`
- `start_date`, `end_date` if available
- `catchup`, `max_active_runs`, `max_active_tasks` if available
- Optional: last parsing time / last run summary (best-effort)

**Task-level**
- `task_id`
- `operator` / `task_type` (e.g., `BashOperator`, `BigQueryInsertJobOperator`)
- `retries`, `retry_delay`, `execution_timeout`, `sla` if available
- `queue`, `pool`, `priority_weight` if available
- `doc_md` / `documentation` if available

**Edges**
- DAG contains tasks
- Task dependencies (task → downstream task)

### 3.2 Ingestion mode(s)

#### Mode A (Primary): Airflow REST API (Airflow 2.x)
Use Airflow’s stable REST API (`/api/v1/...`) to fetch DAG and task metadata.

Pros
- Doesn’t require parsing Python code.
- Works regardless of DAG structure (TaskFlow API, dynamic DAGs) as long as Airflow can serialize it.

Cons
- Metadata completeness depends on Airflow version/config.

#### Mode B (Secondary, optional): DAG folder scan (offline)
Parse Python DAG files (AST-based heuristic) for `DAG(...)` and operator instantiations.

This is **not recommended for P2** due to brittleness and large maintenance surface, but it can be planned as a fallback for environments without API access.

### 3.3 Authentication model (no secrets stored)
We must avoid persisting credentials in `ingestion_jobs.config`.

Recommended approach:
- Allow the user to provide **non-secret config** (base URL, instance name, filters) to the ingestion entrypoint.
- Provide auth via **environment variables** or “secret references”:
  - Example: `AIRFLOW_AUTH_MODE=bearer` and `AIRFLOW_TOKEN` in environment
  - Store `{"auth_mode": "bearer", "token_env": "AIRFLOW_TOKEN"}` in ingestion job config, never the token value.
- Implement a generic `redact_secrets(config: dict) -> dict` as defense-in-depth and apply it in `IngestionJobRepository.start_job()` (or in `IngestionService.ingest()`).

Supported auth modes (initial)
- Bearer token (`Authorization: Bearer ...`)
- Basic auth (`username` + password via env)

Future
- mTLS / OAuth / AWS/GCP identity proxies (out of scope)

---

## 4. Graph Modeling

### 4.1 Node representation
We will reuse `Capsule` for both DAGs and tasks.

**DAG capsule**
- `capsule_type`: `airflow_dag`
- `urn`: `urn:dcs:airflow:dag:{instance}:{dag_id}`
- `name`: `{dag_id}`
- `description`: from Airflow if present
- `meta`: schedule, paused/active flags, owners, tags, file location, etc.
- `source_system_id`: references the Airflow instance

**Task capsule**
- `capsule_type`: `airflow_task`
- `urn`: `urn:dcs:airflow:task:{instance}:{dag_id}.{task_id}`
- `name`: `{task_id}`
- `meta`: operator/type, retries, timeouts, pool/queue, etc.

We leave `layer` empty by default. If desired, `layer` could be set to `orchestration` but this introduces a new conceptual layer not currently used by conformance rules.

### 4.2 Edge representation
We will reuse `CapsuleLineage` for all Airflow relationships.

1. DAG → Task (`edge_type = "CONTAINS"`)
   - Source: DAG capsule
   - Target: Task capsule

2. Task → Task dependencies (`edge_type = "FLOWS_TO"`)
   - Source: upstream task capsule
   - Target: downstream task capsule
   - This allows existing lineage traversal and graph export to work.

Edge `meta` can include:
- `dag_id`
- `dependency_type` (direct)
- Optional: `trigger_rule`, `weight_rule`, etc.

### 4.3 Domain assignment
Options:
- Leave `domain_id` unset for Airflow entities.
- Support a configurable mapping:
  - From DAG tags (e.g., `domain:customer`) → domain
  - From DAG owner/team → domain

Recommendation for P2:
- Implement **tag-based domain inference** as an optional config:
  - `domain_tag_prefix = "domain:"`

---

## 5. Parser Design

### 5.1 New parser: `AirflowParser`
Add `src/parsers/airflow_parser.py` implementing `MetadataParser`.

**Key responsibilities**
- Validate non-secret config.
- Connect to Airflow REST API using `httpx.AsyncClient`.
- Fetch DAGs, then tasks and dependencies.
- Emit normalized `ParseResult` with `RawCapsule` and `RawEdge`.

### 5.2 Parser config: `AirflowParserConfig`
Add `src/parsers/airflow_config.py` similar to `DbtParserConfig`.

Proposed config fields (non-secret)
- `base_url: str` (e.g., `https://airflow.example.com`)
- `instance_name: str` (stable identifier for URN namespace; default derived from base_url hostname)
- `dag_id_allowlist: list[str] | None`
- `dag_id_denylist: list[str] | None`
- `dag_id_regex: str | None`
- `include_paused: bool = False`
- `include_inactive: bool = False`
- `page_limit: int = 100`
- `timeout_seconds: float = 30.0`

Auth fields stored as references
- `auth_mode: Literal["none","bearer_env","basic_env"]`
- `token_env: str = "AIRFLOW_TOKEN"`
- `username_env: str = "AIRFLOW_USERNAME"`
- `password_env: str = "AIRFLOW_PASSWORD"`

### 5.3 Airflow API endpoints used
Assuming Airflow 2.x stable API:
- `GET /api/v1/version` (optional) → set `ParseResult.source_version`
- `GET /api/v1/dags?limit=&offset=`
- `GET /api/v1/dags/{dag_id}`
- `GET /api/v1/dags/{dag_id}/tasks?limit=&offset=`
- `GET /api/v1/dags/{dag_id}/tasks/{task_id}` (only if dependencies aren’t available in list response)

Implementation detail: tolerate minor API shape differences by defensive field access.

### 5.4 Error handling and partial ingestion
- Non-fatal errors (missing optional fields, one DAG failing) → `ParseErrorSeverity.WARNING` and continue.
- Fatal errors (auth failure, unreachable base URL, invalid config) → `ParseErrorSeverity.ERROR` and abort.
- Ensure `ParseResult.source_name` is set to `instance_name`.

---

## 6. Ingestion, API, and CLI Changes

### 6.1 Ingestion service
Add:
- `IngestionService.ingest_airflow(config: dict[str, Any], cleanup_orphans: bool = False)`

This should call the generic `ingest("airflow", config, cleanup_orphans=...)`.

### 6.2 Parser registry
Register the parser:
- `default_registry.register("airflow", AirflowParser)`

### 6.3 API ingestion endpoints
Extend [backend/src/api/routers/ingest.py](backend/src/api/routers/ingest.py) with:
- `POST /ingest/airflow` accepting a JSON body (non-secret fields + env var names)

Do **not** implement file upload for Airflow (no artifacts to upload).

### 6.4 CLI ingestion
Extend [backend/src/cli/main.py](backend/src/cli/main.py):
- `dcs ingest airflow --base-url ... --instance ... [--dag-regex ...] [--include-paused]`

Prefer passing secrets via environment:
- `AIRFLOW_TOKEN=... dab ingest airflow ...`

### 6.5 Graph export and browsing
No changes required if we store DAGs and tasks as capsules.
Users can query:
- `GET /api/v1/capsules?capsule_type=airflow_dag`
- `GET /api/v1/capsules?capsule_type=airflow_task`
- Export subgraphs via `/api/v1/graph/export` and `/api/v1/graph/export/lineage/{urn}`

---

## 7. Data Quality, Performance, and Observability

### 7.1 Performance targets
Airflow instance sizes can vary widely. To stay consistent with DAB NFRs:
- Use pagination on DAG and task listings.
- Use limited concurrency when fetching per-DAG details to avoid overwhelming Airflow.

Suggested approach
- `asyncio.Semaphore(concurrency=5..10)` for per-DAG calls.

### 7.2 Observability
- Use existing structured logging (`structlog`) patterns already configured.
- Add logs:
  - number of DAGs, tasks, edges ingested
  - per-DAG warnings
- Use OpenTelemetry httpx instrumentation already present in dependencies.

### 7.3 Metrics
Add (optional) Prometheus counters:
- `dab_ingest_airflow_dags_total`
- `dab_ingest_airflow_tasks_total`
- `dab_ingest_airflow_requests_total` (by status class)

---

## 8. Testing Strategy

### 8.1 Unit tests
- Parser config validation tests mirroring dbt config tests.
- Airflow parser tests:
  - mock `httpx.AsyncClient` responses for DAG/task endpoints
  - verify `ParseResult` contains expected capsules/edges
  - verify URN construction and namespace

### 8.2 Integration tests
- API tests for `POST /api/v1/ingest/airflow` (use test DB, mock parser HTTP)
- CLI tests for `dcs ingest airflow` option parsing (mock `IngestionService`)

### 8.3 Security tests
- Ensure `IngestionJob.config` does not contain raw secrets when using bearer/basic auth.

---

## 9. Implementation Plan (Detailed)

### Milestone 0 — Prep: secret redaction (required)
1. Add a small utility `src/services/secret_redaction.py` (or similar):
   - `redact_config(config: dict) -> dict`
   - Redact keys: `token`, `password`, `secret`, `authorization`, `api_key` (case-insensitive)
2. Apply redaction before persisting ingestion job config:
   - Best place: `IngestionJobRepository.start_job()`
   - Alternative: `IngestionService.ingest()` right before `start_job()`

Acceptance criteria
- Ingestion job records never contain raw tokens/passwords.

### Milestone 1 — Parser and registry
Files
- `backend/src/parsers/airflow_config.py` (new)
- `backend/src/parsers/airflow_parser.py` (new)
- `backend/src/parsers/__init__.py` (register new parser)

Work
- Implement config parsing + validation.
- Implement Airflow API client wrapper (internal to parser) using `httpx.AsyncClient`.
- Emit DAG and task capsules, plus CONTAINS/FLOWS_TO edges.

Acceptance criteria
- `available_parsers()` includes `airflow`.
- Parser can parse a mocked Airflow API into a non-empty `ParseResult`.

### Milestone 2 — Ingestion service support
Files
- `backend/src/services/ingestion.py`

Work
- Add `ingest_airflow(...)` convenience method.
- Ensure `cleanup_orphans` works correctly for Airflow source system.

Acceptance criteria
- Airflow ingestion produces capsules and edges and completes ingestion job.

### Milestone 3 — API ingestion endpoint
Files
- `backend/src/api/routers/ingest.py`

Work
- Add request/response model for Airflow ingestion.
- Implement `POST /ingest/airflow`.

Acceptance criteria
- Endpoint returns a job id and stats, consistent with dbt.

### Milestone 4 — CLI ingestion support
Files
- `backend/src/cli/main.py`

Work
- Add `airflow` branch under `dcs ingest`.
- Add options for base URL, instance, filters.
- Document env vars for auth.

Acceptance criteria
- `dcs ingest airflow --help` shows correct options.

### Milestone 5 — Tests
Files
- `backend/tests/parsers/test_airflow_parser.py` (new)
- `backend/tests/unit/test_cli.py` (extend)
- `backend/tests/integration/test_api.py` (extend)

Acceptance criteria
- Parser tests cover URN creation, DAG parsing, task parsing, dependency edges, and secret non-persistence.

### Milestone 6 — Documentation
Files
- `README.md` and/or `docs/USER_GUIDE.md` (optional follow-up)

Work
- Add “Airflow ingestion” usage examples.
- Add troubleshooting section for auth and base URL.

---

## 10. Open Questions / Decisions Needed

1. **Airflow version target:** Should we explicitly support only Airflow 2.5+ (or 2.7+) to reduce API-shape variance?
2. **Edge semantics:** Should task dependencies be `FLOWS_TO` or a more explicit `DEPENDS_ON`?
   - Recommendation: `FLOWS_TO` to maximize compatibility with existing traversal/exports.
3. **Domain inference:** Do we want a standard tag convention (e.g., `domain:<name>`) across dbt and Airflow?
4. **Persist tags from ParseResult:** Airflow DAG tags are valuable, but today `ParseResult.tags` isn’t persisted. Do we fix this as part of Airflow work (recommended) or keep tags only on `Capsule.tags`?

---

## 11. Appendix — Example URNs

- DAG: `urn:dcs:airflow:dag:prod-airflow:customer_daily_pipeline`
- Task: `urn:dcs:airflow:task:prod-airflow:customer_daily_pipeline.extract_customers`

---

## 12. Appendix — Example API calls

- List DAG capsules: `GET /api/v1/capsules?capsule_type=airflow_dag`
- Lineage graph for a DAG: `GET /api/v1/capsules/{urn}/lineage?direction=downstream&depth=5`
- Export DAG subgraph (Mermaid): `GET /api/v1/graph/export/lineage/{urn}?format=mermaid&depth=5`
