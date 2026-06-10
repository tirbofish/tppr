from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlmodel import col, select

from questions.db import get_session
from questions.types import PaperDB, PaperOutcome

q_bp = Blueprint("tppr-questions", __name__)


# --- Papers ---


@q_bp.route("/api/papers", methods=["GET"])
def list_papers():
    q = request.args.get("q")
    subject = request.args.get("subject")
    outcomes_raw = request.args.get("outcomes")  # csv
    source = request.args.get("source")
    course_level = request.args.get("course_level")
    year = request.args.get("year")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    with get_session() as session:
        statement = select(PaperDB)

        if q:
            statement = statement.where(
                col(PaperDB.title).contains(q) | col(PaperDB.subject).contains(q)
            )

        if subject:
            statement = statement.where(PaperDB.subject == subject)
        if source:
            statement = statement.where(PaperDB.source == source)
        if course_level:
            statement = statement.where(PaperDB.course_level == course_level)
        if year:
            statement = statement.where(PaperDB.year == int(year))

        if outcomes_raw:
            codes = [c.strip() for c in outcomes_raw.split(",") if c.strip()]
            for code in codes:
                statement = statement.where(
                    col(PaperDB.id).in_(
                        select(PaperOutcome.paper_id).where(
                            PaperOutcome.outcome_code == code
                        )
                    )
                )

        total = len(session.exec(statement).all())

        statement = statement.offset((page - 1) * per_page).limit(per_page)
        papers = session.exec(statement).all()

        return jsonify(
            {
                "papers": [p.model_dump() for p in papers],
                "total": total,
                "page": page,
                "per_page": per_page,
            }
        )


@q_bp.route("/api/papers", methods=["POST"])
@jwt_required()
def create_paper():
    data = request.get_json()
    with get_session() as session:
        paper = PaperDB(**data)
        session.add(paper)
        session.commit()
        session.refresh(paper)
        return jsonify(paper.model_dump()), 201


@q_bp.route("/api/papers/<int:paper_id>", methods=["GET"])
def get_paper(paper_id):
    return jsonify({})


@q_bp.route("/api/papers/<int:paper_id>", methods=["PUT"])
@jwt_required()
def update_paper(paper_id):
    return jsonify({})


@q_bp.route("/api/papers/<int:paper_id>", methods=["DELETE"])
@jwt_required()
def delete_paper(paper_id):
    return jsonify({})


@q_bp.route("/api/papers/<int:paper_id>/export", methods=["GET"])
def export_paper(paper_id):
    return jsonify({})


@q_bp.route("/api/papers/import", methods=["POST"])
@jwt_required()
def import_paper():
    return jsonify({})


# --- Questions within a paper ---


@q_bp.route("/api/papers/<int:paper_id>/questions", methods=["GET"])
def list_paper_questions(paper_id):
    return jsonify([])


@q_bp.route("/api/papers/<int:paper_id>/questions", methods=["POST"])
@jwt_required()
def add_question_to_paper(paper_id):
    return jsonify({})


@q_bp.route("/api/papers/<int:paper_id>/questions/import", methods=["POST"])
@jwt_required()
def import_questions_to_paper(paper_id):
    return jsonify({})


@q_bp.route("/api/papers/<int:paper_id>/questions/reorder", methods=["PUT"])
@jwt_required()
def reorder_paper_questions(paper_id):
    return jsonify({})


@q_bp.route("/api/papers/<int:paper_id>/questions/<int:question_id>", methods=["GET"])
def get_paper_question(paper_id, question_id):
    return jsonify({})


@q_bp.route("/api/papers/<int:paper_id>/questions/<int:question_id>", methods=["PUT"])
@jwt_required()
def update_paper_question(paper_id, question_id):
    return jsonify({})


@q_bp.route(
    "/api/papers/<int:paper_id>/questions/<int:question_id>", methods=["DELETE"]
)
@jwt_required()
def delete_paper_question(paper_id, question_id):
    return jsonify({})


# --- Public paper search ---


@q_bp.route("/api/papers/search", methods=["GET"])
def search_papers():
    """Search publicly published papers with optional filters.

    Query params:
      - q: text search (matches title, subject)
      - subject: filter by subject
      - outcomes: comma-separated list of outcome codes (papers must assess ALL specified outcomes)
      - source: filter by source (hsc, trial, internal, practice, custom)
      - course_level: filter by course level
      - year: filter by year
      - page: page number (default 1)
      - per_page: results per page (default 20)
    """
    # TODO: implement database query - for now return empty results with structure
    return jsonify(
        {
            "papers": [],
            "total": 0,
            "page": int(request.args.get("page", 1)),
            "per_page": int(request.args.get("per_page", 20)),
        }
    )


# --- Global question search ---


@q_bp.route("/api/questions", methods=["GET"])
def search_questions():
    return jsonify([])


@q_bp.route("/api/questions/<int:question_id>", methods=["GET"])
def get_question(question_id):
    return jsonify({})
