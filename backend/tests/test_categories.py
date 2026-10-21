import pytest
from pydantic import ValidationError

from app.db.models import Classification as ClassificationRecord
from app.domain.test_categories import TEST_CATEGORIES
from app.schemas.classification import Classification
from app.schemas.test_suite import GeneratedTestSuiteItem


def test_classification_preserves_structured_output_contract():
    schema = Classification.model_json_schema()
    assert schema["title"] == "Classification"
    assert schema["additionalProperties"] is False
    assert schema["required"] == list(TEST_CATEGORIES)
    assert tuple(schema["properties"]) == TEST_CATEGORIES
    for field in schema["properties"].values():
        assert field["type"] == "number"
        assert field["minimum"] == 0
        assert field["maximum"] == 1


def test_category_fields_match_shared_category_list():
    database_fields = set(ClassificationRecord.__table__.columns.keys()) - {
        "id",
        "classifier_model",
        "created_at",
        "updated_at",
    }
    assert tuple(Classification.model_fields) == TEST_CATEGORIES
    assert database_fields == set(TEST_CATEGORIES)


@pytest.mark.parametrize("category", TEST_CATEGORIES)
def test_categories_validate_scores_and_generated_suite_items(category):
    scores = dict.fromkeys(TEST_CATEGORIES, 0.5)
    assert Classification(**scores).model_dump() == scores
    for invalid in (-0.1, 1.1, float("nan"), float("inf")):
        with pytest.raises(ValidationError):
            Classification(**(scores | {category: invalid}))
    with pytest.raises(ValidationError):
        Classification(**{key: value for key, value in scores.items() if key != category})
    with pytest.raises(ValidationError):
        Classification(**(scores | {"unknown_category": 0.5}))

    item = GeneratedTestSuiteItem(
        category=category, question="A question", expected_behavior="An answer"
    )
    assert item.model_dump(mode="json")["category"] == category
    with pytest.raises(ValidationError):
        GeneratedTestSuiteItem(
            category="unknown_category", question="A question", expected_behavior="An answer"
        )
