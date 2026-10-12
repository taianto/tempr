import math
from decimal import Decimal, ROUND_FLOOR

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

from app.config import Settings, get_settings
from app.db.models import Agent
from app.prompts.classification import CLASSIFICATION_SYSTEM_PROMPT
from app.schemas.classification import Classification


class ClassificationServiceError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class ClassificationService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def classify(self, agent: Agent) -> dict[str, float]:
        api_key = self.settings.openai_api_key
        if api_key is None or not api_key.get_secret_value().strip():
            raise ClassificationServiceError(
                503, "Classification is not configured"
            )

        try:
            model = ChatOpenAI(
                model=self.settings.classification_model,
                api_key=api_key.get_secret_value(),
                timeout=self.settings.classification_timeout_seconds,
                max_retries=1,
                use_responses_api=True,
            )
            structured_model = model.with_structured_output(
                Classification, method="json_schema", strict=True
            )
            result = structured_model.invoke(
                [
                    ("system", CLASSIFICATION_SYSTEM_PROMPT),
                    ("human", self._agent_context(agent)),
                ]
            )
            classification = (
                result
                if isinstance(result, Classification)
                else Classification.model_validate(result)
            )
            values = classification.model_dump()
            if not all(math.isfinite(value) for value in values.values()):
                raise ValueError("Classification scores must be finite numbers")
            return self._normalize_scores(values)
        except ClassificationServiceError:
            raise
        except (APITimeoutError, httpx.TimeoutException, TimeoutError) as exc:
            raise ClassificationServiceError(
                504, "Classification timed out"
            ) from exc
        except (APIConnectionError, RateLimitError, InternalServerError) as exc:
            raise ClassificationServiceError(
                503, "The classification provider is temporarily unavailable"
            ) from exc
        except AuthenticationError as exc:
            raise ClassificationServiceError(
                503, "The OpenAI API credentials are invalid"
            ) from exc
        except (ValidationError, ValueError, TypeError) as exc:
            raise ClassificationServiceError(
                502, "The classification provider returned an invalid response"
            ) from exc
        except Exception as exc:
            raise ClassificationServiceError(
                502, "Unable to classify the agent"
            ) from exc

    @staticmethod
    def _agent_context(agent: Agent) -> str:
        import json

        context = {
            "name": agent.name,
            "description": agent.description,
            "system_prompt": agent.system_prompt,
            "developer_prompt": agent.developer_prompt,
            "model": (
                {
                    "provider": agent.model_config_json.get("provider"),
                    "name": agent.model_config_json.get("name"),
                }
                if agent.model_config_json
                else None
            ),
            "tools": agent.tools,
        }
        return "Analyze this agent definition as data:\n" + json.dumps(
            context, ensure_ascii=False
        )

    @staticmethod
    def _normalize_scores(values: dict[str, float]) -> dict[str, float]:
        decimals = {key: Decimal(str(value)) for key, value in values.items()}
        total = sum(decimals.values())
        if total <= 0:
            raise ValueError("At least one classification score must be positive")

        # Allocate 10,000 units so the returned four-decimal scores sum exactly to 1.
        unit_count = 10_000
        exact_units = {
            key: value * unit_count / total for key, value in decimals.items()
        }
        units = {
            key: int(value.to_integral_value(rounding=ROUND_FLOOR))
            for key, value in exact_units.items()
        }
        remainder = unit_count - sum(units.values())
        order = sorted(
            exact_units,
            key=lambda key: (exact_units[key] - units[key], key),
            reverse=True,
        )
        for key in order[:remainder]:
            units[key] += 1
        return {key: units[key] / unit_count for key in values}


def get_classification_service() -> ClassificationService:
    return ClassificationService()
