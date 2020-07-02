# -*- coding: utf-8 -*-

from flask import url_for, request, jsonify, abort, Blueprint
from flask_cors import cross_origin
from app import app, db
from app.models import User, Room
from datetime import datetime


room = Blueprint('room', __name__)


@room.route('{base_path}/room/all'.format(base_path=app.config['API_BASE_PATH']), methods=['GET'])
@cross_origin()
def get_list():
    rooms = Room.query.filter_by(closed=None).all()
    if str(request.args.get('closed')).lower() == 'y':
        rooms = Room.query.all()
    rooms_json = []
    for room in rooms:
        rooms_json.append({
            'roomId': room.id,
            'roomName': room.room_name,
            'host': room.host.username,
            'status': 'open' if room.closed is None else 'closed',
            'created': room.created,
            'closed': room.closed,
            'connectedUsers': room.connected_users.count(),
            'connect': url_for('room.connect', room_id=room.id)
        })

    return jsonify({'rooms': rooms_json}), 200


@room.route('{base_path}/room'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def create():

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('user.post_token')))

    requesting_user = User.verify_api_auth_token(token)

    hosted_room = Room.query.filter_by(host=requesting_user, closed=None).first()
    if hosted_room:
        abort(403, 'User {username} already has opened room {room_name}! Close it by POST {close_url} before creating new one.'.format(
            username=requesting_user.username,
            room_name=hosted_room.room_name,
            close_url=url_for('room.close', room_id=hosted_room.id)
        ))

    connected_room = requesting_user.connected_rooms
    if connected_room.count() > 0:
        abort(403, 'User {username} already is connected to other room! Disconnect before creating new one.'.format(username=requesting_user.username))

    room_name = request.json.get('roomName')
    new_room = Room(room_name=room_name, host=requesting_user, created=datetime.utcnow())
    db.session.add(new_room)
    new_room.connect(requesting_user)
    db.session.commit()

    return jsonify({
        'roomId': new_room.id,
        'roomName': new_room.room_name,
        'host': new_room.host.username,
        'created': new_room.created,
        'closed': new_room.closed,
        'connectedUsers': new_room.connected_users.count(),
        'status': 'open' if new_room.closed is None else 'closed',
        'connect': url_for('room.connect', room_id=new_room.id)
    }), 201


@room.route('{base_path}/room/<room_id>/close'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
@cross_origin()
def close(room_id):

    token = request.json.get('token')

    requesting_user = User.verify_api_auth_token(token)

    target_room = Room.query.filter_by(id=room_id).first()
    if target_room is None:
        abort(404, 'Room with id {room_id} is not found!'.format(room_id=room_id))
    if target_room.closed is not None:
        abort(400, 'Room {room_name} is already closed!'.format(room_name=target_room.room_name))
    if target_room.host != requesting_user:
        abort(403, 'Only host can close the room!')

    for game in target_room.games:
        game.finished = datetime.utcnow()

    for user in target_room.connected_users:
        target_room.disconnect(user)

    target_room.closed = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'roomId': target_room.id,
        'roomName': target_room.room_name,
        'host': target_room.host.username,
        'created': target_room.created,
        'status': 'open' if target_room.closed is None else 'closed',
        'closed': target_room.closed
    }), 201


@room.route('{base_path}/room/<room_id>/connect'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
@cross_origin()
def connect(room_id):

    token = request.json.get('token')

    requesting_user = User.verify_api_auth_token(token)

    connected_room = requesting_user.connected_rooms
    if connected_room.count() > 0:
        abort(403, 'User {username} already is connected to other room! Disconnect before connecting to new one.'.format(username=requesting_user.username))

    target_room = Room.query.filter_by(id=room_id).first()
    if target_room is None:
        abort(404, 'Room with id {room_id} is not found!'.format(room_id=room_id))
    if target_room.closed is not None:
        abort(400, 'Room {room_name} is closed!'.format(room_name=target_room.room_name))
    if target_room.is_connected(requesting_user):
        abort(400, 'User {username} is already connected to room {room_name}!'.format(username=requesting_user.username, room_name=target_room.room_name))
    if target_room.connected_users.count() >= app.config['MAX_USERS_PER_ROOM']:
        abort(403, 'Maximum number of players exceeded for room {room_name}!'.format(room_name=target_room.room_name))

    target_room.connect(requesting_user)
    db.session.commit()

    return jsonify(200)


@room.route('{base_path}/room/<room_id>/disconnect'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
@cross_origin()
def disconnect(room_id):

    token = request.json.get('token')

    requesting_user = User.verify_api_auth_token(token)

    target_room = Room.query.filter_by(id=room_id).first()
    if target_room is None:
        abort(404, 'Room with id {room_id} is not found!'.format(room_id=room_id))
    if target_room.closed is not None:
        abort(400, 'Room {room_name} is closed!'.format(room_name=target_room.room_name))
    if not target_room.is_connected(requesting_user):
        abort(400, 'User {username} is not connected to room {room_name}!'.format(username=requesting_user.username, room_name=target_room.room_name))
    if target_room.host == requesting_user:
        abort(403, 'Host cannot disconnect the room!')

    target_room.disconnect(requesting_user)

    return jsonify(200)


@room.route('{base_path}/room/<room_id>'.format(base_path=app.config['API_BASE_PATH']), methods=['GET'])
@cross_origin()
def status(room_id):
    room = Room.query.filter_by(id=room_id).first()
    if not room:
        abort(404, 'Room with specified id is not found!')

    connected_users = room.connected_users
    users_json = []
    for u in connected_users:
        users_json.append(u.username)
    games = room.games
    games_json = []
    for game in games:
        games_json.append({
            'id': game.id,
            'status': 'open' if game.finished is None else 'finished'
        })

    return jsonify({
            'roomId': room.id,
            'roomName': room.room_name,
            'host': room.host.username,
            'status': 'open' if room.closed is None else 'closed',
            'created': room.created,
            'closed': room.closed,
            'connectedUserList': users_json,
            'connect': url_for('room.connect', room_id=room.id),
            'games': games_json
    }), 200
