# -*- coding: utf-8 -*-

from flask import url_for, request, jsonify, Blueprint
from flask_cors import cross_origin
from app import app, db
from app.models import User, Game, Player, Hand, HandScore, Turn, DealtCards, TurnCard
from datetime import datetime
import numpy as np


turn = Blueprint('turn', __name__)


@turn.route('{base_path}/game/<game_id>/hand/<hand_id>/turn/bet'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
@cross_origin()
def bet(game_id, hand_id):

    token = request.json.get('token')
    requesting_user = User.verify_api_auth_token(token)

    bet_size = request.json.get('betSize')
    if bet_size is None:
        return jsonify({
            'errors': [
                {
                    'message': 'No bet size in request!'
                }
            ]
        }), 400

    p = Player.query.filter_by(game_id=game_id, user_id=requesting_user.id).first()
    if p is None:
        return jsonify({
            'errors': [
                {
                    'message': 'User {username} is not participating in game {game_id}!'.format(username=requesting_user.username, game_id=game_id)
                }
            ]
        }), 403

    game = Game.query.filter_by(id=game_id).first()

    h = Hand.query.filter_by(id=hand_id).first()
    if h is None or h.is_closed == 1:
        return jsonify({
            'errors': [
                {
                    'message': 'Hand {hand_id} is closed or does not exist!'.format(hand_id=hand_id)
                }
            ]
        }), 403

    requesting_player_bet = HandScore.query.filter_by(hand_id=hand_id, player_id=requesting_user.id).first()
    if requesting_player_bet:
        return jsonify({
            'errors': [
                {
                    'message': 'User {username} already has made a bet in hand {hand_id}!'.format(username=requesting_user.username, hand_id=hand_id)
                }
            ]
        }), 403

    # check if it's your turn
    requesting_player_current_pos = h.get_position(requesting_user)
    if not h.is_registered(requesting_user):
        return jsonify({
            'errors': [
                {
                    'message': 'User {username} is not registered in hand {hand_id} of game {game_id}!'.format(username=requesting_user.username, hand_id=hand_id, game_id=game_id)
                }
            ]
        }), 400
    next_betting_user = h.next_betting_user()
    if next_betting_user != requesting_user:
        return jsonify({
            'errors': [
                {
                    'message': "It is {username}'s turn now!".format(username=next_betting_user.username)
                }
            ]
        }), 403

    # "Someone should stay unhappy" (rule name)
    made_bets = h.get_sum_of_bets()
    is_last_bet = h.is_betting_last(requesting_user)
    if is_last_bet and bet_size + made_bets == h.cards_per_player:
        return jsonify({
            'errors': [
                {
                    'message': 'Someone should stay unhappy! Change your bet size since you are last betting player in hand.'
                }
            ]
        }), 400

    hs = HandScore(player_id=requesting_user.id, hand_id=hand_id, bet_size=bet_size)
    db.session.add(hs)
    db.session.commit()

    next_player = h.next_betting_user()

    return jsonify({
        'numberOfPlayers': game.players.count(),
        'serialNumberOfHand': h.serial_no,
        'playerPosition': requesting_player_current_pos,
        'isLastPlayerToBet': is_last_bet,
        'nextPlayerToBet': next_player.username if next_player and not is_last_bet else None,
        'madeBets': made_bets + bet_size,
        'cardsPerPlayer': h.cards_per_player
    }), 200


@turn.route('{base_path}/game/<game_id>/hand/<hand_id>/turn/card/put/<card_id>'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
@cross_origin()
def put_card(game_id, hand_id, card_id):

    token = request.json.get('token')
    if token is None:
        return jsonify({
            'errors': [
                {
                    'message': 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('user.post_token'))
                }
            ]
        }), 401
    requesting_user = User.verify_api_auth_token(token)

    p = Player.query.filter_by(game_id=game_id, user_id=requesting_user.id).first()
    if p is None:
        return jsonify({
            'errors': [
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

    if not h.all_bets_made():
        return jsonify({
            'errors': [
                {
                    'message': 'Wait until all bets are made in hand {hand_id}'.format(hand_id=hand_id)
                }
            ]
        }), 403

    if h.all_turns_made():
        return jsonify({
            'errors': [
                {
                    'message': 'All turns are made in hand {hand_id} of game {game_id}!'.format(hand_id=hand_id, game_id=game_id)
                }
            ]
        }), 403

    t = h.get_current_turn()
    if t and t.if_put_card(requesting_user):
        return jsonify({
            'errors': [
                {
                    'message': 'Player {username} has already put card in current turn of hand {hand_id}!'.format(username=requesting_user.username, hand_id=hand_id)
                }
            ]
        }), 403

    curr_player = h.next_card_putting_user()
    if requesting_user != curr_player:
        return jsonify({
            'errors': [
                {
                    'message': "It is {username}'s turn now!".format(username=curr_player.username)
                }
            ]
        }), 403

    card_id = card_id.casefold()

    player_current_hand = h.get_user_current_hand(requesting_user)
    if card_id not in player_current_hand:
        return jsonify({
            'errors': [
                {
                    'message': 'Player {username} does not have card {card_id} on his hand!'.format(username=requesting_user.username, card_id=card_id[:1], card_suit=card_id[1:])
                }
            ]
        }), 403

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

        turn_suit = t.get_starting_suit().casefold()
        trump = h.trump.casefold()
        card_suit = card_id[-1:].casefold()
        card_score = str(card_id[:1]).casefold()
        highest_turn_card = t.highest_card()
        trump_hierarchy = np.array(['2', '3', '4', '5', '6', '7', '8', 't', 'q', 'k', 'a', '9', 'j'])
        status_code = 403
        error_msg = '-'
        player_has_turn_suit = False
        player_has_only_trump = True
        players_higher_trump = False
        for card_on_hand in player_current_hand:
            if card_on_hand[-1:] == turn_suit:
                if card_on_hand[-1:] != trump and card_on_hand[1:] != 'j':
                    player_has_turn_suit = True
            if card_on_hand[-1:] != trump:
                player_has_only_trump = False
            if card_on_hand != 'j' + str(trump) and np.where(trump_hierarchy == card_on_hand[:1])[0][0] > np.where(trump_hierarchy == highest_turn_card['id'])[0][0]:
                players_higher_trump = True


        if turn_suit == card_suit:
            status_code = 200                       # putting card of current suit is allowed always

        elif card_suit == trump:
            if card_score == 'j':
                status_code = 200                   # putting J trump is allowed always

            elif highest_turn_card['suit'] != trump:
                status_code = 200                   # putting first trump is allowed always

            else:
                if np.where(trump_hierarchy==card_score)[0][0] > np.where(trump_hierarchy==highest_turn_card['id'])[0][0]:
                    status_code = 200               # putting higher trump is allowed always
                elif player_has_only_trump and not players_higher_trump:
                    status_code = 200               # leaking lower trump is allowed if you do not have higher trump
                else:
                    error_msg = \
                        '{higher_trump_on_hand} is higher than {highest_turn_card}: you cannot leak trumps!'.format(
                            higher_trump_on_hand = players_higher_trump,
                            highest_turn_card = highest_turn_card
                        )                           # leaking trumps is not allowed
        elif player_has_turn_suit:
            error_msg = 'You can put only {turn_suit} and {trump}'.format(turn_suit=turn_suit, trump=trump) # cannot put another suit and non trump if you have turn suit

        else:
            status_code = 200

        if status_code == 403:
            return jsonify({
                'errors': [
                    {
                        'message': error_msg
                    }
                ]
            }), status_code

    tc = TurnCard(player_id=requesting_user.id, card_id=card_id[:1], card_suit=card_id[1:], turn_id=t.id,
                  hand_id=hand_id)
    db.session.add(tc)

    db.session.commit()

    g = Game.query.filter_by(id=game_id).first()
    t = Turn.query.filter_by(id=t.id).first()
    players_count = g.players.count()

    took_player = None
    if len(t.stroke_cards()) == players_count:
        took_player = User.query.filter_by(
            id=DealtCards.query.filter_by(hand_id=hand_id, card_id=t.highest_card()['id'].casefold(),
                                          card_suit=t.highest_card()['suit'].casefold()).first().player_id).first()
        t.took_user_id = took_player.id

    game_scores = None
    turn_cards_count = TurnCard.query.filter_by(turn_id=t.id).count()
    if turn_cards_count == players_count and Hand.query.filter_by(id=hand_id).first().all_turns_made():
        h.is_closed = 1
        db.session.commit()
        h.calculate_current_score()
        if g.all_hands_played():
            g.finished = datetime.utcnow()
            game_scores = g.get_scores()

    db.session.commit()

    cards_on_table = []
    for card in t.stroke_cards():
        cards_on_table.append(str(card.card_id) + card.card_suit)

    return jsonify({
        'turnNo': t.serial_no,
        'cardsOnTable': cards_on_table,
        'startingSuit': t.get_starting_suit(),
        'highestCard': str(t.highest_card()['id']) + t.highest_card()['suit'],
        'tookPlayer': took_player.username if took_player else None,
        'handIsFinished': True if h.is_closed == 1 else False,
        'gameIsFinished': True if g.finished else False,
        'gameScores': game_scores
    }), 200