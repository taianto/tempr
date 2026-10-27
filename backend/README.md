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

Test suite generation uses `TEST_GENERATION_MODEL` when set, otherwise it uses `CLASSIFICATION_MODEL`. `TEST_GENERATION_TIMEOUT_SECONDS` defaults to `120`.

## Migrations and startup

Run these commands from `backend/`:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`, Swagger at `http://localhost:8000/docs`, and health checks at `/health` and `/ready`. Agent, version, and classification resources are under `/api/v1/agents`, `/api/v1/versions`, and `/api/v1/classifications`.

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

The initial label defaults to `1.0`. Versions are immutable; add a schema revision with `POST /api/v1/versions` and a `{ "agent_id": "agt_…", "version": "2.0", "schema": { ... } }` body. Version labels are unique per agent. Agent detail includes the latest created version, and historical versions are available from `GET /api/v1/versions?agent_id=agt_…`. Individual versions are available from `GET /api/v1/versions/{version_id}`.

Classify a version with `POST /api/v1/classifications` and a `{ "version_id": "agv_…" }` body. Classification is saved against that immutable version and reused on later requests. Add `?refresh=true` to classify again and replace its saved scores. Retrieve a classification by ID with `GET /api/v1/classifications/{classification_id}`. Scores are normalized to four decimal places and total `1.0000`. The classifier analyzes the version definition; it does not run the agent. Existing agent schemas are migrated to version `1.0`.

Generate or replace a suite for a classified version with `POST /api/v1/versions/{version_id}/test-suites/generate`. Every request starts a new job and replaces that version's current suite. An optional JSON body `{"total_count": 20}` accepts a suite size from 1 to 100. The endpoint returns a suite ID and status; generation runs in a FastAPI background task. Each version has one test suite row, with generated questions and expected behavior stored together. The requested count is allocated according to the saved classification using Hamilton's largest-remainder method. An earlier job may keep running after replacement, but its result cannot overwrite the newer suite. The classifier must have classified the version first. Background tasks run in the API process, so a process interruption can leave a job queued or running.

Retrieve a version's current suite and generation status with `GET /api/v1/versions/{version_id}/test-suites`. A valid version without a suite returns `null`. The frontend test-suite page classifies an unclassified version before requesting generation, then polls until the job completes or fails. Test categories are defined in `app/domain/test_categories.py`; adding or removing a category also requires a database migration and updates to the classification prompt and frontend display.

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
