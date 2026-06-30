import base64
import io

import pyotp
import qrcode
from flask import Blueprint, current_app, jsonify, request
from settings import SHOW_ERROR_CAUSES
from auth.supabase import get_current_user_id, supabase_auth_required

from .db import AuthenticationDB

two_fa_bp = Blueprint("tppr-account-2fa", __name__)
db = AuthenticationDB()


def error_body(message: str, error: Exception | None = None) -> dict[str, str]:
    body = {"message": message}
    if error is not None and SHOW_ERROR_CAUSES:
        body["cause"] = str(error)
    return body


@two_fa_bp.route("/api/verify_2fa", methods=["POST"])
def verify_2fa():
    return jsonify({"message": "2FA login is handled by Supabase Auth"}), 410


@two_fa_bp.route("/api/account/enable_2fa", methods=["POST"])
@supabase_auth_required(sync_user=True)
def enable_2fa():
    user_id = get_current_user_id()

    try:
        user = db.get_user_by_id(user_id, fields=["user_id", "email", "totp_enabled"])

        if not user:
            return jsonify({"message": "User not found"}), 404

        if user["totp_enabled"]:
            return jsonify({"message": "2FA is already enabled"}), 400

        totp_secret = pyotp.random_base32()
        totp = pyotp.TOTP(totp_secret)
        provisioning_uri = totp.provisioning_uri(name=user["email"], issuer_name="TPPR")

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        qr_code_base64 = base64.b64encode(img_buffer.getvalue()).decode()

        db.enable_totp(user_id, totp_secret)

        return jsonify(
            {
                "message": "2FA enabled. Please verify with your authenticator app.",
                "totp_secret": totp_secret,
                "provisioning_uri": provisioning_uri,
                "qr_code": f"data:image/png;base64,{qr_code_base64}",
            }
        ), 200
    except Exception as e:
        current_app.logger.error(f"Error enabling 2FA: {e}")
        return jsonify(error_body("Failed to enable 2FA", e)), 500


@two_fa_bp.route("/api/account/disable_2fa", methods=["POST"])
@supabase_auth_required(sync_user=True)
def disable_2fa():
    user_id = get_current_user_id()
    totp_code = (request.form.get("totp_code") or "").strip()

    if not totp_code:
        return jsonify({"message": "totp_code is required"}), 400

    try:
        user = db.get_user_by_id(
            user_id, fields=["user_id", "totp_secret", "totp_enabled"]
        )

        if not user:
            return jsonify({"message": "User not found"}), 404
        if not user["totp_enabled"]:
            return jsonify({"message": "2FA is not enabled"}), 400

        totp = pyotp.TOTP(user["totp_secret"])
        if not totp.verify(totp_code, valid_window=1):
            return jsonify({"message": "Invalid 2FA code"}), 401

        db.disable_totp(user_id)
        return jsonify({"message": "2FA disabled"}), 200
    except Exception as e:
        current_app.logger.error(f"Error disabling 2FA: {e}")
        return jsonify(error_body("Failed to disable 2FA", e)), 500
