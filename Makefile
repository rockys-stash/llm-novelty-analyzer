.PHONY: help setup setup-llm data models generate judge experiments e1 e2 e3 e4 e5 results test test-ui lint format web serve screenshots smoke clean

help: ## List targets
	@grep -E '^[a-z0-9-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

setup: ## Install Python (uv) and console (npm) dependencies
	uv sync --locked
	npm --prefix web ci

setup-llm: ## Also install llama-cpp-python, needed only to regenerate items or judgments
	uv sync --locked --extra llm

data: ## Rebuild the literature corpus from the DOI manifest (Crossref; data/raw/, not committed)
	uv run novelty fetch

models: ## Download the two local language models (about 4.8 GB, models/) and verify their SHA-256
	uv run novelty models

generate: data models ## Write the 204 generated ideas and controls (items/items.jsonl; hours on CPU; resumable)
	OMP_NUM_THREADS=1 uv run novelty generate

judge: models ## Model-judge pilot: both models rate every item (items/judgments.jsonl; resumable)
	OMP_NUM_THREADS=1 uv run novelty judge

experiments: data ## THE one command: E1-E5 on the committed items and judgments, then docs/generated/results.md
	OMP_NUM_THREADS=1 uv run novelty experiment all
	uv run novelty results

e1: data ## E1 indicators and prior-art map for every item
	OMP_NUM_THREADS=1 uv run novelty experiment e1
e2: ## E2 validity against controls of known provenance (reads E1)
	uv run novelty experiment e2
e3: ## E3 indicators against human (pending until collected) and model-judge novelty (reads E1)
	uv run novelty experiment e3
e4: ## E4 agreement between indicators; ideas grouped by control thresholds (reads E1)
	uv run novelty experiment e4
e5: data ## E5 robustness: another embedding model, half the corpus
	OMP_NUM_THREADS=1 uv run novelty experiment e5

results: ## Render docs/generated/results.md from results/*/LATEST
	uv run novelty results

smoke: data ## E1-E5 with small bootstrap counts into results/scratch (checks the pipeline; not a result)
	OMP_NUM_THREADS=1 uv run novelty experiment all --configs configs/smoke --results results/scratch

test: ## Unit, pipeline and API tests
	uv run pytest

test-ui: web ## Browser, keyboard and axe accessibility tests (needs Chromium and results/)
	uv run pytest -m ui

lint: ## Ruff, mypy, ESLint and TypeScript checks
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src tests scripts
	npm --prefix web run lint
	npm --prefix web run typecheck

format: ## Auto-format Python
	uv run ruff format .
	uv run ruff check --fix .

web: ## Build the console into web/dist
	npm --prefix web run build

serve: web ## Serve the console and API on http://127.0.0.1:8000 (reads .env if present)
	set -a; [ -f .env ] && . ./.env; set +a; uv run novelty serve

screenshots: web ## Capture docs/screenshots from the running console (needs results/)
	uv run python scripts/screenshots.py

clean: ## Remove build output, caches and smoke runs (keeps data/, items/ and results/)
	rm -rf web/dist results/scratch .pytest_cache .mypy_cache .ruff_cache
