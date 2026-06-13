from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlmodel import col, select
from datetime import datetime, UTC

from questions.db import get_session
from questions.types import (
    PaperCreate,
    PaperDB,
    PaperOutcome,
    PaperUpdate,
    paper_db_to_meta_read,
    paper_db_to_read,
)
from questions.utils import _build_question_db

q_bp = Blueprint("tppr-questions", __name__)


# --- Papers ---

@q_bp.route("/api/papers/search", methods=["GET"])
def search_papers():
    q = request.args.get("q")
    subject = request.args.get("subject")
    source = request.args.get("source")
    course_level = request.args.get("course_level")
    year = request.args.get("year")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    with get_session() as session:
        statement = select(PaperDB).where(PaperDB.visibility == "public")

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

        total = len(session.exec(statement).all())
        statement = statement.offset((page - 1) * per_page).limit(per_page)
        papers = session.exec(statement).all()

        return jsonify(
            {
                "papers": [paper_db_to_meta_read(p).model_dump(mode="json") for p in papers],
                "total": total,
                "page": page,
                "per_page": per_page,
            }
        )

@q_bp.route("/api/papers", methods=["GET"])
@jwt_required()
def list_papers():
    user_id = get_jwt_identity()
    q = request.args.get("q")
    subject = request.args.get("subject")
    source = request.args.get("source")
    course_level = request.args.get("course_level")
    year = request.args.get("year")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    with get_session() as session:
        statement = select(PaperDB).where(PaperDB.author_id == str(user_id))

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

        total = len(session.exec(statement).all())
        statement = statement.offset((page - 1) * per_page).limit(per_page)
        papers = session.exec(statement).all()

        return jsonify(
            {
                "papers": [paper_db_to_meta_read(p).model_dump(mode="json") for p in papers],
                "total": total,
                "page": page,
                "per_page": per_page,
            }
        )

@q_bp.route("/api/papers/<string:paper_id>", methods=["GET"])
@jwt_required(optional=True)
def get_paper(paper_id):
    user_id = get_jwt_identity()  # None if not logged in

    with get_session() as session:
        paper = session.get(PaperDB, paper_id)
        if not paper:
            return jsonify({"message": "Paper not found"}), 404

        # Private papers are only visible to their author
        if paper.visibility == "private" and str(paper.author_id) != str(user_id):
            return jsonify({"message": "Paper not found"}), 404

        return jsonify(paper_db_to_read(paper).model_dump(mode="json"))


# --- SYNCING ---

@q_bp.route("/api/papers", methods=["POST"])
@jwt_required()
def create_paper():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({"message": "No data provided"}), 400

    with get_session() as session:
        paper = PaperDB(
            id=data.get("id", str(__import__("uuid").uuid4())),
            title=data.get("title", "Untitled"),
            author_id=str(user_id),
            subject=data.get("subject", ""),
            syllabus_id=data.get("syllabus_id"),
            year=data.get("year"),
            source=data.get("source"),
            school=data.get("school"),
            course_level=data.get("course_level"),
            visibility=data.get("visibility", "private"),
            question_count=data.get("question_count", 0),
            total_marks=data.get("total_marks", 0),
            duration_minutes=data.get("duration_minutes"),
        )
        if data.get("topics"):
            paper.set_topics(data["topics"])

        session.add(paper)

        for q_data in data.get("questions", []):
            q = _build_question_db(q_data, paper.id, str(user_id))
            session.add(q)

        session.commit()
        session.refresh(paper)
        return jsonify(paper_db_to_read(paper).model_dump(mode="json")), 201


@q_bp.route("/api/papers/<string:paper_id>", methods=["PUT"])
@jwt_required()
def update_paper(paper_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({"message": "No data provided"}), 400

    with get_session() as session:
        paper = session.get(PaperDB, paper_id)
        if not paper:
            return jsonify({"message": "Paper not found"}), 404
        if paper.author_id != str(user_id):
            return jsonify({"message": "Forbidden"}), 403

        # Update paper fields
        if "title" in data:
            paper.title = data["title"]
        if "subject" in data:
            paper.subject = data["subject"]
        if "syllabus_id" in data:
            paper.syllabus_id = data["syllabus_id"]
        if "year" in data:
            paper.year = data["year"]
        if "source" in data:
            paper.source = data["source"]
        if "school" in data:
            paper.school = data["school"]
        if "course_level" in data:
            paper.course_level = data["course_level"]
        if "visibility" in data:
            paper.visibility = data["visibility"]
        if "question_count" in data:
            paper.question_count = data["question_count"]
        if "total_marks" in data:
            paper.total_marks = data["total_marks"]
        if "duration_minutes" in data:
            paper.duration_minutes = data["duration_minutes"]
        if "topics" in data:
            paper.set_topics(data["topics"])

        paper.updated_at = datetime.now(UTC)

        if "questions" in data:
            paper.questions.clear()
            session.flush()

            new_questions = []
            for q_data in data["questions"]:
                q = _build_question_db(q_data, paper_id, str(user_id))
                new_questions.append(q)
            paper.questions = new_questions

            paper.question_count = len(data["questions"])
            paper.total_marks = sum(q.get("marks", 0) for q in data["questions"])

        session.commit()
        session.refresh(paper)
        return jsonify(paper_db_to_read(paper).model_dump(mode="json")), 200

        session.add(paper)
        session.commit()
        session.refresh(paper)
        return jsonify(paper_db_to_read(paper).model_dump(mode="json")), 200

@q_bp.route("/api/papers/<string:paper_id>", methods=["DELETE"])
@jwt_required()
def delete_paper(paper_id):
    user_id = get_jwt_identity()

    with get_session() as session:
        paper = session.get(PaperDB, paper_id)
        if not paper:
            return jsonify({"message": "Paper not found"}), 404
        if paper.author_id != str(user_id):
            return jsonify({"message": "Forbidden"}), 403

        session.delete(paper)
        session.commit()
        return jsonify({"message": "Deleted"}), 200

# --- PUBLISHING ---

@q_bp.route("/api/papers/<string:paper_id>/publish", methods=["POST"])
@jwt_required()
def publish_paper(paper_id):
    user_id = get_jwt_identity()

    with get_session() as session:
        paper = session.get(PaperDB, paper_id)

        if paper:
            # it exists, verify it
            if paper.author_id != str(user_id):
                return jsonify({"message": "Forbidden"}), 403
            if paper.visibility == "public":
                return jsonify({"message": "Paper is already public"}), 409
        else:
            # paper doesnt exist on server, create it
            data = request.get_json()
            if not data:
                return jsonify({"message": "Paper not found and no body provided"}), 400

            paper = PaperDB(
                id=paper_id,
                title=data.get("title", "Untitled"),
                author_id=str(user_id),
                subject=data.get("subject", ""),
                syllabus_id=data.get("syllabus_id"),
                year=data.get("year"),
                source=data.get("source"),
                school=data.get("school"),
                course_level=data.get("course_level"),
                question_count=data.get("question_count", 0),
                total_marks=data.get("total_marks", 0),
                duration_minutes=data.get("duration_minutes"),
            )
            session.add(paper)

        paper.visibility = "public"
        paper.updated_at = datetime.now(UTC)
        session.add(paper)
        session.commit()
        session.refresh(paper)

        return jsonify(paper_db_to_meta_read(paper).model_dump(mode="json")), 200

@q_bp.route("/api/papers/<string:paper_id>/publish", methods=["DELETE"])
@jwt_required()
def unpublish_paper(paper_id):
    user_id = get_jwt_identity()

    with get_session() as session:
        paper = session.get(PaperDB, paper_id)
        if not paper:
            return jsonify({"message": "Paper not found"}), 404
        if paper.author_id != str(user_id):
            return jsonify({"message": "Forbidden"}), 403
        if paper.visibility == "private":
            return jsonify({"message": "Paper is already private"}), 409

        paper.visibility = "private"
        paper.updated_at = datetime.now(UTC)
        
        session.add(paper)
        session.commit()
        session.refresh(paper)

        return jsonify(paper_db_to_meta_read(paper).model_dump(mode="json")), 200