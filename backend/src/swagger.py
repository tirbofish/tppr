from flask import Blueprint, jsonify
from flask_swagger_ui import get_swaggerui_blueprint

swagger_bp = Blueprint("swagger", __name__)
SWAGGER_URL = "/api/docs"
API_URL = "/swagger.json"


def form_request_body(fields, required=None):
    required = required or []
    return {
        "required": True,
        "content": {
            "application/x-www-form-urlencoded": {
                "schema": {
                    "type": "object",
                    "properties": fields,
                    "required": required,
                }
            }
        },
    }


@swagger_bp.route(API_URL)
def swagger_json():
    return jsonify(
        {
            "openapi": "3.0.3",
            "info": {
                "title": "tppr-backend",
                "version": "0.1.0",
                "description": "Backend API for Thribhu's Past Paper Repository.",
            },
            "servers": [{"url": "/"}],
            "components": {
                "securitySchemes": {
                    "cookieAuth": {
                        "type": "apiKey",
                        "in": "cookie",
                        "name": "access_token_cookie",
                    }
                },
                "schemas": {
                    "Message": {
                        "type": "object",
                        "properties": {"message": {"type": "string"}},
                    },
                },
            },
            "paths": {
                "/ping": {
                    "get": {
                        "summary": "Health check",
                        "responses": {
                            "200": {
                                "description": "Backend is running",
                                "content": {
                                    "application/json": {"schema": {"type": "string"}}
                                },
                            }
                        },
                    }
                },
                "/api/register": {
                    "post": {
                        "summary": "Register a user",
                        "requestBody": form_request_body(
                            {
                                "email": {"type": "string", "format": "email"},
                                "username": {"type": "string"},
                                "password": {"type": "string", "format": "password"},
                                "enable_2fa": {
                                    "type": "boolean",
                                    "default": False,
                                },
                            },
                            ["email", "username", "password"],
                        ),
                        "responses": {
                            "201": {"description": "User created"},
                            "400": {"description": "Invalid registration details"},
                            "500": {"description": "Database error"},
                        },
                    }
                },
                "/api/login": {
                    "post": {
                        "summary": "Log in",
                        "requestBody": form_request_body(
                            {
                                "email": {"type": "string"},
                                "password": {"type": "string", "format": "password"},
                            },
                            ["email", "password"],
                        ),
                        "responses": {
                            "200": {"description": "Login successful"},
                            "400": {"description": "Missing credentials"},
                            "401": {"description": "Invalid credentials"},
                            "500": {"description": "Login error"},
                        },
                    }
                },
                "/api/logout": {
                    "post": {
                        "summary": "Log out",
                        "security": [{"cookieAuth": []}],
                        "responses": {
                            "200": {"description": "Logout successful"},
                            "401": {"description": "Missing or invalid JWT"},
                        },
                    }
                },
                "/api/whoami": {
                    "get": {
                        "summary": "Get the authenticated user",
                        "security": [{"cookieAuth": []}],
                        "responses": {
                            "200": {"description": "Authenticated user details"},
                            "401": {"description": "Missing or invalid JWT"},
                            "404": {"description": "User not found"},
                            "500": {"description": "Failed to fetch user"},
                        },
                    }
                },
                "/api/verify_2fa": {
                    "post": {
                        "summary": "Verify a two-factor authentication code",
                        "requestBody": form_request_body(
                            {
                                "user_id": {"type": "integer"},
                                "totp_code": {"type": "string"},
                            },
                            ["user_id", "totp_code"],
                        ),
                        "responses": {
                            "200": {"description": "2FA verified"},
                            "400": {"description": "Invalid 2FA request"},
                            "401": {"description": "Invalid 2FA code"},
                            "404": {"description": "User not found"},
                            "500": {"description": "2FA verification error"},
                        },
                    }
                },
                "/api/account/username": {
                    "put": {
                        "summary": "Update username",
                        "security": [{"cookieAuth": []}],
                        "requestBody": form_request_body(
                            {"username": {"type": "string"}},
                            ["username"],
                        ),
                        "responses": {
                            "200": {"description": "Username updated"},
                            "400": {"description": "Invalid or duplicate username"},
                            "401": {"description": "Missing or invalid JWT"},
                            "404": {"description": "User not found"},
                            "500": {"description": "Failed to update username"},
                        },
                    }
                },
                "/api/account/password": {
                    "put": {
                        "summary": "Update password",
                        "security": [{"cookieAuth": []}],
                        "requestBody": form_request_body(
                            {
                                "current_password": {
                                    "type": "string",
                                    "format": "password",
                                },
                                "new_password": {
                                    "type": "string",
                                    "format": "password",
                                },
                                "totp_code": {"type": "string"},
                            },
                            ["current_password", "new_password"],
                        ),
                        "responses": {
                            "200": {"description": "Password updated"},
                            "400": {"description": "Missing password details"},
                            "401": {"description": "Invalid password, 2FA, or JWT"},
                            "404": {"description": "User not found"},
                            "500": {"description": "Failed to update password"},
                        },
                    }
                },
                "/api/account": {
                    "delete": {
                        "summary": "Delete account",
                        "security": [{"cookieAuth": []}],
                        "responses": {
                            "200": {"description": "Account deleted"},
                            "401": {"description": "Missing or invalid JWT"},
                            "404": {"description": "User not found"},
                            "500": {"description": "Failed to delete account"},
                        },
                    }
                },
                "/api/account/enable_2fa": {
                    "post": {
                        "summary": "Enable two-factor authentication",
                        "security": [{"cookieAuth": []}],
                        "responses": {
                            "200": {"description": "2FA setup details generated"},
                            "400": {"description": "2FA is already enabled"},
                            "401": {"description": "Missing or invalid JWT"},
                            "404": {"description": "User not found"},
                            "500": {"description": "Failed to enable 2FA"},
                        },
                    }
                },
                "/api/account/disable_2fa": {
                    "post": {
                        "summary": "Disable two-factor authentication",
                        "security": [{"cookieAuth": []}],
                        "requestBody": form_request_body(
                            {"totp_code": {"type": "string"}},
                            ["totp_code"],
                        ),
                        "responses": {
                            "200": {"description": "2FA disabled"},
                            "400": {"description": "Missing 2FA code or 2FA disabled"},
                            "401": {"description": "Invalid 2FA code or JWT"},
                            "404": {"description": "User not found"},
                            "500": {"description": "Failed to disable 2FA"},
                        },
                    }
                },
            },
        }
    )


def register_blueprint(app):
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={"app_name": "tppr-api"},
    )
    app.register_blueprint(swagger_bp)
    app.register_blueprint(swaggerui_blueprint)
