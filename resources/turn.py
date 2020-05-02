# -*- coding: utf-8 -*-

from flask import url_for, request, jsonify, abort, Blueprint
from app import app, db
from app.models import User, Game, Player, Hand, HandScore, Turn, DealtCards, TurnCard
from datetime import datetime


turn = Blueprint('turn', __name__)


@turn.route('{base_path}/game/<game_id>/hand/<hand_id>/turn/bet'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def bet(game_id, hand_id):

    token = request.json.get('token')
    requesting_user = User.verify_api_auth_token(token)

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


@turn.route('{base_path}/game/<game_id>/hand/<hand_id>/turn/card/put/<card_id>'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
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
        abort(403, 'Player {username} does not have card {card_id} on his hand!'.format(username=requesting_user.username, card_id=card_id[:1], card_suit=card_id[1:]))

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
            if card_suit == h.trump and turn_suit != h.trump and t.highest_card()['suit']==h.trump.casefold() and trump_hierarchy.index(card_score) < trump_hierarchy.index(t.highest_card()['score']):
                abort(403, 'You cannot utilize lower trumps!')

    tc = TurnCard(player_id=requesting_user.id, card_id=card_id[:1], card_suit=card_id[1:], turn_id=t.id, hand_id=hand_id)
    db.session.add(tc)

    db.session.commit()

    g = Game.query.filter_by(id=game_id).first()
    t = Turn.query.filter_by(id=t.id).first()
    players_count = g.players.count()

    took_player = None
    if len(t.stroke_cards()) == players_count:
        took_player = User.query.filter_by(id=DealtCards.query.filter_by(hand_id=hand_id, card_id=t.highest_card()['id'].casefold(), card_suit=t.highest_card()['suit'].casefold()).first().player_id).first()
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
        cards_on_table.append(str(card.card_id) + card.card_suit)

    return jsonify({
        'turn_no': t.serial_no,
        'cards_on_table': cards_on_table,
        'starting_suit': t.get_starting_suit(),
        'highest_card': str(t.highest_card()['id']) + t.highest_card()['suit'],
        'took_player': took_player.username if took_player else None,
        'hand_is_finished': True if h.is_closed == 1 else False,
        'game_is finished': True if g.finished else False,
        'game_scores': game_scores
    }), 200
