import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import get_db
from app.db.models import Agent, AgentVersion, Base, Classification
from app.config import Settings
from app.main import app
from app.services.classification import (
    ClassificationService,
    ClassificationServiceError,
)


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def minimal_agent() -> dict:
    return {"name": "Refund Agent", "initial_version": {"schema": {"prompt": {"system": "Handle refunds."}}}}


def create_agent(client) -> dict:
    response = client.post("/api/v1/agents", json=minimal_agent())
    assert response.status_code == 201
    return response.json()


def test_create_agent_creates_default_initial_version(client):
    body = create_agent(client)
    assert body["id"].startswith("agt_")
    assert body["latest_version"]["id"].startswith("agv_")
    assert body["latest_version"]["version"] == "1.0"
    assert body["latest_version"]["schema"]["prompt"] == {"system": "Handle refunds.", "developer": None}
    assert body["latest_version"]["classification"] is None


def test_create_full_agent_schema_and_custom_version(client):
    payload = minimal_agent() | {"initial_version": {
        "version": " beta-3 ",
        "schema": {
            "description": "Handles refunds.",
            "prompt": {"system": "Help customers.", "developer": "Be concise."},
            "model": {"provider": "openai", "name": "gpt-5", "parameters": {"temperature": 0.1}},
            "tools": [{"name": "get_order", "input_schema": {"type": "object"}}],
            "metadata": {"team": "support"},
        },
    }}
    response = client.post("/api/v1/agents", json=payload)
    assert response.status_code == 201
    version = response.json()["latest_version"]
    assert version["version"] == "beta-3"
    assert version["schema"]["model"]["parameters"] == {"temperature": 0.1}
    assert version["schema"]["tools"][0]["metadata"] == {}
    assert version["schema"]["metadata"] == {"team": "support"}


@pytest.mark.parametrize("payload", [
    {"name": "Missing version"},
    {"name": "Missing schema", "initial_version": {"schema": {}}},
    {"name": "Legacy flat schema", "prompt": {"system": "hello"}},
])
def test_reject_missing_or_legacy_initial_version(client, payload):
    assert client.post("/api/v1/agents", json=payload).status_code == 422


def test_version_endpoints_and_duplicate_labels(client):
    created = create_agent(client)
    agent_id = created["id"]
    payload = {"version": "2.0", "schema": {"prompt": {"system": "New prompt."}}}
    response = client.post(f"/api/v1/agents/{agent_id}/versions", json=payload)
    assert response.status_code == 201
    new_version = response.json()
    assert new_version["schema"]["prompt"]["system"] == "New prompt."
    assert client.post(f"/api/v1/agents/{agent_id}/versions", json=payload).status_code == 409
    assert client.get(f"/api/v1/agents/{agent_id}").json()["latest_version"]["id"] == new_version["id"]
    versions = client.get(f"/api/v1/agents/{agent_id}/versions").json()
    assert versions["total"] == 2
    assert versions["items"][0]["id"] == new_version["id"]
    assert client.get(f"/api/v1/agents/{agent_id}/versions/{new_version['id']}").status_code == 200


def test_agent_name_is_editable_but_version_schema_is_not(client):
    created = create_agent(client)
    updated = client.patch(f"/api/v1/agents/{created['id']}", json={"name": "Returns Agent"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Returns Agent"
    assert client.patch(f"/api/v1/agents/{created['id']}", json={"prompt": {"system": "changed"}}).status_code == 422
    assert client.patch(f"/api/v1/agents/{created['id']}", json={}).status_code == 422


class FakeClassificationService:
    class Settings:
        classification_model = "test-model"

    settings = Settings()

    def __init__(self):
        self.calls = 0
        self.fail = False

    def classify(self, version):
        self.calls += 1
        if self.fail:
            raise ClassificationServiceError(503, "provider down")
        return {
            "happy_path": 0.3, "boundary_probe": 0.2, "missing_information": 0.1,
            "ambiguous_input": 0.1, "prompt_injection": 0.1, "policy_bypass": 0.1,
            "sensitive_data_request": 0.05, "hallucination_probe": 0.05,
        }


@pytest.fixture
def fake_classification():
    fake = FakeClassificationService()

    def service(db=Depends(get_db)):
        instance = ClassificationService(db)
        instance.settings = Settings(
            classification_model="test-model", openai_api_key="test-key"
        )
        instance._call_model = fake.classify
        return instance

    app.dependency_overrides[ClassificationService] = service
    yield fake
    app.dependency_overrides.pop(ClassificationService, None)


def test_classification_persists_reuses_and_refreshes(client, fake_classification):
    created = create_agent(client)
    agent_id = created["id"]
    version_id = created["latest_version"]["id"]
    path = f"/api/v1/agents/{agent_id}/versions/{version_id}"
    first = client.post(f"{path}/classify")
    assert first.status_code == 200
    assert first.json()["classifier_model"] == "test-model"
    assert sum(first.json()["scores"].values()) == 1
    classification_id = first.json()["id"]
    assert client.get(f"{path}/classification").json()["id"] == classification_id
    assert client.post(f"{path}/classify").json()["id"] == classification_id
    assert fake_classification.calls == 1
    refreshed = client.post(f"{path}/classify?refresh=true")
    assert refreshed.status_code == 200
    assert refreshed.json()["id"] == classification_id
    assert fake_classification.calls == 2


def test_failed_refresh_preserves_saved_classification(client, fake_classification):
    created = create_agent(client)
    path = f"/api/v1/agents/{created['id']}/versions/{created['latest_version']['id']}"
    saved = client.post(f"{path}/classify").json()
    fake_classification.fail = True
    assert client.post(f"{path}/classify?refresh=true").status_code == 503
    assert client.get(f"{path}/classification").json() == saved


def test_nested_routes_reject_deleted_agent(client):
    created = create_agent(client)
    agent_id, version_id = created["id"], created["latest_version"]["id"]
    assert client.delete(f"/api/v1/agents/{agent_id}").status_code == 204
    for path in (
        f"/api/v1/agents/{agent_id}/versions",
        f"/api/v1/agents/{agent_id}/versions/{version_id}",
        f"/api/v1/agents/{agent_id}/versions/{version_id}/classification",
    ):
        assert client.get(path).status_code == 404
    assert client.post(f"/api/v1/agents/{agent_id}/versions/{version_id}/classify").status_code == 404


def test_foreign_keys_enabled_and_list_envelope(client):
    body = create_agent(client)
    listed = client.get("/api/v1/agents").json()
    assert listed["total"] == 1
    assert listed["items"][0]["latest_version"]["id"] == body["latest_version"]["id"]
    assert client.get("/api/v1/agents/agt_missing").status_code == 404


def test_database_enforces_foreign_keys_and_one_to_one_classification():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    scores = {
        "happy_path": 0.3, "boundary_probe": 0.2, "missing_information": 0.1,
        "ambiguous_input": 0.1, "prompt_injection": 0.1, "policy_bypass": 0.1,
        "sensitive_data_request": 0.05, "hallucination_probe": 0.05,
    }
    with Session() as db:
        with pytest.raises(IntegrityError):
            db.add(AgentVersion(
                id="agv_orphan", agent_id="agt_missing", version="1.0",
                system_prompt="prompt", tools=[], metadata_json={},
            ))
            db.commit()
        db.rollback()
        agent = Agent(id="agt_parent", name="Parent")
        classification = Classification(id="cls_shared", classifier_model="test", **scores)
        agent.versions.extend([
            AgentVersion(id="agv_one", version="1.0", system_prompt="one", tools=[], metadata_json={}, classification=classification),
            AgentVersion(id="agv_two", version="2.0", system_prompt="two", tools=[], metadata_json={}, classification_id="cls_shared"),
        ])
        db.add(agent)
        with pytest.raises(IntegrityError):
            db.commit()
    engine.dispose()
