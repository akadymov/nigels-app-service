# -*- coding: utf-8 -*-

from flask import url_for, request, jsonify, abort, Blueprint
from app import app, db
from app.models import User, Room, Game, Player, Hand, DealtCards, HandScore
import random
from math import floor


hand = Blueprint('hand', __name__)


@hand.route('{base_path}/game/<game_id>/hand/deal'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def deal_cards(game_id):

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('user.post_token')))
    requesting_user = User.verify_api_auth_token(token)

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


@hand.route('{base_path}/game/<game_id>/hand/<hand_id>/cards'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def get_hand_cards(game_id, hand_id):

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('user.post_token')))
    requesting_user = User.verify_api_auth_token(token)

    p = Player.query.filter_by(game_id=game_id, user_id=requesting_user.id).first()
    if p is None:
        abort(403, 'User {username} is not participating in game {game_id}!'.format(username=requesting_user.username, game_id=game_id))

    h = Hand.query.filter_by(id=hand_id).first()
    if h is None or h.is_closed == 1:
        abort(403, 'Hand {hand_id} is closed or does not exist!'.format(hand_id=hand_id))

    if str(request.args.get('burned')).lower() == 'y':
        cards = h.get_user_initial_hand(requesting_user)
    else:
        cards = h.get_user_current_hand(requesting_user)

    return jsonify({
        'game_id': game_id,
        'hand_id': hand_id,
        'cards_per_player': h.cards_per_player,
        'trump': h.trump,
        'player': requesting_user.username,
        'cards_in_hand': cards
    }), 200


@hand.route('{base_path}/game/<game_id>/hand/<hand_id>'.format(base_path=app.config['API_BASE_PATH']), methods=['GET'])
def status(game_id, hand_id):

    game = Game.query.filter_by(id=game_id).first()
    if not game:
        abort(404, 'Game with specified id is not found!')

    hand = Hand.query.filter_by(id=hand_id).first()
    if not hand:
        abort(404, 'Hand with specified id is not found')
    if int(hand.game_id) != int(game_id):
        abort(404, 'Specified hand is not part of specified game!')

    players = Player.query.filter_by(game_id=game_id).order_by(Player.position).all()
    players_enriched = []
    for player in players:
        user = User.query.filter_by(id=player.user_id).first()
        if user:
            user_scores = HandScore.query.filter_by(player_id=user.id).first()
            players_enriched.append({
                'username': user.username,
                'position': hand.get_position(user),
                'bet_size': user_scores.bet_size if user_scores else None,
                'took_turns': user_scores.took_turns() if user_scores else 0,
                'cards_on_hand': len(hand.get_user_current_hand(user))
            })

    current_turn = hand.get_current_turn(closed=True)
    next_player = hand.next_card_putting_user()

    return jsonify({
            'hand_id': hand.id,
            'next_acting_player': next_player.username if next_player else None,
            'game_id': game.id,
            'room_id': game.room_id,
            'hand_serial_no': hand.serial_no,
            'cards_per_player': hand.cards_per_player,
            'trump': hand.trump,
            'starting_player': hand.starting_player,
            'hand_is_closed': hand.is_closed,
            'players': players_enriched,
            'current_turn_serial_no': current_turn.serial_no if current_turn else None
    }), 200
