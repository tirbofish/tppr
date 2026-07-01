import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from questions.types import (  # noqa: E402
    QuestionDB,
    question_db_to_read,
    question_verified_fingerprint,
)


def _question(content: str = "Original") -> QuestionDB:
    return QuestionDB(
        id="question-1",
        paper_id="paper-1",
        author_id="user-1",
        number=1,
        type="short_answer",
        marks=2,
        content_json=json.dumps([{"kind": "text", "text": content}]),
    )


def test_verified_question_with_matching_fingerprint_is_not_changed():
    question = _question()
    question.verified_fingerprint = question_verified_fingerprint(question)

    read = question_db_to_read(question, paper_verified=True)

    assert read.verified_changed is False


def test_verified_question_with_different_fingerprint_is_changed():
    question = _question()
    question.verified_fingerprint = question_verified_fingerprint(question)
    question.content_json = json.dumps([{"kind": "text", "text": "Changed"}])

    read = question_db_to_read(question, paper_verified=True)

    assert read.verified_changed is True


def test_unverified_paper_does_not_surface_question_change_state():
    question = _question("Changed")
    question.verified_fingerprint = ""

    read = question_db_to_read(question, paper_verified=False)

    assert read.verified_changed is False


def test_new_question_after_verification_is_changed():
    question = _question("Added later")
    question.verified_fingerprint = ""

    read = question_db_to_read(question, paper_verified=True)

    assert read.verified_changed is True


def test_legacy_verified_question_without_baseline_is_not_marked_changed():
    question = _question("Legacy")

    read = question_db_to_read(question, paper_verified=True)

    assert read.verified_changed is False
