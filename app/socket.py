from app import socketio
from flask_socketio import emit, send, join_room, leave_room


@socketio.on('connect')
def connect():
    print('New socket connection established')
    emit("connect", {'eventCategory': 'service_events', 'event': 'server connection established'})


@socketio.on('create_room', namespace='/lobby')
def create_room(room_name):
    print('New room ' + str(room_name) + ' was created')
    emit('update_lobby', {'eventCategory': 'lobby', 'event': 'create', 'roomName': room_name}, broadcast=True)


@socketio.on('remove_room_from_lobby', namespace='/lobby')
def remove_room_from_lobby(room_id):
    print('Room#' + str(room_id) + ' was closed')
    emit('update_lobby', {'eventCategory': 'lobby', 'event': 'create', 'roomId': room_id}, broadcast=True)


@socketio.on('connect_to_room', namespace='/room')
def connect_to_room(username, room_id):
    join_room(room_id)
    print('User ' + str(username) + ' connected to Room #' + str(room_id))
    emit("update_room", {'eventCategory': 'room', 'event': 'connect', 'roomId': room_id, 'username': username}, broadcast=True)#, to=room_id)


@socketio.on('disconnect_from_room', namespace='/room')
def disconnect_from_room(username, room_id):
    leave_room(room_id)
    print('User ' + str(username) + ' disconnected from Room #' + str(room_id))
    emit("update_room", {'eventCategory': 'room', 'event': 'disconnect', 'roomId': room_id, 'username': username}, broadcast=True)#, to=room_id)


@socketio.on('ready', namespace='/room')
def ready(username, room_id):
    print('User ' + str(username) + ' is ready to start in Room #' + str(room_id))
    emit("update_room", {'eventCategory': 'room', 'event': 'ready', 'roomId': room_id, 'username': username}, broadcast=True)#, to=room_id)


@socketio.on('not_ready', namespace='/room')
def not_ready(username, room_id):
    print('User ' + str(username) + ' is NOT ready to start in Room #' + str(room_id))
    emit("update_room", {'eventCategory': 'room', 'event': 'not ready', 'roomId': room_id, 'username': username}, broadcast=True)#, to=room_id)


@socketio.on('close_room', namespace='/room')
def close_room(room_id):
    print('Host has closed Room #' + str(room_id))
    emit("exit_room", {'eventCategory': 'room', 'event': 'close', 'roomId': room_id}, broadcast=True)#, to=room_id)