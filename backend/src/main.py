from flask import Flask, send_from_directory
import os
import sys

static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../assets"))

api_only = "--api-only" in sys.argv

if api_only:
    app = Flask(__name__)
    print("Currently using API only configuration (flag passed with `--api-only`)")

    @app.route("/")
    def index():
        return send_from_directory(assets_dir, "missing.html")
else:
    app = Flask(__name__, static_folder=static_dir, static_url_path="")
    print("Currently using static-hosting configuration")

    @app.route("/")
    def index():
        return send_from_directory(static_dir, "index.html")

if __name__ == "__main__":
    app.run()