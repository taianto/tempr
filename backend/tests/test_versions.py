def test_version_endpoints_and_duplicate_labels(client, agent_factory):
    created = agent_factory()
    agent_id = created["id"]
    payload = {"version": "2.0", "schema": {"prompt": {"system": "New prompt."}}}
    response = client.post("/api/v1/versions", json={"agent_id": agent_id, **payload})
    assert response.status_code == 201
    new_version = response.json()
    assert new_version["schema"]["prompt"]["system"] == "New prompt."
    assert (
        client.post(
            "/api/v1/versions", json={"agent_id": agent_id, **payload}
        ).status_code
        == 409
    )
    assert (
        client.get(f"/api/v1/agents/{agent_id}").json()["latest_version"]["id"]
        == new_version["id"]
    )
    versions = client.get(f"/api/v1/versions?agent_id={agent_id}").json()
    assert versions["total"] == 2
    assert versions["items"][0]["id"] == new_version["id"]
    assert client.get(f"/api/v1/versions/{new_version['id']}").status_code == 200


def test_versions_are_filtered_by_agent_and_require_agent_id(client, agent_factory):
    first = agent_factory()
    second = agent_factory()
    response = client.post(
        "/api/v1/versions",
        json={
            "agent_id": first["id"],
            "version": "2.0",
            "schema": {"prompt": {"system": "First agent v2."}},
        },
    )
    assert response.status_code == 201
    assert client.get("/api/v1/versions").status_code == 422
    first_versions = client.get(f"/api/v1/versions?agent_id={first['id']}").json()
    second_versions = client.get(f"/api/v1/versions?agent_id={second['id']}").json()
    assert first_versions["total"] == 2
    assert second_versions["total"] == 1
    assert all(
        item["id"] != second["latest_version"]["id"] for item in first_versions["items"]
    )
