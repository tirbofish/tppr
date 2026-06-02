import os
import sys
from datetime import timedelta

import auth
import db
import swagger
from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from shared import BLOCKLIST

load_dotenv()

static_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../frontend/dist")
)
assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../assets"))

api_only = "--api-only" in sys.argv

if api_only:
    app = Flask(__name__)
    print("Currently using API only configuration (flag passed with `--api-only`)")
else:
    app = Flask(__name__, static_folder=static_dir, static_url_path="")
    print("Currently using static-hosting configuration")

# --- secure stuff ---
CORS(app, supports_credentials=True)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = os.getenv("JWT_COOKIE_SECURE", "0") == "1"
app.config["JWT_COOKIE_SAMESITE"] = os.getenv("JWT_COOKIE_SAMESITE", "Lax")
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)

jwt = JWTManager(app)


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return jti in BLOCKLIST


# --- basic routes ---


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def index(path):
    if api_only:
        return send_from_directory(assets_dir, "missing.html")
    if path and os.path.isfile(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


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


# --- do not add code any further than this line, or else...👻👻👻 ---

print("\nAvailable endpoints:")
for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
    if methods:
        print(f"  {methods:8s} {rule.rule}")
print()

if __name__ == "__main__":
    db.prepare(app.logger)
    app.run(debug=True, host="0.0.0.0", port=5000)
