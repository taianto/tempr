import httpx
import pytest
from task_manager.tempr.client import TemprAPIError, TemprClient


def test_client_builds_api_requests():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"id": "agv_1"})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = TemprClient("http://tempr/api/v1", client=http)

    response = client.create_version("agt_1", "1.1", {"prompt": {"system": "hi"}})

    assert response["id"] == "agv_1"
    assert requests[0].url.path == "/api/v1/versions"
    assert requests[0].read() == (
        b'{"agent_id":"agt_1","version":"1.1","schema":{"prompt":{"system":"hi"}}}'
    )
    http.close()


def test_client_reports_api_detail_and_status():
    http = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                409, json={"detail": "Version already exists"}
            )
        )
    )
    client = TemprClient("http://tempr/api/v1", client=http)

    with pytest.raises(
        TemprAPIError, match="HTTP 409: Version already exists"
    ) as error:
        client.create_version("agt_1", "1.1", {})

    assert error.value.status_code == 409
    http.close()
