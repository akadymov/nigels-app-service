from app import socketio, app
from flask_socketio import emit #, join_room, leave_room


@socketio.on('connect', namespace='/lobby')
def connect():
    if app.debug:
        print('New socket connection established')
    # emit("connect", {'eventCategory': 'service_events', 'event': 'server connection established'})


@socketio.on('create_room', namespace='/lobby')
def create_room(room_id, room_name, host, created):
    if app.debug:
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
def remove_room_from_lobby(room_id):
    if app.debug:
        print('Room #' + str(room_id) + ' was closed')
    emit(
        'update_lobby',
        {
            'eventCategory': 'lobby',
            'event': 'close',
            'roomId': room_id
        },
        json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('increase_room_players', namespace='/lobby')
def connect_to_room(username, room_id, room_name, connected_users):
    # join_room(room_id)
    if app.debug:
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
    if app.debug:
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


@socketio.on('ready', namespace='/room')
def ready(actor, username, room_id):
    if app.debug:
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
        namespace='/room',
        # json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('not_ready', namespace='/room')
def not_ready(actor, username, room_id):
    if app.debug:
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
        namespace='/room',
        # json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('close_room', namespace='/room')
def close_room(actor, room_id):
    if app.debug:
        print('Host has closed Room #' + str(room_id))
    emit(
        "exit_room",
        {
            'eventCategory': 'room',
            'event': 'close',
            'roomId': room_id,
            'username': 0,
            'actor': actor
        },
        # to=room_id,
        namespace='/room',
        broadcast=True
    )
    emit(
        'update_lobby',
        {
            'eventCategory': 'lobby',
            'event': 'close',
            'roomId': room_id
        },
        # to=room_id,
        namespace='/lobby',
        broadcast=True
    )


@socketio.on('remove_room_from_lobby', namespace='/lobby')
def remove_room_from_lobby (room_id):
    emit(
        'update_lobby',
        {
            'eventCategory': 'lobby',
            'event': 'close',
            'roomId': room_id
        },
        json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('start_game_in_room', namespace='/room')
def start_game(actor, game_id, room_id):
    if app.debug:
        print('Game #' + str(game_id) + ' started in room #' + str(room_id))
    emit(
        "start_game",
        {
            "eventCategory": "game",
            "event": "start",
            "gameId": game_id,
            "roomId": int(room_id),
            'actor': actor
        },
        json=True,
        # to=room_id,
        broadcast=True,
        namespace='/room'
    )
    emit(
        'update_lobby',
        {
            'eventCategory': 'lobby',
            'event': 'start',
            'roomId': room_id,
            'newStatus': 'started'
        },
        json=True,
        # to=room_id,
        broadcast=True,
        namespace='/room'
    )


@socketio.on('define_positions', namespace='/game')
def define_positions(game_id, players_array):
    if app.debug:
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
        namespase='/game',
        # to=room_id,
        broadcast=True
    )


@socketio.on('deal_cards', namespace='/game')
def deal_cards(game_id):
    if app.debug:
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
def make_bet(game_id, hand_id, actor, bet_size, is_last_bet, next_acting_player):
    if app.debug:
        print('Player "' + str(actor) + '" made bet of size: ' + str(bet_size) + ' in hand #' + str(hand_id) + ' of game #' + str(game_id))
    emit(
        "refresh_game_table",
        {
            'eventCategory': 'game',
            'event': 'make bet',
            'gameId': game_id,
            'handId': hand_id,
            'actor': actor,
            'betSize': bet_size,
            'nextActingPlayer': next_acting_player,
            'isLastPlayerToBet': is_last_bet
        },
        json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('put_card', namespace='/game')
def next_turn(game_id, hand_id, actor, cards_on_table, took_player, next_player, is_last_card_in_hand):
    if app.debug:
        print('Next turn in game #' + str(game_id))
    emit(
        "refresh_game_table",
        {
            'eventCategory': 'game',
            'event': 'put card',
            'gameId': game_id,
            'actor': actor,
            'cardsOnTable': cards_on_table,
            'tookPlayer': took_player,
            'nextActingPlayer': next_player,
            'isLastCardInHand': is_last_card_in_hand
        },
        json=True,
        # to=room_id,
        broadcast=True
    )


@socketio.on('finish_game_in_room', namespace='/game')
def finish_game(actor, game_id, room_id):
    if app.debug:
        print('Game #' + str(game_id) + ' finished in room #' + str(room_id))
    emit(
        "refresh_game_table",
        {
            "eventCategory": "game",
            "event": "finish",
            "gameId": game_id,
            "roomId": room_id,
            'actor': actor
        },
        json=True,
        # to=room_id,
        broadcast=True,
        namespace='/game'
    )
    emit(
        "finish_game",
        {
            "eventCategory": "game",
            "event": "finish",
            "gameId": game_id,
            "roomId": room_id,
            'actor': actor
        },
        json=True,
        # to=room_id,
        broadcast=True,
        namespace='/room'
    )
    emit(
        'update_lobby',
        {
            'eventCategory': 'lobby',
            'event': 'finish',
            'roomId': room_id,
            'newStatus': 'started'
        },
        json=True,
        # to=room_id,
        broadcast=True,
        namespace='/lobby'
    )