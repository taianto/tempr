import json
import math
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
from app.prompts.evaluation import EVALUATION_SYSTEM_PROMPT
from app.schemas.evaluation import RubricScores


class EvaluationFailure(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class Evaluator:
    """Score one execution against its saved suite item."""

    def __init__(self, settings: Settings, model_name: str) -> None:
        self.settings = settings
        self.model_name = model_name

    def evaluate(
        self,
        agent: dict[str, Any],
        case: dict[str, Any],
    ) -> dict[str, Any]:
        api_key = self.settings.openai_api_key
        if api_key is None or not api_key.get_secret_value().strip():
            raise EvaluationFailure("Evaluation is not configured")
        try:
            model = ChatOpenAI(
                model=self.model_name,
                api_key=api_key.get_secret_value(),
                timeout=self.settings.evaluation_timeout_seconds,
                max_retries=0,
                use_responses_api=True,
            ).with_structured_output(RubricScores, method="json_schema", strict=True)
            result = model.invoke(
                [
                    ("system", EVALUATION_SYSTEM_PROMPT),
                    (
                        "human",
                        "Evaluate this supplied data only:\n"
                        + json.dumps(
                            {"agent": agent, "test_case": case},
                            ensure_ascii=False,
                        ),
                    ),
                ]
            )
            scores = (
                result
                if isinstance(result, RubricScores)
                else RubricScores.model_validate(result)
            )
            values = scores.model_dump()
            for name in (
                "adherence_score",
                "consistency_score",
                "grounding_score",
            ):
                value = values[name]
                if not math.isfinite(value) or not 0 <= value <= 1:
                    raise ValueError("Evaluation score is outside [0, 1]")
            return values
        except (APITimeoutError, httpx.TimeoutException, TimeoutError) as exc:
            raise EvaluationFailure("Evaluation timed out") from exc
        except (APIConnectionError, RateLimitError, InternalServerError) as exc:
            raise EvaluationFailure(
                "The evaluation provider is temporarily unavailable"
            ) from exc
        except AuthenticationError as exc:
            raise EvaluationFailure("The OpenAI API credentials are invalid") from exc
        except (ValidationError, ValueError, TypeError) as exc:
            raise EvaluationFailure(
                "The evaluation provider returned an invalid response"
            ) from exc
        except EvaluationFailure:
            raise
        except Exception as exc:
            raise EvaluationFailure("Unable to evaluate the agent execution") from exc
