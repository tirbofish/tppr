from flask import Blueprint, jsonify

auth_bp = Blueprint('tppr-authentication', __name__)


@auth_bp.route('/api/login')
def api_login():
    return jsonify("WIP")
