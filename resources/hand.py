# -*- coding: utf-8 -*-

from flask import url_for, request, jsonify, abort, Blueprint
from app import app, db
from app.models import User, Room, Game, Player, Hand, DealtCards, TurnCard, Turn
import random
from math import floor
from datetime import datetime


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


@hand.route('{base_path}/game/<game_id>/hand/<hand_id>/get'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
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

    return jsonify({
        'game_id': game_id,
        'hand_id': hand_id,
        'cards_per_player': h.cards_per_player,
        'trump': h.trump,
        'player': requesting_user.username,
        'cards_in_hand': h.get_user_current_hand(requesting_user)
    }), 200


@hand.route('{base_path}/game/<game_id>/hand/<hand_id>/turn/card/put/<card_id>'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def put_card(game_id, hand_id, card_id):

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

    if not h.all_bets_made():
        abort(403, 'Wait until all bets are made in hand {hand_id}'.format(hand_id=hand_id))

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

    g = Game.query.filter_by(id=game_id).first()
    t = Turn.query.filter_by(id=t.id).first()
    players_count = g.players.count()

    took_player = None
    if len(t.stroke_cards()) == players_count:
        took_player = User.query.filter_by(id=DealtCards.query.filter_by(hand_id=hand_id, card_id=t.highest_card().casefold()).first().player_id).first()
        t.took_user_id = took_player.id

    game_scores = None
    turn_cards_count = TurnCard.query.filter_by(turn_id=t.id).count()
    if turn_cards_count == players_count and h.all_turns_made():
        h.is_closed = 1
        h.calculate_current_score()
        if g.all_hands_played():
            g.finished = datetime.utcnow()
            game_scores = g.get_scores()


    db.session.commit()

    cards_on_table = []
    for card in t.stroke_cards():
        cards_on_table.append(card.card_id)

    return jsonify({
        'turn_no': t.serial_no,
        'cards_on_table': cards_on_table,
        'starting_suit': t.get_starting_suit(),
        'highest_card': t.highest_card(),
        'took_player': took_player.username if took_player else None,
        'hand_is_finished': True if h.is_closed == 1 else False,
        'game_is finished': True if g.finished else False,
        'game_scores': game_scores
    }), 200
