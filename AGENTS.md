# Repository Guidelines

## Project Structure & Module Organization
Core application code lives in `app/`. `app/api/routes` exposes FastAPI endpoints, `app/services` holds RAG workflow components (PDF processing, vectorstore, summarizer, Redis adapters), `app/core` stores settings and dependency wires, `app/db` manages async SQLAlchemy + migrations, and `app/utils` contains shared helpers. Data schemas reside in `app/models`. Use `content/` for ingestible sample documents and `docs/` for published guides. Automated checks live in `tests/unit_tests` for pure logic and `tests/integration_tests` for API and pipeline coverage.

## Build, Test, and Development Commands
Set up dependencies with `pip install -r requirements.txt`. Load a local environment via `cp .env.example .env` and populate API keys before bootstrapping services (Redis, Pinecone). Run the app in development with `uvicorn app.main:app --reload`. Execute the full test suite with `pytest`, or scope to faster checks using `pytest tests/unit_tests -q`. Generate coverage locally with `pytest --cov=app --cov-report=term-missing`. Use `scripts/create_admin.py` for seeding admin users after configuring the database URL.

## Coding Style & Naming Conventions
Target Python 3.10+, four-space indentation, and PEP 8 line widths (aim for ≤100 characters). Keep modules focused; favor dependency-injected services rather than global state. Classes (including Pydantic models) use `PascalCase`, functions and variables use `snake_case`, and API routes remain grouped by version under `app/api/routes/v1_*.py`. Type hints are expected across public interfaces. Run `pytest --maxfail=1` before pushing to catch regressions quickly.

## Testing Guidelines
Prefer deterministic unit tests that mock external APIs; integration tests may touch Redis or Pinecone but should be guarded with fixtures. Name new test files `test_<module>.py` and mirror the app package layout. Maintain coverage for critical services (vector store operations, summarization, authentication). When adding async code, mark tests with `@pytest.mark.asyncio`.

## Commit & Pull Request Guidelines
Follow the existing Conventional Commit style (`feat`, `fix`, `refactor`, `test`, `docs` prefixes). Keep subject lines imperative and under 72 characters. Each PR should summarize functional impact, list test evidence (`pytest`, `pytest --cov`), reference related issues, and attach screenshots or sample payloads when API responses change. Ensure secrets never appear in commits; rely on `.env.local` for local overrides.

## Environment & Security Notes
Review `.env.example` for required credentials (OpenAI, Pinecone, Redis). Do not commit `.env` files or downloaded confidential PDFs—store operational backups in `backup/` and sanitize before sharing. When deploying, align with the instructions in `DEPLOYMENT.md` and confirm Cloudflare R2 buckets are scoped to least privilege.
