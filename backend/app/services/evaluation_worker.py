import logging

from app.config import get_settings
from app.db.database import SessionLocal
from app.repositories.evaluations import EvaluationRepository
from app.services.evaluator import EvaluationFailure, Evaluator

logger = logging.getLogger(__name__)


def run_evaluation(evaluation_id: str) -> None:
    """Claim one evaluation and atomically store its complete set of scores."""
    with SessionLocal() as db:
        request = EvaluationRepository(db).claim(evaluation_id)
    if request is None:
        return

    settings = get_settings()
    judge_model = settings.evaluation_model or settings.classification_model
    results = []
    try:
        evaluator = Evaluator(settings, judge_model)
        for case in request["cases"]:
            scores = evaluator.evaluate(request["agent"], case)
            results.append(
                {
                    "test_case_id": case["id"],
                    "category": case["category"],
                    **scores,
                }
            )
        with SessionLocal() as db:
            EvaluationRepository(db).complete(evaluation_id, results)
    except EvaluationFailure as exc:
        logger.warning("Evaluation failed for %s: %s", evaluation_id, exc.detail)
        with SessionLocal() as db:
            EvaluationRepository(db).fail(evaluation_id, exc.detail)
    except Exception:
        logger.exception("Unexpected evaluation failure for %s", evaluation_id)
        with SessionLocal() as db:
            EvaluationRepository(db).fail(evaluation_id, "Unable to evaluate the trace")
