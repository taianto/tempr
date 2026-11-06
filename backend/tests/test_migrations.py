import json

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from app.config import get_settings


def _config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_migrations_match_current_models(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'schema.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    try:
        config = _config(url)
        command.upgrade(config, "head")
        command.check(config)
    finally:
        get_settings.cache_clear()


def test_trace_migration_adds_unique_cascading_suite_foreign_key(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'trace-schema.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    try:
        command.upgrade(_config(url), "head")
        engine = sa.create_engine(url)
        with engine.connect() as connection:
            foreign_key = (
                connection.exec_driver_sql("PRAGMA foreign_key_list(traces)")
                .mappings()
                .one()
            )
            indexes = (
                connection.exec_driver_sql("PRAGMA index_list(traces)").mappings().all()
            )
            assert foreign_key["table"] == "test_suites"
            assert foreign_key["from"] == "test_suite_id"
            assert foreign_key["on_delete"] == "CASCADE"
            assert any(index["unique"] for index in indexes)
        engine.dispose()
    finally:
        get_settings.cache_clear()


def test_evaluation_migration_backfills_existing_suite_case_ids(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'evaluation-schema.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    try:
        config = _config(url)
        command.upgrade(config, "0004_test_suite_traces")
        engine = sa.create_engine(url)
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO agents (id, name, created_at, updated_at) "
                    "VALUES ('agt_eval', 'Eval', '2026-01-01', '2026-01-01')"
                )
            )
            connection.execute(
                sa.text("""
                    INSERT INTO agent_versions
                    (id, agent_id, version, system_prompt, tools, metadata, created_at)
                    VALUES ('agv_eval', 'agt_eval', '1.0', 'prompt', '[]', '{}', '2026-01-01')
                """)
            )
            connection.execute(
                sa.text("""
                    INSERT INTO test_suites
                    (id, version_id, status, request_json, result_json, created_at, updated_at)
                    VALUES ('ts_eval', 'agv_eval', 'completed', '{}', :result, '2026-01-01', '2026-01-01')
                """),
                {
                    "result": json.dumps(
                        {
                            "items": [
                                {
                                    "category": "happy_path",
                                    "question": "Q",
                                    "expected_behavior": "A",
                                }
                            ]
                        }
                    )
                },
            )

        command.upgrade(config, "head")
        with engine.connect() as connection:
            result = connection.execute(
                sa.text("SELECT result_json FROM test_suites WHERE id='ts_eval'")
            ).scalar_one()
            if isinstance(result, str):
                result = json.loads(result)
            assert result["items"][0]["id"].startswith("tc_")
            assert result["items"][0]["question"] == "Q"
        engine.dispose()
    finally:
        get_settings.cache_clear()


def test_migration_backfills_existing_and_deleted_agents(tmp_path, monkeypatch):
    database = tmp_path / "legacy.db"
    url = f"sqlite:///{database}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    config = _config(url)
    command.upgrade(config, "0001_create_agents")
    engine = sa.create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            sa.text("""
            INSERT INTO agents (id, name, description, system_prompt, developer_prompt,
              model_config, tools, metadata, created_at, updated_at, deleted_at)
            VALUES (:id, :name, :description, :system_prompt, :developer_prompt,
              :model_config, :tools, :metadata, :created_at, :updated_at, :deleted_at)
        """),
            {
                "id": "agt_legacy",
                "name": "Legacy",
                "description": "saved schema",
                "system_prompt": "old prompt",
                "developer_prompt": None,
                "model_config": json.dumps(
                    {"provider": "openai", "name": "gpt-5", "parameters": {}}
                ),
                "tools": "[]",
                "metadata": "{}",
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-02-01T00:00:00",
                "deleted_at": "2025-03-01T00:00:00",
            },
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        row = (
            connection.execute(
                sa.text("SELECT * FROM agent_versions WHERE agent_id='agt_legacy'")
            )
            .mappings()
            .one()
        )
        agent = (
            connection.execute(sa.text("SELECT * FROM agents WHERE id='agt_legacy'"))
            .mappings()
            .one()
        )
        assert row["version"] == "1.0"
        assert row["system_prompt"] == "old prompt"
        assert row["created_at"].startswith("2025-02-01 00:00:00")
        assert row["classification_id"] is None
        assert agent["deleted_at"] == "2025-03-01T00:00:00"
        assert "system_prompt" not in agent
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    engine.dispose()


def test_downgrade_refuses_to_discard_multiple_versions(tmp_path, monkeypatch):
    database = tmp_path / "versions.db"
    url = f"sqlite:///{database}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    config = _config(url)
    command.upgrade(config, "head")
    engine = sa.create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            sa.text("""
          INSERT INTO agents (id,name,created_at,updated_at) VALUES
          ('agt_one','One','2025-01-01','2025-01-01')
        """)
        )
        for version in ("1.0", "2.0"):
            connection.execute(
                sa.text("""
              INSERT INTO agent_versions (id,agent_id,version,system_prompt,tools,metadata,created_at)
              VALUES (:id,'agt_one',:version,'prompt','[]','{}','2025-01-01')
            """),
                {"id": f"agv_{version}", "version": version},
            )
    with pytest.raises(RuntimeError, match="multiple versions"):
        command.downgrade(config, "0001_create_agents")
    engine.dispose()
