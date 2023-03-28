from flask import jsonify, Blueprint, request
from flask_cors import cross_origin
from app.email import send_feedback
from app.models import Stats, User
from config import get_settings, get_environment


general = Blueprint('general', __name__)
env = get_environment()

@general.route('{base_path}/rules'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['GET'])
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


@general.route('{base_path}/info'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['GET'])
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

@general.route('{base_path}/feedback'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['POST'])
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

    if len(message)>get_settings('CONTENT')['MAX_SYMBOLS'][env]:
        return jsonify({
            'errors': [{
                'field': 'message',
                'message': 'Too long message!'
            }]
        })

    send_feedback(message=message, sender_name=sender_name, sender_email=sender_email)
    return jsonify({'message': 'Feedback message sent'}), 200


@general.route('{base_path}/ratings'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['GET'])
@cross_origin()
def ratings():
    ratings = Stats.query.filter(Stats.games_played>0).all()
    ratings_final = []
    if ratings:
        for rating in ratings:
            user = User.query.filter_by(id=rating.user_id).first()
            if user:
                ratings_final.append({
                    'username': user.username,
                    'gamesPlayed': rating.games_played,
                    'gamesWon': rating.games_won,
                    'winRatio': rating.games_won / rating.games_played,
                    'sumOfBets': rating.sum_of_bets,
                    'bonuses': rating.bonuses,
                    'totalScore': rating.total_score,
                    'avgScore': rating.total_score / rating.games_played,
                    'avgBonuses': rating.bonuses / rating.games_played,
                    'avgBetSize': rating.sum_of_bets / rating.games_played
                })
    return ratings_final