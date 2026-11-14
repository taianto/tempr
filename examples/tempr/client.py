"""Small HTTP client for the tempr API used by the workflow."""

from typing import Any, Self

import httpx


class TemprAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class TemprClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8080/api/v1",
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def create_agent(self, name: str, version: str, schema: dict[str, Any]):
        return self._request(
            "POST",
            "/agents",
            json={
                "name": name,
                "initial_version": {"version": version, "schema": schema},
            },
        )

    def list_agents(self):
        return self._request("GET", "/agents")

    def list_versions(self, agent_id: str):
        return self._request("GET", "/versions", params={"agent_id": agent_id})

    def create_version(self, agent_id: str, version: str, schema: dict[str, Any]):
        return self._request(
            "POST",
            "/versions",
            json={"agent_id": agent_id, "version": version, "schema": schema},
        )

    def classify(self, version_id: str):
        return self._request(
            "POST", "/classifications", json={"version_id": version_id}
        )

    def generate_suite(self, version_id: str, count: int):
        return self._request(
            "POST",
            f"/versions/{version_id}/test-suites/generate",
            json={"total_count": count},
        )

    def get_suite(self, version_id: str):
        return self._request("GET", f"/versions/{version_id}/test-suites")

    def upload_trace(self, suite_id: str, trace: dict[str, Any]):
        return self._request(
            "POST", f"/test-suites/{suite_id}/trace", json={"trace": trace}
        )

    def start_evaluation(self, suite_id: str):
        return self._request("POST", f"/test-suites/{suite_id}/evaluation")

    def get_evaluation(self, suite_id: str):
        return self._request("GET", f"/test-suites/{suite_id}/evaluation")

    def _request(self, method: str, path: str, **kwargs: Any):
        try:
            response = self._client.request(method, f"{self.base_url}{path}", **kwargs)
        except httpx.HTTPError as exc:
            raise TemprAPIError(f"Could not connect to tempr: {exc}") from exc
        if response.is_error:
            try:
                body = response.json()
            except ValueError:
                body = response.text
            detail = body.get("detail", body) if isinstance(body, dict) else body
            raise TemprAPIError(
                f"tempr returned HTTP {response.status_code}: {detail}",
                response.status_code,
            )
        if response.status_code == 204:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise TemprAPIError("tempr returned an invalid JSON response") from exc
