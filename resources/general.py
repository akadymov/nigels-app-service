from flask import jsonify, Blueprint
from flask_cors import cross_origin
from app import app


general = Blueprint('general', __name__)


@general.route('{base_path}/rules'.format(base_path=app.config['API_BASE_PATH']), methods=['GET'])
@cross_origin()
def get_rules():
    with open("rules.html", 'r') as f:
        content = f.read()
        f.close()
    if not content:
        return jsonify({
            'errors': [
                {
                    'message': 'Game rules not found!'
                }
            ]
        }), 404

    return jsonify({'rules': content}), 200


@general.route('{base_path}/info'.format(base_path=app.config['API_BASE_PATH']), methods=['GET'])
@cross_origin()
def get_info():
    with open("info.html", 'r') as f:
        content = f.read()
        f.close()
    if not content:
        return jsonify({
            'errors': [
                {
                    'message': 'Game info not found!'
                }
            ]
        }), 404

    return jsonify({'info': content}), 200
