# -*- coding: utf-8 -*-

from flask import url_for, request, jsonify, Blueprint
from flask_cors import cross_origin
from app import app, db
from app.models import User, Game, Player, Hand, HandScore, Turn, DealtCards, TurnCard, Stats, Room
from datetime import datetime
import numpy as np
from config import get_settings, get_environment


turn = Blueprint('turn', __name__)
env = get_environment()


@turn.route('{base_path}/game/<game_id>/hand/<hand_id>/turn/bet'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['POST'])
@cross_origin()
def bet(game_id, hand_id):

    token = request.json.get('token')
    requesting_user = User.verify_api_auth_token(token)

    bet_size = request.json.get('betSize')
    if bet_size is None:
        return jsonify({
            'errors': [
                {
                    'message': 'Please, write down bet size!'
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
    next_acting_player = h.next_acting_player()
    if next_acting_player != requesting_user:
        return jsonify({
            'errors': [
                {
                    'message': "It is {username}'s turn now!".format(username=next_acting_player.username)
                }
            ]
        }), 403

    # "Someone should stay unhappy" (rule name)
    made_bets = h.get_sum_of_bets()

    bets_count = HandScore.query.filter_by(hand_id=hand_id).count()
    is_last_bet = bets_count == Player.query.filter_by(game_id=game_id).count() - 1
    if is_last_bet and bet_size + made_bets == h.cards_per_player:
        return jsonify({
            'errors': [
                {
                    'message': 'Someone should stay unhappy! You cannot bet {bet_size} since you are last betting player in hand.'.format(bet_size=bet_size)
                }
            ]
        }), 400

    hs = HandScore(player_id=requesting_user.id, hand_id=hand_id, bet_size=bet_size)
    db.session.add(hs)
    db.session.commit()

    next_player = h.next_acting_player()

    return jsonify({
        'numberOfPlayers': game.players.count(),
        'serialNumberOfHand': h.serial_no,
        'playerPosition': requesting_player_current_pos,
        'isLastPlayerToBet': is_last_bet,
        'nextActingPlayer': next_player.username,
        'madeBets': made_bets + bet_size,
        'cardsPerPlayer': h.cards_per_player
    }), 200


@turn.route('{base_path}/game/<game_id>/hand/<hand_id>/turn/card/put/<card_id>'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['POST'])
@cross_origin()
def put_card(game_id, hand_id, card_id):
    if app.debug:
        print('game_id:' + str(game_id))
        print('hand_id:' + str(hand_id))
        print('card_id:' + str(card_id))

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

    curr_player = h.next_acting_player()
    if not h.next_acting_player:
        return jsonify({
            'errors': [
                {
                    'message': "Technical error: can not define next acting player!"
                }
            ]
        }), 403
    if curr_player is not None:
        if requesting_user != curr_player:
            return jsonify({
                'errors': [
                    {
                        'message': "It is {username}'s turn now!".format(username=curr_player.username)
                    }
                ]
            }), 403

    card_id = card_id.casefold()

    player_current_hand = h.get_user_current_hand(requesting_user, h.trump)
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

    highest_turn_card = t.highest_card()

    if len(t.stroke_cards()) > 0 and len(player_current_hand) > 1:

        # put card checking logic (schematically described in https://drive.google.com/file/d/15X_s6eI3ouRcgYh_IWEoDF0dOTr7VPvo/view?usp=sharing )

        turn_suit = t.get_starting_suit().casefold()
        card_suit = card_id[-1:].casefold()
        card_score = str(card_id[:1]).casefold()
        hand_trump = h.trump
        if hand_trump:
            hand_trump = hand_trump.casefold()
        trump_hierarchy = np.array(['2', '3', '4', '5', '6', '7', '8', 't', 'q', 'k', 'a', '9', 'j'])

        is_turn_suit = turn_suit == card_suit
        is_trump = hand_trump == card_suit
        player_has_turn_suit = False
        is_first_trump = False
        is_higher_trump = False
        all_remaining_cards_are_lower_trumps = True
        status_code = 403
        error_msg = '-'

        if app.debug:
            print('turn_suit:       ' + str(turn_suit))
            print('card_suit:       ' + str(card_suit))
            print('card_score:      ' + str(card_score))
            print('hand_trump:      ' + str(hand_trump))
            print('is_turn_suit:    ' + str(is_turn_suit))


        if is_turn_suit:
            status_code = 200                                           # putting card of current suit is allowed always
        else:
            if is_trump:
                if card_score == 'j':
                    status_code = 200                                   # putting J trump is allowed always
                else:
                    if highest_turn_card['suit'] != hand_trump:
                        is_first_trump = True
                    if app.debug:
                        print('is_first_trump:    ' + str(is_first_trump))
                    if is_first_trump:
                        status_code = 200                               # putting first trump is allowed always
                    else:
                        if np.where(trump_hierarchy==card_score)[0][0] > np.where(trump_hierarchy==highest_turn_card['id'])[0][0]:
                            is_higher_trump = True
                        if app.debug:
                            print('is_higher_trump:    ' + str(is_higher_trump))
                        if is_higher_trump:
                            status_code = 200                           # putting higher trump is allowed always
                        else:
                            for card_on_hand in player_current_hand:
                                if card_on_hand != card_id and \
                                    card_on_hand[-1:].casefold() == hand_trump and \
                                    np.where(trump_hierarchy==card_on_hand[:1].casefold())[0][0] > np.where(trump_hierarchy==highest_turn_card['id'])[0][0] and \
                                    card_on_hand[:1].casefold() != 'j':
                                        all_remaining_cards_are_lower_trumps = False
                                if card_on_hand[-1:].casefold() != hand_trump:
                                    all_remaining_cards_are_lower_trumps = False
                            if app.debug:
                                print('all_remaining_cards_are_lower_trumps:    ' + str(all_remaining_cards_are_lower_trumps))
                            if all_remaining_cards_are_lower_trumps:
                                status_code = 200                       # leaking lower trump if player has no other option is allowed
                            else:
                                error_msg = 'You cannot leak trumps!'   # leaking trumps is not allowed if you have another option
            else:
                suitable_cards = []
                for card_on_hand in player_current_hand:
                    if card_on_hand[-1:].casefold() == turn_suit:
                        player_has_turn_suit = True
                        print(card_on_hand)
                        suitable_cards.append(card_on_hand)
                if app.debug:
                    print('player_has_turn_suit:    ' + str(player_has_turn_suit))
                if turn_suit == hand_trump and suitable_cards == ['j' + hand_trump]:
                    status_code = 200                               # putting card of non trump suit in trump suited turn is allowed if the only remaining trump on hand is J
                elif player_has_turn_suit:
                    error_msg = 'You should put card with following suits: {turn_suit}, {hand_trump}!'.format(
                        turn_suit = turn_suit,
                        hand_trump = hand_trump
                    )                                               # putting card of non trump and non turn suit is not allowed if player has turn suited cards on hand
                else:
                    status_code = 200                               # putting card of non trump suit not matching turn suit is allowed if player has no turn suited cards

        if status_code == 403:
            return jsonify({
                'errors': [
                    {
                        'message': error_msg
                    }
                ]
            }), status_code

    if app.debug:
        print('Adding turn card ' + str(card_id) + ' in turn #' + str(t.id) + ' of hand #' + str(hand_id) + ', put by player #' + str(requesting_user.id))
    tc = TurnCard(player_id=requesting_user.id, card_id=card_id[:1], card_suit=card_id[1:], turn_id=t.id,
                  hand_id=hand_id)
    db.session.add(tc)

    db.session.commit()

    g = Game.query.filter_by(id=game_id).first()
    t = Turn.query.filter_by(id=t.id).first()
    players_count = g.players.count()

    took_player = None
    game_scores = None
    requesting_user_is_player = False
    if app.debug:
        print(str(len(t.stroke_cards())) + ' cards were stroke in turn #' + str(t.id))
    if len(t.stroke_cards()) == players_count:
        highest_turn_card = t.highest_card()
        if app.debug:
            print('All cards were stroke in turn #' + str(t.id))
            print('Highest turn card is ' + str(highest_turn_card))
        took_player = User.query.filter_by(
            id=DealtCards.query.filter_by(
                hand_id=str(hand_id),
                card_id=str(highest_turn_card['id']),
                card_suit=str(t.highest_card()['suit'].casefold())
            ).first().player_id
        ).first()
        if app.debug:
            print('took_player: ' + str(took_player.username))
        t.took_user_id = took_player.id

        hand_turns_cnt = Turn.query.filter_by(hand_id=hand_id).count()
        if h.cards_per_player == hand_turns_cnt:
            h.is_closed = 1
            for player in g.players:
                if player.id == requesting_user.id:
                    requesting_user_is_player = True
                hs = HandScore.query.filter_by(hand_id = hand_id, player_id = player.id).first()
                if hs:
                    hs.calculate_current_score()
            if g.all_hands_played():
                g.finished = datetime.utcnow()
                game_scores = g.get_scores()
                top_score = 0
                winner_id = None
                r = Room.query.filter_by(id=g.room_id).first()
                for player in g.players:
                    user = User.query.filter_by(id=player.id).first()
                    r.not_ready(user)
                    player_scores = user.calc_game_stats(game_id=game_id)
                    if player_scores:
                        if player_scores['totalScore'] >= top_score:
                            top_score = player_scores['totalScore']
                            winner_id = player.user_id
                g.winner_id = winner_id


    db.session.commit()

    for player in g.players:
        user = User.query.filter_by(id=player.id).first()
        player_scores = user.calc_game_stats(game_id=game_id)
        if player_scores:
            s = Stats.query.filter_by(user_id=user.id).first()
            if not s:
                s = Stats(
                    user_id=user.id,
                    games_played=player_scores['gamesPlayed'],
                    games_won = player_scores['gamesWon'],
                    sum_of_bets = player_scores['sumOfBets'],
                    bonuses = player_scores['bonuses'],
                    total_score = player_scores['totalScore']
                )
                db.session.add(s)
            else:
                s.games_played += player_scores['gamesPlayed']
                s.games_won += player_scores['gamesWon']
                s.sum_of_bets += player_scores['sumOfBets']
                s.bonuses += player_scores['bonuses'],
                s.total_score += player_scores['totalScore']
            db.session.commit()

    cards_on_table = []
    for card in t.stroke_cards():
        card_user = User.query.filter_by(id=card.player_id).first()
        player_position = None
        player_relative_position = None
        if card_user:
            player_position = h.get_position(card_user)
            player_relative_position = player_position
            if requesting_user_is_player:
                player_relative_position = g.get_player_relative_positions(requesting_user.id, card_user.id)
        cards_on_table.append({
            'cardId': str(card.card_id) + card.card_suit,
            'playerId': card.player_id,
            'playerPosition': player_position,
            'playerRelativePosition': player_relative_position
        })

    next_player = h.next_acting_player()

    return jsonify({
        'turnNo': t.serial_no,
        'cardsOnTable': cards_on_table,
        'startingSuit': t.get_starting_suit(),
        'highestCard': str(t.highest_card()['id']) + t.highest_card()['suit'],
        'tookPlayer': took_player.username if took_player else None,
        'handIsFinished': True if h.is_closed == 1 else False,
        'gameIsFinished': True if g.finished else False,
        'gameScores': game_scores,
        'isLastCardInHand': h.is_closed == 1,
        'nextActingPlayer': next_player.username if next_player else None
    }), 200