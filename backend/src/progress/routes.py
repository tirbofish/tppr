from datetime import UTC, datetime
from uuid import uuid4

from flask import Blueprint, jsonify, request
from sqlmodel import Session, col, select

from auth.supabase import get_current_user_id, supabase_auth_required
from questions.db import get_session
from questions.types import PaperDB

from .aggregations import compute_student_stats
from .models import PaperAttemptDB, QuestionAttemptDB

progress_bp = Blueprint("tppr-progress", __name__)


def _error(message: str, status: int):
    return jsonify({"message": message}), status


def _part_path_key(part_path) -> str:
    if not part_path:
        return ""
    if isinstance(part_path, str):
        return part_path
    return ".".join(str(p) for p in part_path)


def _paper_meta_map(session: Session, paper_ids: list[str]) -> dict[str, dict]:
    if not paper_ids:
        return {}
    rows = session.exec(
        select(PaperDB).where(col(PaperDB.id).in_(paper_ids))
    ).all()
    return {
        p.id: {
            "title": p.title,
            "subject": p.subject,
            "visibility": p.visibility,
            "question_count": p.question_count,
            "total_marks": p.total_marks,
            "duration_minutes": p.duration_minutes,
            "available": p.visibility != "removed",
        }
        for p in rows
    }


def _question_time_dict(qt: QuestionAttemptDB) -> dict:
    return {
        "question_id": qt.question_id,
        "part_path": qt.part_path or None,
        "seconds": qt.seconds,
        "revealed_answer": qt.revealed_answer,
        "reveal_count": qt.reveal_count,
        "views": qt.views,
    }


def _attempt_dict(attempt: PaperAttemptDB, paper_meta: dict | None) -> dict:
    completed = attempt.completed
    if paper_meta and paper_meta.get("question_count") is not None:
        completed = completed or attempt.max_slide >= int(paper_meta["question_count"]) + 1

    return {
        "id": attempt.id,
        "paper_id": attempt.paper_id,
        "paper": paper_meta,
        "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
        "last_active_at": attempt.last_active_at.isoformat() if attempt.last_active_at else None,
        "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
        "elapsed_seconds": attempt.elapsed_seconds,
        "completed": completed,
        "questions_seen": attempt.questions_seen,
        "questions_answered": attempt.questions_answered,
        "reveal_count": attempt.reveal_count,
        "max_slide": attempt.max_slide,
    }


def _attempt_detail_dict(attempt: PaperAttemptDB, paper_meta: dict | None) -> dict:
    data = _attempt_dict(attempt, paper_meta)
    data["question_times"] = [
        _question_time_dict(qt) for qt in sorted(
            attempt.question_times, key=lambda q: (q.question_id, q.part_path or "")
        )
    ]
    return data


def _upsert_question_time(
    session: Session,
    attempt: PaperAttemptDB,
    question_id: str,
    part_path,
    seconds: int,
    revealed_answer: bool,
    reveal_count: int,
    views: int,
) -> QuestionAttemptDB:
    key = _part_path_key(part_path)
    existing = next(
        (
            qt for qt in attempt.question_times
            if qt.question_id == question_id and (qt.part_path or "") == key
        ),
        None,
    )
    if existing is None:
        qt = QuestionAttemptDB(
            attempt_id=attempt.id,
            question_id=question_id,
            part_path=key or None,
            seconds=int(seconds),
            revealed_answer=bool(revealed_answer),
            reveal_count=int(reveal_count),
            views=int(views),
        )
        session.add(qt)
        attempt.question_times.append(qt)
        return qt
    existing.seconds = max(existing.seconds, int(seconds))
    existing.revealed_answer = existing.revealed_answer or bool(revealed_answer)
    existing.reveal_count = max(existing.reveal_count, int(reveal_count))
    existing.views = max(existing.views, int(views))
    return existing


@progress_bp.route("/api/attempts", methods=["POST"])
@supabase_auth_required()
def start_attempt():
    user_id = get_current_user_id()
    data = request.get_json(silent=True) or {}
    paper_id = (data.get("paper_id") or "").strip()
    if not paper_id:
        return _error("paper_id is required", 400)

    now = datetime.now(UTC)
    attempt = PaperAttemptDB(
        id=str(uuid4()),
        user_id=str(user_id),
        paper_id=paper_id,
        started_at=now,
        last_active_at=now,
    )
    with get_session() as session:
        session.add(attempt)
        session.commit()
        session.refresh(attempt)
        meta = _paper_meta_map(session, [paper_id]).get(paper_id)
        return jsonify(_attempt_dict(attempt, meta)), 201


@progress_bp.route("/api/attempts/<string:attempt_id>", methods=["GET"])
@supabase_auth_required()
def get_attempt(attempt_id):
    user_id = str(get_current_user_id())
    with get_session() as session:
        attempt = session.get(PaperAttemptDB, attempt_id)
        if not attempt:
            return _error("Attempt not found", 404)
        if attempt.user_id != user_id:
            return _error("Forbidden", 403)
        meta = _paper_meta_map(session, [attempt.paper_id]).get(attempt.paper_id)
        return jsonify(_attempt_detail_dict(attempt, meta)), 200


@progress_bp.route("/api/attempts", methods=["GET"])
@supabase_auth_required()
def list_attempts():
    user_id = str(get_current_user_id())
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    paper_id = request.args.get("paper_id")
    completed = request.args.get("completed")

    with get_session() as session:
        stmt = select(PaperAttemptDB).where(PaperAttemptDB.user_id == user_id)
        if paper_id:
            stmt = stmt.where(PaperAttemptDB.paper_id == paper_id)
        if completed is not None:
            stmt = stmt.where(PaperAttemptDB.completed.is_(completed == "true"))

        total = len(session.exec(stmt).all())
        rows = session.exec(
            stmt.order_by(col(PaperAttemptDB.started_at).desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        ).all()

        meta_map = _paper_meta_map(session, [r.paper_id for r in rows])
        return jsonify({
            "attempts": [_attempt_dict(r, meta_map.get(r.paper_id)) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
        }), 200


@progress_bp.route("/api/attempts/<string:attempt_id>", methods=["PATCH"])
@supabase_auth_required()
def update_attempt(attempt_id):
    user_id = str(get_current_user_id())
    data = request.get_json(silent=True) or {}
    with get_session() as session:
        attempt = session.get(PaperAttemptDB, attempt_id)
        if not attempt:
            return _error("Attempt not found", 404)
        if attempt.user_id != user_id:
            return _error("Forbidden", 403)

        if "elapsed_seconds" in data:
            attempt.elapsed_seconds = max(
                attempt.elapsed_seconds, int(data["elapsed_seconds"] or 0)
            )
        if "questions_seen" in data:
            attempt.questions_seen = max(
                attempt.questions_seen, int(data["questions_seen"] or 0)
            )
        if "questions_answered" in data:
            attempt.questions_answered = max(
                attempt.questions_answered, int(data["questions_answered"] or 0)
            )
        if "reveal_count" in data:
            attempt.reveal_count = max(
                attempt.reveal_count, int(data["reveal_count"] or 0)
            )
        if "max_slide" in data:
            attempt.max_slide = max(attempt.max_slide, int(data["max_slide"] or 0))
        attempt.last_active_at = datetime.now(UTC)

        session.add(attempt)
        session.commit()
        session.refresh(attempt)
        meta = _paper_meta_map(session, [attempt.paper_id]).get(attempt.paper_id)
        return jsonify(_attempt_dict(attempt, meta)), 200


@progress_bp.route("/api/attempts/<string:attempt_id>/questions", methods=["POST"])
@supabase_auth_required()
def record_question_time(attempt_id):
    user_id = str(get_current_user_id())
    data = request.get_json(silent=True) or {}
    question_id = (data.get("question_id") or "").strip()
    if not question_id:
        return _error("question_id is required", 400)

    with get_session() as session:
        attempt = session.get(PaperAttemptDB, attempt_id)
        if not attempt:
            return _error("Attempt not found", 404)
        if attempt.user_id != user_id:
            return _error("Forbidden", 403)

        qt = _upsert_question_time(
            session,
            attempt,
            question_id=question_id,
            part_path=data.get("part_path"),
            seconds=int(data.get("seconds", 0) or 0),
            revealed_answer=bool(data.get("revealed_answer", False)),
            reveal_count=int(data.get("reveal_count", 0) or 0),
            views=int(data.get("views", 0) or 0),
        )
        attempt.last_active_at = datetime.now(UTC)
        session.add(attempt)
        session.commit()
        session.refresh(qt)
        return jsonify(_question_time_dict(qt)), 200


@progress_bp.route("/api/attempts/<string:attempt_id>/complete", methods=["POST"])
@supabase_auth_required()
def complete_attempt(attempt_id):
    user_id = str(get_current_user_id())
    data = request.get_json(silent=True) or {}
    with get_session() as session:
        attempt = session.get(PaperAttemptDB, attempt_id)
        if not attempt:
            return _error("Attempt not found", 404)
        if attempt.user_id != user_id:
            return _error("Forbidden", 403)

        now = datetime.now(UTC)
        if "elapsed_seconds" in data:
            attempt.elapsed_seconds = max(
                attempt.elapsed_seconds, int(data["elapsed_seconds"] or 0)
            )
        if "questions_answered" in data:
            attempt.questions_answered = max(
                attempt.questions_answered, int(data["questions_answered"] or 0)
            )
        if "reveal_count" in data:
            attempt.reveal_count = max(
                attempt.reveal_count, int(data["reveal_count"] or 0)
            )
        if "max_slide" in data:
            attempt.max_slide = max(attempt.max_slide, int(data["max_slide"] or 0))
        if "questions_seen" in data:
            attempt.questions_seen = max(
                attempt.questions_seen, int(data["questions_seen"] or 0)
            )

        for qt_data in data.get("question_times", []) or []:
            qid = (qt_data.get("question_id") or "").strip()
            if not qid:
                continue
            _upsert_question_time(
                session,
                attempt,
                question_id=qid,
                part_path=qt_data.get("part_path"),
                seconds=int(qt_data.get("seconds", 0) or 0),
                revealed_answer=bool(qt_data.get("revealed_answer", False)),
                reveal_count=int(qt_data.get("reveal_count", 0) or 0),
                views=int(qt_data.get("views", 0) or 0),
            )

        attempt.completed = True
        attempt.completed_at = now
        attempt.last_active_at = now

        session.add(attempt)
        session.commit()
        session.refresh(attempt)
        meta = _paper_meta_map(session, [attempt.paper_id]).get(attempt.paper_id)
        return jsonify(_attempt_detail_dict(attempt, meta)), 200


@progress_bp.route("/api/attempts/<string:attempt_id>", methods=["DELETE"])
@supabase_auth_required()
def delete_attempt(attempt_id):
    user_id = str(get_current_user_id())
    with get_session() as session:
        attempt = session.get(PaperAttemptDB, attempt_id)
        if not attempt:
            return _error("Attempt not found", 404)
        if attempt.user_id != user_id:
            return _error("Forbidden", 403)
        session.delete(attempt)
        session.commit()
        return jsonify({"message": "Deleted"}), 200


@progress_bp.route("/api/attempts/stats", methods=["GET"])
@supabase_auth_required()
def my_attempt_stats():
    """Lightweight student stats for the current user (no user profile join)."""
    user_id = str(get_current_user_id())
    with get_session() as session:
        return jsonify(compute_student_stats(session, user_id)), 200
