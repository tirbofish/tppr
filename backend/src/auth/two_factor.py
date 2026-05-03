import io
import base64
import sqlite3
from shared import DB_PATH

import pyotp
import qrcode
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

two_fa_bp = Blueprint('tppr-account-2fa', __name__)


def get_db(row_factory=False):
    conn = sqlite3.connect(DB_PATH)
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn


@two_fa_bp.route('/api/verify_2fa', methods=['POST'])
def verify_2fa():
    data = request.form
    user_id = data.get("user_id")
    totp_code = data.get("totp_code")

    if not user_id or not totp_code:
        return jsonify({"message": "user_id and totp_code are required"}), 400

    conn = None
    try:
        conn = get_db(row_factory=True)
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, username, email, totp_secret, last_login FROM users WHERE user_id = ?",
            (user_id,)
        )
        user = cur.fetchone()

        if not user:
            return jsonify({"message": "User not found"}), 404

        if not user['totp_secret']:
            return jsonify({"message": "2FA is not enabled for this account"}), 400

        totp = pyotp.TOTP(user['totp_secret'])
        if not totp.verify(totp_code, valid_window=1):
            return jsonify({"message": "Invalid 2FA code"}), 401

        cur.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()

        access_token = create_access_token(
            identity=str(user['user_id']),
            additional_claims={
                'email': user['email'], 'username': user['username']}
        )

        response = jsonify({
            "message": "2FA verified!",
            "user": {
                "user_id": user['user_id'],
                "username": user['username'],
                "email": user['email']
            }
        })
        response.set_cookie(
            'access_token_cookie', access_token,
            httponly=True, secure=False, samesite='Lax', max_age=86400
        )
        return response, 200
    except Exception as e:
        current_app.logger.error(f"Error verifying 2FA: {e}")
        return jsonify({"message": "Error verifying 2FA", "cause": str(e)}), 500
    finally:
        if conn:
            conn.close()


@two_fa_bp.route('/api/account/enable_2fa', methods=['POST'])
@jwt_required()
def enable_2fa():
    user_id = get_jwt_identity()

    conn = None
    try:
        conn = get_db(row_factory=True)
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, email, totp_enabled FROM users WHERE user_id = ?", (user_id,))
        user = cur.fetchone()

        if not user:
            return jsonify({"message": "User not found"}), 404

        if user['totp_enabled']:
            return jsonify({"message": "2FA is already enabled"}), 400

        totp_secret = pyotp.random_base32()
        totp = pyotp.TOTP(totp_secret)
        provisioning_uri = totp.provisioning_uri(
            name=user['email'], issuer_name='TPPR')

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        qr_code_base64 = base64.b64encode(img_buffer.getvalue()).decode()

        cur.execute(
            "UPDATE users SET totp_secret = ?, totp_enabled = 1 WHERE user_id = ?",
            (totp_secret, user_id)
        )
        conn.commit()

        return jsonify({
            "message": "2FA enabled. Please verify with your authenticator app.",
            "totp_secret": totp_secret,
            "provisioning_uri": provisioning_uri,
            "qr_code": f"data:image/png;base64,{qr_code_base64}"
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error enabling 2FA: {e}")
        return jsonify({"message": "Failed to enable 2FA", "cause": str(e)}), 500
    finally:
        if conn:
            conn.close()


@two_fa_bp.route('/api/account/disable_2fa', methods=['POST'])
@jwt_required()
def disable_2fa():
    user_id = get_jwt_identity()
    totp_code = (request.form.get("totp_code") or "").strip()

    if not totp_code:
        return jsonify({"message": "totp_code is required"}), 400

    conn = None
    try:
        conn = get_db(row_factory=True)
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, totp_secret, totp_enabled FROM users WHERE user_id = ?", (user_id,))
        user = cur.fetchone()

        if not user:
            return jsonify({"message": "User not found"}), 404
        if not user['totp_enabled']:
            return jsonify({"message": "2FA is not enabled"}), 400

        totp = pyotp.TOTP(user['totp_secret'])
        if not totp.verify(totp_code, valid_window=1):
            return jsonify({"message": "Invalid 2FA code"}), 401

        cur.execute(
            "UPDATE users SET totp_secret = NULL, totp_enabled = 0 WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()
        return jsonify({"message": "2FA disabled"}), 200
    except Exception as e:
        current_app.logger.error(f"Error disabling 2FA: {e}")
        return jsonify({"message": "Failed to disable 2FA", "cause": str(e)}), 500
    finally:
        if conn:
            conn.close()
