.PHONY: setup fixtures audit enclosure test build serve demo

setup:
	uv sync --locked
	npm --prefix web ci

fixtures:
	uv run --locked python -m scripts.fixtures
	uv run --locked python -m enclosure.fixtures

enclosure:
	uv run --locked python -m enclosure.demo

audit:
	uv run --locked python -m scripts.audit

test:
	uv run --locked python -m pytest -q
	uv run --locked ruff check engine enclosure api scripts tests

build:
	npm --prefix web run build

serve:
	uv run --locked uvicorn api.main:app --host 127.0.0.1 --port 8000

demo: setup fixtures audit build serve
