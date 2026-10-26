from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.db.database import get_db
from app.db.models import Agent, AgentVersion, Base, Classification, TestSuite as SuiteRecord, utc_now
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
        db.add(Agent(
            id="agt_suite", name="Suite agent", versions=[AgentVersion(
                id="agv_suite", version="1.0", system_prompt="Handle refunds.",
                classification=Classification(
                    id="cls_suite", classifier_model="test",
                    **(dict.fromkeys(TEST_CATEGORIES, 0.0) | {"happy_path": 1.0}),
                ),
            )],
        ))
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


GENERATION_PATH = "/api/v1/agents/agt_suite/versions/agv_suite/test-suites/generate"
SUITE_ITEM = {
    "category": "happy_path", "question": "Can I get a refund?",
    "expected_behavior": "Explain the refund process.",
}


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
    messages = provider.return_value.with_structured_output.return_value.invoke.call_args.args[0]
    assert messages[0] == ("system", TEST_SUITE_SYSTEM_PROMPT)
    operation = client.get("/openapi.json").json()["paths"][GENERATION_PATH.replace(
        "agt_suite", "{agent_id}"
    ).replace("agv_suite", "{version_id}")]["post"]
    assert operation["tags"] == ["test suites"]
    assert operation["operationId"].startswith("generate_test_suite_")


@pytest.mark.parametrize("items", [
    [],
    [SUITE_ITEM | {"category": "boundary_probe"}],
    [SUITE_ITEM | {"question": "   "}],
])
def test_invalid_generated_suite_fails_job(suite_environment, items):
    client, sessions, provider = suite_environment
    provider.return_value.with_structured_output.return_value.invoke.return_value = {"items": items}

    response = client.post(GENERATION_PATH, json={"total_count": 1})
    assert response.status_code == 202
    with sessions() as db:
        record = db.get(SuiteRecord, response.json()["id"])
        assert record.status == "failed"
        assert record.result_json is None
        assert record.error == "The generation provider returned an invalid response"


def test_get_suite_returns_null_when_version_has_no_suite(suite_environment):
    client, _, _ = suite_environment

    response = client.get("/api/v1/agents/agt_suite/versions/agv_suite/test-suites")

    assert response.status_code == 200
    assert response.json() is None


def test_get_suite_returns_generated_items_and_status(suite_environment):
    client, sessions, _ = suite_environment
    with sessions() as db:
        db.add(SuiteRecord(
            id="ts_saved", version_id="agv_suite", status="completed",
            request_json={"total_count": 1, "allocation": {"happy_path": 1}},
            result_json={"items": [SUITE_ITEM], "generated_at": "2026-10-20T12:00:00+00:00"},
        ))
        db.commit()

    response = client.get("/api/v1/agents/agt_suite/versions/agv_suite/test-suites")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "ts_saved"
    assert body["status"] == "completed"
    assert body["items"] == [SUITE_ITEM]
    assert body["generated_at"] == "2026-10-20T12:00:00Z"


def test_get_suite_rejects_missing_or_mismatched_version(suite_environment):
    client, _, _ = suite_environment

    missing = client.get("/api/v1/agents/agt_suite/versions/unknown/test-suites")
    mismatched = client.get("/api/v1/agents/missing/versions/agv_suite/test-suites")

    assert missing.status_code == 404
    assert mismatched.status_code == 404


def test_get_suite_rejects_deleted_agent(suite_environment):
    client, sessions, _ = suite_environment
    with sessions() as db:
        db.get(Agent, "agt_suite").deleted_at = utc_now()
        db.commit()

    response = client.get("/api/v1/agents/agt_suite/versions/agv_suite/test-suites")

    assert response.status_code == 404
