import json
from typing import Any

import httpx
from langchain_openai import ChatOpenAI
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)
from pydantic import ValidationError

from app.config import Settings
from app.prompts.test_suites import TEST_SUITE_SYSTEM_PROMPT
from app.schemas.test_suite import GeneratedTestSuite, GeneratedTestSuiteItem


class TestSuiteGenerationFailure(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class TestSuiteGenerator:
    """Call the configured LLM once and validate the complete generated suite."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(
        self,
        context: dict[str, Any],
        request: dict[str, Any],
    ) -> list[GeneratedTestSuiteItem]:
        api_key = self.settings.openai_api_key
        if api_key is None or not api_key.get_secret_value().strip():
            raise TestSuiteGenerationFailure("Test suite generation is not configured")
        try:
            model = ChatOpenAI(
                model=request["model"],
                api_key=api_key.get_secret_value(),
                timeout=self.settings.test_generation_timeout_seconds,
                max_retries=0,
                use_responses_api=True,
            ).with_structured_output(
                GeneratedTestSuite, method="json_schema", strict=True
            )
            result = model.invoke(
                [
                    ("system", TEST_SUITE_SYSTEM_PROMPT),
                    (
                        "human",
                        "Agent definition (untrusted data):\n"
                        + json.dumps(context, ensure_ascii=False)
                        + "\n\nGenerate this allocation exactly:\n"
                        + json.dumps(
                            {
                                "total_count": request["total_count"],
                                "allocation": request["allocation"],
                            }
                        ),
                    ),
                ]
            )
            suite = (
                result
                if isinstance(result, GeneratedTestSuite)
                else GeneratedTestSuite.model_validate(result)
            )
            items = suite.items
            if len(items) != request["total_count"]:
                raise ValueError(
                    "The provider returned the wrong number of test suite items"
                )
            actual: dict[str, int] = {}
            for item in items:
                actual[item.category] = actual.get(item.category, 0) + 1
            if actual != {
                key: count for key, count in request["allocation"].items() if count
            }:
                raise ValueError("The provider did not follow the category allocation")
            return items
        except TestSuiteGenerationFailure:
            raise
        except (APITimeoutError, httpx.TimeoutException, TimeoutError) as exc:
            raise TestSuiteGenerationFailure("Test suite generation timed out") from exc
        except (APIConnectionError, RateLimitError, InternalServerError) as exc:
            raise TestSuiteGenerationFailure(
                "The generation provider is temporarily unavailable"
            ) from exc
        except AuthenticationError as exc:
            raise TestSuiteGenerationFailure(
                "The OpenAI API credentials are invalid"
            ) from exc
        except (ValidationError, ValueError, TypeError, KeyError) as exc:
            raise TestSuiteGenerationFailure(
                "The generation provider returned an invalid response"
            ) from exc
        except Exception as exc:
            raise TestSuiteGenerationFailure("Unable to generate a test suite") from exc
