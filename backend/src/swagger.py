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


def asset_id_parameter():
    return {
        "name": "asset_id",
        "in": "path",
        "required": True,
        "schema": {"type": "string", "pattern": "^[A-Za-z0-9_-]{8,128}$"},
    }


def question_id_parameter():
    return {
        "name": "question_id",
        "in": "path",
        "required": True,
        "schema": {"type": "string"},
    }


def multipart_request_body(fields, required=None):
    required = required or []
    return {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "properties": fields,
                    "required": required,
                }
            }
        },
    }


def binary_response(description, content_type="application/octet-stream"):
    return {
        "description": description,
        "content": {
            content_type: {
                "schema": {"type": "string", "format": "binary"}
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
            "tags": [
                {"name": "System", "description": "Health checks and API metadata."},
                {"name": "Authentication", "description": "Supabase identity and session validation."},
                {"name": "Account", "description": "Local account profile and 2FA management."},
                {"name": "Papers", "description": "Past paper search, authoring, publishing, and remixing."},
                {"name": "Assets", "description": "Paper image asset upload and retrieval."},
                {"name": "Admin", "description": "Admin verification and takedown moderation."},
            ],
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "Supabase JWT",
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
                            "user_id": {"type": "string"},
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
                            "user_id": {"type": "string"},
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
                    "AssetUploadResult": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "paper_id": {"type": "string"},
                            "mime_type": {"type": "string"},
                        },
                        "required": ["id", "paper_id", "mime_type"],
                    },
                    "QuestionRemixRequest": {
                        "type": "object",
                        "properties": {
                            "target_paper_id": {
                                "type": "string",
                                "description": "Authenticated user's paper that will receive the cloned question.",
                            },
                        },
                        "required": ["target_paper_id"],
                    },
                    "AdminVerifyRequest": {
                        "type": "object",
                        "properties": {
                            "passcode": {"type": "string", "format": "password"},
                        },
                        "required": ["passcode"],
                    },
                    "AdminStatus": {
                        "type": "object",
                        "properties": {"admin": {"type": "boolean"}},
                        "required": ["admin"],
                    },
                    "AdminTakedownResult": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"},
                            "taken_down": {"type": "array", "items": {"type": "string"}},
                            "restored": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["message"],
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
                "/api/whoami": {
                    "get": {
                        "tags": ["Authentication"],
                        "summary": "Get the authenticated user",
                        "security": [{"bearerAuth": []}],
                        "responses": {
                            "200": response("Authenticated user details", ref("WhoAmI")),
                            "401": error_response("Missing or invalid Supabase token"),
                            "404": error_response("User not found"),
                            "500": error_response("Failed to fetch user"),
                        },
                    }
                },
                "/api/verify_2fa": {
                    "post": {
                        "tags": ["Authentication"],
                        "summary": "Verify a two-factor authentication code",
                        "description": "Legacy endpoint. Login and 2FA sessions are handled by Supabase Auth.",
                        "responses": {
                            "410": message_response("2FA login is handled by Supabase Auth"),
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
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {
                            "200": response(
                                "User summary",
                                {
                                    "type": "object",
                                    "properties": {
                                        "user_id": {"type": "string"},
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
                        "security": [{"bearerAuth": []}],
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
                            "401": error_response("Missing or invalid Supabase token"),
                            "404": error_response("User not found"),
                            "500": error_response("Failed to update username"),
                        },
                    }
                },
                "/api/account/password": {
                    "put": {
                        "tags": ["Account"],
                        "summary": "Update password",
                        "description": "Password changes are handled by Supabase Auth, so this legacy local endpoint is disabled.",
                        "security": [{"bearerAuth": []}],
                        "responses": {
                            "410": message_response("Password changes are handled by Supabase Auth"),
                        },
                    }
                },
                "/api/account": {
                    "delete": {
                        "tags": ["Account"],
                        "summary": "Delete account",
                        "security": [{"bearerAuth": []}],
                        "responses": {
                            "200": message_response("Account deleted"),
                            "401": error_response("Missing or invalid Supabase token"),
                            "404": error_response("User not found"),
                            "500": error_response("Failed to delete account"),
                        },
                    }
                },
                "/api/account/enable_2fa": {
                    "post": {
                        "tags": ["Account"],
                        "summary": "Enable two-factor authentication",
                        "security": [{"bearerAuth": []}],
                        "responses": {
                            "200": response("2FA setup details generated", ref("TwoFactorSetup")),
                            "400": error_response("2FA is already enabled"),
                            "401": error_response("Missing or invalid Supabase token"),
                            "404": error_response("User not found"),
                            "500": error_response("Failed to enable 2FA"),
                        },
                    }
                },
                "/api/account/disable_2fa": {
                    "post": {
                        "tags": ["Account"],
                        "summary": "Disable two-factor authentication",
                        "security": [{"bearerAuth": []}],
                        "requestBody": form_request_body(
                            {"totp_code": {"type": "string"}},
                            ["totp_code"],
                        ),
                        "responses": {
                            "200": message_response("2FA disabled"),
                            "400": error_response("Missing 2FA code or 2FA disabled"),
                            "401": error_response("Invalid 2FA code or Supabase token"),
                            "404": error_response("User not found"),
                            "500": error_response("Failed to disable 2FA"),
                        },
                    }
                },
                "/api/papers/{paper_id}/assets": {
                    "post": {
                        "tags": ["Assets"],
                        "summary": "Upload a paper image asset",
                        "description": "Uploads an image asset for an author-owned paper. Removed papers cannot receive new assets.",
                        "security": [{"bearerAuth": []}],
                        "parameters": [paper_id_parameter()],
                        "requestBody": multipart_request_body(
                            {
                                "file": {"type": "string", "format": "binary"},
                                "asset_id": {
                                    "type": "string",
                                    "pattern": "^[A-Za-z0-9_-]{8,128}$",
                                    "description": "Optional client-generated asset id. A UUID is generated if omitted.",
                                },
                            },
                            ["file"],
                        ),
                        "responses": {
                            "201": response("Asset uploaded", ref("AssetUploadResult")),
                            "400": error_response("Missing file, invalid asset id, or unsupported file type"),
                            "401": error_response("Missing or invalid Supabase token"),
                            "403": error_response("Authenticated user is not the paper author"),
                            "404": error_response("Paper not found"),
                            "409": error_response("Asset id already belongs to another paper"),
                            "410": error_response("Paper has been removed"),
                        },
                    }
                },
                "/api/assets/{asset_id}": {
                    "get": {
                        "tags": ["Assets"],
                        "summary": "Get an uploaded asset",
                        "description": "Returns an asset only if the caller can view the parent paper. Public paper assets can be read without login; private paper assets require the author or an admin.",
                        "security": [{"bearerAuth": []}, {}],
                        "parameters": [asset_id_parameter()],
                        "responses": {
                            "200": binary_response("Asset bytes", "image/*"),
                            "404": error_response("Asset not found or not visible"),
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
                        "security": [{"bearerAuth": []}],
                        "parameters": pagination_parameters(),
                        "responses": {
                            "200": response("User paper results", ref("PaperList")),
                            "401": error_response("Missing or invalid Supabase token"),
                            "500": error_response("Failed to list papers"),
                        },
                    },
                    "post": {
                        "tags": ["Papers"],
                        "summary": "Create a paper",
                        "security": [{"bearerAuth": []}],
                        "requestBody": json_request_body(ref("PaperWrite")),
                        "responses": {
                            "201": response("Paper created", ref("Paper")),
                            "400": error_response("No data provided"),
                            "401": error_response("Missing or invalid Supabase token"),
                            "500": error_response("Failed to create paper"),
                        },
                    },
                },
                "/api/papers/{paper_id}": {
                    "get": {
                        "tags": ["Papers"],
                        "summary": "Get a paper",
                        "description": "Public papers can be read without login. Private papers require the author's Supabase bearer token.",
                        "security": [{"bearerAuth": []}, {}],
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
                        "security": [{"bearerAuth": []}],
                        "parameters": [paper_id_parameter()],
                        "requestBody": json_request_body(ref("PaperWrite")),
                        "responses": {
                            "200": response("Paper updated", ref("Paper")),
                            "400": error_response("No data provided"),
                            "401": error_response("Missing or invalid Supabase token"),
                            "403": error_response("Authenticated user is not the author"),
                            "404": error_response("Paper not found"),
                            "500": error_response("Failed to update paper"),
                        },
                    },
                    "delete": {
                        "tags": ["Papers"],
                        "summary": "Delete a paper",
                        "security": [{"bearerAuth": []}],
                        "parameters": [paper_id_parameter()],
                        "responses": {
                            "200": message_response("Paper deleted"),
                            "401": error_response("Missing or invalid Supabase token"),
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
                        "security": [{"bearerAuth": []}],
                        "parameters": [paper_id_parameter()],
                        "requestBody": json_request_body(ref("PaperWrite"), required=False),
                        "responses": {
                            "200": response("Paper published", ref("PaperMeta")),
                            "400": error_response("Paper does not exist and no body was provided"),
                            "401": error_response("Missing or invalid Supabase token"),
                            "403": error_response("Authenticated user is not the author"),
                            "409": error_response("Paper is already public"),
                            "500": error_response("Failed to publish paper"),
                        },
                    },
                    "delete": {
                        "tags": ["Papers"],
                        "summary": "Unpublish a paper",
                        "security": [{"bearerAuth": []}],
                        "parameters": [paper_id_parameter()],
                        "responses": {
                            "200": response("Paper unpublished", ref("PaperMeta")),
                            "401": error_response("Missing or invalid Supabase token"),
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
                        "security": [{"bearerAuth": []}],
                        "parameters": [paper_id_parameter()],
                        "responses": {
                            "201": response("Private remix created", ref("Paper")),
                            "401": error_response("Missing or invalid Supabase token"),
                            "403": error_response("Cannot remix a private paper"),
                            "404": error_response("Paper not found"),
                            "500": error_response("Failed to remix paper"),
                        },
                    }
                },
                "/api/papers/{paper_id}/questions/{question_id}/remix": {
                    "post": {
                        "tags": ["Papers"],
                        "summary": "Remix a question into one of the user's papers",
                        "description": "Copies one question from a public source paper into an authenticated user's target paper.",
                        "security": [{"bearerAuth": []}],
                        "parameters": [paper_id_parameter(), question_id_parameter()],
                        "requestBody": json_request_body(ref("QuestionRemixRequest")),
                        "responses": {
                            "201": response("Target paper with cloned question", ref("Paper")),
                            "400": error_response("target_paper_id is required"),
                            "401": error_response("Missing or invalid Supabase token"),
                            "403": error_response("Source paper is private or target paper is not owned by the caller"),
                            "404": error_response("Source paper, source question, or target paper not found"),
                            "410": error_response("Target paper has been removed"),
                        },
                    }
                },
                "/api/admin/verify": {
                    "post": {
                        "tags": ["Admin"],
                        "summary": "Activate admin mode",
                        "description": "Validates the authenticated user's configured admin email and passcode.",
                        "security": [{"bearerAuth": []}],
                        "requestBody": json_request_body(ref("AdminVerifyRequest")),
                        "responses": {
                            "200": response("Admin mode activated", ref("AdminStatus")),
                            "400": error_response("Missing request body or passcode"),
                            "401": error_response("Invalid credentials or Supabase token"),
                        },
                    }
                },
                "/api/admin/status": {
                    "get": {
                        "tags": ["Admin"],
                        "summary": "Get admin status",
                        "security": [{"bearerAuth": []}],
                        "responses": {
                            "200": response("Current admin status", ref("AdminStatus")),
                            "401": error_response("Missing or invalid Supabase token"),
                        },
                    }
                },
                "/api/admin/takedowns": {
                    "get": {
                        "tags": ["Admin"],
                        "summary": "List removed papers",
                        "security": [{"bearerAuth": []}],
                        "parameters": [
                            {"name": "q", "in": "query", "schema": {"type": "string"}},
                            {"name": "page", "in": "query", "schema": {"type": "integer", "minimum": 1, "default": 1}},
                            {"name": "per_page", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}},
                        ],
                        "responses": {
                            "200": response("Removed paper results", ref("PaperList")),
                            "401": error_response("Missing or invalid Supabase token"),
                            "403": error_response("Authenticated user is not an active admin"),
                        },
                    }
                },
                "/api/admin/takedown/{paper_id}": {
                    "post": {
                        "tags": ["Admin"],
                        "summary": "Take down a paper and its remixes",
                        "security": [{"bearerAuth": []}],
                        "parameters": [paper_id_parameter()],
                        "responses": {
                            "200": response("Papers taken down", ref("AdminTakedownResult")),
                            "401": error_response("Missing or invalid Supabase token"),
                            "403": error_response("Authenticated user is not an active admin"),
                            "404": error_response("Paper not found"),
                        },
                    },
                    "delete": {
                        "tags": ["Admin"],
                        "summary": "Restore a taken-down paper and its remixes",
                        "description": "Restores remembered previous visibility where available; otherwise restores papers to private.",
                        "security": [{"bearerAuth": []}],
                        "parameters": [paper_id_parameter()],
                        "responses": {
                            "200": response("Papers restored", ref("AdminTakedownResult")),
                            "401": error_response("Missing or invalid Supabase token"),
                            "403": error_response("Authenticated user is not an active admin"),
                            "404": error_response("Paper not found"),
                            "409": error_response("Paper is not taken down"),
                        },
                    },
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
