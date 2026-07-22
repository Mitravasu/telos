.DEFAULT_GOAL := help

.PHONY: install db-up db-init migrate run dev test lint docker-build docker-run down help

install: ## Install locked dependencies
	uv sync

db-up: ## Start PostgreSQL
	docker compose up -d postgres

migrate: ## Upgrade application schema
	@set -a; [ ! -f .env ] || . ./.env; set +a; uv run alembic upgrade head

db-init: migrate ## Initialize application and checkpoint schemas
	@set -a; [ ! -f .env ] || . ./.env; set +a; uv run python scripts/db_init.py

run: ## Run the host CLI
	@set -a; [ ! -f .env ] || . ./.env; set +a; uv run telos

dev: db-up db-init run ## Start dependencies and run Telos

test: ## Run tests
	uv run pytest

test-integration: ## Run PostgreSQL integration tests
	@set -a; [ ! -f .env ] || . ./.env; set +a; TELOS_TEST_DATABASE_URL="$${DATABASE_URL:-postgresql+psycopg://telos:telos@localhost:5432/telos}" uv run pytest -m integration --no-cov

lint: ## Run lint checks
	uv run ruff check .

docker-build: ## Build the application image
	docker compose build telos

docker-run: ## Run the containerized CLI
	docker compose run --rm telos

down: ## Stop containers
	docker compose down

help: ## Show command help
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "%-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
