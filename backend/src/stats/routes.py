from flask import Blueprint, jsonify
from sqlmodel import col, select

from auth.db import AuthenticationDB, UserDB
from auth.supabase import get_current_user_id, supabase_auth_required
from progress.aggregations import compute_many_students, ZERO_STUDENT_STATS
from progress.models import PaperAttemptDB
from progress.routes import _attempt_dict, _paper_meta_map
from questions.db import get_session

stats_bp = Blueprint("tppr-stats", __name__)
auth_db = AuthenticationDB()

RECENT_ATTEMPTS_LIMIT = 6


def _is_admin(user_id: str) -> bool:
    """Local import avoids a circular import with the admin module."""
    from admin import is_admin

    return is_admin(user_id)


def _student_payload(user: UserDB, stats: dict) -> dict:
    return {
        "user_id": user.user_id,
        "username": user.username,
        "avatar_url": user.avatar_url,
        "joined_at": user.created_at.isoformat() if user.created_at else None,
        "attempts_count": stats.get("attempts_count", 0),
        "papers_attempted": stats.get("papers_attempted", 0),
        "papers_completed": stats.get("papers_completed", 0),
        "questions_answered": stats.get("questions_answered", 0),
        "total_study_seconds": stats.get("total_study_seconds", 0),
        "reveal_count": stats.get("reveal_count", 0),
        "current_streak": stats.get("current_streak", 0),
        "longest_streak": stats.get("longest_streak", 0),
        "last_active_at": stats.get("last_active_at"),
    }


@stats_bp.route("/api/stats/me", methods=["GET"])
@supabase_auth_required(sync_user=True)
def my_stats():
    user_id = get_current_user_id()

    with get_session() as session:
        user = session.get(UserDB, user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404

        stats = compute_many_students(session, [user_id]).get(
            user_id, dict(ZERO_STUDENT_STATS)
        )

        recent = session.exec(
            select(PaperAttemptDB)
            .where(PaperAttemptDB.user_id == str(user_id))
            .order_by(col(PaperAttemptDB.started_at).desc())
            .limit(RECENT_ATTEMPTS_LIMIT)
        ).all()
        meta_map = _paper_meta_map(session, [a.paper_id for a in recent])
        recent_attempts = [_attempt_dict(a, meta_map.get(a.paper_id)) for a in recent]

        payload = _student_payload(user, stats)
        payload["recent_attempts"] = recent_attempts
        return jsonify(payload), 200


@stats_bp.route("/api/stats/users", methods=["GET"])
@supabase_auth_required()
def all_user_stats():
    user_id = get_current_user_id()
    if not _is_admin(user_id):
        return jsonify({"message": "Forbidden"}), 403

    with get_session() as session:
        users = list(session.exec(select(UserDB)).all())
        stats = compute_many_students(session, [u.user_id for u in users])

        rows = [_student_payload(u, stats.get(u.user_id, dict(ZERO_STUDENT_STATS))) for u in users]

    rows.sort(
        key=lambda r: (
            -r["papers_completed"],
            -r["total_study_seconds"],
            -r["questions_answered"],
            r["username"],
        )
    )
    return jsonify({"users": rows}), 200
