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

## Migrations and startup

Run these commands from `backend/`:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`, Swagger at `http://localhost:8000/docs`, and health checks at `/health` and `/ready`. Agent CRUD endpoints are under `/api/v1/agents`.

## Tests

```bash
pytest
```

Tests use an isolated in-memory SQLite database and do not access the configured local database.
