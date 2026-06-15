# ensure tippy top of script
from dotenv import load_dotenv
load_dotenv()

import os
from datetime import timedelta

import auth
import swagger
from auth.db import AuthenticationDB
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from questions.db import prepare as prepare_paper_db
from questions.endpoints import q_bp
from admin import admin_bp, init_admins, teardown_admins
from shared import BLOCKLIST

static_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../frontend/dist")
)
assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../assets"))

app = Flask(__name__)

# --- secure stuff ---
CORS(app, supports_credentials=True, origins=os.getenv("BACKEND_ALLOWED_ORIGINS", "http://localhost:5173").split(","))

app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET_KEY"]
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = os.getenv("JWT_COOKIE_SECURE", "0") == "1"
app.config["JWT_COOKIE_SAMESITE"] = os.getenv("JWT_COOKIE_SAMESITE", "Lax")
app.config["JWT_COOKIE_CSRF_PROTECT"] = True
app.config["JWT_CSRF_IN_COOKIES"] = True
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)

jwt = JWTManager(app)


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return jti in BLOCKLIST

@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["200 per minute"])


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
    return jsonify(
        {"message": "404, requested resource not found", "cause": str(e)}
    ), 404

# --- blueprint registration ---

auth.register_blueprint(app)
swagger.register_blueprint(app)
app.register_blueprint(q_bp)
app.register_blueprint(admin_bp)

# --- do not add code any further than this line, or else...👻👻👻 ---

print("\nAvailable endpoints:")
for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
    if methods:
        print(f"  {methods:8s} {rule.rule}")
print()

if __name__ == "__main__":
    auth_db = AuthenticationDB()
    auth_db.prepare(app.logger)
    prepare_paper_db(app.logger)
    init_admins()
    try:
        app.run(debug=os.getenv("BACKEND_DEBUG_MODE", "0") == "1", host="0.0.0.0", port=5000)
    finally:
        teardown_admins()
