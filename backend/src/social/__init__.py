from flask import Flask

# Importing the model registers it with SQLModel.metadata so that
# SQLModel.metadata.create_all() creates the friendships table on startup.
from . import models  # noqa: F401
from .routes import social_bp

__all__ = ["social_bp", "register_blueprint"]


def register_blueprint(app: Flask):
    app.register_blueprint(social_bp)