# Backend

FastAPI service for creating and managing agent definitions.

## Requirements and installation

Python 3.12 or newer is required. From this directory, create and activate a virtual environment, then install the project and development dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Configuration

`DATABASE_URL` selects the SQLAlchemy database URL. It defaults to `sqlite:///./data/app.db`; a PostgreSQL URL such as `postgresql+psycopg://user:password@host/database` can be used when the corresponding driver is installed.

Copy `.env.example` to `.env` in `backend/` and set `OPENAI_API_KEY` to enable classification. The backend loads this file regardless of the directory used to start the server. `CLASSIFICATION_MODEL` defaults to `gpt-6-luna`, and `CLASSIFICATION_TIMEOUT_SECONDS` defaults to `30`.

## Migrations and startup

Run these commands from `backend/`:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`, Swagger at `http://localhost:8000/docs`, and health checks at `/health` and `/ready`. Agent and version endpoints are under `/api/v1/agents`.

Create an agent with its required initial version and schema:

```json
{
  "name": "Support agent",
  "initial_version": {
    "version": "1.0",
    "schema": {
      "description": "Handles customer support requests.",
      "prompt": { "system": "You are a helpful support assistant." },
      "model": null,
      "tools": [],
      "metadata": {}
    }
  }
}
```

The initial label defaults to `1.0`. Versions are immutable; add a schema revision with `POST /api/v1/agents/{agent_id}/versions` and a `{ "version": "2.0", "schema": { ... } }` body. Version labels are unique per agent. Agent detail includes the latest created version, and historical versions are available from `GET /api/v1/agents/{agent_id}/versions`.

Classify or retrieve a specific version with `POST /api/v1/agents/{agent_id}/versions/{version_id}/classify` and `GET /api/v1/agents/{agent_id}/versions/{version_id}/classification`. Classification is saved against that immutable version and reused on later requests. Add `?refresh=true` to classify again and replace its saved scores. Scores are normalized to four decimal places and total `1.0000`. The classifier analyzes the version definition; it does not run the agent. Existing agent schemas are migrated to version `1.0`.

## Development checks

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Install the development dependencies, including Ruff, with `pip install -e '.[dev]'`.
Apply safe lint fixes and formatting with:

```bash
python -m ruff check . --fix
python -m ruff format .
```

Tests use isolated SQLite databases and mocked model calls; they do not access the configured local database or call the classification provider.
