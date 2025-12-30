# Data Capsule Server - User & Administrator Manual

**Version**: 1.0  
**Date**: December 2025

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Architecture](#2-system-architecture)
3. [Features](#3-features)
4. [User Guide](#4-user-guide)
    - [Getting Started](#41-getting-started)
    - [Web Dashboard](#42-web-dashboard)
    - [CLI Usage](#43-cli-usage)
    - [API Usage](#44-api-usage)
5. [Support & Operations](#5-support--operations)
    - [Health Checks](#51-health-checks)
    - [Troubleshooting](#52-troubleshooting)
    - [Configuration](#53-configuration)

---

## 1. Introduction

**Data Capsule Server** is a comprehensive architecture intelligence platform designed to provide a unified view of your organization's data landscape. It ingests metadata from various sources (such as dbt and Airflow), constructs a property graph representation of data assets, and offers intelligent insights for governance, compliance, and architecture optimization.

### Key Value Propositions

*   **Unified Visibility**: A "single pane of glass" for all data assets, regardless of their source system.
*   **PII & Sensitive Data Tracking**: Automated tracing of sensitive data elements through transformation pipelines to detect exposure risks.
*   **Architecture Conformance**: Continuous validation of data models against defined standards (e.g., naming conventions, Medallion architecture).
*   **Redundancy Detection**: Identification of duplicate or overlapping data assets to reduce storage and compute costs.
*   **Impact Analysis**: Assessment of downstream effects for proposed changes to data models.

### Target Audience

*   Data Architects
*   Data Governance Teams
*   Platform Engineers
*   Data Product Owners
*   Compliance Officers

---

## 2. System Architecture

The Data Capsule Server follows a layered architecture designed for scalability and separation of concerns.

### High-Level Architecture

```mermaid
graph TD
    Client[Clients] --> API[API Layer]
    API --> Service[Service Layer]
    Service --> Repo[Repository Layer]
    Repo --> Data[Data Layer]

    subgraph Clients
        CLI[CLI (dab)]
        Web[Web Dashboard]
        REST[REST API Clients]
    end

    subgraph API_Layer
        FastAPI[FastAPI Application]
        IngestR[Ingest Router]
        QueryR[Query Router]
        CompR[Compliance Router]
        ConfR[Conformance Router]
    end

    subgraph Service_Layer
        IngestS[Ingestion Service]
        GraphS[Graph Service]
        PIIS[PII Service]
        ConfS[Conformance Service]
    end

    subgraph Repository_Layer
        CapRepo[Capsule Repo]
        ColRepo[Column Repo]
        LinRepo[Lineage Repo]
        RuleRepo[Rule Repo]
    end

    subgraph Data_Layer
        Postgres[(PostgreSQL)]
        Redis[(Redis Cache)]
    end

    CLI --> FastAPI
    Web --> FastAPI
    REST --> FastAPI

    FastAPI --> IngestS
    FastAPI --> GraphS
    FastAPI --> PIIS
    FastAPI --> ConfS

    IngestS --> CapRepo
    GraphS --> LinRepo
    PIIS --> ColRepo
    ConfS --> RuleRepo

    CapRepo --> Postgres
    ColRepo --> Postgres
    LinRepo --> Postgres
    RuleRepo --> Postgres
```

### Component Description

| Component | Technology | Description |
|-----------|------------|-------------|
| **Web Dashboard** | React, Next.js | The primary user interface for exploring data capsules, lineage, and reports. |
| **API Server** | Python, FastAPI | The backend service that handles requests, business logic, and orchestration. |
| **Database** | PostgreSQL | The primary data store for metadata, graph relationships (nodes/edges), and rules. |
| **Cache** | Redis | Used for caching frequent queries and rate limiting API requests. |
| **CLI** | Python (Typer) | Command-line interface for administrative tasks and metadata ingestion. |

---

## 3. Features

### Web Dashboard
*   **Data Capsule Browser**: Search, filter, and explore data assets with pagination.
*   **Interactive Lineage**: Visual graph of data flow with upstream/downstream navigation.
*   **PII Compliance**: Dashboard for tracking sensitive data inventory and exposure risks.
*   **Conformance Scoring**: Real-time monitoring of architecture violations.
*   **Impact Analysis**: Visual tool to assess the blast radius of changes.
*   **Redundancy Detection**: Identification of similar data assets.
*   **Reporting**: Export capabilities for audit and analysis.

### Core Platform
*   **Metadata Ingestion**: Parsers for dbt artifacts (manifest.json, catalog.json) and Airflow DAGs.
*   **Graph Analysis**: Advanced graph algorithms for lineage and relationship mapping.
*   **Tag Management**: Flexible tagging system for organizing assets.
*   **Data Products**: Grouping of assets into logical business units with SLO tracking.

---

## 4. User Guide

### 4.1 Getting Started

#### Prerequisites
*   Docker Desktop 4.0+
*   Docker Compose 2.0+
*   Make (optional)

#### Installation & Running
1.  Clone the repository.
2.  Start the services using Docker Compose:
    ```bash
    make up
    # OR
    docker compose -f docker/docker-compose.yml up -d
    ```
3.  Run database migrations:
    ```bash
    make migrate
    ```
4.  Access the application:
    *   **Dashboard**: [http://localhost:3000](http://localhost:3000)
    *   **API Docs**: [http://localhost:8002/docs](http://localhost:8002/docs)

### 4.2 Web Dashboard

The dashboard is the main entry point for users.

*   **Capsules**: Navigate to `/capsules` to see a list of all data assets. Use the search bar to find specific tables or views. Click on a capsule to view its details, schema, and lineage.
*   **Lineage**: The `/lineage` page provides an interactive graph. You can select a node to see its dependencies.
*   **Compliance**: The `/compliance` page highlights PII risks. It lists columns tagged as sensitive and shows if they are exposed in downstream reports.
*   **Conformance**: Check `/conformance` to see if your data architecture adheres to defined rules (e.g., "All staging tables must start with `stg_`").
*   **Settings**: Configure domains, tags, and rules in the `/settings` area.

### 4.3 CLI Usage

The `dcs` (Data Capsule Server) CLI is used primarily for ingesting metadata.

**Ingest dbt Project:**
```bash
dcs ingest dbt --manifest /path/to/manifest.json --catalog /path/to/catalog.json --project my_project
```

**Options:**
*   `--manifest`: Path to the dbt `manifest.json` file (Required).
*   `--catalog`: Path to the dbt `catalog.json` file (Optional).
*   `--project`: Override the project name.

### 4.4 API Usage

The platform exposes a comprehensive REST API.

*   **Base URL**: `http://localhost:8002/api/v1`
*   **Authentication**: API Key required (configured in environment variables).
*   **Documentation**: Full Swagger UI is available at `/docs`.

**Common Endpoints:**
*   `GET /capsules`: List data capsules.
*   `GET /lineage/{urn}`: Get lineage for a specific asset.
*   `GET /compliance/pii`: Get PII inventory.

---

## 5. Support & Operations

### 5.1 Health Checks

The system provides health endpoints for monitoring:

*   `GET /api/v1/health`: Full system health (DB connection, Cache status).
*   `GET /api/v1/health/live`: Liveness probe (returns 200 OK if service is running).
*   `GET /api/v1/health/ready`: Readiness probe (returns 200 OK if ready to accept traffic).

### 5.2 Troubleshooting

**Common Issues:**

1.  **Ingestion Fails**:
    *   Check if the `manifest.json` path is correct.
    *   Ensure the database is running and accessible.
    *   Check logs for parsing errors.

2.  **Dashboard not loading**:
    *   Verify the frontend container is running (`docker ps`).
    *   Check browser console for API connection errors (CORS or network issues).

3.  **Database Connection Error**:
    *   Ensure PostgreSQL container is healthy.
    *   Check `DATABASE_URL` environment variable in `backend/.env`.

### 5.3 Configuration

Configuration is managed via environment variables and `.env` files.

*   **Backend**: `backend/.env` (Database URL, Redis URL, API Keys).
*   **Frontend**: `frontend/.env.local` (API Base URL, Public Keys).
*   **Docker**: `docker/docker-compose.yml` (Port mappings, volume mounts).

For detailed configuration options, refer to the `RUNBOOK.md` file in the `docs` directory.
