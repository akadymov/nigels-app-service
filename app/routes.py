# -*- coding: utf-8 -*-
from app import app, db
from app.models import User, Room
from flask import jsonify


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
@app.route('/rooms', methods=['GET'])
def get_rooms():
    rooms = Room.query.all()
    rooms_json = []
    """for room in rooms:
        rooms_json.append({
            'room_id': room.id,
            'room_name': room.room_name,
            'host': room.host.username,
            'created': room.created,
            'finished': room.finished,
            'connected_users': room.connected_users.count()
        })"""

    # temporary mock up

    rooms = [
        {
            'id': 1,
            'room_name': u'First Room',
            'host':  'akadymov',
            'created': '2020-04-08 14:00:00 GMT',
            'finished': None,
            'connected_users': 2
        },
        {
            'id': 2,
            'room_name': u'Second Room',
            'host': 'gsukhy',
            'created': '2020-04-08 14:30:00 GMT',
            'finished': None,
            'connected_users': 0
        }
    ]
    for room in rooms:
        rooms_json.append({
            'room_id': room['id'],
            'room_name': room['room_name'],
            'host': room['host'],
            'created': room['created'],
            'finished': room['finished'],
            'connected_users': room['connected_users'],
        })

    return jsonify({'rooms': rooms_json})
