from flask import Flask

from .routes import stats_bp

__all__ = ["stats_bp", "register_blueprint"]


def register_blueprint(app: Flask):
    app.register_blueprint(stats_bp)