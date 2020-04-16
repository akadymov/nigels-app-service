# -*- coding: utf-8 -*-

from flask import render_template, flash, redirect, url_for, request, jsonify, abort
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm
from app.models import User, Room, Game, Player, Hand, DealtCards, HandScore, TurnCard, Turn
from app.social_login import OAuthSignIn
from datetime import datetime
import re
import random
from math import floor


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def index():
    return 'This is Nigels App Service Home! Work In Progress!'


@app.route('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def create_user():
    username = request.json.get('username')
    email = request.json.get('email')
    preferred_lang = request.json.get('preferred_lang') or app.config['DEFAULT_LANG']
    password = request.json.get('password')
    last_seen = datetime.utcnow()
    registered = datetime.utcnow()
    if username is None or \
            password is None or \
            email is None:
        abort(400, 'Missing mandatory arguments (username, password or email)!')
    if not re.match(app.config['USERNAME_REGEXP'], password):
        abort(400, 'Bad username!')
    if not re.match(app.config['EMAIL_REGEXP'], email):
        abort(400, 'Bad email!')
    if not re.match(app.config['PASSWORD_REGEXP'], password):
        abort(400, 'Password does not satisfy security requirements!')
    if User.query.filter_by(username=username).first() is not None:
        abort(400, 'User with username {username} already exists!'.format(username=username))
    if User.query.filter_by(email=email).first() is not None:
        abort(400, 'User with email {email} already exists!'.format(email=email))
    if preferred_lang not in ['ru', 'en']:
        abort(400, 'Language {lang} is not supported!'.format(lang=preferred_lang))
    user = User(
        username=username,
        email=email,
        preferred_language=preferred_lang,
        last_seen=last_seen,
        registered=registered
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return \
        jsonify({
            'username': user.username,
            'email': user.email,
            'preferred_lang': user.preferred_language,
            'registered': user.registered,
            'last_seen': user.last_seen,
            'about_me': user.about_me
        }), \
        201, \
        {'Location': url_for('get_user', username=username, _external=True)}


@app.route('{base_path}/user/<username>'.format(base_path=app.config['API_BASE_PATH']), methods=['GET'])
def get_user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404, 'User {username} not found!'.format(username=username))
    return jsonify({
        'username': user.username,
        'email': user.email,
        'preferred_lang': user.preferred_language,
        'registered': user.registered,
        'last_seen': user.last_seen,
        'about_me': user.about_me
    }), 200


@app.route('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def post_token():
    username = request.json.get('username')
    password = request.json.get('password')
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(str(password)):
        abort(401, 'Invalid username or password')
    else:
        token = user.generate_auth_token()
        return jsonify({
            'token': token.decode('ascii'),
            'expires_in': app.config['TOKEN_LIFETIME']
        })


@app.route('{base_path}/user/<username>'.format(base_path=app.config['API_BASE_PATH']), methods=['PUT'])
def edit_user(username):

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))

    modified_user = User.query.filter_by(username=username).first()
    if modified_user is None:
        abort(404, 'User {username} not found!'.format(username=username))
    if modified_user != requesting_user:
        abort(401, 'You can update only your own profile ({username})!'.format(username=str(requesting_user)))

    email = request.json.get('email') or modified_user.email
    about_me = request.json.get('about_me') or modified_user.about_me
    preferred_lang = request.json.get('preferred_lang') or modified_user.preferred_language
    if not re.match(app.config['EMAIL_REGEXP'], email):
        abort(400, 'Bad email!')
    conflict_user = User.query.filter_by(email=email).first()
    if conflict_user is not None and conflict_user != modified_user:
        abort(400, 'User with email {email} already exists!'.format(email=email))
    if preferred_lang not in ['ru', 'en']:
        abort(400, 'Language {lang} is not supported!'.format(lang=preferred_lang))

    modified_user.email = email
    modified_user.about_me = about_me
    modified_user.preferred_language = preferred_lang
    modified_user.last_seen = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'username': modified_user.username,
        'email': modified_user.email,
        'preferred_lang': modified_user.preferred_language,
        'registered': modified_user.registered,
        'last_seen': modified_user.last_seen,
        'about_me': modified_user.about_me
    }), 200


@app.route('{base_path}/room'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def create_room():

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))

    hosted_room = Room.query.filter_by(host=requesting_user, closed=None).first()
    if hosted_room:
        abort(403, 'User {username} already has opened room {room_name}! Close it by POST {close_room_url} before creating new one.'.format(
            username=requesting_user.username,
            room_name=hosted_room.room_name,
            close_room_url=url_for('close_room', room_id=hosted_room.id)
        ))

    connected_room = requesting_user.connected_rooms
    if connected_room.count() > 0:
        abort(403, 'User {username} already is connected to other room! Disconnect before creating new one.'.format(username=requesting_user.username))

    room_name = request.json.get('room_name')
    new_room = Room(room_name=room_name, host=requesting_user, created=datetime.utcnow())
    db.session.add(new_room)
    new_room.connect(requesting_user)
    db.session.commit()

    return jsonify({
        'room_id': new_room.id,
        'room_name': new_room.room_name,
        'host': new_room.host.username,
        'created': new_room.created,
        'closed': new_room.closed,
        'connected_users': new_room.connected_users.count(),
        'status': 'open' if new_room.closed is None else 'closed',
        'connect': url_for('connect_room', room_id=new_room.id)
    }), 201


@app.route('{base_path}/room/<room_id>/close'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def close_room(room_id):

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))

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
        'room_id': target_room.id,
        'room_name': target_room.room_name,
        'host': target_room.host.username,
        'created': target_room.created,
        'status': 'open' if target_room.closed is None else 'closed',
        'closed': target_room.closed
    }), 201


@app.route('{base_path}/room/<room_id>/connect'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def connect_room(room_id):

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))

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


@app.route('{base_path}/room/<room_id>/disconnect'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def disconnect_room(room_id):

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))

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


@app.route('{base_path}/room/all'.format(base_path=app.config['API_BASE_PATH']), methods=['GET'])
def get_rooms():
    rooms = Room.query.filter_by(closed=None).all()
    if str(request.args.get('closed')).lower() == 'y':
        rooms = Room.query.all()
    rooms_json = []
    for room in rooms:
        rooms_json.append({
            'room_id': room.id,
            'room_name': room.room_name,
            'host': room.host.username,
            'status': 'open' if room.closed is None else 'closed',
            'created': room.created,
            'closed': room.closed,
            'connected_users': room.connected_users.count(),
            'connect': url_for('connect_room', room_id=room.id)
        })

    return jsonify({'rooms': rooms_json}), 200


@app.route('{base_path}/game/start'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def start_game():

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))

    hosted_room = Room.query.filter_by(host=requesting_user, closed=None).first()
    if not hosted_room:
        abort(403, 'User {username} does not have open rooms! Create room by POST {create_room_url} before managing games.'.format(
            username=requesting_user.username,
            create_room_url=url_for('create_room')
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
        'game_id': g.id,
        'room': g.room.room_name,
        'host': g.room.host.username,
        'status': 'active' if g.finished is None else 'finished',
        'started': g.started,
        'players': players_list
    }), 200


@app.route('{base_path}/game/finish'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def finish_game():

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))

    hosted_room = Room.query.filter_by(host=requesting_user, closed=None).first()
    if not hosted_room:
        abort(403, 'User {username} does not have open rooms! Create room by POST {create_room_url} before managing games.'.format(
            username=requesting_user.username,
            create_room_url=url_for('create_room')
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
        'game_id': g.id,
        'room': g.room.room_name,
        'host': g.room.host.username,
        'status': 'active' if g.finished is None else 'finished',
        'started': g.started,
        'finished': g.finished,
        'players': players_list
    }), 200


@app.route('{base_path}/game/<game_id>/positions'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def define_positions(game_id):

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))

    game = Game.query.filter_by(id=game_id).first()
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
        'game_id': game_id,
        'players': players_list
    }), 200


@app.route('{base_path}/game/<game_id>/hand/deal'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def deal_cards(game_id):

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))

    game = Game.query.filter_by(id=game_id).first()
    room = Room.query.filter_by(id=game.room_id).first()
    if room.host != requesting_user:
        abort(403, 'Only host can deal cards!')

    if game.has_open_hands():
        abort(403, 'Game {game_id} has open hand {hand_id}! You should finish it before dealing new hand!'.format(game_id=game_id, hand_id=game.last_open_hand().id))

    # no more hands allowed
    if game.all_hands_played():
        abort(403, 'All hands in game {game_id} are already dealt!'.format(game_id=game_id))

    # first hand configuration by default
    serial_no = 1
    trump = 'd'
    cards_per_player = min(floor(52/game.players.count()), 10)
    starting_player = game.get_starter()
    new_hand_id = 1
    # FIXME: for some reason hand.id autoincrement does not work - it's temporary fix until autoincrement is restored
    last_hand = Hand.query.order_by(Hand.id.desc()).first()
    if last_hand:
        new_hand_id = last_hand.id + 1

    # hand configuration based on previous hands configuration
    last_closed_hand = Hand.query.filter_by(game_id=game_id, is_closed=1).order_by(Hand.serial_no.desc()).first()
    if last_closed_hand:

        # serial_no for new hand
        serial_no = int(last_closed_hand.serial_no) + 1

        # next trump
        if last_closed_hand.trump == 'd':
            trump = 'h'
        elif last_closed_hand.trump == 'h':
            trump = 'c'
        elif last_closed_hand.trump == 'c':
            trump = 's'
        elif last_closed_hand.trump == 's':
            trump = None
        else:
            trump = 'd'

        # defining number of cards to be dealt in new hand
        single_card_closed_hands = Hand.query.filter_by(game_id=game_id, is_closed=1, cards_per_player=1).all()
        if len(single_card_closed_hands) == 2:
            if last_closed_hand.cards_per_player == 1:
                cards_per_player = 1
            else:
                cards_per_player = last_closed_hand.cards_per_player + 1
        else:
            cards_per_player = last_closed_hand.cards_per_player - 1

        # next starting player is the one who was second is previous hand
        starting_player = last_closed_hand.get_player_by_pos(2)

    h = Hand(id=new_hand_id, game_id=int(game_id), serial_no=serial_no, trump=trump, cards_per_player=cards_per_player, starting_player=starting_player.id)
    db.session.add(h)

    # creating and shuffling card deck
    deck = []
    card_grades = list(range(2, 10))
    card_grades.append('t')
    card_grades.append('j')
    card_grades.append('q')
    card_grades.append('k')
    card_grades.append('a')
    suits = ['d', 'h', 'c', 's']
    # d for diamond, h for hearts, c for clubs, s for spades
    for grade in card_grades:
        for suit in suits:
            deck.append(str(grade) + str(suit))

    random.shuffle(deck)

    # deal (distribute) cards
    i = 0
    # dcs_json = {}
    for card in deck:
        i = i + 1
        if i <= cards_per_player * game.players.count():
            card_player = h.get_player_by_pos(deck.index(card) % game.players.count() + 1)
            dc = DealtCards(hand_id=h.id, card_id=card, player_id=card_player.id)
            db.session.add(dc)

    """players_cards = {}
    for player in game.players.all():
        player_obj = User.query.filter_by(id=player.id).first()
        player_cards = h.get_user_initial_hand(player_obj)
        players_cards[player_obj.username]=player_cards"""

    db.session.commit()

    return jsonify(
        {
            'hand_id': h.id,
            'game_id': h.game_id,
            'dealt_cards_per_player': h.cards_per_player,
            'trump': h.trump,
            'starting_player': starting_player.username,
            # 'dealt_cards': players_cards
        }
    ), 200


@app.route('{base_path}/game/<game_id>/hand/<hand_id>/turn/bet'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def make_bet(game_id, hand_id):

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))

    bet_size = request.json.get('bet_size')
    if bet_size is None:
        abort(400, 'No bet size in request!')

    p = Player.query.filter_by(game_id=game_id, user_id=requesting_user.id).first()
    if p is None:
        abort(403, 'User {username} is not participating in game {game_id}!'.format(username=requesting_user.username, game_id=game_id))

    game = Game.query.filter_by(id=game_id).first()

    h = Hand.query.filter_by(id=hand_id).first()
    if h is None or h.is_closed == 1:
        abort(403, 'Hand {hand_id} is closed or does not exist!'.format(hand_id=hand_id))

    requesting_player_bet = HandScore.query.filter_by(hand_id=hand_id, player_id=requesting_user.id).first()
    if requesting_player_bet:
        abort(403, 'User {username} already has made a bet in hand {hand_id}!'.format(username=requesting_user.username, hand_id=hand_id))

    # check if it's your turn
    requesting_player_current_pos = h.get_position(requesting_user)
    if not h.is_registered(requesting_user):
        abort(400, 'User {username} is not registered in hand {hand_id} of game {game_id}!'.format(username=requesting_user.username, hand_id=hand_id, game_id=game_id))
    next_betting_user = h.next_betting_user()
    if next_betting_user != requesting_user:
        abort(403, "It is {username}'s turn now!".format(username=next_betting_user.username))

    # "Someone should stay unhappy" (rule name)
    made_bets = h.get_sum_of_bets()
    is_last_bet = h.is_betting_last(requesting_user)
    if is_last_bet and bet_size + made_bets == h.cards_per_player:
        abort(400, 'Someone should stay unhappy! Change your bet size since you are last betting player in hand.')

    hs = HandScore(player_id=requesting_user.id, hand_id=hand_id, bet_size=bet_size)
    db.session.add(hs)
    db.session.commit()

    next_player = h.next_betting_user()

    return jsonify({
        'number_of_players': game.players.count(),
        'serial_number_of_hand': h.serial_no,
        'player_position': requesting_player_current_pos,
        'is_last_player_to_bet': is_last_bet,
        'next_player_to_bet': next_player.username if next_player and not is_last_bet else None,
        'made_bets': made_bets + bet_size,
        'cards_per_player = restricted sum of bets': h.cards_per_player
    }), 200


@app.route('{base_path}/game/<game_id>/hand/<hand_id>/turn/card/put/<card_id>'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def put_card(game_id, hand_id, card_id):

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))

    p = Player.query.filter_by(game_id=game_id, user_id=requesting_user.id).first()
    if p is None:
        abort(403, 'User {username} is not participating in game {game_id}!'.format(username=requesting_user.username, game_id=game_id))

    h = Hand.query.filter_by(id=hand_id).first()
    if h is None or h.is_closed == 1:
        abort(403, 'Hand {hand_id} is closed or does not exist!'.format(hand_id=hand_id))

    if h.all_turns_made():
        abort(403, 'All turns are made in hand {hand_id} of game {game_id}!'.format(hand_id=hand_id, game_id=game_id))

    t = h.get_current_turn()
    if t and t.if_put_card(requesting_user):
        abort(403, 'Player {username} has already put card in current turn of hand {hand_id}!'.format(username=requesting_user.username, hand_id=hand_id))

    curr_player = h.next_card_putting_user()
    if requesting_user != curr_player:
        abort(403, "It is {username}'s turn now!".format(username=curr_player.username))

    card_id = card_id.casefold()

    player_current_hand = h.get_user_current_hand(requesting_user)
    if card_id not in player_current_hand:
        abort(403, 'Player {username} does not have card {card_id} on his hand!'.format(username=requesting_user.username, card_id=card_id))

    last_turn = h.get_last_turn()
    serial_no = 1
    if last_turn:
        serial_no = last_turn.serial_no + 1

    if not t:
        t = Turn(
            hand_id=hand_id,
            serial_no=serial_no
        )
        db.session.add(t)

    if len(t.stroke_cards()) > 0 and len(player_current_hand) > 1:
        turn_suit = t.get_starting_suit()
        card_suit = card_id[-1:]
        card_score = str(card_id[:1])
        if card_id != 'J' + str(h.trump):
            if h.user_has_suit(suit=turn_suit, user=requesting_user) and card_suit != turn_suit and card_suit != h.trump:
                abort(403, 'You should put card of following suits: {turn_suit} or {trump}'.format(turn_suit=turn_suit, trump=h.trump))
            trump_hierarchy = ['2', '3', '4', '5', '6', '7', '8', 't', 'q', 'k', 'a', '9', 'j']
            if card_suit == h.trump and turn_suit != h.trump and t.highest_card()[-1:]==h.trump.casefold() and trump_hierarchy.index(card_score) < trump_hierarchy.index(t.highest_card()[:1]):
                abort(403, 'You cannot utilize lower trumps!')

    tc = TurnCard(player_id=requesting_user.id, card_id=card_id, turn_id=t.id, hand_id=hand_id)
    db.session.add(tc)

    db.session.commit()

    t = Turn.query.filter_by(id=t.id).first()

    took_player = None
    if len(t.stroke_cards()) == Game.query.filter_by(id=game_id).first().players.count():
        took_player = User.query.filter_by(id=DealtCards.query.filter_by(hand_id=hand_id, card_id=t.highest_card().casefold()).first().player_id).first()
        t.took_user_id = took_player.id

    db.session.commit()

    cards_on_table = []
    for card in t.stroke_cards():
        cards_on_table.append(card.card_id)

    return jsonify({
        'turn_no': t.serial_no,
        'cards_on_table': cards_on_table,
        'starting_suit': t.get_starting_suit(),
        'highest_card': t.highest_card(),
        'took_player': took_player.username if took_player else None
    }), 200


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            last_seen=datetime.utcnow(),
            registered=datetime.utcnow(),
            preferred_language=form.preferred_language.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


# social login oauth
@app.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()


# social login callback oauth
@app.route('/callback/<provider>')
def oauth_callback(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    social_id, username, email, gender, timezone, locale, pic = oauth.callback()
    if social_id is None:
        flash('Authentication failed.')
        return redirect(url_for('index'))
    user = User.query.filter_by(social_id=social_id).first()
    if not user:
        user = User.query.filter_by(email=email).first()
    if user:
        user.facebook_pic = pic
        user.social_id = social_id
    else:
        user = User(social_id=social_id, username=username, email=email, facebook_pic=pic)
        db.session.add(user)
    db.session.commit()
    login_user(user, True)
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))
