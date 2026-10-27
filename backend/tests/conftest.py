from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.database import get_db
from app.db.models import Base
from app.main import app
from app.services.classification import (
    ClassificationService,
    ClassificationServiceError,
)


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

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


def minimal_agent_payload() -> dict:
    return {
        "name": "Refund Agent",
        "initial_version": {"schema": {"prompt": {"system": "Handle refunds."}}},
    }


@pytest.fixture
def minimal_agent() -> dict:
    return minimal_agent_payload()


@pytest.fixture
def agent_factory(client):
    def create_agent() -> dict:
        response = client.post("/api/v1/agents", json=minimal_agent_payload())
        assert response.status_code == 201
        return response.json()

    return create_agent


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
            "happy_path": 0.3,
            "boundary_probe": 0.2,
            "missing_information": 0.1,
            "ambiguous_input": 0.1,
            "prompt_injection": 0.1,
            "policy_bypass": 0.1,
            "sensitive_data_request": 0.05,
            "hallucination_probe": 0.05,
        }


@pytest.fixture
def fake_classification():
    fake = FakeClassificationService()

    def service(db: Annotated[Session, Depends(get_db)]) -> ClassificationService:
        instance = ClassificationService(db)
        instance.settings = Settings(
            classification_model="test-model", openai_api_key="test-key"
        )
        instance._call_model = fake.classify
        return instance

    app.dependency_overrides[ClassificationService] = service
    yield fake
    app.dependency_overrides.pop(ClassificationService, None)
