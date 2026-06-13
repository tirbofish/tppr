import base64
import io
import sqlite3

import bcrypt
import pyotp
import qrcode
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from shared import BLOCKLIST

from .db import AuthenticationDB

account_bp = Blueprint("tppr-account-authentication", __name__)
db = AuthenticationDB()


@account_bp.route("/api/register", methods=["POST"])
def register():
    data = request.form
    email = data.get("email")
    password = data.get("password")
    username = data.get("username")
    enable_2fa = data.get("enable_2fa", "false").lower() == "true"

    if not email or not password or not username:
        return jsonify({"message": "Email, username, and password are required"}), 400

    try:
        if db.user_exists(email, username):
            return jsonify(
                {"message": "User with this email or username already exists"}
            ), 400
    except Exception as e:
        current_app.logger.error(f"Error checking existing user: {e}")
        return jsonify({"message": "Database error", "cause": str(e)}), 500

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    totp_secret = None
    qr_code_base64 = None
    provisioning_uri = None

    if enable_2fa:
        totp_secret = pyotp.random_base32()
        totp = pyotp.TOTP(totp_secret)
        provisioning_uri = totp.provisioning_uri(name=email, issuer_name="TPPR")

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        qr_code_base64 = base64.b64encode(img_buffer.getvalue()).decode()

    try:
        user_id = db.create_user(
            username=username,
            email=email,
            password_hash=password_hash,
            totp_secret=totp_secret,
            totp_enabled=enable_2fa,
        )

        if enable_2fa:
            return jsonify(
                {
                    "message": "User created. Please verify 2FA.",
                    "user_id": user_id,
                    "requires_2fa": True,
                    "totp_secret": totp_secret,
                    "provisioning_uri": provisioning_uri,
                    "qr_code": f"data:image/png;base64,{qr_code_base64}",
                }
            ), 201
        else:
            access_token = create_access_token(
                identity=str(user_id),
                additional_claims={"email": email, "username": username},
            )
            response = jsonify(
                {
                    "message": "User created.",
                    "user_id": user_id,
                    "requires_2fa": False,
                    "user": {"user_id": user_id, "username": username, "email": email},
                }
            )
            response.status_code = 201
            response.set_cookie(
                "access_token_cookie",
                access_token,
                httponly=True,
                secure=False,
                samesite="Lax",
                max_age=86400,
            )
            return response

    except sqlite3.IntegrityError:
        return jsonify({"message": "User already exists"}), 400
    except Exception as e:
        current_app.logger.error(f"Error while creating user: {e}")
        return jsonify({"message": "Error while creating user", "cause": str(e)}), 400


@account_bp.route("/api/login", methods=["POST"])
def login():
    data = request.form
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email or username, and password required"}), 400

    try:
        user = db.get_user_by_email_or_username(email)
    except Exception as e:
        current_app.logger.error(f"Error while attempting to login: {e}")
        return jsonify(
            {"message": "Error while attempting to login", "cause": str(e)}
        ), 500

    if not user or not bcrypt.checkpw(
        password.encode(), user["password_hash"].encode()
    ):
        return jsonify({"message": "Invalid credentials"}), 401

    token = create_access_token(
        identity=str(user["user_id"]),
        additional_claims={"email": user["email"], "username": user["username"]},
    )
    response = jsonify(
        {
            "message": "Login successful",
            "requires_2fa": False,
            "user": {
                "user_id": user["user_id"],
                "username": user["username"],
                "email": user["email"],
            },
        }
    )
    response.set_cookie(
        "access_token_cookie",
        token,
        httponly=True,
        secure=False,
        samesite="Lax",
        max_age=86400,
    )
    return response, 200


@account_bp.route("/api/whoami", methods=["GET"])
@jwt_required()
def whoami():
    user_id = get_jwt_identity()

    try:
        user = db.get_user_by_id(
            user_id, fields=["user_id", "username", "email", "totp_enabled"]
        )

        if not user:
            return jsonify({"message": "User not found"}), 404

        return jsonify(
            {
                "user_id": user["user_id"],
                "username": user["username"],
                "email": user["email"],
                "totp_enabled": bool(user["totp_enabled"]),
            }
        ), 200
    except Exception as e:
        current_app.logger.error(f"Error in whoami: {e}")
        return jsonify({"message": "Error fetching user info"}), 500


@account_bp.route("/api/logout", methods=["POST"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    BLOCKLIST.add(jti)
    response = jsonify({"message": "Logout successful"})
    response.delete_cookie("access_token_cookie")
    return response, 200
