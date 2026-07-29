PYTHON := .venv/bin/python
RUFF := .venv/bin/ruff
MYPY := .venv/bin/mypy
PYTEST := .venv/bin/pytest

.PHONY: bootstrap dev build format lint typecheck test e2e run pairing vlc-http

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
	$(MYPY) backend scripts
	npm run typecheck

test:
	$(PYTEST)
	npm run test

e2e:
	npm run test:e2e

run:
	./scripts/run_production.sh

pairing:
	$(PYTHON) scripts/show_pairing_qr.py

vlc-http:
	$(PYTHON) scripts/launch_vlc_http.py
