# Convenience wrappers. Every target maps to a command documented in README.md,
# so make is optional -- it is not installed by default on Windows.

PY := backend/.venv/Scripts/python.exe
NPM := npm --prefix frontend

.PHONY: help venv install run dev test test-api test-web lint typecheck format check clean

help:
	@echo "venv       Create the backend virtualenv (needs Python 3.11+)"
	@echo "install    Install backend and frontend dependencies"
	@echo "run        Start the API with reload on :8000"
	@echo "dev        Start the web app on :5173"
	@echo "test       Run every test suite"
	@echo "lint       Lint backend and frontend"
	@echo "typecheck  Type-check the frontend"
	@echo "format     Format the backend"
	@echo "check      lint + typecheck + test + build"

venv:
	py -3.13 -m venv backend/.venv

install:
	$(PY) -m pip install -e "backend[dev]"
	$(NPM) install

run:
	cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000

dev:
	$(NPM) run dev

test: test-api test-web

test-api:
	cd backend && .venv/Scripts/python.exe -m pytest -q

test-web:
	$(NPM) run test

lint:
	$(PY) -m ruff check backend/app backend/tests
	$(PY) -m ruff format --check backend/app backend/tests
	$(NPM) run lint

typecheck:
	$(NPM) run typecheck

format:
	$(PY) -m ruff format backend/app backend/tests
	$(PY) -m ruff check --fix backend/app backend/tests

build:
	$(NPM) run build

check: lint typecheck test build

clean:
	rm -rf frontend/dist frontend/node_modules/.vite backend/.pytest_cache backend/.ruff_cache
