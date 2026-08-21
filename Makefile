.PHONY: help setup dev test lint format check audit

PYTHON ?= $(shell if [ -f .venv/bin/python ]; then echo .venv/bin/python; else which python3; fi)
PYTEST ?= $(shell if [ -f .venv/bin/pytest ]; then echo .venv/bin/pytest; else which pytest; fi)
RUFF ?= $(shell if [ -f .venv/bin/ruff ]; then echo .venv/bin/ruff; else which ruff; fi)
UVICORN ?= $(shell if [ -f .venv/bin/uvicorn ]; then echo .venv/bin/uvicorn; else which uvicorn; fi)

help:  ## Display this help screen
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup:  ## Install dependencies into virtual environment
	$(PYTHON) -m pip install -e ".[dev]"

dev:  ## Start the FastAPI development server
	$(UVICORN) backend.app.main:app --host 0.0.0.0 --port 8000 --reload

test:  ## Run pytest test suite
	$(PYTEST) -v tests/

audit:  ## Run CV diagnostic audit and generate dated comparison reports
	$(PYTHON) tools/run_audit.py

lint:  ## Run ruff linter checks
	$(RUFF) check backend/ tests/ tools/

format:  ## Format and fix code with ruff
	$(RUFF) format backend/ tests/ tools/
	$(RUFF) check --fix backend/ tests/ tools/

check: lint test  ## Run all linting and test checks
