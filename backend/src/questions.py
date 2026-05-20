from flask import Blueprint, request, jsonify
from typing import Literal, Optional, Union, Annotated
from pydantic import BaseModel, Field, ValidationError, TypeAdapter

# --- api ---

q_bp = Blueprint("tppr-questions-access", __name__)


@q_bp.route("/api/questions/upload", methods=["POST"])
def upload_question():
    data = request.get_json(silent=True)

    if data is None:
        return jsonify(
            {
                "error": "invalid_json",
                "message": "Request body must be valid JSON.",
            }
        ), 400

    try:
        question = QuestionAdapter.validate_python(data)
    except ValidationError as err:
        return jsonify(
            {
                "error": "validation_error",
                "message": "Question format is invalid.",
                "details": err.errors(),
            }
        ), 400

    return jsonify(
        {
            "message": "Question validated successfully.",
            "question_type": question.kind,
            "question": question.model_dump(mode="json"),
        }
    ), 200
