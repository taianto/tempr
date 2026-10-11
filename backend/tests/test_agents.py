import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import get_db
from app.db.models import Base
from app.main import app


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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
    return {"name": "Refund Agent", "prompt": {"system": "Handle refunds."}}


def test_create_minimal_agent(client):
    response = client.post("/api/v1/agents", json=minimal_agent())
    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("agt_")
    assert body["tools"] == []
    assert body["metadata"] == {}
    assert body["model"] is None
    assert body["prompt"] == {"system": "Handle refunds.", "developer": None}


def test_create_full_agent(client):
    payload = minimal_agent() | {
        "description": "Handles customer refund requests.",
        "prompt": {"system": "Help customers.", "developer": "Be concise."},
        "model": {"provider": "openai", "name": "gpt-5", "parameters": {"temperature": 0.1}},
        "tools": [{"name": "get_order", "input_schema": {"type": "object"}}],
        "metadata": {"team": "support"},
    }
    response = client.post("/api/v1/agents", json=payload)
    assert response.status_code == 201
    assert response.json()["model"]["parameters"] == {"temperature": 0.1}
    assert response.json()["tools"][0]["metadata"] == {}
    assert response.json()["metadata"] == {"team": "support"}


@pytest.mark.parametrize("payload", [{"prompt": {"system": "hello"}}, {"name": "Missing prompt"}])
def test_reject_missing_required_fields(client, payload):
    assert client.post("/api/v1/agents", json=payload).status_code == 422


def test_list_agents(client):
    client.post("/api/v1/agents", json=minimal_agent())
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert "prompt" not in response.json()["items"][0]


def test_get_agent_and_missing_agent(client):
    created = client.post("/api/v1/agents", json=minimal_agent()).json()
    assert client.get(f"/api/v1/agents/{created['id']}").json()["name"] == "Refund Agent"
    assert client.get("/api/v1/agents/agt_missing").status_code == 404


def test_update_name_prompt_and_tools(client):
    created = client.post("/api/v1/agents", json=minimal_agent()).json()
    agent_id = created["id"]
    updated = client.patch(f"/api/v1/agents/{agent_id}", json={"name": "Returns Agent"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Returns Agent"
    updated = client.patch(f"/api/v1/agents/{agent_id}", json={"prompt": {"system": "New prompt."}})
    assert updated.json()["prompt"]["system"] == "New prompt."
    updated = client.patch(f"/api/v1/agents/{agent_id}", json={"tools": [{"name": "lookup"}]})
    assert [tool["name"] for tool in updated.json()["tools"]] == ["lookup"]


def test_delete_soft_deletes_agent(client):
    created = client.post("/api/v1/agents", json=minimal_agent()).json()
    agent_id = created["id"]
    assert client.delete(f"/api/v1/agents/{agent_id}").status_code == 204
    assert client.get("/api/v1/agents").json() == {"items": [], "total": 0}
    assert client.get(f"/api/v1/agents/{agent_id}").status_code == 404


def test_health_and_readiness(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ok"}
