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

Generate or replace a suite for a classified version with `POST /api/v1/agents/{agent_id}/versions/{version_id}/test-suites/generate`. Every request starts a new job and replaces the version's current suite. An optional JSON body `{"total_count": 20}` accepts a suite item count from 1 to 100. The endpoint returns a suite ID and status; the single LLM call runs in FastAPI's in-process background task. Each version has one row in `test_suites`, with the generated questions and expected behavior stored together under `result_json.items`. Hamilton's largest-remainder method allocates the requested count using the saved classification. If an earlier job is already running, its LLM call may continue, but its result cannot overwrite the new suite. Classify the version first. Since FastAPI background tasks run in the API process, process interruption can leave a job queued or running; durable recovery is not included.

Retrieve a version's current suite and generation status with `GET /api/v1/agents/{agent_id}/versions/{version_id}/test-suites`. A valid version without a suite returns `null`; a saved suite includes its status, generated items, and generation timestamp when complete. The frontend's per-version test suite page classifies an unclassified version before requesting generation, then polls until the job completes or fails.

## Tests

Supported test categories are defined in `app/domain/test_categories.py`. The classification validation fields and database score columns are derived from that list. Adding or removing a category also requires an Alembic migration for the stored columns, and updates to the classifier prompt and frontend category display. Keep historical migrations unchanged.

```bash
pytest
```

Tests use an isolated in-memory SQLite database and do not access the configured local database.
