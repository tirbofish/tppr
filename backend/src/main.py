# ensure tippy top of script
from dotenv import load_dotenv
load_dotenv()

import os

import auth
import swagger
import settings
from admin import admin_bp, init_admins, teardown_admins
from auth.db import AuthenticationDB
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, verify_jwt_in_request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from questions.db import prepare as prepare_paper_db
from questions.endpoints import q_bp
from shared import BLOCKLIST

assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../assets"))

app = Flask(__name__)

# --- secure stuff ---
if settings.BACKEND_ALLOWED_ORIGINS:
    CORS(
        app,
        supports_credentials=True,
        origins=settings.BACKEND_ALLOWED_ORIGINS,
        resources={r"/api/*": {"origins": settings.BACKEND_ALLOWED_ORIGINS}},
    )

app.config.update(
    ENV="production" if settings.PRODUCTION else "development",
    DEBUG=settings.BACKEND_DEBUG,
    TESTING=False,
    SECRET_KEY=settings.SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=settings.PRODUCTION,
    SESSION_COOKIE_SAMESITE=settings.JWT_COOKIE_SAMESITE,
    JWT_SECRET_KEY=settings.JWT_SECRET_KEY,
    JWT_TOKEN_LOCATION=settings.JWT_TOKEN_LOCATION,
    JWT_COOKIE_SECURE=settings.JWT_COOKIE_SECURE,
    JWT_COOKIE_SAMESITE=settings.JWT_COOKIE_SAMESITE,
    JWT_COOKIE_CSRF_PROTECT=settings.JWT_COOKIE_CSRF_PROTECT,
    JWT_CSRF_IN_COOKIES=settings.JWT_CSRF_IN_COOKIES,
    JWT_SESSION_COOKIE=settings.JWT_SESSION_COOKIE,
    JWT_ACCESS_COOKIE_NAME=settings.ACCESS_TOKEN_COOKIE_NAME,
    JWT_ACCESS_TOKEN_EXPIRES=settings.JWT_ACCESS_TOKEN_EXPIRES,
)

jwt = JWTManager(app)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[settings.RATELIMIT_DEFAULT],
    storage_uri=settings.RATELIMIT_STORAGE_URI,
)

PUBLIC_API_ENDPOINTS = {
    "ping",
    "tppr-account-authentication.register",
    "tppr-account-authentication.login",
    "tppr-account-2fa.verify_2fa",
    "tppr-account-management.whotfisthis",
    "tppr-questions.get_asset",
    "tppr-questions.search_papers",
    "tppr-questions.get_paper",
}

PUBLIC_API_DOC_ENDPOINTS = {
    "swagger.swagger_json",
    "swagger_ui.show",
    "swagger_ui.static",
}

PUBLIC_ENDPOINT_RATE_LIMITS = {
    "ping": "60 per minute",
    "tppr-account-authentication.register": "5 per hour",
    "tppr-account-authentication.login": "10 per minute",
    "tppr-account-2fa.verify_2fa": "10 per minute",
    "tppr-account-management.whotfisthis": "60 per minute",
    "tppr-questions.search_papers": "60 per minute",
    "tppr-questions.get_paper": "120 per minute",
    "tppr-questions.get_asset": "120 per minute",
    "tppr-admin.verify_admin": "5 per minute",
}


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return jti in BLOCKLIST


@app.before_request
def require_auth_for_private_api_routes():
    if request.method == "OPTIONS":
        return None
    if not settings.PRODUCTION or not request.path.startswith("/api/"):
        return None
    if request.endpoint in PUBLIC_API_ENDPOINTS:
        return None
    if settings.PUBLIC_API_DOCS and request.endpoint in PUBLIC_API_DOC_ENDPOINTS:
        return None
    verify_jwt_in_request()
    return None


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = (
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), payment=(), usb=()"
    )
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

    if response.content_type.startswith("text/html"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self'"
        )

    if settings.PRODUCTION:
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )

    if request.path.startswith("/api/") and "Cache-Control" not in response.headers:
        response.headers["Cache-Control"] = "no-store"
    return response


# --- basic routes ---

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def index(path):
    return send_from_directory(assets_dir, "missing.html")


@app.route("/ping")
def ping():
    return jsonify('tppr says "Pong!"')


@app.errorhandler(404)
def page_not_found(e):
    body = {"message": "404, requested resource not found"}
    if settings.SHOW_ERROR_CAUSES:
        body["cause"] = str(e)
    return jsonify(body), 404

# --- blueprint registration ---

auth.register_blueprint(app)
swagger.register_blueprint(app)
app.register_blueprint(q_bp)
app.register_blueprint(admin_bp)

for endpoint, limit in PUBLIC_ENDPOINT_RATE_LIMITS.items():
    view = app.view_functions.get(endpoint)
    if view:
        app.view_functions[endpoint] = limiter.limit(limit)(view)


_runtime_initialized = False


def initialize_runtime():
    global _runtime_initialized
    if _runtime_initialized:
        return

    auth_db = AuthenticationDB()
    auth_db.prepare(app.logger)
    prepare_paper_db(app.logger)
    init_admins()
    _runtime_initialized = True


initialize_runtime()

# --- do not add code any further than this line, or else...👻👻👻 ---

if not settings.PRODUCTION:
    print("\nAvailable endpoints:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
        if methods:
            print(f"  {methods:8s} {rule.rule}")
    print()

if __name__ == "__main__":
    try:
        app.run(
            debug=settings.BACKEND_DEBUG,
            host=settings.BACKEND_HOST,
            port=settings.BACKEND_PORT,
        )
    finally:
        teardown_admins()
