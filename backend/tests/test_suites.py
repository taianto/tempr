from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.db.database import get_db
from app.db.models import (
    Agent,
    AgentVersion,
    Base,
    Classification,
    utc_now,
)
from app.db.models import (
    TestSuite as SuiteRecord,
)
from app.db.models import TestSuiteTrace as TraceRecord
from app.domain.test_categories import TEST_CATEGORIES
from app.main import app
from app.prompts.test_suites import TEST_SUITE_SYSTEM_PROMPT
from app.schemas.test_suite import GeneratedTestSuite
from app.services import test_suite_generator, test_suite_worker


@pytest.fixture
def suite_environment(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with sessions() as db:
        db.add(
            Agent(
                id="agt_suite",
                name="Suite agent",
                versions=[
                    AgentVersion(
                        id="agv_suite",
                        version="1.0",
                        system_prompt="Handle refunds.",
                        classification=Classification(
                            id="cls_suite",
                            classifier_model="test",
                            **(
                                dict.fromkeys(TEST_CATEGORIES, 0.0)
                                | {"happy_path": 1.0}
                            ),
                        ),
                    )
                ],
            )
        )
        db.commit()

    def override_get_db():
        with sessions() as db:
            yield db

    settings = Settings(_env_file=None, openai_api_key="test-key")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(test_suite_worker, "SessionLocal", sessions)
    monkeypatch.setattr(test_suite_worker, "get_settings", lambda: settings)
    provider = Mock()
    monkeypatch.setattr(test_suite_generator, "ChatOpenAI", provider)
    try:
        with TestClient(app) as client:
            yield client, sessions, provider
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


GENERATION_PATH = "/api/v1/versions/agv_suite/test-suites/generate"
SUITE_ITEM = {
    "category": "happy_path",
    "question": "Can I get a refund?",
    "expected_behavior": "Explain the refund process.",
}
TRACE_PATH = "/api/v1/test-suites/ts_completed/trace"


def _save_completed_suite(sessions, suite_id="ts_completed"):
    with sessions() as db:
        db.add(
            SuiteRecord(
                id=suite_id,
                version_id="agv_suite",
                status="completed",
                request_json={"total_count": 1, "allocation": {"happy_path": 1}},
                result_json={"items": [SUITE_ITEM]},
            )
        )
        db.commit()


@pytest.mark.parametrize("structured", [False, True])
def test_generate_suite_persists_items(suite_environment, structured):
    client, sessions, provider = suite_environment
    result = {"items": [SUITE_ITEM]}
    provider.return_value.with_structured_output.return_value.invoke.return_value = (
        GeneratedTestSuite(**result) if structured else result
    )

    response = client.post(GENERATION_PATH, json={"total_count": 1})
    assert response.status_code == 202
    body = response.json()
    assert body["id"].startswith("ts_")
    assert body["requested_count"] == 1
    assert body["allocation"]["happy_path"] == 1
    with sessions() as db:
        record = db.get(SuiteRecord, body["id"])
        assert record.status == "completed"
        assert record.result_json["items"] == [SUITE_ITEM]
        assert record.error is None
    provider.return_value.with_structured_output.assert_called_once_with(
        GeneratedTestSuite, method="json_schema", strict=True
    )
    messages = (
        provider.return_value.with_structured_output.return_value.invoke.call_args.args[
            0
        ]
    )
    assert messages[0] == ("system", TEST_SUITE_SYSTEM_PROMPT)
    operation = client.get("/openapi.json").json()["paths"][
        GENERATION_PATH.replace("agv_suite", "{version_id}")
    ]["post"]
    assert operation["tags"] == ["test suites"]
    assert operation["operationId"].startswith("generate_test_suite_")


@pytest.mark.parametrize(
    "items",
    [
        [],
        [SUITE_ITEM | {"category": "boundary_probe"}],
        [SUITE_ITEM | {"question": "   "}],
    ],
)
def test_invalid_generated_suite_fails_job(suite_environment, items):
    client, sessions, provider = suite_environment
    provider.return_value.with_structured_output.return_value.invoke.return_value = {
        "items": items
    }

    response = client.post(GENERATION_PATH, json={"total_count": 1})
    assert response.status_code == 202
    with sessions() as db:
        record = db.get(SuiteRecord, response.json()["id"])
        assert record.status == "failed"
        assert record.result_json is None
        assert record.error == "The generation provider returned an invalid response"


def test_get_suite_returns_null_when_version_has_no_suite(suite_environment):
    client, _, _ = suite_environment

    response = client.get("/api/v1/versions/agv_suite/test-suites")

    assert response.status_code == 200
    assert response.json() is None


def test_get_suite_returns_generated_items_and_status(suite_environment):
    client, sessions, _ = suite_environment
    with sessions() as db:
        db.add(
            SuiteRecord(
                id="ts_saved",
                version_id="agv_suite",
                status="completed",
                request_json={"total_count": 1, "allocation": {"happy_path": 1}},
                result_json={
                    "items": [SUITE_ITEM],
                    "generated_at": "2026-10-20T12:00:00+00:00",
                },
            )
        )
        db.commit()

    response = client.get("/api/v1/versions/agv_suite/test-suites")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "ts_saved"
    assert body["status"] == "completed"
    assert body["items"] == [SUITE_ITEM]
    assert body["generated_at"] == "2026-10-20T12:00:00Z"


def test_get_suite_rejects_missing_or_mismatched_version(suite_environment):
    client, _, _ = suite_environment

    missing = client.get("/api/v1/versions/unknown/test-suites")
    assert missing.status_code == 404


def test_get_suite_rejects_deleted_agent(suite_environment):
    client, sessions, _ = suite_environment
    with sessions() as db:
        db.get(Agent, "agt_suite").deleted_at = utc_now()
        db.commit()

    response = client.get("/api/v1/versions/agv_suite/test-suites")

    assert response.status_code == 404


def test_create_get_delete_and_recreate_trace(suite_environment):
    client, sessions, _ = suite_environment
    _save_completed_suite(sessions)
    trace = {"steps": [{"input": "Can I get a refund?", "output": "Yes."}]}

    created = client.post(TRACE_PATH, json={"trace": trace})

    assert created.status_code == 201
    body = created.json()
    assert body["id"].startswith("trc_")
    assert body["test_suite_id"] == "ts_completed"
    assert body["trace"] == trace
    assert body["created_at"]
    assert created.headers["location"] == TRACE_PATH
    assert client.get(TRACE_PATH).json() == body
    with sessions() as db:
        record = db.get(TraceRecord, body["id"])
        assert record.trace_json == trace

    deleted = client.delete(TRACE_PATH)
    assert deleted.status_code == 204
    assert client.get(TRACE_PATH).status_code == 404

    recreated = client.post(TRACE_PATH, json={"trace": ["raw", 3, True, None]})
    assert recreated.status_code == 201
    assert recreated.json()["trace"] == ["raw", 3, True, None]


def test_create_trace_rejects_duplicate_and_invalid_body(suite_environment):
    client, sessions, _ = suite_environment
    _save_completed_suite(sessions)

    assert client.post(TRACE_PATH, json={"trace": {"ok": True}}).status_code == 201
    duplicate = client.post(TRACE_PATH, json={"trace": {"ok": False}})
    missing_payload = client.post(TRACE_PATH, json={})
    extra_payload = client.post(TRACE_PATH, json={"trace": {}, "other": "no"})

    assert duplicate.status_code == 409
    assert missing_payload.status_code == 422
    assert extra_payload.status_code == 422


def test_create_trace_requires_completed_available_suite(suite_environment):
    client, sessions, _ = suite_environment
    queued_path = "/api/v1/test-suites/ts_queued/trace"
    with sessions() as db:
        db.add(
            SuiteRecord(
                id="ts_queued",
                version_id="agv_suite",
                status="queued",
                request_json={"total_count": 1, "allocation": {"happy_path": 1}},
            )
        )
        db.commit()

    assert client.post(queued_path, json={"trace": {}}).status_code == 409
    assert client.post(TRACE_PATH, json={"trace": {}}).status_code == 404
    assert client.get(TRACE_PATH).status_code == 404
    assert client.delete(TRACE_PATH).status_code == 404

    with sessions() as db:
        db.delete(db.get(SuiteRecord, "ts_queued"))
        db.commit()
    _save_completed_suite(sessions)
    with sessions() as db:
        db.get(Agent, "agt_suite").deleted_at = utc_now()
        db.commit()
    assert client.post(TRACE_PATH, json={"trace": {}}).status_code == 404


def test_regenerating_suite_cascades_trace_deletion(suite_environment):
    client, sessions, provider = suite_environment
    _save_completed_suite(sessions)
    provider.return_value.with_structured_output.return_value.invoke.return_value = {
        "items": [SUITE_ITEM]
    }
    created = client.post(TRACE_PATH, json={"trace": {"steps": []}})
    assert created.status_code == 201

    generated = client.post(GENERATION_PATH, json={"total_count": 1})

    assert generated.status_code == 202
    assert client.get(TRACE_PATH).status_code == 404
    with sessions() as db:
        assert db.get(TraceRecord, created.json()["id"]) is None
