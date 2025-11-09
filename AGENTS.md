# Repository Guidelines

## Project Structure & Module Organization
- `app/` contains the FastAPI service: `routers/` (HTTP endpoints), `database/` (SQLAlchemy models, sessions, Alembic migrations), `schemas/` (Pydantic DTOs), `services/` (infrastructure such as RabbitMQ), and `rpc_client/` (gRPC integrations). `app/main.py` wires the FastAPI application.
- `alembic/` plus `alembic.ini` hold migration scripts and configuration.
- `tests/` mirrors the router layout (`tests/routers/v1/...`). When adding new endpoints, create sibling test modules to keep scopes focused.
- Shared enums, utilities, and configuration live in `app/core/` and `app/config.py`. Reuse them rather than redefining constants in feature modules.

## Build, Test, and Development Commands
- `poetry install` – sets up the Python 3.13 environment with runtime and dev dependencies.
- `uvicorn app.main:app --reload` – runs the FastAPI server locally with auto-reload for rapid development.
- `pytest` or `pytest tests/routers/v1/bid` – executes the async pytest suite (strict asyncio mode). Use `-k` to target specific endpoints.
- `alembic upgrade head` – applies the latest DB migrations (ensure `DATABASE_URL` is configured).

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation, typed function signatures, and snake_case for modules, functions, and variables. Use PascalCase for Pydantic models and Enums.
- Prefer dependency injection via `Depends(...)` inside routers; avoid instantiating services at import time.
- Keep FastAPI routers in `app/routers/<version>/<resource>.py`, with helper functions defined above their route handlers.
- Reuse shared helpers (e.g., `_build_bid_payload`) or move new ones into the nearest module-level utility block to keep routers concise.

## Testing Guidelines
- Pytest with `pytest-asyncio` powers all tests. Name files `test_<feature>.py`; name coroutines `test_<behavior>`.
- Use the stubs in `tests/routers/v1/bid/stubs.py` when mocking BidService, RPC clients, or RabbitMQ—extend this module instead of redefining fixtures.
- Always validate both success paths and failure cases (e.g., RPC errors, validation guards) before opening a PR. CI expects `pytest` to pass without `-s`.

## Commit & Pull Request Guidelines
- Write imperative, descriptive commits (e.g., `Add bid placement tests`) and keep changes scoped.
- Pull requests should include: problem statement, summary of changes, screenshots/logs for user-facing or ops-visible updates, and explicit test evidence (`pytest ...` output).
- Link to tracking tickets or issues when available, and call out breaking changes or new environment variables in the PR description.
