from flask import jsonify, Blueprint, request
from flask_cors import cross_origin
from app import app
from app.email import send_feedback


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

@general.route('{base_path}/feedback'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
@cross_origin()
def feedback():
    message = request.json.get('message')
    sender_email = request.json.get('senderEmail')
    sender_name = request.json.get('senderName')

    if not message:
        return jsonify({
            'errors': [{
                'field': 'message',
                'message': 'Empty message!'
            }]
        })

    if len(message)>app.config['MAX_TEXT_SYMBOLS']:
        return jsonify({
            'errors': [{
                'field': 'message',
                'message': 'Too long message!'
            }]
        })

    send_feedback(message=message, sender_name=sender_name, sender_email=sender_email)
    return jsonify({'message': 'Feedback message sent'}), 200

