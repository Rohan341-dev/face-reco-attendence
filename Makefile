SHELL := /bin/bash
PY := backend/.venv/bin/python
PIP := backend/.venv/bin/pip
PYVERSION := 3.12

.PHONY: help venv install db-up db-down migrate run-backend run-ai run-web test lint typecheck check codegen seed

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

venv: ## Create Python 3.12 venv for backend and ai
	python3.12 -m venv backend/.venv
	backend/.venv/bin/pip install --upgrade pip

install: venv ## Install backend + ai dependencies
	$(PIP) install -r backend/requirements.txt
	$(PIP) install -r ai/requirements.txt
	cd web && npm install

db-up: ## Start Postgres + Redis (homebrew services or docker if available)
	@if command -v docker >/dev/null 2>&1; then \
		docker compose -f docker-compose.dev.yml up -d postgres redis; \
	else \
		brew services start postgresql@18 || brew services start postgresql; \
		brew services start redis; \
	fi

db-down: ## Stop dev services
	@if command -v docker >/dev/null 2>&1; then \
		docker compose -f docker-compose.dev.yml down; \
	else \
		brew services stop postgresql@18 || true; \
		brew services stop redis || true; \
	fi

migrate: ## Apply backend migrations
	cd backend && $(PY) manage.py migrate

run-backend: ## Run Django dev server
	cd backend && $(PY) manage.py runserver 0.0.0.0:8000

run-ai: ## Run AI service (uvicorn)
	cd ai && ../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

run-web: ## Run web dashboard (Vite)
	cd web && npm run dev

test: ## Run backend + ai + web tests
	cd backend && $(PY) -m pytest -q
	cd ai && $(PY) -m pytest -q
	cd web && npm test -- --run

lint: ## Ruff + eslint
	cd backend && $(PY) -m ruff check .
	cd ai && $(PY) -m ruff check .
	cd web && npm run lint --if-present

typecheck: ## mypy + tsc
	cd backend && $(PY) -m mypy apps config || true
	cd web && npm run typecheck --if-present

codegen: ## Generate OpenAPI spec and TS client types
	cd backend && $(PY) manage.py spectacular --file ../shared/openapi.json --format openapi-json
	scripts/generate-api-types.sh

check: lint typecheck test ## Full quality gate
