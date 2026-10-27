import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Agent, AgentVersion, Base, Classification


def test_create_agent_creates_default_initial_version(client, agent_factory):
    body = agent_factory()
    assert body["id"].startswith("agt_")
    assert body["latest_version"]["id"].startswith("agv_")
    assert body["latest_version"]["version"] == "1.0"
    assert body["latest_version"]["schema"]["prompt"] == {
        "system": "Handle refunds.",
        "developer": None,
    }
    assert body["latest_version"]["classification"] is None


def test_create_full_agent_schema_and_custom_version(client, minimal_agent):
    payload = minimal_agent | {
        "initial_version": {
            "version": " beta-3 ",
            "schema": {
                "description": "Handles refunds.",
                "prompt": {"system": "Help customers.", "developer": "Be concise."},
                "model": {
                    "provider": "openai",
                    "name": "gpt-5",
                    "parameters": {"temperature": 0.1},
                },
                "tools": [{"name": "get_order", "input_schema": {"type": "object"}}],
                "metadata": {"team": "support"},
            },
        }
    }
    response = client.post("/api/v1/agents", json=payload)
    assert response.status_code == 201
    version = response.json()["latest_version"]
    assert version["version"] == "beta-3"
    assert version["schema"]["model"]["parameters"] == {"temperature": 0.1}
    assert version["schema"]["tools"][0]["metadata"] == {}
    assert version["schema"]["metadata"] == {"team": "support"}


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Missing version"},
        {"name": "Missing schema", "initial_version": {"schema": {}}},
        {"name": "Legacy flat schema", "prompt": {"system": "hello"}},
    ],
)
def test_reject_missing_or_legacy_initial_version(client, payload):
    assert client.post("/api/v1/agents", json=payload).status_code == 422


def test_agent_name_is_editable_but_version_schema_is_not(client, agent_factory):
    created = agent_factory()
    updated = client.patch(
        f"/api/v1/agents/{created['id']}", json={"name": "Returns Agent"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Returns Agent"
    assert (
        client.patch(
            f"/api/v1/agents/{created['id']}", json={"prompt": {"system": "changed"}}
        ).status_code
        == 422
    )
    assert client.patch(f"/api/v1/agents/{created['id']}", json={}).status_code == 422


def test_foreign_keys_enabled_and_list_envelope(client, agent_factory):
    body = agent_factory()
    listed = client.get("/api/v1/agents").json()
    assert listed["total"] == 1
    assert listed["items"][0]["latest_version"]["id"] == body["latest_version"]["id"]
    assert client.get("/api/v1/agents/agt_missing").status_code == 404


def test_database_enforces_foreign_keys_and_one_to_one_classification():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    scores = {
        "happy_path": 0.3,
        "boundary_probe": 0.2,
        "missing_information": 0.1,
        "ambiguous_input": 0.1,
        "prompt_injection": 0.1,
        "policy_bypass": 0.1,
        "sensitive_data_request": 0.05,
        "hallucination_probe": 0.05,
    }
    with Session() as db:
        with pytest.raises(IntegrityError):
            db.add(
                AgentVersion(
                    id="agv_orphan",
                    agent_id="agt_missing",
                    version="1.0",
                    system_prompt="prompt",
                    tools=[],
                    metadata_json={},
                )
            )
            db.commit()
        db.rollback()
        agent = Agent(id="agt_parent", name="Parent")
        classification = Classification(
            id="cls_shared", classifier_model="test", **scores
        )
        agent.versions.extend(
            [
                AgentVersion(
                    id="agv_one",
                    version="1.0",
                    system_prompt="one",
                    tools=[],
                    metadata_json={},
                    classification=classification,
                ),
                AgentVersion(
                    id="agv_two",
                    version="2.0",
                    system_prompt="two",
                    tools=[],
                    metadata_json={},
                    classification_id="cls_shared",
                ),
            ]
        )
        db.add(agent)
        with pytest.raises(IntegrityError):
            db.commit()
    engine.dispose()
