from flask import Flask

from .routes import progress_bp

__all__ = ["progress_bp", "register_blueprint"]


def register_blueprint(app: Flask):
    app.register_blueprint(progress_bp)