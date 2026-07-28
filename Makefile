PYTHON := .venv/bin/python
RUFF := .venv/bin/ruff
MYPY := .venv/bin/mypy
PYTEST := .venv/bin/pytest

.PHONY: bootstrap dev build format lint typecheck test run

bootstrap:
	./scripts/bootstrap.sh

dev:
	./scripts/run_dev.sh

build:
	npm run build

format:
	$(RUFF) format backend scripts

lint:
	$(RUFF) format --check backend scripts
	$(RUFF) check backend scripts
	npm run lint

typecheck:
	$(MYPY) backend scripts/check_vlc.py
	npm run typecheck

test:
	$(PYTEST)
	npm run test

run:
	./scripts/run_production.sh
