from flask import Blueprint, jsonify, request

from auth.db import AuthenticationDB, UserDB
from auth.supabase import get_current_user_id, supabase_auth_required
from questions.db import get_session
from sqlmodel import select

from .aggregations import compute_many
from .db import SocialDB
from .models import FriendshipDB  # noqa: F401 (ensures table registered)

social_bp = Blueprint("tppr-social", __name__)
auth_db = AuthenticationDB()
social_db = SocialDB()

LEADERBOARD_LIMIT = 100


def _error(message: str, status: int):
    return jsonify({"message": message}), status


@social_bp.route("/api/friends/requests", methods=["POST"])
@supabase_auth_required()
def send_friend_request():
    user_id = get_current_user_id()
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()

    if not username:
        return _error("username is required", 400)

    target = auth_db.get_user_by_username(username)
    if not target:
        return _error("No user with that username", 404)

    ok, message = social_db.send_request(user_id, target["user_id"])
    if not ok:
        return _error(message, 400)
    return jsonify({"message": message}), 201


@social_bp.route("/api/friends/requests/incoming", methods=["GET"])
@supabase_auth_required()
def list_incoming_requests():
    user_id = get_current_user_id()
    return jsonify({"requests": social_db.list_incoming(user_id)}), 200


@social_bp.route("/api/friends/requests/outgoing", methods=["GET"])
@supabase_auth_required()
def list_outgoing_requests():
    user_id = get_current_user_id()
    return jsonify({"requests": social_db.list_outgoing(user_id)}), 200


@social_bp.route("/api/friends/requests/<int:friendship_id>/accept", methods=["POST"])
@supabase_auth_required()
def accept_friend_request(friendship_id):
    user_id = get_current_user_id()
    ok, message = social_db.accept_request(friendship_id, user_id)
    if not ok:
        return _error(message, 400)
    return jsonify({"message": message}), 200


@social_bp.route("/api/friends/requests/<int:friendship_id>/decline", methods=["POST"])
@supabase_auth_required()
def decline_friend_request(friendship_id):
    user_id = get_current_user_id()
    ok, message = social_db.decline_request(friendship_id, user_id)
    if not ok:
        return _error(message, 400)
    return jsonify({"message": message}), 200


@social_bp.route("/api/friends/requests/<int:friendship_id>", methods=["DELETE"])
@supabase_auth_required()
def cancel_friend_request(friendship_id):
    user_id = get_current_user_id()
    ok, message = social_db.cancel_outgoing(friendship_id, user_id)
    if not ok:
        return _error(message, 400)
    return jsonify({"message": message}), 200


@social_bp.route("/api/friends", methods=["GET"])
@supabase_auth_required()
def list_friends():
    user_id = get_current_user_id()
    return jsonify({"friends": social_db.list_friends(user_id)}), 200


@social_bp.route("/api/friends/<string:other_id>", methods=["DELETE"])
@supabase_auth_required()
def remove_friend(other_id):
    user_id = get_current_user_id()
    ok, message = social_db.remove_friend(user_id, other_id)
    if not ok:
        return _error(message, 400)
    return jsonify({"message": message}), 200


def _leaderboard_entries(session, users: list[UserDB]) -> list[dict]:
    if not users:
        return []

    stats = compute_many(session, [u.user_id for u in users])

    entries = []
    for u in users:
        s = stats.get(u.user_id, {})
        entries.append(
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

    entries.sort(
        key=lambda e: (-e["total_marks"], -e["question_count"], e["username"])
    )
    for i, entry in enumerate(entries, start=1):
        entry["rank"] = i
    return entries[:LEADERBOARD_LIMIT]


@social_bp.route("/api/leaderboard", methods=["GET"])
@supabase_auth_required(optional=True)
def leaderboard():
    scope = (request.args.get("scope") or "").strip().lower()
    user_id = get_current_user_id()

    with get_session() as session:
        if scope == "friends":
            if not user_id:
                return _error("Sign in to view the friends leaderboard", 401)
            ids = social_db.list_friend_user_ids(user_id)
            ids.append(user_id)  # include the caller
            users = list(
                session.exec(
                    select(UserDB).where(UserDB.user_id.in_(ids))
                ).all()
            )
        else:
            users = list(session.exec(select(UserDB)).all())

        entries = _leaderboard_entries(session, users)

    return jsonify({"entries": entries}), 200