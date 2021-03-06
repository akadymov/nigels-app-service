# -*- coding: utf-8 -*-

from flask import url_for, request, jsonify, abort, Blueprint
from flask_cors import cross_origin
from app import app, db
from app.models import User, Room, Game, Player, Hand
from datetime import datetime
import random


game = Blueprint('game', __name__)


@game.route('{base_path}/game/<game_id>/score'.format(base_path=app.config['API_BASE_PATH']), methods=['GET'])
@cross_origin()
def game_score(game_id):

    g = Game.query.filter_by(id=game_id).first()
    if not g:
        abort(400, 'Game does not exist!')

    game_scores = g.get_scores()

    return jsonify({
        'gameId': game_id,
        'gameScores': game_scores
    }), 200


@game.route('{base_path}/game/start'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
@cross_origin()
def start():

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('user.post_token')))
    requesting_user = User.verify_api_auth_token(token)

    hosted_room = Room.query.filter_by(host=requesting_user, closed=None).first()
    if not hosted_room:
        abort(403, 'User {username} does not have open rooms! Create room by POST {create_room_url} before managing games.'.format(
            username=requesting_user.username,
            create_room_url=url_for('room.create')
        ))
    if not app.config['MIN_PLAYER_TO_START'] <= hosted_room.connected_users.count() <= app.config['MAX_PLAYER_TO_START']:
        abort(403, 'Incorrect number of players to start ({players_count} connected to room {room_name}!'.format(
            players_count=hosted_room.connected_users.count(),
            room_name=hosted_room.room_name
        ))
    for room_game in hosted_room.games:
        if room_game.finished is None:
            abort(403, 'Game {game_id} is already started at {game_start} and is not finished yet! You cannot run more than one game in room at one moment!'.format(
                game_id=room_game.id,
                game_start=room_game.started
            ))

    g = Game(room=hosted_room)
    db.session.add(g)
    db.session.commit()

    players_list = []
    for player in hosted_room.connected_users.all():
        g.connect(player)
        p = Player(game_id=g.id, user_id=player.id)
        db.session.add(p)
        players_list.append(player.username)
    db.session.commit()

    return jsonify({
        'gameId': g.id,
        'room': g.room.room_name,
        'host': g.room.host.username,
        'status': 'active' if g.finished is None else 'finished',
        'started': g.started,
        'players': players_list
    }), 200


@game.route('{base_path}/game/finish'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
@cross_origin()
def finish():

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('user.post_token')))
    requesting_user = User.verify_api_auth_token(token)

    hosted_room = Room.query.filter_by(host=requesting_user, closed=None).first()
    if not hosted_room:
        abort(403, 'User {username} does not have open rooms! Create room by POST {create_room_url} before managing games.'.format(
            username=requesting_user.username,
            create_room_url=url_for('room.create')
        ))
    active_games = []
    for room_game in hosted_room.games:
        if room_game.finished is None:
            active_games.append(room_game)
    if len(active_games) != 1:
        abort(403, 'Room {room_name} has {active_games} active game(s)!'.format(room_name=hosted_room.room_name, active_games=len(active_games)))

    g = active_games[0]
    g.finished = datetime.utcnow()
    db.session.commit()

    players_list = []
    for player in hosted_room.connected_users.all():
        g.connect(player)
        players_list.append(player.username)

    return jsonify({
        'gameId': g.id,
        'room': g.room.room_name,
        'host': g.room.host.username,
        'status': 'active' if g.finished is None else 'finished',
        'started': g.started,
        'finished': g.finished,
        'players': players_list
    }), 200


@game.route('{base_path}/game/<game_id>/positions'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
@cross_origin()
def positions(game_id):

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('user.post_token')))
    requesting_user = User.verify_api_auth_token(token)

    game = Game.query.filter_by(id=game_id).first()
    if not game:
        abort(400, 'Game is not started yet!')

    room = Room.query.filter_by(id=game.room_id).first()
    if room.host != requesting_user:
        abort(403, 'Only host can shuffle positions!')

    players = Player.query.filter_by(game_id=game_id).all()
    for player in players:
        if player.position is not None:
            abort(403, 'Positions of players are already defined in this game!')

    players = game.players.all()
    random.shuffle(players)

    players_list = []
    for player in players:
        p = Player.query.filter_by(game_id=game_id,user_id=player.id).first()
        p.position = players.index(player) + 1
        db.session.commit()
        players_list.append({
            'username': User.query.filter_by(id=p.user_id).first().username,
            'position': p.position
        })

    return jsonify({
        'gameId': game_id,
        'players': players_list
    }), 200


@game.route('{base_path}/game/<game_id>'.format(base_path=app.config['API_BASE_PATH']), methods=['GET'])
@cross_origin()
def status(game_id):
    game = Game.query.filter_by(id=game_id).first()
    if not game:
        abort(404, 'Game with specified id is not found!')

    players = Player.query.filter_by(game_id=game_id).order_by(Player.position).all()
    players_enriched = []
    for player in players:
        user = User.query.filter_by(id=player.user_id).first()
        if user:
            players_enriched.append({
                'username': user.username,
                'position': player.position
            })

    current_hand = game.last_open_hand()
    played_hands_count = Hand.query.filter_by(game_id=game_id, is_closed=1).count()

    return jsonify({
            'gameId': game.id,
            'roomId': game.room_id,
            'currentHandId': current_hand.id if current_hand else None,
            'currentHandSerialNo': current_hand.serial_no if current_hand else None,
            'currentHandLocation': url_for('hand.status', hand_id=current_hand.id, game_id=game_id) if current_hand else None,
            'playedHandsCount': played_hands_count,
            'started': game.started,
            'status': 'open' if game.finished is None else 'finished',
            'finished': game.finished,
            'players': players_enriched
    }), 200
