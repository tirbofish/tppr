from flask import Blueprint, current_app, jsonify, request
from settings import SHOW_ERROR_CAUSES, SUPABASE_QUESTION_ASSET_BUCKET
from auth.supabase import get_current_user_id, supabase_auth_required
from storage import delete_object, storage_configured

from .avatar_storage import (
    ALLOWED_AVATAR_MIME,
    MAX_AVATAR_BYTES,
    delete_avatar,
    store_avatar,
)
from .db import AuthenticationDB
from .supabase_admin import delete_supabase_auth_user

management_bp = Blueprint("tppr-account-management", __name__)
db = AuthenticationDB()


def error_body(message: str, error: Exception | None = None) -> dict[str, str]:
    body = {"message": message}
    if error is not None and SHOW_ERROR_CAUSES:
        body["cause"] = str(error)
    return body


def delete_authored_question_assets(user_id: str) -> None:
    if not storage_configured():
        return
    for path in db.list_authored_asset_paths(user_id):
        delete_object(SUPABASE_QUESTION_ASSET_BUCKET, path)


@management_bp.route("/api/whotf", methods=["GET"])
def whotfisthis():
    """Get a username by user_id. 
    
    `Who The F*** Is This`
    """
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"message": "user_id is required"}), 400

    user = db.get_user_by_id(user_id, fields=["user_id", "username", "avatar_url"])
    if not user:
        return jsonify({"message": "User not found"}), 404

    return (
        jsonify(
            {
                "user_id": user["user_id"],
                "username": user["username"],
                "avatar_url": user.get("avatar_url"),
            }
        ),
        200,
    )

@management_bp.route("/api/account/username", methods=["PUT"])
@supabase_auth_required(sync_user=True)
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
@supabase_auth_required(sync_user=True)
def update_password():
    """Password changes are handled by Supabase Auth."""
    return jsonify({"message": "Password changes are handled by Supabase Auth"}), 410


@management_bp.route("/api/account", methods=["DELETE"])
@supabase_auth_required(sync_user=True)
def delete_account():
    """Delete the authenticated user's account."""
    user_id = get_current_user_id()

    try:
        existing_row = db.get_user_by_id(user_id, fields=["avatar_url"])
        if not existing_row:
            return jsonify({"message": "User not found"}), 404

        delete_avatar(user_id, existing_row.get("avatar_url"))
        delete_authored_question_assets(user_id)
        delete_supabase_auth_user(user_id)
        deleted = db.delete_user(user_id)
        if not deleted:
            return jsonify({"message": "User not found"}), 404

        return jsonify({"message": "Account deleted"}), 200
    except Exception as e:
        current_app.logger.error(f"Error deleting account: {e}")
        return jsonify(error_body("Failed to delete account", e)), 500


@management_bp.route("/api/account/data", methods=["DELETE"])
@supabase_auth_required(sync_user=True)
def reset_account_data():
    """Delete the authenticated user's app data without deleting the account."""
    user_id = get_current_user_id()

    try:
        delete_authored_question_assets(user_id)
        reset = db.reset_user_data(user_id)
        if not reset:
            return jsonify({"message": "User not found"}), 404
        return jsonify({"message": "Account data reset"}), 200
    except Exception as e:
        current_app.logger.error(f"Error resetting account data: {e}")
        return jsonify(error_body("Failed to reset account data", e)), 500


@management_bp.route("/api/account/avatar", methods=["PUT"])
@supabase_auth_required(sync_user=True)
def update_avatar():
    """Upload (or replace) the authenticated user's avatar image."""
    user_id = get_current_user_id()

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"message": "file is required"}), 400

    mime = (file.mimetype or "").lower()
    if mime not in ALLOWED_AVATAR_MIME:
        return jsonify({"message": "Unsupported image type"}), 400

    data = file.read()
    if len(data) == 0:
        return jsonify({"message": "Empty file"}), 400
    if len(data) > MAX_AVATAR_BYTES:
        return jsonify({"message": "Image is too large (max 1 MB)"}), 400

    try:
        # Remove any previously-stored avatar object before storing the new one.
        existing_row = db.get_user_by_id(user_id, fields=["avatar_url"])
        if existing_row:
            delete_avatar(user_id, existing_row.get("avatar_url"))

        avatar_url = store_avatar(user_id, mime, data)
        db.update_avatar_url(user_id, avatar_url)
        return jsonify({"avatar_url": avatar_url}), 200
    except Exception as e:
        current_app.logger.error(f"Error updating avatar: {e}")
        return jsonify(error_body("Failed to update avatar", e)), 500


@management_bp.route("/api/account/avatar", methods=["DELETE"])
@supabase_auth_required(sync_user=True)
def delete_user_avatar():
    """Remove the authenticated user's avatar image."""
    user_id = get_current_user_id()

    try:
        existing_row = db.get_user_by_id(user_id, fields=["avatar_url"])
        if not existing_row:
            return jsonify({"message": "User not found"}), 404
        delete_avatar(user_id, existing_row.get("avatar_url"))
        db.update_avatar_url(user_id, None)
        return jsonify({"message": "Avatar removed"}), 200
    except Exception as e:
        current_app.logger.error(f"Error removing avatar: {e}")
        return jsonify(error_body("Failed to remove avatar", e)), 500
