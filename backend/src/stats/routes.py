from flask import Blueprint, jsonify

from auth.db import AuthenticationDB, UserDB
from auth.supabase import get_current_user_id, supabase_auth_required
from questions.db import get_session
from sqlmodel import select

from social.aggregations import compute_many

stats_bp = Blueprint("tppr-stats", __name__)
auth_db = AuthenticationDB()


def _is_admin(user_id: str) -> bool:
    """Local import avoids a circular import with the admin module."""
    from admin import is_admin

    return is_admin(user_id)


@stats_bp.route("/api/stats/me", methods=["GET"])
@supabase_auth_required()
def my_stats():
    user_id = get_current_user_id()

    with get_session() as session:
        user = session.get(UserDB, user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404

        stats = compute_many(session, [user_id]).get(user_id, {})
        return (
            jsonify(
                {
                    "user_id": user.user_id,
                    "username": user.username,
                    "avatar_url": user.avatar_url,
                    "joined_at": user.created_at.isoformat()
                    if user.created_at
                    else None,
                    "paper_count": stats.get("paper_count", 0),
                    "public_paper_count": stats.get("public_paper_count", 0),
                    "question_count": stats.get("question_count", 0),
                    "total_marks": stats.get("total_marks", 0),
                    "remixes_received": stats.get("remixes_received", 0),
                }
            ),
            200,
        )


@stats_bp.route("/api/stats/users", methods=["GET"])
@supabase_auth_required()
def all_user_stats():
    user_id = get_current_user_id()
    if not _is_admin(user_id):
        return jsonify({"message": "Forbidden"}), 403

    with get_session() as session:
        users = session.exec(select(UserDB)).all()
        stats = compute_many(session, [u.user_id for u in users])

        rows = []
        for u in users:
            s = stats.get(u.user_id, {})
            rows.append(
                {
                    "user_id": u.user_id,
                    "username": u.username,
                    "avatar_url": u.avatar_url,
                    "paper_count": s.get("paper_count", 0),
                    "public_paper_count": s.get("public_paper_count", 0),
                    "question_count": s.get("question_count", 0),
                    "total_marks": s.get("total_marks", 0),
                    "remixes_received": s.get("remixes_received", 0),
                }
            )

    rows.sort(key=lambda r: (-r["total_marks"], -r["question_count"], r["username"]))
    return jsonify({"users": rows}), 200