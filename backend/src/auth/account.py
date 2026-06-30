from flask import Blueprint, current_app, jsonify
from settings import SHOW_ERROR_CAUSES
from auth.supabase import get_current_user_id, supabase_auth_required

from .db import AuthenticationDB

account_bp = Blueprint("tppr-account-authentication", __name__)
db = AuthenticationDB()


def error_body(message: str, error: Exception | None = None) -> dict[str, str]:
    body = {"message": message}
    if error is not None and SHOW_ERROR_CAUSES:
        body["cause"] = str(error)
    return body


@account_bp.route("/api/whoami", methods=["GET"])
@supabase_auth_required(sync_user=True)
def whoami():
    user_id = get_current_user_id()

    try:
        user = db.get_user_by_id(
            user_id,
            fields=["user_id", "username", "email", "totp_enabled", "avatar_url"],
        )

        if not user:
            return jsonify({"message": "User not found"}), 404

        from admin import has_admin_role, is_admin

        return (
            jsonify(
                {
                    "user_id": user["user_id"],
                    "username": user["username"],
                    "email": user["email"],
                    "totp_enabled": bool(user["totp_enabled"]),
                    "avatar_url": user.get("avatar_url"),
                    "admin": is_admin(user["user_id"]),
                    "admin_available": has_admin_role(user["user_id"]),
                }
            ),
            200,
        )
    except Exception as e:
        current_app.logger.error(f"Error in whoami: {e}")
        return jsonify({"message": "Error fetching user info"}), 500
