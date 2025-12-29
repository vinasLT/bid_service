# Repository Guidelines

## Project Structure & Module Organization
- `app/` holds the FastAPI service. Key areas: `routers/` (HTTP endpoints), `database/` (SQLAlchemy models, CRUD, sessions, Alembic), `schemas/` (Pydantic DTOs), `services/` (infra like RabbitMQ), and `rpc_client/` (gRPC integrations). `app/main.py` wires the app.
- `alembic/` and `alembic.ini` manage migrations.
- `tests/` mirrors router layout (e.g., `tests/routers/v1/bid/`). Add sibling test modules when adding endpoints.

## Build, Test, and Development Commands
- `poetry install` sets up the Python 3.13 environment and dev deps.
- `uvicorn app.main:app --reload` runs the API locally with auto-reload.
- `pytest` or `pytest tests/routers/v1/bid -k <pattern>` runs async test suites.
- `alembic upgrade head` applies the latest database migrations (requires `DATABASE_URL`).

## Coding Style & Naming Conventions
- Follow PEP 8, 4-space indentation, and type-annotated function signatures.
- Use snake_case for modules/functions/variables, PascalCase for Pydantic models and Enums.
- Prefer dependency injection via `Depends(...)` inside routers; avoid instantiating services at import time.
- Keep helper functions above route handlers; reuse shared helpers in `app/core/` or module utility blocks.

## Testing Guidelines
- Tests use `pytest` with `pytest-asyncio` (strict async). Name files `test_<feature>.py` and coroutines `test_<behavior>`.
- Use stubs in `tests/routers/v1/bid/stubs.py` for BidService/RPC/RabbitMQ mocks; extend them rather than duplicating fixtures.
- Cover success and failure paths (validation guards, RPC errors, edge cases).

## Commit & Pull Request Guidelines
- Commit messages are imperative and descriptive (e.g., "Add bid placement tests"). Keep changes scoped.
- PRs should include: problem statement, summary, test evidence (`pytest ...`), and screenshots/logs for user-facing or ops-visible changes. Link issues and call out breaking changes or new env vars.

## Configuration & Environment
- App configuration lives in `app/config.py`; set required env vars (e.g., `DATABASE_URL`) before running migrations.
- gRPC stubs live under `app/rpc_client/gen/`; do not hand-edit generated files.
