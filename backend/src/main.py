import auth
from flask import Flask, send_from_directory, jsonify
import os
import sys

static_dir = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../../frontend/dist"))
assets_dir = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../assets"))

api_only = "--api-only" in sys.argv

if api_only:
    app = Flask(__name__)
    print("Currently using API only configuration (flag passed with `--api-only`)")
else:
    app = Flask(__name__, static_folder=static_dir, static_url_path="")
    print("Currently using static-hosting configuration")


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    if api_only:
        # serve the API-only html file
        return send_from_directory(assets_dir, 'missing.html')
    if path and os.path.isfile(os.path.join(app.static_folder, path)):
        # try to serve the frontend
        return send_from_directory(app.static_folder, path)
    # otherwise serve whatever is in here
    return send_from_directory(app.static_folder, 'index.html')


@app.route("/ping")
def ping():
    return jsonify("tppr says \"Pong!\"")


# --- blueprint registration ---

app.register_blueprint(auth.auth_bp)

# --- do not add code any further than this line, or else...👻👻👻 ---

if __name__ == "__main__":
    app.run()
