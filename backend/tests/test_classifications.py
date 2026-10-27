def test_classification_persists_reuses_and_refreshes(
    client, fake_classification, agent_factory
):
    created = agent_factory()
    version_id = created["latest_version"]["id"]
    first = client.post("/api/v1/classifications", json={"version_id": version_id})
    assert first.status_code == 200
    assert first.json()["classifier_model"] == "test-model"
    assert sum(first.json()["scores"].values()) == 1
    classification_id = first.json()["id"]
    assert (
        client.get(f"/api/v1/classifications/{classification_id}").json()["id"]
        == classification_id
    )
    assert (
        client.post("/api/v1/classifications", json={"version_id": version_id}).json()[
            "id"
        ]
        == classification_id
    )
    assert fake_classification.calls == 1

    refreshed = client.post(
        "/api/v1/classifications?refresh=true", json={"version_id": version_id}
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["id"] == classification_id
    assert fake_classification.calls == 2
    assert client.get("/api/v1/classifications/cls_missing").status_code == 404


def test_failed_refresh_preserves_saved_classification(
    client, fake_classification, agent_factory
):
    created = agent_factory()
    version_id = created["latest_version"]["id"]
    saved = client.post(
        "/api/v1/classifications", json={"version_id": version_id}
    ).json()
    fake_classification.fail = True
    assert (
        client.post(
            "/api/v1/classifications?refresh=true", json={"version_id": version_id}
        ).status_code
        == 503
    )
    assert client.get(f"/api/v1/classifications/{saved['id']}").json() == saved


def test_flat_resource_routes_reject_deleted_agent(
    client, fake_classification, agent_factory
):
    created = agent_factory()
    agent_id, version_id = created["id"], created["latest_version"]["id"]
    classification = client.post(
        "/api/v1/classifications", json={"version_id": version_id}
    ).json()
    assert client.delete(f"/api/v1/agents/{agent_id}").status_code == 204
    for path in (
        f"/api/v1/versions?agent_id={agent_id}",
        f"/api/v1/versions/{version_id}",
    ):
        assert client.get(path).status_code == 404
    assert (
        client.post(
            "/api/v1/classifications", json={"version_id": version_id}
        ).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/classifications/{classification['id']}").status_code == 404
    )
    assert client.get(f"/api/v1/agents/{agent_id}/versions").status_code == 404
