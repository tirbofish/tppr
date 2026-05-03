import sqlite3
from shared import DB_PATH, BLOCKLIST

import bcrypt
import pyotp
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

management_bp = Blueprint('tppr-account-management', __name__)


def get_db(row_factory=False):
    conn = sqlite3.connect(DB_PATH)
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn


@management_bp.route('/api/account/username', methods=['PUT'])
@jwt_required()
def update_username():
    """Update the authenticated user's username."""
    user_id = get_jwt_identity()
    new_username = (request.form.get("username") or "").strip()

    if not new_username:
        return jsonify({"message": "username is required"}), 400

    conn = None
    try:
        conn = get_db(row_factory=True)
        cur = conn.cursor()

        cur.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not cur.fetchone():
            return jsonify({"message": "User not found"}), 404

        cur.execute(
            "SELECT user_id FROM users WHERE username = ? AND user_id != ?",
            (new_username, user_id)
        )
        if cur.fetchone():
            return jsonify({"message": "Username already in use"}), 400

        cur.execute("UPDATE users SET username = ? WHERE user_id = ?",
                    (new_username, user_id))
        conn.commit()
        return jsonify({"message": "Username updated", "username": new_username}), 200
    except Exception as e:
        current_app.logger.error(f"Error updating username: {e}")
        return jsonify({"message": "Failed to update username", "cause": str(e)}), 500
    finally:
        if conn:
            conn.close()


@management_bp.route('/api/account/password', methods=['PUT'])
@jwt_required()
def update_password():
    """Update password. Requires current_password and new_password. Also requires totp_code if 2FA is enabled."""
    user_id = get_jwt_identity()
    data = request.form
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    totp_code = (data.get("totp_code") or "").strip()

    if not current_password or not new_password:
        return jsonify({"message": "current_password and new_password are required"}), 400

    conn = None
    try:
        conn = get_db(row_factory=True)
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, password_hash, totp_secret, totp_enabled FROM users WHERE user_id = ?",
            (user_id,)
        )
        user = cur.fetchone()

        if not user:
            return jsonify({"message": "User not found"}), 404

        if user["totp_enabled"]:
            if not totp_code:
                return jsonify({"message": "totp_code is required when 2FA is enabled"}), 400
            totp = pyotp.TOTP(user["totp_secret"])
            if not totp.verify(totp_code, valid_window=1):
                return jsonify({"message": "Invalid 2FA code"}), 401

        if not bcrypt.checkpw(current_password.encode(), user["password_hash"].encode()):
            return jsonify({"message": "Current password is incorrect"}), 401

        password_hash = bcrypt.hashpw(
            new_password.encode(), bcrypt.gensalt()).decode()
        cur.execute(
            "UPDATE users SET password_hash = ? WHERE user_id = ?", (password_hash, user_id))
        conn.commit()
        return jsonify({"message": "Password updated"}), 200
    except Exception as e:
        current_app.logger.error(f"Error updating password: {e}")
        return jsonify({"message": "Failed to update password", "cause": str(e)}), 500
    finally:
        if conn:
            conn.close()


@management_bp.route('/api/account', methods=['DELETE'])
@jwt_required()
def delete_account():
    """Delete the authenticated user's account."""
    user_id = get_jwt_identity()

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        if cur.rowcount == 0:
            return jsonify({"message": "User not found"}), 404
        conn.commit()

        try:
            jti = get_jwt().get("jti")
            if jti:
                BLOCKLIST.add(jti)
        except RuntimeError as e:
            current_app.logger.warning(
                f"delete_account: unable to blocklist JWT: {e}")

        response = jsonify({"message": "Account deleted"})
        response.delete_cookie('access_token_cookie')
        return response, 200
    except Exception as e:
        current_app.logger.error(f"Error deleting account: {e}")
        return jsonify({"message": "Failed to delete account", "cause": str(e)}), 500
    finally:
        if conn:
            conn.close()
