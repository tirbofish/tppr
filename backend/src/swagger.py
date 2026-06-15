from flask import Blueprint, jsonify
from flask_swagger_ui import get_swaggerui_blueprint
from settings import PRODUCTION, PUBLIC_API_DOCS

swagger_bp = Blueprint("swagger", __name__)
SWAGGER_URL = "/api/docs"
API_URL = "/swagger.json"


def ref(schema_name):
    return {"$ref": f"#/components/schemas/{schema_name}"}


def array_of(schema_name):
    return {"type": "array", "items": ref(schema_name)}


def json_content(schema):
    return {"application/json": {"schema": schema}}


def json_request_body(schema, required=True, description=None):
    body = {
        "required": required,
        "content": json_content(schema),
    }
    if description:
        body["description"] = description
    return body


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


def response(description, schema=None):
    result = {"description": description}
    if schema is not None:
        result["content"] = json_content(schema)
    return result


def message_response(description):
    return response(description, ref("Message"))


def error_response(description):
    return response(description, ref("Error"))


def pagination_parameters():
    return [
        {
            "name": "q",
            "in": "query",
            "schema": {"type": "string"},
            "description": "Search term matched against paper title or subject.",
        },
        {
            "name": "subject",
            "in": "query",
            "schema": {"type": "string"},
        },
        {
            "name": "source",
            "in": "query",
            "schema": {"type": "string", "enum": ["hsc", "trial", "internal", "practice", "custom"]},
        },
        {
            "name": "course_level",
            "in": "query",
            "schema": {
                "type": "string",
                "enum": ["standard", "advanced", "extension_1", "extension_2"],
            },
        },
        {
            "name": "year",
            "in": "query",
            "schema": {"type": "integer"},
        },
        {
            "name": "page",
            "in": "query",
            "schema": {"type": "integer", "minimum": 1, "default": 1},
        },
        {
            "name": "per_page",
            "in": "query",
            "schema": {"type": "integer", "minimum": 1, "default": 20},
        },
    ]


def paper_id_parameter():
    return {
        "name": "paper_id",
        "in": "path",
        "required": True,
        "schema": {"type": "string"},
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
            "tags": [
                {"name": "System", "description": "Health checks and API metadata."},
                {"name": "Authentication", "description": "Registration, login, logout, and identity."},
                {"name": "Account", "description": "Account profile, password, and 2FA management."},
                {"name": "Papers", "description": "Past paper search, authoring, publishing, and remixing."},
            ],
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
                        "required": ["message"],
                    },
                    "Error": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"},
                            "cause": {"type": "string"},
                        },
                        "required": ["message"],
                    },
                    "User": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "integer"},
                            "username": {"type": "string"},
                            "email": {"type": "string", "format": "email"},
                        },
                        "required": ["user_id", "username", "email"],
                    },
                    "WhoAmI": {
                        "allOf": [
                            ref("User"),
                            {
                                "type": "object",
                                "properties": {"totp_enabled": {"type": "boolean"}},
                                "required": ["totp_enabled"],
                            },
                        ]
                    },
                    "AuthSuccess": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"},
                            "requires_2fa": {"type": "boolean"},
                            "user": ref("User"),
                        },
                        "required": ["message", "requires_2fa", "user"],
                    },
                    "RegisterTwoFactorRequired": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"},
                            "user_id": {"type": "integer"},
                            "requires_2fa": {"type": "boolean"},
                            "totp_secret": {"type": "string"},
                            "provisioning_uri": {"type": "string"},
                            "qr_code": {"type": "string", "description": "Data URL containing a PNG QR code."},
                        },
                        "required": [
                            "message",
                            "user_id",
                            "requires_2fa",
                            "totp_secret",
                            "provisioning_uri",
                            "qr_code",
                        ],
                    },
                    "TwoFactorSetup": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"},
                            "totp_secret": {"type": "string"},
                            "provisioning_uri": {"type": "string"},
                            "qr_code": {"type": "string", "description": "Data URL containing a PNG QR code."},
                        },
                        "required": ["message", "totp_secret", "provisioning_uri", "qr_code"],
                    },
                    "VerifyTwoFactorSuccess": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"},
                            "user": ref("User"),
                        },
                        "required": ["message", "user"],
                    },
                    "TextBlock": {
                        "type": "object",
                        "properties": {
                            "kind": {"type": "string", "enum": ["text"]},
                            "text": {"type": "string"},
                        },
                        "required": ["kind", "text"],
                    },
                    "ImageBlock": {
                        "type": "object",
                        "properties": {
                            "kind": {"type": "string", "enum": ["image"]},
                            "url": {"type": "string"},
                            "mime_type": {"type": "string", "nullable": True},
                            "alt": {"type": "string", "nullable": True},
                            "width": {"type": "integer", "minimum": 1, "nullable": True},
                            "height": {"type": "integer", "minimum": 1, "nullable": True},
                        },
                        "required": ["kind", "url"],
                    },
                    "TableBlock": {
                        "type": "object",
                        "properties": {
                            "kind": {"type": "string", "enum": ["table"]},
                            "html": {"type": "string", "minLength": 1},
                        },
                        "required": ["kind", "html"],
                    },
                    "ContentBlock": {
                        "oneOf": [ref("TextBlock"), ref("ImageBlock"), ref("TableBlock")],
                        "discriminator": {
                            "propertyName": "kind",
                            "mapping": {
                                "text": "#/components/schemas/TextBlock",
                                "image": "#/components/schemas/ImageBlock",
                                "table": "#/components/schemas/TableBlock",
                            },
                        },
                    },
                    "SyllabusPoint": {
                        "type": "object",
                        "properties": {
                            "syllabus_id": {"type": "string"},
                            "point_code": {"type": "string"},
                            "label": {"type": "string", "nullable": True},
                        },
                        "required": ["syllabus_id", "point_code"],
                    },
                    "ChoiceOption": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string", "pattern": "^[A-Z]$"},
                            "content": array_of("ContentBlock"),
                        },
                        "required": ["label", "content"],
                    },
                    "QuestionAnswer": {
                        "type": "object",
                        "properties": {
                            "option_label": {"type": "string", "pattern": "^[A-Z]$", "nullable": True},
                            "summary": {"type": "string", "nullable": True},
                            "content": {"type": "array", "items": ref("ContentBlock"), "nullable": True},
                            "alternatives": {
                                "type": "array",
                                "items": {"type": "array", "items": ref("ContentBlock")},
                                "nullable": True,
                            },
                        },
                    },
                    "RubricCriterion": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string", "nullable": True},
                            "marks": {"type": "integer", "minimum": 0, "nullable": True},
                            "min_marks": {"type": "integer", "minimum": 0, "nullable": True},
                            "max_marks": {"type": "integer", "minimum": 0, "nullable": True},
                            "description": array_of("ContentBlock"),
                        },
                        "required": ["description"],
                    },
                    "QuestionRubric": {
                        "type": "object",
                        "properties": {
                            "criteria": array_of("RubricCriterion"),
                            "notes": {"type": "array", "items": ref("ContentBlock"), "nullable": True},
                        },
                        "required": ["criteria"],
                    },
                    "QuestionPart": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string", "pattern": "^[a-z]+$"},
                            "stimulus": {"type": "array", "items": ref("ContentBlock"), "nullable": True},
                            "content": array_of("ContentBlock"),
                            "marks": {"type": "integer", "minimum": 0, "nullable": True},
                            "is_independent": {"type": "boolean", "nullable": True},
                            "answer": {
                                "oneOf": [{"type": "string"}, ref("QuestionAnswer")],
                                "nullable": True,
                            },
                            "rubric": {"allOf": [ref("QuestionRubric")], "nullable": True},
                            "guidelines": {"type": "array", "items": ref("ContentBlock"), "nullable": True},
                        },
                        "required": ["label", "content"],
                    },
                    "QuestionWrite": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "number": {"type": "integer", "minimum": 1},
                            "type": {
                                "type": "string",
                                "enum": ["multiple_choice", "short_answer", "long_answer"],
                                "default": "short_answer",
                            },
                            "marks": {"type": "integer", "minimum": 0, "default": 0},
                            "stimulus": {"type": "array", "items": ref("ContentBlock"), "nullable": True},
                            "content": {"type": "array", "items": ref("ContentBlock"), "nullable": True},
                            "parts": {"type": "array", "items": ref("QuestionPart"), "nullable": True},
                            "options": {"type": "array", "items": ref("ChoiceOption"), "nullable": True},
                            "answer": {
                                "oneOf": [{"type": "string"}, ref("QuestionAnswer")],
                                "nullable": True,
                            },
                            "rubric": {"allOf": [ref("QuestionRubric")], "nullable": True},
                            "guidelines": {"type": "array", "items": ref("ContentBlock"), "nullable": True},
                            "topics": {"type": "array", "items": {"type": "string"}, "nullable": True},
                            "outcomes": {"type": "array", "items": {"type": "string"}, "nullable": True},
                            "syllabus_points": {"type": "array", "items": ref("SyllabusPoint"), "nullable": True},
                            "difficulty": {
                                "type": "string",
                                "enum": ["easy", "medium", "hard"],
                                "nullable": True,
                            },
                            "created_at": {"type": "string", "format": "date-time"},
                            "updated_at": {"type": "string", "format": "date-time"},
                        },
                    },
                    "QuestionRead": {
                        "allOf": [
                            ref("QuestionWrite"),
                            {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "paper_id": {"type": "string"},
                                    "author_id": {"type": "string"},
                                    "number": {"type": "integer"},
                                    "type": {
                                        "type": "string",
                                        "enum": ["multiple_choice", "short_answer", "long_answer"],
                                    },
                                    "marks": {"type": "integer"},
                                    "topics": {"type": "array", "items": {"type": "string"}},
                                    "outcomes": {"type": "array", "items": {"type": "string"}},
                                    "syllabus_points": array_of("SyllabusPoint"),
                                    "created_at": {"type": "string", "format": "date-time"},
                                    "updated_at": {"type": "string", "format": "date-time"},
                                },
                                "required": [
                                    "id",
                                    "paper_id",
                                    "author_id",
                                    "number",
                                    "type",
                                    "marks",
                                    "topics",
                                    "outcomes",
                                    "syllabus_points",
                                    "created_at",
                                    "updated_at",
                                ],
                            },
                        ]
                    },
                    "PaperWrite": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string", "default": "Untitled"},
                            "subject": {"type": "string"},
                            "syllabus_id": {"type": "string", "nullable": True},
                            "year": {"type": "integer", "minimum": 2000, "nullable": True},
                            "source": {
                                "type": "string",
                                "enum": ["hsc", "trial", "internal", "practice", "custom"],
                                "nullable": True,
                            },
                            "school": {"type": "string", "nullable": True},
                            "course_level": {
                                "type": "string",
                                "enum": ["standard", "advanced", "extension_1", "extension_2"],
                                "nullable": True,
                            },
                            "topics": {"type": "array", "items": {"type": "string"}, "nullable": True},
                            "outcomes": {"type": "array", "items": {"type": "string"}, "nullable": True},
                            "visibility": {
                                "type": "string",
                                "enum": ["private", "public"],
                                "default": "private",
                            },
                            "question_count": {"type": "integer", "minimum": 0, "default": 0},
                            "total_marks": {"type": "integer", "minimum": 0, "default": 0},
                            "duration_minutes": {"type": "integer", "minimum": 0, "nullable": True},
                            "questions": {"type": "array", "items": ref("QuestionWrite")},
                        },
                    },
                    "PaperMeta": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "author_id": {"type": "string"},
                            "subject": {"type": "string"},
                            "year": {"type": "integer", "nullable": True},
                            "source": {
                                "type": "string",
                                "enum": ["hsc", "trial", "internal", "practice", "custom"],
                                "nullable": True,
                            },
                            "school": {"type": "string", "nullable": True},
                            "course_level": {
                                "type": "string",
                                "enum": ["standard", "advanced", "extension_1", "extension_2"],
                                "nullable": True,
                            },
                            "topics": {"type": "array", "items": {"type": "string"}},
                            "outcomes": {"type": "array", "items": {"type": "string"}},
                            "visibility": {"type": "string", "enum": ["private", "public"]},
                            "question_count": {"type": "integer"},
                            "total_marks": {"type": "integer"},
                            "duration_minutes": {"type": "integer", "nullable": True},
                            "created_at": {"type": "string", "format": "date-time"},
                            "updated_at": {"type": "string", "format": "date-time"},
                            "remixed": {"type": "string", "nullable": True},
                        },
                        "required": [
                            "id",
                            "title",
                            "author_id",
                            "subject",
                            "topics",
                            "outcomes",
                            "visibility",
                            "question_count",
                            "total_marks",
                            "created_at",
                            "updated_at",
                        ],
                    },
                    "Paper": {
                        "allOf": [
                            ref("PaperMeta"),
                            {
                                "type": "object",
                                "properties": {
                                    "syllabus_id": {"type": "string", "nullable": True},
                                    "questions": {"type": "array", "items": ref("QuestionRead")},
                                },
                                "required": ["questions"],
                            },
                        ]
                    },
                    "PaperList": {
                        "type": "object",
                        "properties": {
                            "papers": {"type": "array", "items": ref("PaperMeta")},
                            "total": {"type": "integer"},
                            "page": {"type": "integer"},
                            "per_page": {"type": "integer"},
                        },
                        "required": ["papers", "total", "page", "per_page"],
                    },
                },
            },
            "paths": {
                "/ping": {
                    "get": {
                        "tags": ["System"],
                        "summary": "Health check",
                        "responses": {
                            "200": response("Backend is running", {"type": "string"}),
                        },
                    }
                },
                "/api/register": {
                    "post": {
                        "tags": ["Authentication"],
                        "summary": "Register a user",
                        "description": "Creates a user. When 2FA is not enabled, the response also sets the access token cookie.",
                        "requestBody": form_request_body(
                            {
                                "email": {"type": "string", "format": "email"},
                                "username": {"type": "string"},
                                "password": {"type": "string", "format": "password"},
                                "enable_2fa": {"type": "boolean", "default": False},
                            },
                            ["email", "username", "password"],
                        ),
                        "responses": {
                            "201": response(
                                "User created",
                                {"oneOf": [ref("AuthSuccess"), ref("RegisterTwoFactorRequired")]},
                            ),
                            "400": error_response("Invalid registration details"),
                            "500": error_response("Database error"),
                        },
                    }
                },
                "/api/login": {
                    "post": {
                        "tags": ["Authentication"],
                        "summary": "Log in",
                        "description": "Authenticates by email or username and sets the access token cookie.",
                        "requestBody": form_request_body(
                            {
                                "email": {
                                    "type": "string",
                                    "description": "Email address or username.",
                                },
                                "password": {"type": "string", "format": "password"},
                            },
                            ["email", "password"],
                        ),
                        "responses": {
                            "200": response("Login successful", ref("AuthSuccess")),
                            "400": error_response("Missing credentials"),
                            "401": error_response("Invalid credentials"),
                            "500": error_response("Login error"),
                        },
                    }
                },
                "/api/logout": {
                    "post": {
                        "tags": ["Authentication"],
                        "summary": "Log out",
                        "security": [{"cookieAuth": []}],
                        "responses": {
                            "200": message_response("Logout successful"),
                            "401": error_response("Missing or invalid JWT"),
                        },
                    }
                },
                "/api/whoami": {
                    "get": {
                        "tags": ["Authentication"],
                        "summary": "Get the authenticated user",
                        "security": [{"cookieAuth": []}],
                        "responses": {
                            "200": response("Authenticated user details", ref("WhoAmI")),
                            "401": error_response("Missing or invalid JWT"),
                            "404": error_response("User not found"),
                            "500": error_response("Failed to fetch user"),
                        },
                    }
                },
                "/api/verify_2fa": {
                    "post": {
                        "tags": ["Authentication"],
                        "summary": "Verify a two-factor authentication code",
                        "description": "Completes 2FA login or registration and sets the access token cookie.",
                        "requestBody": form_request_body(
                            {
                                "user_id": {"type": "integer"},
                                "totp_code": {"type": "string"},
                            },
                            ["user_id", "totp_code"],
                        ),
                        "responses": {
                            "200": response("2FA verified", ref("VerifyTwoFactorSuccess")),
                            "400": error_response("Invalid 2FA request"),
                            "401": error_response("Invalid 2FA code"),
                            "404": error_response("User not found"),
                            "500": error_response("2FA verification error"),
                        },
                    }
                },
                "/api/whotf": {
                    "get": {
                        "tags": ["Account"],
                        "summary": "Get a public username by user id",
                        "parameters": [
                            {
                                "name": "user_id",
                                "in": "query",
                                "required": True,
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {
                            "200": response(
                                "User summary",
                                {
                                    "type": "object",
                                    "properties": {
                                        "user_id": {"type": "integer"},
                                        "username": {"type": "string"},
                                    },
                                    "required": ["user_id", "username"],
                                },
                            ),
                            "400": error_response("Missing user_id"),
                            "404": error_response("User not found"),
                        },
                    }
                },
                "/api/account/username": {
                    "put": {
                        "tags": ["Account"],
                        "summary": "Update username",
                        "security": [{"cookieAuth": []}],
                        "requestBody": form_request_body(
                            {"username": {"type": "string"}},
                            ["username"],
                        ),
                        "responses": {
                            "200": response(
                                "Username updated",
                                {
                                    "type": "object",
                                    "properties": {
                                        "message": {"type": "string"},
                                        "username": {"type": "string"},
                                    },
                                    "required": ["message", "username"],
                                },
                            ),
                            "400": error_response("Invalid or duplicate username"),
                            "401": error_response("Missing or invalid JWT"),
                            "404": error_response("User not found"),
                            "500": error_response("Failed to update username"),
                        },
                    }
                },
                "/api/account/password": {
                    "put": {
                        "tags": ["Account"],
                        "summary": "Update password",
                        "security": [{"cookieAuth": []}],
                        "requestBody": form_request_body(
                            {
                                "current_password": {"type": "string", "format": "password"},
                                "new_password": {"type": "string", "format": "password"},
                                "totp_code": {
                                    "type": "string",
                                    "description": "Required when 2FA is enabled for the account.",
                                },
                            },
                            ["current_password", "new_password"],
                        ),
                        "responses": {
                            "200": message_response("Password updated"),
                            "400": error_response("Missing password details"),
                            "401": error_response("Invalid password, 2FA code, or JWT"),
                            "404": error_response("User not found"),
                            "500": error_response("Failed to update password"),
                        },
                    }
                },
                "/api/account": {
                    "delete": {
                        "tags": ["Account"],
                        "summary": "Delete account",
                        "security": [{"cookieAuth": []}],
                        "responses": {
                            "200": message_response("Account deleted"),
                            "401": error_response("Missing or invalid JWT"),
                            "404": error_response("User not found"),
                            "500": error_response("Failed to delete account"),
                        },
                    }
                },
                "/api/account/enable_2fa": {
                    "post": {
                        "tags": ["Account"],
                        "summary": "Enable two-factor authentication",
                        "security": [{"cookieAuth": []}],
                        "responses": {
                            "200": response("2FA setup details generated", ref("TwoFactorSetup")),
                            "400": error_response("2FA is already enabled"),
                            "401": error_response("Missing or invalid JWT"),
                            "404": error_response("User not found"),
                            "500": error_response("Failed to enable 2FA"),
                        },
                    }
                },
                "/api/account/disable_2fa": {
                    "post": {
                        "tags": ["Account"],
                        "summary": "Disable two-factor authentication",
                        "security": [{"cookieAuth": []}],
                        "requestBody": form_request_body(
                            {"totp_code": {"type": "string"}},
                            ["totp_code"],
                        ),
                        "responses": {
                            "200": message_response("2FA disabled"),
                            "400": error_response("Missing 2FA code or 2FA disabled"),
                            "401": error_response("Invalid 2FA code or JWT"),
                            "404": error_response("User not found"),
                            "500": error_response("Failed to disable 2FA"),
                        },
                    }
                },
                "/api/papers/search": {
                    "get": {
                        "tags": ["Papers"],
                        "summary": "Search public papers",
                        "parameters": pagination_parameters(),
                        "responses": {
                            "200": response("Public paper search results", ref("PaperList")),
                            "500": error_response("Failed to search papers"),
                        },
                    }
                },
                "/api/papers": {
                    "get": {
                        "tags": ["Papers"],
                        "summary": "List authenticated user's papers",
                        "security": [{"cookieAuth": []}],
                        "parameters": pagination_parameters(),
                        "responses": {
                            "200": response("User paper results", ref("PaperList")),
                            "401": error_response("Missing or invalid JWT"),
                            "500": error_response("Failed to list papers"),
                        },
                    },
                    "post": {
                        "tags": ["Papers"],
                        "summary": "Create a paper",
                        "security": [{"cookieAuth": []}],
                        "requestBody": json_request_body(ref("PaperWrite")),
                        "responses": {
                            "201": response("Paper created", ref("Paper")),
                            "400": error_response("No data provided"),
                            "401": error_response("Missing or invalid JWT"),
                            "500": error_response("Failed to create paper"),
                        },
                    },
                },
                "/api/papers/{paper_id}": {
                    "get": {
                        "tags": ["Papers"],
                        "summary": "Get a paper",
                        "description": "Public papers can be read without login. Private papers require the author's cookie.",
                        "security": [{"cookieAuth": []}, {}],
                        "parameters": [paper_id_parameter()],
                        "responses": {
                            "200": response("Paper details", ref("Paper")),
                            "404": error_response("Paper not found or private"),
                            "500": error_response("Failed to get paper"),
                        },
                    },
                    "put": {
                        "tags": ["Papers"],
                        "summary": "Update a paper",
                        "security": [{"cookieAuth": []}],
                        "parameters": [paper_id_parameter()],
                        "requestBody": json_request_body(ref("PaperWrite")),
                        "responses": {
                            "200": response("Paper updated", ref("Paper")),
                            "400": error_response("No data provided"),
                            "401": error_response("Missing or invalid JWT"),
                            "403": error_response("Authenticated user is not the author"),
                            "404": error_response("Paper not found"),
                            "500": error_response("Failed to update paper"),
                        },
                    },
                    "delete": {
                        "tags": ["Papers"],
                        "summary": "Delete a paper",
                        "security": [{"cookieAuth": []}],
                        "parameters": [paper_id_parameter()],
                        "responses": {
                            "200": message_response("Paper deleted"),
                            "401": error_response("Missing or invalid JWT"),
                            "403": error_response("Authenticated user is not the author"),
                            "404": error_response("Paper not found"),
                            "500": error_response("Failed to delete paper"),
                        },
                    },
                },
                "/api/papers/{paper_id}/publish": {
                    "post": {
                        "tags": ["Papers"],
                        "summary": "Publish a paper",
                        "description": "Marks an existing author-owned paper as public. If the paper does not exist, the JSON body is used to create it before publishing.",
                        "security": [{"cookieAuth": []}],
                        "parameters": [paper_id_parameter()],
                        "requestBody": json_request_body(ref("PaperWrite"), required=False),
                        "responses": {
                            "200": response("Paper published", ref("PaperMeta")),
                            "400": error_response("Paper does not exist and no body was provided"),
                            "401": error_response("Missing or invalid JWT"),
                            "403": error_response("Authenticated user is not the author"),
                            "409": error_response("Paper is already public"),
                            "500": error_response("Failed to publish paper"),
                        },
                    },
                    "delete": {
                        "tags": ["Papers"],
                        "summary": "Unpublish a paper",
                        "security": [{"cookieAuth": []}],
                        "parameters": [paper_id_parameter()],
                        "responses": {
                            "200": response("Paper unpublished", ref("PaperMeta")),
                            "401": error_response("Missing or invalid JWT"),
                            "403": error_response("Authenticated user is not the author"),
                            "404": error_response("Paper not found"),
                            "409": error_response("Paper is already private"),
                            "500": error_response("Failed to unpublish paper"),
                        },
                    },
                },
                "/api/papers/{paper_id}/remix": {
                    "post": {
                        "tags": ["Papers"],
                        "summary": "Remix a public paper",
                        "description": "Copies a public paper and its questions into the authenticated user's private library.",
                        "security": [{"cookieAuth": []}],
                        "parameters": [paper_id_parameter()],
                        "responses": {
                            "201": response("Private remix created", ref("Paper")),
                            "401": error_response("Missing or invalid JWT"),
                            "403": error_response("Cannot remix a private paper"),
                            "404": error_response("Paper not found"),
                            "500": error_response("Failed to remix paper"),
                        },
                    }
                },
            },
        }
    )


def register_blueprint(app):
    if PRODUCTION and not PUBLIC_API_DOCS:
        return

    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={"app_name": "tppr-api"},
    )
    app.register_blueprint(swagger_bp)
    app.register_blueprint(swaggerui_blueprint)
