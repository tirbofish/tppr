from flask import Blueprint, current_app, jsonify, request
from settings import SHOW_ERROR_CAUSES
from auth.supabase import get_current_user_id, supabase_auth_required

from .db import AuthenticationDB

management_bp = Blueprint("tppr-account-management", __name__)
db = AuthenticationDB()


def error_body(message: str, error: Exception | None = None) -> dict[str, str]:
    body = {"message": message}
    if error is not None and SHOW_ERROR_CAUSES:
        body["cause"] = str(error)
    return body


@management_bp.route("/api/whotf", methods=["GET"])
def whotfisthis():
    """Get a username by user_id. 
    
    `Who The F*** Is This`
    """
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"message": "user_id is required"}), 400

    user = db.get_user_by_id(user_id, fields=["user_id", "username"])
    if not user:
        return jsonify({"message": "User not found"}), 404

    return jsonify({"user_id": user["user_id"], "username": user["username"]}), 200

@management_bp.route("/api/account/username", methods=["PUT"])
@supabase_auth_required()
def update_username():
    """Update the authenticated user's username."""
    user_id = get_current_user_id()
    new_username = (request.form.get("username") or "").strip()

    if not new_username:
        return jsonify({"message": "username is required"}), 400

    try:
        user = db.get_user_by_id(user_id, fields=["user_id"])
        if not user:
            return jsonify({"message": "User not found"}), 404

        if db.is_username_taken(new_username, exclude_user_id=user_id):
            return jsonify({"message": "Username already in use"}), 400

        db.update_username(user_id, new_username)
        return jsonify({"message": "Username updated", "username": new_username}), 200
    except Exception as e:
        current_app.logger.error(f"Error updating username: {e}")
        return jsonify(error_body("Failed to update username", e)), 500


@management_bp.route("/api/account/password", methods=["PUT"])
@supabase_auth_required()
def update_password():
    """Password changes are handled by Supabase Auth."""
    return jsonify({"message": "Password changes are handled by Supabase Auth"}), 410


@management_bp.route("/api/account", methods=["DELETE"])
@supabase_auth_required()
def delete_account():
    """Delete the authenticated user's account."""
    user_id = get_current_user_id()

    try:
        deleted = db.delete_user(user_id)
        if not deleted:
            return jsonify({"message": "User not found"}), 404

        return jsonify({"message": "Local account deleted"}), 200
    except Exception as e:
        current_app.logger.error(f"Error deleting account: {e}")
        return jsonify(error_body("Failed to delete account", e)), 500
