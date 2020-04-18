# -*- coding: utf-8 -*-

from flask import url_for, request, jsonify, abort, Blueprint
from app import app, db
from app.models import User, Game, Player, Hand, HandScore


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

