import json
import uuid
from datetime import datetime, UTC
from questions.types import QuestionDB

def _parse_dt(value) -> datetime:
    """Parse an ISO string or return current UTC time."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now(UTC)


def _build_question_db(q_data: dict, paper_id: str, author_id: str) -> QuestionDB:
    return QuestionDB(
        id=q_data.get("id", str(uuid.uuid4())),
        paper_id=paper_id,
        author_id=author_id,
        number=q_data.get("number", 1),
        type=q_data.get("type", "short_answer"),
        marks=q_data.get("marks", 0),
        stimulus_json=json.dumps(q_data["stimulus"]) if q_data.get("stimulus") else None,
        content_json=json.dumps(q_data["content"]) if q_data.get("content") else None,
        parts_json=json.dumps(q_data["parts"]) if q_data.get("parts") else None,
        options_json=json.dumps(q_data["options"]) if q_data.get("options") else None,
        topics_json=json.dumps(q_data["topics"]) if q_data.get("topics") else None,
        answer=q_data.get("answer"),
        difficulty=q_data.get("difficulty"),
        created_at=_parse_dt(q_data.get("created_at")),
        updated_at=_parse_dt(q_data.get("updated_at")),
    )