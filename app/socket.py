from app import socketio
from flask_socketio import emit #, join_room, leave_room


@socketio.on('connect', namespace='/lobby')
def connect():
    print('New socket connection established')
    # emit("connect", {'eventCategory': 'service_events', 'event': 'server connection established'})


@socketio.on('create_room', namespace='/lobby')
def create_room(room_id, room_name, host, created):
    print('New room "' + str(room_name) + '" was created')
    emit(
        'update_lobby',
        {
            'eventCategory': 'lobby',
            'event': 'create',
            'roomId': room_id,
            'roomName': room_name,
            'host': host,
            'created': created
        },
        json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('remove_room_from_lobby', namespace='/lobby')
def remove_room_from_lobby(room_name):
    print('Room ' + str(room_name) + ' was closed')
    emit(
        'update_lobby',
        {
            'eventCategory': 'lobby',
            'event': 'close',
            'roomName': room_name
        },
        json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('increase_room_players', namespace='/lobby')
def connect_to_room(username, room_id, room_name, connected_users):
    # join_room(room_id)
    print('User ' + str(username) + ' connected to Room "' + str(room_name) + '" (now connected ' + str(connected_users) + ' players).')
    emit(
        'update_lobby',
        {
            'eventCategory': 'lobby',
            'event': 'connect',
            'roomId': room_id,
            'roomName': room_name,
            'connectedUsers': connected_users,
            'actor': username
        },
        namespace='/lobby',
        # to=room_id,
        broadcast=True
    )


@socketio.on('add_player_to_room', namespace='/room')
def connect_to_room(username, room_id, room_name, connected_users):
    emit(
        "update_room",
        {
            'eventCategory': 'room',
            'event': 'connect',
            'roomId': room_id,
            'roomName': room_name,
            'connectedUsers': connected_users,
            'username': username,
            'actor': username
        },
        json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('decrease_room_players', namespace='/lobby')
def disconnect_from_room(actor, username, room_id, room_name, connected_users):
    # leave_room(room_id)
    print('User ' + str(username) + ' disconnected from Room "' + str(room_name) + '" (now connected ' + str(connected_users) + ' players).')
    emit(
        'update_lobby',
        {
            'eventCategory': 'lobby',
            'event': 'disconnect',
            'roomId': room_id,
            'roomName': room_name,
            'connectedUsers': connected_users,
            'actor': actor
        },
        namespace='/lobby',
        # to=room_id,
        broadcast=True
    )


@socketio.on('remove_player_from_room', namespace='/room')
def disconnect_from_room(actor, username, room_id, room_name, connected_users):
    emit(
        "update_room",
        {
            'eventCategory': 'room',
            'event': 'disconnect',
            'roomId': room_id,
            'roomName': room_name,
            'connectedUsers': connected_users,
            'username': username,
            'actor': actor
        },
        json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('ready', namespace='/room')
def ready(actor, username, room_id):
    print('User ' + str(username) + ' is ready to start in Room #' + str(room_id))
    emit(
        "update_room",
        {
            'eventCategory': 'room',
            'event': 'ready',
            'roomId': room_id,
            'username': username,
            'actor': actor
        },
        json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('not_ready', namespace='/room')
def not_ready(actor, username, room_id):
    print('User ' + str(username) + ' is NOT ready to start in Room #' + str(room_id))
    emit(
        "update_room",
        {
            'eventCategory': 'room',
            'event': 'not ready',
            'roomId': room_id,
            'username': username,
            'actor': actor
        },
        json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('close_room', namespace='/room')
def close_room(actor, room_name):
    print('Host has closed Room ' + str(room_name))
    emit(
        "exit_room",
        {
            'eventCategory': 'room',
            'event': 'close',
            'roomName': room_name,
            'username': 0,
            'actor': actor
        },
        # to=room_id,
        broadcast=True
    )


@socketio.on('remove_room_from_lobby', namespace='/lobby')
def remove_room_from_lobby (room_name):
    emit(
        'update_lobby',
        {
            'eventCategory': 'lobby',
            'event': 'close',
            'roomName': room_name
        },
        json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('start_game_in_room', namespace='/room')
def start_game(actor, game_id, room_id):
    print('Game #' + str(game_id) + ' started in room #' + str(room_id))
    emit(
        "start_game",
        {
            "eventCategory": "game",
            "event": "start",
            "gameId": game_id,
            "roomId": room_id,
            'actor': actor
        },
        json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('define_positions', namespace='/game')
def define_positions(game_id, players_array):
    print('Defined positions in game #' + str(game_id))
    emit(
        "refresh_game_table",
        {
            'eventCategory': 'game',
            'event': 'define positions',
            'gameId': game_id,
            'players': players_array
        },
        json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('deal_cards', namespace='/game')
def deal_cards(game_id):
    print('Dealt cards in game #' + str(game_id))
    emit(
        "refresh_game_table",
        {
            'eventCategory': 'game',
            'event': 'deal cards',
            'gameId': game_id
        },
        json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('make_bet', namespace='/game')
def make_bet(game_id, hand_id, actor, bet_size, next_betting_player):
    print('Player "' + str(actor) + '" made bet of size: ' + str(bet_size) + ' in hand #' + str(hand_id) + ' of game #' + str(game_id))
    emit(
        "refresh_game_table",
        {
            'eventCategory': 'game',
            'event': 'make bet',
            'gameId': game_id,
            'hadnId': hand_id,
            'actor': actor,
            'betSize': bet_size,
            'nextPlayerToBet': next_betting_player
        },
        json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('next_turn', namespace='/game')
def next_turn(game_id, hand_id, actor):
    print('Next turn in game #' + str(game_id))
    emit(
        "refresh_game_table",
        {
            'eventCategory': 'game',
            'event': 'next turn',
            'gameId': game_id,
            'actor': actor
        },
        json=True,
        # to=room_id,
        broadcast=True
    )