# Data Capsule Server - Makefile
# Run `make help` to see available commands

.PHONY: help up down logs test lint format migrate shell clean build

# Default target
.DEFAULT_GOAL := help

# Colors for output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RESET := \033[0m

help: ## Show this help message
	@echo "$(CYAN)Data Capsule Server$(RESET) - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2}'

# ============================================
# Docker Commands
# ============================================

up: ## Start all services
	docker compose -f docker/docker-compose.yml up -d

up-dev: ## Start services in development mode (with hot reload)
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d

up-tools: ## Start services with development tools (pgAdmin)
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml --profile tools up -d

down: ## Stop all services
	docker compose -f docker/docker-compose.yml down

down-v: ## Stop all services and remove volumes
	docker compose -f docker/docker-compose.yml down -v

logs: ## View logs (follow mode)
	docker compose -f docker/docker-compose.yml logs -f

logs-api: ## View API logs only
	docker compose -f docker/docker-compose.yml logs -f dcs-api

build: ## Build Docker images
	docker compose -f docker/docker-compose.yml build

rebuild: ## Force rebuild Docker images
	docker compose -f docker/docker-compose.yml build --no-cache

# ============================================
# Database Commands
# ============================================

migrate: ## Run database migrations
	docker compose -f docker/docker-compose.yml exec dcs-api alembic upgrade head

migrate-new: ## Create a new migration (usage: make migrate-new MSG="description")
	docker compose -f docker/docker-compose.yml exec dcs-api alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Rollback one migration
	docker compose -f docker/docker-compose.yml exec dcs-api alembic downgrade -1

migrate-history: ## Show migration history
	docker compose -f docker/docker-compose.yml exec dcs-api alembic history

db-shell: ## Open PostgreSQL shell
	docker compose -f docker/docker-compose.yml exec postgres psql -U dcs -d dcs

# ============================================
# Development Commands
# ============================================

shell: ## Open shell in API container
	docker compose -f docker/docker-compose.yml exec dcs-api /bin/bash

install: ## Install dependencies locally
	cd backend && pip install -e ".[dev]"

install-hooks: ## Install pre-commit hooks
	cd backend && pre-commit install

# ============================================
# Testing & Quality
# ============================================

test: ## Run tests
	cd backend && pytest tests/ -v

test-cov: ## Run tests with coverage
	cd backend && pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

test-unit: ## Run unit tests only
	cd backend && pytest tests/unit/ -v

test-integration: ## Run integration tests only
	cd backend && pytest tests/integration/ -v

lint: ## Run linting
	cd backend && ruff check src/ tests/

lint-fix: ## Run linting with auto-fix
	cd backend && ruff check src/ tests/ --fix

format: ## Format code
	cd backend && ruff format src/ tests/

typecheck: ## Run type checking
	cd backend && mypy src/

check: lint typecheck test ## Run all checks (lint, typecheck, test)

# ============================================
# CLI Commands
# ============================================

cli-help: ## Show CLI help
	docker compose -f docker/docker-compose.yml exec dcs-api python -m src.cli.main --help

ingest-dbt: ## Ingest dbt artifacts (usage: make ingest-dbt MANIFEST=/path/to/manifest.json)
	docker compose -f docker/docker-compose.yml exec dcs-api python -m src.cli.main ingest dbt --manifest $(MANIFEST)

pii-inventory: ## Show PII inventory
	docker compose -f docker/docker-compose.yml exec dcs-api python -m src.cli.main pii inventory

conformance-score: ## Show conformance score
	docker compose -f docker/docker-compose.yml exec dcs-api python -m src.cli.main conformance score

# ============================================
# Cleanup
# ============================================

clean: ## Remove all containers, volumes, and images
	docker compose -f docker/docker-compose.yml down -v --remove-orphans
	docker system prune -f

clean-pyc: ## Remove Python cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name ".mypy_cache" -delete
	find . -type d -name ".ruff_cache" -delete

# ============================================
# Documentation
# ============================================

docs-serve: ## Serve documentation locally
	cd backend && mkdocs serve

docs-build: ## Build documentation
	cd backend && mkdocs build
