# -*- coding: utf-8 -*-

from flask import url_for, request, jsonify, Blueprint
from flask_cors import cross_origin
from app import app, db
from app.models import User, Room, Game, Player, Hand, DealtCards, HandScore
import random
from math import floor
from config import get_settings, get_environment


hand = Blueprint('hand', __name__)
env = get_environment()


@hand.route('{base_path}/game/<game_id>/hand/deal'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['POST'])
@cross_origin()
def deal_cards(game_id):

    token = request.json.get('token')
    if token is None:
        return jsonify({
            'errors':[
                {'message': 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('user.post_token'))}
            ]
        }), 401
    requesting_user = User.verify_api_auth_token(token)

    game = Game.query.filter_by(id=game_id).first()
    room = Room.query.filter_by(id=game.room_id).first()
    if room.host != requesting_user:
        return jsonify({
            'errors': [
                {
                    'message': 'Only host can deal cards!'
                }
            ]
        }), 403

    if game.has_open_hands():
        return jsonify({
            'errors':[
                {
                    'message': 'Game {game_id} has open hand {hand_id}! You should finish it before dealing new hand!'.format(game_id=game_id, hand_id=game.last_open_hand().id)
                }
            ]
        }), 403

    # no more hands allowed
    if game.all_hands_played():
        return jsonify({
            'errors':[
                {
                    'message': 'All hands in game {game_id} are already dealt!'.format(game_id=game_id)
                }
            ]
        }), 403

    # first hand configuration by default
    serial_no = 1
    trump = 'd'
    cards_per_player = min(floor(52/game.players.count()), 10)
    starting_player = game.get_starter()
    if app.debug:
        print('Game starter is ' + str(starting_player.username))
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
        if len(single_card_closed_hands) == 0:
            cards_per_player = last_closed_hand.cards_per_player - 1
        elif len(single_card_closed_hands) == 1 and last_closed_hand.cards_per_player == 1:
            cards_per_player = 1
        elif len(single_card_closed_hands) == 2:
            cards_per_player = last_closed_hand.cards_per_player + 1
        else:
            print('Cannot calculate cards per player count in hand #' + str(new_hand_id) + ' of game #' + str(game_id))

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
            dc = DealtCards(hand_id=h.id, card_id=card[:1], card_suit=card[1:], player_id=card_player.id)
            db.session.add(dc)

    """players_cards = {}
    for player in game.players.all():
        player_obj = User.query.filter_by(id=player.id).first()
        player_cards = h.get_user_initial_hand(player_obj)
        players_cards[player_obj.username]=player_cards"""

    db.session.commit()

    return jsonify(
        {
            'handId': h.id,
            'gameId': h.game_id,
            'dealtCardsPerPlayer': h.cards_per_player,
            'trump': h.trump,
            'startingPlayer': starting_player.username,
            # 'dealtCards': players_cards
        }
    ), 200


@hand.route('{base_path}/game/<game_id>/hand/<hand_id>/cards'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['POST'])
@cross_origin()
def get_hand_cards(game_id, hand_id):

    token = request.json.get('token')
    if token is None:
        return jsonify({
            'errors':[
                {'message': 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('user.post_token'))}
            ]
        }), 401
    requesting_user = User.verify_api_auth_token(token)

    p = Player.query.filter_by(game_id=game_id, user_id=requesting_user.id).first()
    if p is None:
        return jsonify({
            'errors':[
                {
                    'message': 'User {username} is not participating in game {game_id}!'.format(username=requesting_user.username, game_id=game_id)
                }
            ]
        }), 403

    h = Hand.query.filter_by(id=hand_id).first()
    if h is None or h.is_closed == 1:
        return jsonify({
            'errors': [
                {
                    'message': 'Hand {hand_id} is closed or does not exist!'.format(hand_id=hand_id)
                }
            ]
        }), 403

    if str(request.args.get('burned')).lower() == 'y':
        cards = h.get_user_initial_hand(requesting_user, h.trump)
    else:
        cards = h.get_user_current_hand(requesting_user, h.trump)

    return jsonify({
        'gameId': game_id,
        'handId': hand_id,
        'cardsPerPlayer': h.cards_per_player,
        'trump': h.trump,
        'player': requesting_user.username,
        'cardsInHand': cards,
        'myPosition': h.get_players_relative_positions(requesting_user.id)
    }), 200


@hand.route('{base_path}/game/<game_id>/hand/<hand_id>'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['POST'])
@cross_origin()
def status(game_id, hand_id):
    token = request.json.get('token')
    my_position = 0
    requesting_user = None
    if token:
        requesting_user = User.verify_api_auth_token(token)

    game = Game.query.filter_by(id=game_id).first()
    if not game:
        return jsonify({
            'errors':[
                {'message': 'Game #{game_id} is not found!'.format(game_id=game_id)}
            ]
        }), 404

    hand = Hand.query.filter_by(id=hand_id).first()
    if not hand:
        return jsonify({
            'errors':[
                {'message': 'Hand #{hand_id} is not found!'.format(hand_id=hand_id)}
            ]
        }), 404
    if int(hand.game_id) != int(game_id):
        return jsonify({
            'errors':[
                {'message': 'Hand #{hand_id} is not part of game#{game_id}!'.format(hand_id=hand_id,game_id=game_id)}
            ]
        }), 404

    players = Player.query.filter_by(game_id=game_id).order_by(Player.position).all()
    players_enriched = []
    for player in players:
        user = User.query.filter_by(id=player.user_id).first()
        if user == requesting_user:
            my_position = hand.get_position(user)
        if user:
            user_scores = HandScore.query.filter_by(player_id=user.id, hand_id=hand_id).first()
            players_enriched.append({
                'username': user.username,
                'position': hand.get_position(user),
                'betSize': user_scores.bet_size if user_scores else None,
                'tookTurns': user_scores.took_turns() if user_scores else 0,
                'cardsOnHand': len(hand.get_user_current_hand(user))
            })

    current_turn = hand.get_current_turn(closed=True)
    next_player = hand.next_acting_player()

    cards_on_table = []
    if current_turn:
        for card in current_turn.stroke_cards():
            cards_on_table.append(str(card.card_id) + card.card_suit)

    return jsonify({
            'handId': hand.id,
            'betsAreMade': hand.all_bets_made(),
            'nextActingPlayer': next_player.username if next_player else None,
            'gameId': game.id,
            'roomId': game.room_id,
            'handSerialNo': hand.serial_no,
            'cardsPerPlayer': hand.cards_per_player,
            'trump': hand.trump,
            'startingPlayer': hand.starting_player,
            'handIsClosed': hand.is_closed,
            'players': players_enriched,
            'myPosition': my_position,
            'cardsOnTable': cards_on_table,
            'currentTurnSerialNo': current_turn.serial_no if current_turn else None
    }), 200
