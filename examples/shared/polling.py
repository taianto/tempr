import time
from collections.abc import Callable
from typing import Any

from tempr.client import TemprAPIError

TERMINAL = {"completed", "failed"}


def wait_for_completion(
    fetch: Callable[[], dict[str, Any] | None], label: str, timeout: float = 600
) -> dict[str, Any]:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        result = fetch()
        if result and result.get("status") in TERMINAL:
            if result["status"] == "failed":
                raise TemprAPIError(f"{label} failed: {result.get('error')}")
            return result
        elapsed = int(time.monotonic() - start)
        print(
            f"{label}: {result.get('status', 'waiting') if result else 'waiting'} ({elapsed}s)"
        )
        time.sleep(1)
    raise TemprAPIError(f"Timed out waiting for {label} after {timeout:g} seconds")
