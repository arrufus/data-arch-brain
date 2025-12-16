"""Ingestion endpoints."""

import tempfile
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, Form
from pydantic import BaseModel

from src.api.exceptions import NotFoundError, IngestionError
from src.database import DbSession
from src.services.ingestion import IngestionService, IngestionStats as ServiceStats

router = APIRouter(prefix="/ingest")


class DbtIngestRequest(BaseModel):
    """Request body for dbt ingestion via JSON."""

    manifest_path: str
    catalog_path: Optional[str] = None
    project_name: Optional[str] = None


class AirflowIngestRequest(BaseModel):
    """Request body for Airflow ingestion via REST API.

    Authentication credentials should be provided via environment variables
    referenced in token_env, username_env, and password_env fields.
    """

    base_url: str
    instance_name: Optional[str] = None
    auth_mode: str = "none"
    token_env: str = "AIRFLOW_TOKEN"
    username_env: str = "AIRFLOW_USERNAME"
    password_env: str = "AIRFLOW_PASSWORD"
    dag_id_allowlist: Optional[list[str]] = None
    dag_id_denylist: Optional[list[str]] = None
    dag_id_regex: Optional[str] = None
    include_paused: bool = False
    include_inactive: bool = False
    page_limit: int = 100
    timeout_seconds: float = 30.0
    domain_tag_prefix: str = "domain:"
    cleanup_orphans: bool = False


class IngestionStats(BaseModel):
    """Statistics from an ingestion job."""

    capsules_created: int = 0
    capsules_updated: int = 0
    capsules_unchanged: int = 0
    columns_created: int = 0
    columns_updated: int = 0
    edges_created: int = 0
    edges_updated: int = 0
    domains_created: int = 0
    pii_columns_detected: int = 0
    warnings: int = 0
    errors: int = 0

    @classmethod
    def from_service(cls, stats: ServiceStats) -> "IngestionStats":
        """Create from service stats."""
        return cls(**stats.to_dict())


class IngestionResponse(BaseModel):
    """Response from an ingestion job."""

    job_id: UUID
    status: str
    source_type: str
    source_name: Optional[str] = None
    stats: Optional[IngestionStats] = None
    message: Optional[str] = None
    duration_seconds: Optional[float] = None


class IngestionStatusResponse(BaseModel):
    """Status of an ingestion job."""

    job_id: UUID
    status: str
    source_type: str
    source_name: Optional[str] = None
    stats: Optional[dict] = None
    started_at: str
    completed_at: Optional[str] = None
    elapsed_seconds: Optional[float] = None
    error_message: Optional[str] = None


class IngestionHistoryItem(BaseModel):
    """Item in ingestion history."""

    job_id: UUID
    status: str
    source_type: str
    source_name: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None
    stats: Optional[dict] = None


class IngestionHistoryResponse(BaseModel):
    """Response for ingestion history."""

    data: list[IngestionHistoryItem]
    pagination: dict


@router.post("/dbt", response_model=IngestionResponse)
async def ingest_dbt(
    request: DbtIngestRequest,
    db: DbSession,
) -> IngestionResponse:
    """
    Ingest dbt artifacts (manifest.json, catalog.json).

    This endpoint accepts file paths on the server filesystem.
    For file uploads, use POST /ingest/dbt/upload instead.
    """
    service = IngestionService(db)

    result = await service.ingest_dbt(
        manifest_path=request.manifest_path,
        catalog_path=request.catalog_path,
        project_name=request.project_name,
    )

    response = IngestionResponse(
        job_id=result.job_id,
        status=result.status.value,
        source_type=result.source_type,
        source_name=result.source_name,
        stats=IngestionStats.from_service(result.stats),
        duration_seconds=result.duration_seconds,
    )

    if result.error_message:
        response.message = result.error_message

    return response


@router.post("/airflow", response_model=IngestionResponse)
async def ingest_airflow(
    request: AirflowIngestRequest,
    db: DbSession,
) -> IngestionResponse:
    """
    Ingest Airflow DAG and task metadata via REST API.

    Authentication credentials must be provided via environment variables.
    The request specifies which env vars to use (e.g., AIRFLOW_TOKEN).

    Example:
        {
            "base_url": "https://airflow.example.com",
            "instance_name": "prod-airflow",
            "auth_mode": "bearer_env",
            "token_env": "AIRFLOW_TOKEN",
            "dag_id_regex": "customer_.*",
            "include_paused": false,
            "cleanup_orphans": true
        }

    Note: Actual credentials (tokens, passwords) are read from environment
    variables at runtime and are never stored in the request or database.
    """
    service = IngestionService(db)

    result = await service.ingest_airflow(
        base_url=request.base_url,
        instance_name=request.instance_name,
        auth_mode=request.auth_mode,
        token_env=request.token_env,
        username_env=request.username_env,
        password_env=request.password_env,
        dag_id_allowlist=request.dag_id_allowlist,
        dag_id_denylist=request.dag_id_denylist,
        dag_id_regex=request.dag_id_regex,
        include_paused=request.include_paused,
        include_inactive=request.include_inactive,
        page_limit=request.page_limit,
        timeout_seconds=request.timeout_seconds,
        domain_tag_prefix=request.domain_tag_prefix,
        cleanup_orphans=request.cleanup_orphans,
    )

    response = IngestionResponse(
        job_id=result.job_id,
        status=result.status.value,
        source_type=result.source_type,
        source_name=result.source_name,
        stats=IngestionStats.from_service(result.stats),
        duration_seconds=result.duration_seconds,
    )

    if result.error_message:
        response.message = result.error_message

    return response


@router.post("/dbt/upload", response_model=IngestionResponse)
async def ingest_dbt_upload(
    db: DbSession,
    manifest: UploadFile = File(..., description="manifest.json file"),
    catalog: Optional[UploadFile] = File(None, description="catalog.json file"),
    project_name: Optional[str] = Form(None),
) -> IngestionResponse:
    """
    Ingest dbt artifacts via file upload.

    Upload manifest.json (required) and optionally catalog.json.
    """
    # Save uploaded files to temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Save manifest
        manifest_path = tmpdir_path / "manifest.json"
        manifest_content = await manifest.read()
        manifest_path.write_bytes(manifest_content)

        # Save catalog if provided
        catalog_path = None
        if catalog:
            catalog_path = tmpdir_path / "catalog.json"
            catalog_content = await catalog.read()
            catalog_path.write_bytes(catalog_content)

        # Run ingestion
        service = IngestionService(db)
        result = await service.ingest_dbt(
            manifest_path=str(manifest_path),
            catalog_path=str(catalog_path) if catalog_path else None,
            project_name=project_name,
        )

    response = IngestionResponse(
        job_id=result.job_id,
        status=result.status.value,
        source_type=result.source_type,
        source_name=result.source_name,
        stats=IngestionStats.from_service(result.stats),
        duration_seconds=result.duration_seconds,
    )

    if result.error_message:
        response.message = result.error_message

    return response


@router.get("/status/{job_id}", response_model=IngestionStatusResponse)
async def get_ingestion_status(
    job_id: UUID,
    db: DbSession,
) -> IngestionStatusResponse:
    """Get status of an ingestion job."""
    service = IngestionService(db)
    job = await service.get_job_status(job_id)

    if not job:
        raise NotFoundError("Ingestion job", str(job_id))

    return IngestionStatusResponse(
        job_id=job.id,
        status=job.status,
        source_type=job.source_type,
        source_name=job.source_name,
        stats=job.stats,
        started_at=job.started_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        elapsed_seconds=job.duration_seconds,
        error_message=job.error_message,
    )


@router.post("/cancel/{job_id}", response_model=IngestionStatusResponse)
async def cancel_ingestion(
    job_id: UUID,
    db: DbSession,
) -> IngestionStatusResponse:
    """Cancel a running ingestion job."""
    service = IngestionService(db)
    job = await service.cancel_job(job_id)

    if not job:
        raise NotFoundError("Ingestion job", str(job_id))

    return IngestionStatusResponse(
        job_id=job.id,
        status=job.status,
        source_type=job.source_type,
        source_name=job.source_name,
        stats=job.stats,
        started_at=job.started_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        elapsed_seconds=job.duration_seconds,
        error_message=job.error_message,
    )


@router.get("/history", response_model=IngestionHistoryResponse)
async def get_ingestion_history(
    db: DbSession,
    source_type: Optional[str] = None,
    limit: int = 50,
) -> IngestionHistoryResponse:
    """Get ingestion job history."""
    service = IngestionService(db)
    jobs = await service.get_recent_jobs(limit=limit, source_type=source_type)

    items = [
        IngestionHistoryItem(
            job_id=job.id,
            status=job.status,
            source_type=job.source_type,
            source_name=job.source_name,
            started_at=job.started_at.isoformat(),
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            stats=job.stats,
        )
        for job in jobs
    ]

    return IngestionHistoryResponse(
        data=items,
        pagination={
            "total": len(items),
            "limit": limit,
            "has_more": len(items) == limit,
        },
    )
