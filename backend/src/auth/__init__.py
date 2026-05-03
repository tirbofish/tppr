from flask import Flask

__all__ = ["two_factor", "management", "account"]

from . import two_factor
from . import account
from . import management


def register_blueprint(app: Flask):
    app.register_blueprint(two_factor.two_fa_bp)
    app.register_blueprint(account.account_bp)
    app.register_blueprint(management.management_bp)
