"""
Structural validation of the eval question set (evals/questions.py). Catches
copy-paste errors (duplicate IDs, empty question text) without needing a live
backend - the questions module itself already asserts count/uniqueness at
import time, this makes those checks visible as named, individually-reportable
CI test results instead of one import-time assertion.
"""
from evals.questions import QUESTIONS

_VALID_CATEGORIES = {
    "simple_lookup", "trend", "comparison", "name_resolution",
    "ambiguous", "no_answer", "adversarial",
}


def test_all_ids_unique():
    ids = [q.id for q in QUESTIONS]
    assert len(ids) == len(set(ids)), "duplicate question IDs found"


def test_all_categories_are_known():
    for q in QUESTIONS:
        assert q.category in _VALID_CATEGORIES, f"{q.id} has unknown category {q.category!r}"


def test_all_questions_nonempty():
    for q in QUESTIONS:
        assert q.question.strip(), f"{q.id} has empty question text"


def test_expected_numbers_or_behavior_makes_sense():
    for q in QUESTIONS:
        if q.expected_behavior:
            assert q.expected_behavior in ("refuse", "disambiguate"), q.id
            assert not q.expected_numbers, f"{q.id} has both expected_behavior and expected_numbers"


def test_every_category_has_at_least_one_question():
    covered = {q.category for q in QUESTIONS}
    missing = _VALID_CATEGORIES - covered
    assert not missing, f"categories with zero questions: {missing}"
