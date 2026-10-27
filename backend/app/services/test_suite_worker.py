import logging
from datetime import UTC, datetime

from app.config import get_settings
from app.db.database import SessionLocal
from app.repositories.test_suites import TestSuiteRepository
from app.services.test_suite_generator import (
    TestSuiteGenerationFailure,
    TestSuiteGenerator,
)
from app.services.test_suites import completed_result

logger = logging.getLogger(__name__)


def run_test_suite_generation(test_suite_id: str) -> None:
    """Claim a queued suite, generate it, and persist one terminal outcome."""
    with SessionLocal() as db:
        repository = TestSuiteRepository(db)
        claimed = repository.claim(test_suite_id)
        if claimed is None:
            repository.fail_queued_for_deleted_agent(test_suite_id)
    if claimed is None:
        return
    request, context = claimed

    try:
        items = TestSuiteGenerator(get_settings()).generate(context, request)
        result = completed_result(
            request,
            [item.model_dump() for item in items],
            datetime.now(UTC),
        )
        with SessionLocal() as db:
            saved = TestSuiteRepository(db).complete(test_suite_id, result)
            if not saved:
                TestSuiteRepository(db).fail(
                    test_suite_id, "Agent was deleted during generation"
                )
    except TestSuiteGenerationFailure as exc:
        logger.warning(
            "Test suite generation failed for %s: %s", test_suite_id, exc.detail
        )
        with SessionLocal() as db:
            TestSuiteRepository(db).fail(test_suite_id, exc.detail)
    except Exception:
        logger.exception(
            "Unexpected test suite generation failure for %s", test_suite_id
        )
        with SessionLocal() as db:
            TestSuiteRepository(db).fail(
                test_suite_id, "Unable to generate a test suite"
            )
