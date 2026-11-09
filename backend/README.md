# tempr backend

FastAPI service for versioned agent definitions, classification, test generation, execution traces, and LLM-based evaluation. See the [product walkthrough](../README.md) for the complete workflow and screenshots.

## Run locally

Requires Python 3.12 or newer. From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
```

Set `OPENAI_API_KEY` in `backend/.env` to enable classification, test generation, and evaluation. Agent management and saved-data browsing work without a key.

Run migrations and start the API in the same terminal:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. Open [Swagger UI](http://localhost:8000/docs) to explore endpoints and submit requests. `/health` checks that the server responds; `/ready` checks database connectivity. Run migrations again after pulling changes that add them.

Start the [frontend](../frontend/README.md) in a separate terminal to use the workspace. Unless stated otherwise, the commands below run from `backend/` with the virtual environment activated.

## Configuration

The backend loads `backend/.env`; environment variables override values in that file. Restart the API after changing settings.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLAlchemy database URL. |
| `OPENAI_API_KEY` | Unset | Credentials for classification, generation, and judging. |
| `CLASSIFICATION_MODEL` | `gpt-6-luna` | Model used to plan testing allocations. |
| `CLASSIFICATION_TIMEOUT_SECONDS` | `30` | Classification request timeout. |
| `TEST_GENERATION_MODEL` | `CLASSIFICATION_MODEL` | Model used to generate test cases; blank uses the fallback. |
| `TEST_GENERATION_TIMEOUT_SECONDS` | `120` | Test-generation request timeout. |
| `EVALUATION_MODEL` | `CLASSIFICATION_MODEL` | Judge model; blank uses the fallback. |
| `EVALUATION_TIMEOUT_SECONDS` | `120` | Timeout for each case's judge request. |

SQLite needs no separate database server; its data directory is created automatically. The default path is relative to the working directory, so run both migrations and the API from `backend/` to use the same database.

For PostgreSQL, set a URL such as `postgresql+psycopg://user:password@host/database`, install the matching driver (`python -m pip install 'psycopg[binary]'` for this example), and run migrations against that database. The driver is not included in the default dependencies.

These model settings control tempr's analysis services. An agent version's own `schema.model` records the model used by your agent; tempr does not execute that agent or its tools.

## API workflow

All endpoints below use the `/api/v1` prefix. Use Swagger UI's **Try it out** to send the example bodies and inspect responses. Substitute returned IDs for `{agent_id}`, `{version_id}`, and `{test_suite_id}`.

### 1. Register an agent and its first version

Send `POST /api/v1/agents`:

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

Save the response's `id` (agent ID) and `latest_version.id` (version ID). The initial version label defaults to `1.0`; `schema.prompt.system` is required. Optional configuration includes `prompt.developer`, a `model` object with `provider`, `name`, and `parameters`, and tool definitions with `name`, `description`, `input_schema`, `output_schema`, and `metadata`.

Versions are immutable. Create a revision with `POST /api/v1/versions`, using the same schema shape:

```json
{
  "agent_id": "agt_REPLACE_ME",
  "version": "1.1",
  "schema": {
    "prompt": { "system": "You are a support assistant. Ask for missing order details." }
  }
}
```

Version creation accepts a complete configuration, rather than a patch to the previous version. Labels must be unique within the agent. The latest version is the most recently created, regardless of its label.

| Action | Endpoint |
| --- | --- |
| List or inspect agents | `GET /api/v1/agents` or `GET /api/v1/agents/{agent_id}` |
| Rename an agent | `PATCH /api/v1/agents/{agent_id}` with `{"name":"New name"}` |
| Remove an agent from the workspace | `DELETE /api/v1/agents/{agent_id}` |
| List an agent's versions | `GET /api/v1/versions?agent_id={agent_id}` |
| Inspect a version and its classification | `GET /api/v1/versions/{version_id}` |

### 2. Classify the version

Send `POST /api/v1/classifications` with `{"version_id":"agv_REPLACE_ME"}`. Classification analyzes the definition and allocates testing effort across eight categories. Scores total `1.0000` (100%); they describe testing priorities, not measured agent performance.

The result is saved per version and reused. Add `?refresh=true` to replace it. Retrieve a saved result with `GET /api/v1/classifications/{classification_id}`.

### 3. Generate a test suite

Send `POST /api/v1/versions/{version_id}/test-suites/generate` with the optional body `{"total_count":20}`. The count defaults to 20 and accepts 1–100. The version must already be classified.

The response is `202 Accepted` with a suite `id` and job status. Poll `GET /api/v1/versions/{version_id}/test-suites` until `status` is `completed` or `failed`. Completed `items` contain case IDs, categories, questions, and `expected_behavior`. A valid version without a suite returns `null`.

Each version has one current suite. Generating again replaces it immediately, including its trace and evaluation, even if the new generation later fails. A refreshed classification affects the next generated suite; an existing suite retains its allocation snapshot.

### 4. Run cases and upload a trace

Execute the generated cases in your own agent runtime, then send `POST /api/v1/test-suites/{test_suite_id}/trace`. Use the actual case IDs from the completed suite:

```json
{
  "trace": {
    "executions": [
      {
        "test_case_id": "tc_REPLACE_ME",
        "execution": {
          "messages": [
            {"role": "user", "content": "Where is my order?"},
            {"role": "assistant", "content": "Please provide your order ID."}
          ],
          "tool_calls": [],
          "retrieved_information": []
        }
      }
    ]
  }
}
```

Include one entry for every suite case. Each `execution` must be a nonempty JSON object. Include ordered messages, actions, tool results, and retrieved information so the judge can assess the evidence available to the agent. Missing, duplicate, or unknown case IDs are rejected when starting evaluation.

Only one trace can be stored per completed suite. Retrieve it with `GET` on the same URL. To replace it, first `DELETE` that URL, then upload again; deleting a trace also deletes its evaluation.

### 5. Evaluate and review results

Send `POST /api/v1/test-suites/{test_suite_id}/evaluation` with no body. Poll `GET` on the same URL until `completed` or `failed`. Completed `results` include each case's adherence, consistency, and grounding scores (0–1), with an explanation for each dimension. The judge assesses only the supplied configuration, expected behavior, and execution evidence.

Repeated POSTs reuse the existing job or result, including a failed job. Add `?refresh=true` to replace it and run the judge again. The frontend displays scores, explanations, traces, and comparisons between versions once results are available.

## Troubleshooting

- **Missing tables:** activate the backend environment and run `alembic upgrade head` from `backend/`, using the same `DATABASE_URL` as the API.
- **Analysis is not configured:** set a nonempty `OPENAI_API_KEY` and restart the API. For provider failures, check credentials, model access, and the returned error. Background jobs expose failures in their `error` field.
- **Job stays queued or running after a restart:** generation and evaluation run inside the API process, without a durable worker queue. Request generation again to replace an interrupted suite, or POST evaluation with `?refresh=true` to retry judging.
- **Trace or evaluation conflict:** wait for generation to complete, upload a trace before evaluation, and delete the existing trace before uploading a replacement.

## Development checks

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Tests use isolated SQLite databases and mocked model calls, without accessing the configured local database or making live provider requests. To apply lint fixes and formatting:

```bash
python -m ruff check . --fix
python -m ruff format .
```

Test categories are defined in `app/domain/test_categories.py`. Changing the category set also requires updating database migrations, prompts, and the frontend display. See the [repository guide](../README.md#git-hooks) to enable pre-commit checks.
