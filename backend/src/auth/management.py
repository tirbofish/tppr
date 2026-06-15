import bcrypt
import pyotp
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required, unset_jwt_cookies
from settings import SHOW_ERROR_CAUSES
from shared import BLOCKLIST

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
@jwt_required()
def update_username():
    """Update the authenticated user's username."""
    user_id = get_jwt_identity()
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
@jwt_required()
def update_password():
    """Update password. Requires current_password and new_password. Also requires totp_code if 2FA is enabled."""
    user_id = get_jwt_identity()
    data = request.form
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    totp_code = (data.get("totp_code") or "").strip()

    if not current_password or not new_password:
        return jsonify(
            {"message": "current_password and new_password are required"}
        ), 400

    try:
        user = db.get_user_by_id(
            user_id, fields=["user_id", "password_hash", "totp_secret", "totp_enabled"]
        )

        if not user:
            return jsonify({"message": "User not found"}), 404

        if user["totp_enabled"]:
            if not totp_code:
                return jsonify(
                    {"message": "totp_code is required when 2FA is enabled"}
                ), 400
            totp = pyotp.TOTP(user["totp_secret"])
            if not totp.verify(totp_code, valid_window=1):
                return jsonify({"message": "Invalid 2FA code"}), 401

        if not bcrypt.checkpw(
            current_password.encode(), user["password_hash"].encode()
        ):
            return jsonify({"message": "Current password is incorrect"}), 401

        password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        db.update_password(user_id, password_hash)
        return jsonify({"message": "Password updated"}), 200
    except Exception as e:
        current_app.logger.error(f"Error updating password: {e}")
        return jsonify(error_body("Failed to update password", e)), 500


@management_bp.route("/api/account", methods=["DELETE"])
@jwt_required()
def delete_account():
    """Delete the authenticated user's account."""
    user_id = get_jwt_identity()

    try:
        deleted = db.delete_user(user_id)
        if not deleted:
            return jsonify({"message": "User not found"}), 404

        try:
            jti = get_jwt().get("jti")
            if jti:
                BLOCKLIST.add(jti)
        except RuntimeError as e:
            current_app.logger.warning(f"delete_account: unable to blocklist JWT: {e}")

        response = jsonify({"message": "Account deleted"})
        unset_jwt_cookies(response)
        return response, 200
    except Exception as e:
        current_app.logger.error(f"Error deleting account: {e}")
        return jsonify(error_body("Failed to delete account", e)), 500
