from datetime import datetime
from app import db, login, app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
# from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
from flask import url_for, jsonify
from time import time
import jwt
from sqlalchemy import text
from config import get_settings, get_environment



auth = get_settings('AUTH')
env = get_environment()

connections = db.Table(
    'connections',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('room_id', db.Integer, db.ForeignKey('room.id')),
    db.Column('ready', db.Integer, default=0)
)

'''class connectionsClass(db.Model):
    room_id = db.Column(db.integer, nullable=False),
    user_id = db.Column(db.integer, nullable=False),
    ready = db.Column(db.integer, nullable=False, default=0)'''


players = db.Table(
    'players',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('game_id', db.Integer, db.ForeignKey('game.id')),
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True, nullable=True)
    password_hash = db.Column(db.String(128))
    rooms = db.relationship('Room', backref='host', lazy='dynamic')
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    facebook_pic = db.Column(db.String(128), nullable=True)
    registered = db.Column(db.DateTime)
    about_me = db.Column(db.String(140), nullable=True)
    social_id = db.Column(db.String(64), unique=True, nullable=True)
    preferred_language = db.Column(db.String(6), default='en')
    connected_rooms_bad = db.relationship(
        'Room',
        secondary=connections,
        backref=db.backref('connected_users', lazy='dynamic'),
        overlaps="connected_rooms_bad,connected_users"
    )
    active_games = db.relationship(
        'Game',
        secondary=players,
        backref=db.backref('players', lazy='dynamic')
    )

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def is_connected_to_room(self, room):
        return self.connected_rooms.filter(
            connections.c.room_id == room.id).count() > 0

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_auth_token(self):
        # s = Serializer(auth['SECRET_KEY'][env]) #, expires_in=auth['SECRET_KEY'][TOKEN_LIFETIME])
        return jwt.encode(
            {'username': self.username, 'email': self.email},
            auth['SECRET_KEY'][env],
            algorithm='HS256'
        )
        # return s.dumps({'username': self.username, 'email': self.email})

    def get_connected_room_id(self):
        query = "SELECT room_id FROM connections WHERE user_id = {user_id}".format(user_id=self.id)
        user_connections = db.session.execute(text(query))
        if user_connections:
            for connection in user_connections:
                return connection[0]
        return None

    @staticmethod
    def verify_auth_token(token):
        # s = Serializer(auth['SECRET_KEY'][env])
        try:
            data = jwt.decode(token, auth['SECRET_KEY'][env], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidIssuerError:
            return None
        except jwt.InvalidTokenError:
            return None
        user = User.query.filter_by(username=data['username']).first()
        return user

    def get_reset_password_token(self, expires_in=600):
        new_token = jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            auth['SECRET_KEY'][env],
            algorithm='HS256'
        )
        new_token_entry = Token(token=new_token, status='active', type='reset_password')
        db.session.add(new_token_entry)
        db.session.commit()
        return new_token

    @staticmethod
    def verify_reset_password_token(token):
        saved_token = Token.query.filter_by(token=token).first()
        if not saved_token:
            return
        if saved_token.status != 'active':
            return
        try:
            id = jwt.decode(token, auth['SECRET_KEY'][env],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    @staticmethod
    def verify_api_auth_token(token):
        if token is None:
            return jsonify({
                'errors': [
                    {
                        'message': 'Authentication token is absent! You should request token by POST {post_token_url}'.format(
                post_token_url=url_for('user.post_token'))
                    }
                ]
            }), 401
        requesting_user = User.verify_auth_token(token)
        if requesting_user is None:
            return jsonify({
                'errors': [
                    {
                        'message': 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(
                post_token_url=url_for('user.post_token'))
                    }
                ]
            }), 401
        return requesting_user

    def calc_game_stats(self, game_id=None):
        player_entries = Player.query.filter_by(user_id=self.id).all()
        if game_id:
            player_entries = Player.query.filter_by(user_id=self.id, game_id=game_id).all()
        if not player_entries:
            return None
        played_games = 0
        games_won = 0
        played_hands = 0
        sum_of_bets = 0
        total_score = 0
        bonuses = 0
        for entry in player_entries:
            if app.debug:
                print('Building user stats: checking game #' + str(entry.game_id))
            game = Game.query.filter_by(id=entry.game_id).first()
            if game:
                if game.winner_id is not None and game.finished is not None:
                    print('Building user stats: game #' + str(entry.game_id) + ' is finished')
                    played_games += 1
                    played_hands += Hand.query.filter_by(game_id=game.id, is_closed=1).count()
                    if game.winner_id == self.id:
                        games_won += 1
                    game_scores = game.get_user_score(self.id)
                    sum_of_bets += game_scores['sum_of_bets']
                    bonuses += game_scores['bonuses']
                    total_score += game_scores['total_score']
        if player_entries==0 or played_hands==0:
            return None
        avg_score = total_score / played_games
        avg_bonuses = bonuses / played_games
        avg_bet_size = sum_of_bets / played_hands
        return {
            'gamesPlayed': played_games,
            'gamesWon': games_won,
            'winRatio': games_won / played_games,
            'handsPlayed': played_hands,
            'sumOfBets': sum_of_bets,
            'bonuses': bonuses,
            'totalScore': total_score,
            'avgScore': avg_score,
            'avgBonuses': avg_bonuses,
            'avgBetSize': avg_bet_size
        }

    def get_stats(self):
        stats = Stats.query.filter_by(user_id=self.id).first()
        if not stats:
            return None
        return {
            'gamesPlayed': stats.games_played,
            'gamesWon': stats.games_won,
            'winRatio': stats.games_won / stats.games_played,
            'sumOfBets': stats.sum_of_bets,
            'bonuses': stats.bonuses,
            'totalScore': stats.total_score,
            'avgScore': stats.total_score / stats.games_played,
            'avgBonuses': stats.bonuses / stats.games_played,
            'avgBetSize': stats.sum_of_bets / stats.games_played
        }


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_name = db.Column(db.String(64), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    games = db.relationship('Game', backref='room', lazy='dynamic')
    closed = db.Column(db.DateTime)
    connected_users_bad = db.relationship(
        'User',
        secondary=connections,
        backref=db.backref('connected_rooms', lazy='dynamic',overlaps="connected_rooms_bad,connected_users"),
        overlaps="connected_rooms_bad,connected_users"
    )

    def __repr__(self):
        return '<Room {} (created by {} at {})>'.format(self.room_name, self.host.username, self.created)

    def connect(self, user):
        self.connected_users.append(user)
        db.session.commit()

    def disconnect(self, user):
        self.connected_users.remove(user)
        db.session.commit()

    def is_connected(self, user):
        return self.connected_users.filter(
            connections.c.user_id == user.id).count() > 0

    def ready(self, user):
        sql = text("UPDATE connections SET ready = 1 WHERE room_id= " + str(self.id) + " AND user_id = " + str(user.id))
        db.session.execute(sql)
        db.session.commit()

    def not_ready(self, user):
        sql = text("UPDATE connections SET ready = 0 WHERE room_id= " + str(self.id) + " AND user_id = " + str(user.id))
        db.session.execute(sql)
        db.session.commit()

    def if_user_is_ready(self, user):
        sql = text("SELECT ready FROM connections WHERE room_id= " + str(self.id) + " AND user_id=" + str(user.id))
        result = db.session.execute(sql).first()
        if result[0]==1:
            return True
        return False

    def current_status(self):
        if self.closed:
            return 'closed'
        open_games = Game.query.filter_by(room_id=self.id, finished=None).count()
        if open_games > 0:
            return 'started'
        return 'open'


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False, index=True)
    started = db.Column(db.DateTime, nullable=True, default=datetime.utcnow())
    finished = db.Column(db.DateTime, nullable=True, default=None)
    winner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    autodeal = db.Column(db.Integer, default=0)
    hands = db.relationship('Hand', backref='game', lazy='dynamic')

    def __repr__(self):
        return '<Game {}, room {}, started on {}>'.format(self.id, self.room_id, self.started)

    def connect(self, user):
        self.players.append(user)

    def get_starter(self):
        player = Player.query.filter_by(game_id=self.id, position=1).first()
        return User.query.filter_by(id=player.user_id).first()

    def get_position(self, user):
        return Player.query.filter_by(game_id=self.id, user_id=user.id).first().position

    def has_open_hands(self):
        return Hand.query.filter_by(game_id=self.id, is_closed=0).order_by(Hand.serial_no.desc()).first() is not None

    def last_open_hand(self):
        return Hand.query.filter_by(game_id=self.id, is_closed=0).order_by(Hand.serial_no.desc()).first()

    def all_hands_played(self):
        all_games_played = False
        players_count = self.players.count()
        hands_count = Hand.query.filter_by(game_id=self.id).count()
        if players_count in [9, 10] and hands_count >= 10:
            all_games_played = True
        elif players_count == 8 and hands_count >= 12:
            all_games_played = True
        elif players_count == 7 and hands_count >= 14:
            all_games_played = True
        elif players_count == 6 and hands_count >= 16:
            all_games_played = True
        elif players_count <= 5 and hands_count >= 20:
            all_games_played = True
        return all_games_played

    def get_scores(self):
        played_hands = Hand.query.filter_by(game_id=self.id).all()
        players = self.players.all()
        headers = ['']
        rows = []
        total_score = {}
        data_array = [{}]
        for player in players:
            total_score[player.username] = 0
            headers.append(str(player.username))
            data_array.append({
                'type': 'scores subtitle'
            })
        rows.append({
            'id': 'subtitle',
            'dataArray': data_array
        })
        for hand in played_hands:
            data_array = [{
                'type': 'hand id',
                'cards': str(hand.cards_per_player),
                'trump': str(hand.trump) if hand.trump else 'x'
            }]
            for player in players:
                hand_score = HandScore.query.filter_by(hand_id=hand.id, player_id=player.id).first()
                if hand_score:
                    data_array.append({
                        'type': 'score',
                        'betSize': hand_score.bet_size,
                        'tookTurns': hand_score.score if hand_score.score else 0 - (10 if hand_score.bonus else 0),
                        'bonus': hand_score.bonus,
                        'score': hand_score.score
                    })
                    total_score[player.username] += hand_score.score if hand_score.score else 0
                else:
                    data_array.append({
                        'type': 'score',
                        'betSize': '',
                        'tookTurns': '',
                        'bonus': '',
                        'score': ''
                    })
            rows.append({
                'id': str(hand.cards_per_player) + str(hand.trump),
                'dataArray': data_array
            })
        totals_data_array = [{'type': 'text', 'value': 'total'}]
        for player in players:
            totals_data_array.append({
                'type': 'score',
                'total': True,
                'score': total_score[player.username]
            })
        rows.append({
            'id': 'total',
            'dataArray':totals_data_array
        })
        return {
            'headers': headers,
            'rows': rows
        }

    def get_user_score(self, user_id):
        player_entry = Player.query.filter_by(game_id=self.id, user_id=user_id).first()
        if not player_entry:
            return None
        played_hands = Hand.query.filter_by(game_id=self.id).all()
        if not played_hands:
            return None
        hands_played = len(played_hands)
        sum_of_bets = 0
        total_score = 0
        bonuses = 0
        for hand in played_hands:
            hand_score = HandScore.query.filter_by(hand_id=hand.id, player_id=player_entry.user_id).first()
            if hand_score:
                if hand_score.bet_size:
                    sum_of_bets += hand_score.bet_size
                if hand_score.bonus:
                    bonuses += 1
                if hand_score.score:
                    total_score += hand_score.score
        return {
            'hands_played': hands_played,
            'sum_of_bets': sum_of_bets,
            'bonuses': bonuses,
            'total_score': total_score
        }

    def get_player_relative_positions(self, source_player_id, required_player_id):
        source_player = Player.query.filter_by(game_id=self.id, user_id=source_player_id).first()
        if not source_player:
            return None
        required_player = Player.query.filter_by(game_id=self.id, user_id=required_player_id).first()
        if not required_player:
            return None
        if not required_player.position or not source_player.position:
            return None
        game_players = Player.query.filter_by(game_id=self.id).count()
        return (required_player.position - source_player.position) % game_players



class Player(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, primary_key=True)
    game_id = db.Column(db.Integer, nullable=False, index=True, primary_key=True)
    position = db.Column(db.Integer, nullable=True, default=None, index=True)

    def __repr__(self):
        return '<Player {} on position {} in game {}>'.format(User.query.filter_by(id=self.user_id).first().username, self.position, self.game_id)


class Hand(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False, index=True, primary_key=True)
    serial_no = db.Column(db.Integer, primary_key=True)
    trump = db.Column(db.String(1), nullable=True)
    cards_per_player = db.Column(db.Integer, nullable=True)
    starting_player = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_closed = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return '<Hand {} (hand #{} in game {}): {}{}, starter {}>'.format(self.id, self.serial_no, self.game_id, self.trump if self.trump is not None else '-', self.cards_per_player, self.get_starter().username)

    def get_starter(self):
        return User.query.filter_by(id=self.starting_player).first()

    def get_position(self, user):
        players_count = Player.query.filter_by(game_id=self.game_id).count()
        game = Game.query.filter_by(id=self.game_id).first()
        user_game_pos = game.get_position(user)
        user_hand_pos = ((user_game_pos - self.serial_no) % players_count) + 1
        return user_hand_pos

    def get_player_by_pos(self, position):
        players_count = Player.query.filter_by(game_id=self.game_id).count()
        initial_position = players_count - ((position - self.serial_no) % players_count)
        player = Player.query.filter_by(game_id=self.game_id, position=initial_position).first()
        if player:
            return User.query.filter_by(id=player.user_id).first()
        else:
            return None

    def get_user_initial_hand(self, user, trump=None):
        possible_suits_ordered = ['s', 'c', 'h', 'd']
        if trump:
            if app.debug:
                print('updating possible suits regarding trump (' + str(trump) + ')')
            possible_suits_ordered.remove(trump)
            possible_suits_ordered.append(trump)
        if app.debug:
            print(possible_suits_ordered)
        initial_hand = []
        for suit in possible_suits_ordered:
            suit_cards = list()
            player_cards_suited = DealtCards.query.filter_by(hand_id=self.id, player_id=user.id, card_suit=suit).all()
            for card in player_cards_suited:
                if card.card_id == 'j':
                    if card.card_suit == trump:
                        card_index = 14
                    else:
                        card_index=11
                elif card.card_id == 'q':
                    if card.card_suit == trump:
                        card_index = 10
                    else:
                        card_index = 12
                elif card.card_id == 'k':
                    if card.card_suit == trump:
                        card_index = 11
                    else:
                        card_index = 13
                elif card.card_id == 'a':
                    if card.card_suit == trump:
                        card_index = 12
                    else:
                        card_index = 14
                elif card.card_id == 't':
                    if card.card_suit == trump:
                        card_index = 9
                    else:
                        card_index = 10
                elif card.card_id == '9':
                    if card.card_suit == trump:
                        card_index = 13
                    else:
                        card_index = 9
                else:
                    card_index = int(card.card_id)

                suit_cards.append({
                    'card_index': card_index,
                    'card': str(card.card_id) + card.card_suit
                })
            for card in sorted(suit_cards, key=lambda c: c['card_index']):
                initial_hand.append(card['card'])

        return initial_hand

    def get_user_current_hand(self, user, trump=None):
        initial_cards = self.get_user_initial_hand(user, trump)
        burned_cards = TurnCard.query.filter_by(hand_id=self.id, player_id=user.id)
        burned_cards_list = []
        for card in burned_cards:
            burned_cards_list.append(str(card.card_id) + card.card_suit)
        current_hand = []
        for card in initial_cards:
            if card not in burned_cards_list:
                current_hand.append(card)
        return current_hand

    def is_registered(self, user):
        hand_players = Player.query.filter_by(game_id=self.game_id).all()
        for player in hand_players:
            if player.user_id == user.id:
                return True
        return False

    def next_betting_user(self):
        game_players_ordered = Player.query.filter_by(game_id=self.game_id).order_by(Player.position).all()
        hand_players = {}
        for player in game_players_ordered:
            hand_players[self.get_position(User.query.filter_by(id=player.user_id).first())] = player.user_id
        hand_players_ordered = []
        for index in sorted(hand_players):
            hand_players_ordered.append(hand_players[index])
        for player_id in hand_players_ordered:
            if HandScore.query.filter_by(hand_id=self.id, player_id=player_id).first() is None:
                return User.query.filter_by(id=player_id).first()
        last_turn = self.get_last_turn()
        if last_turn:
            return User.query.filter_by(id=last_turn.took_user_id).first()
        return self.get_starter()

    def get_hand_turned_cards(self):
        turned_cards_obj = TurnCard.query.filter_by(hand_id=self.id).all()
        turned_cards = []
        for tc in turned_cards_obj:
            turned_cards.append(str(tc.card_id) + tc.card_suit)
        return turned_cards

    def user_has_suit(self, user, suit):
        user_hand = self.get_user_current_hand(user)
        for card in user_hand:
            if suit == card[-1:]:
                return True
        return False

    def is_betting_last(self, user):
        players_count = Player.query.filter_by(game_id=self.game_id).count()
        if players_count > 0 and self.get_position(user) % players_count == 0:
            return True
        return False

    def get_sum_of_bets(self):
        hand_bets = HandScore.query.filter_by(hand_id=self.id).all()
        made_bets = 0
        for hb in hand_bets:
            made_bets = made_bets + hb.bet_size
        return made_bets

    def all_bets_made(self):
        hand_bets = HandScore.query.filter_by(hand_id=self.id).all()
        players_count = Player.query.filter_by(game_id=self.game_id).count()
        if players_count != len(hand_bets):
            return False
        for bet in hand_bets:
            if bet.bet_size is None:
                return False
        return True

    def all_turns_made(self):
        hand_turns = Turn.query.filter_by(hand_id=self.id).all()
        finished_hand_turns = 0
        for hand_turn in hand_turns:
            if hand_turn.took_user_id is not None:
                finished_hand_turns =+ 1
        if app.debug:
            print('Hand turns: ' + str(hand_turns))
            print('Finished hand turns: ' + str(finished_hand_turns))
            print('All turns are made? - ' + str(finished_hand_turns >= self.cards_per_player))
        return finished_hand_turns >= self.cards_per_player

    def get_current_turn(self, closed=False):
        hand_turns = Turn.query.filter_by(hand_id=self.id).order_by(Turn.serial_no.desc()).all()
        if not hand_turns:
            return None
        if closed:
            return hand_turns[0]
        for ht in hand_turns:
            if ht.took_user_id is None:
                return ht
        return None

    def get_last_turn(self):
        curr_turn = self.get_current_turn()
        players_count = Player.query.filter_by(game_id=self.game_id).count()
        if TurnCard.query.all():
            hand_turns_ordered = Turn.query.filter_by(hand_id=self.id).order_by(Turn.id.desc()).all()
            for hand_turn in hand_turns_ordered:
                turn_cards_count = TurnCard.query.filter_by(turn_id=hand_turn.id).count()
                if turn_cards_count == players_count and hand_turn != curr_turn:
                    return hand_turn
        return None


    def next_acting_player(self):

        if self.is_closed:
            return None

        # next acting player defining logic (schematically described in https://drive.google.com/file/d/1ApaKjPUeCXoCUVF_v5ui6uddn8flp85i/view?usp=sharing
        # calculating position shift due to made actions in current turn
        source_position = 1
        hand_made_bets = HandScore.query.filter_by(hand_id=self.id).count()
        current_turn = self.get_current_turn()
        played_hands = Hand.query.filter_by(game_id=self.game_id, is_closed=1).count()
        turn_put_cards = 0
        print('current_turn is ' + str(current_turn))
        if current_turn:
            turn_put_cards = TurnCard.query.filter_by(turn_id=current_turn.id).count()

        # getting current players sequence
        game_players_cnt = Player.query.filter_by(game_id=self.game_id).count()
        if game_players_cnt == 0:
            # Error: no players in the game
            if app.debug:
                print('no players in the game')
            return None

        # if bets are not made in hand position shift is defined with made bets
        if hand_made_bets == 0:
            if app.debug:
                print('No bets are made in hand: shift is defined with played hands')
            position_shift = played_hands
        elif hand_made_bets != game_players_cnt:
            if app.debug:
                print('Bets are not made in hand: shift is defined with both made bets and played hands')
            position_shift = hand_made_bets + played_hands
        # if bets are made in hand position shift is defined with put cards in turn
        else:
            if app.debug:
                print('Bets are made in hand: shift is defined with put cards in turn and/or last turn taker')
            turns_in_hand = Turn.query.filter_by(hand_id=self.id).all()
            finished_turns_in_hand = 0
            for turn_in_hand in turns_in_hand:
                if turn_in_hand.took_user_id:
                    finished_turns_in_hand = + 1
            if finished_turns_in_hand == 0:
                if app.debug:
                    print('This is first turn in hand: position shift is defined with put cards and played hands')
                position_shift = turn_put_cards + played_hands
            else:
                if app.debug:
                    print('This is NOT first turn in game: position shift is defined with put cards, starter position is last turn taker position')
                last_turn = self.get_last_turn()
                if not last_turn:
                    if app.debug:
                        print('Something went wrong: last turn not found but should be...')
                    return None
                last_turn_taker = User.query.filter_by(id=last_turn.took_user_id).first()
                source_position_player = Player.query.filter_by(game_id=self.game_id, user_id=last_turn_taker.id).first()
                if not source_position_player:
                    if app.debug:
                        print('Something went wrong: last turn taker position not found but should be...')
                    return None
                source_position = source_position_player.position
                position_shift = turn_put_cards

        #next acting player position calculation
        shifted_position = (source_position + position_shift) % game_players_cnt
        if shifted_position == 0:
            shifted_position = game_players_cnt
        if app.debug:
            print('position_shift: ' + str(position_shift))
            print('source_position: ' + str(source_position))
            print(' player "' + str(User.query.filter_by(id=Player.query.filter_by(position=source_position, game_id=self.game_id).first().user_id).first().username) + '")')
            print('shifted_position: ' + str(shifted_position))
            print(' (player "' + str(User.query.filter_by(id=Player.query.filter_by(position=shifted_position, game_id=self.game_id).first().user_id).first().username) + '")')
        next_player = Player.query.filter_by(game_id=self.game_id, position=shifted_position).first()
        if not next_player:
            # Error: player at calculated position not found
            if app.debug:
                print('player at calculated position (' + str(shifted_position) + ') not found')
            return None
        return User.query.filter_by(id=next_player.user_id).first()


    def next_card_putting_user(self):
        curr_turn = self.get_current_turn()
        last_turn = self.get_last_turn()
        if app.debug:
            print('Current turn is ' + str(curr_turn))
            print('Last turn is ' + str(last_turn))
        if last_turn and curr_turn:         # This is ongoing and not last turn
            if app.debug:
                print('This is ongoing and not last turn')
            turn_players_sorted = self.get_players_relative_positions()
            for turn_player in turn_players_sorted:
                player_card = TurnCard.query.filter_by(turn_id=curr_turn.id, player_id=turn_player['player_id']).first()
                if app.debug:
                    card_string = 'no card'
                    if player_card:
                        card_string = 'card "' + str(player_card.card_id) + str(player_card.card_suit) + '"'
                    print('Player "' + str(User.query.filter_by(id=turn_player['player_id']).first().username) + '" on position #' + str(turn_player['turn_position'] + 1) + ' has ' + card_string)
                if not player_card:
                    return User.query.filter_by(id=turn_player['player_id']).first()
            return User.query.filter_by(id=last_turn.took_user_id).first()
        elif curr_turn:                     # if this is first turn in hand
            if app.debug:
                print('This is first ongoing turn in hand')
            turn_players_sorted = self.get_players_relative_positions()
            if app.debug:
                print("Players' cards in turn:")
            for turn_player in turn_players_sorted:
                player_card = TurnCard.query.filter_by(turn_id=curr_turn.id, player_id=turn_player['player_id']).first()
                if app.debug:
                    card_string = 'no card'
                    if player_card:
                        card_string = 'card "' + str(player_card.card_id) + str(player_card.card_suit) + '"'
                    print('Player "' + str(User.query.filter_by(id=turn_player['player_id']).first().username) + '" on position #' + str(turn_player['turn_position'] + 1) + ' has ' + card_string)
                if app.debug:
                    print(str(player_card))
                if not player_card:
                    return User.query.filter_by(id=turn_player['player_id']).first()
        elif last_turn:                     # if this is last turn in hand
            if app.debug:
                print('Now starting new turn in hand (last turn #' + str(last_turn.id) + ' was taken by player with #' + str(last_turn.took_user_id) + ')')
            return User.query.filter_by(id=last_turn.took_user_id).first()
        if app.debug:
            print('This is first turn of hand')
        return self.get_starter()           # if this is first turn of whole game


    def get_players_relative_positions(self, user_id=None):
        game_players = Player.query.filter_by(game_id=self.game_id).all()
        turn_players = []
        players_count = len(game_players)
        last_turn = self.get_last_turn()
        last_turn_took_player_pos = 0
        if last_turn:
            last_turn_took_player_pos = self.get_position(User.query.filter_by(id=last_turn.took_user_id).first())
        if app.debug:
            print("Players' unsorted positions: ")
        for player in game_players:
            if last_turn:
                turn_position = (self.get_position(
                    User.query.filter_by(id=player.user_id).first()) + last_turn_took_player_pos) % players_count
            else:
                turn_position = self.get_position(User.query.filter_by(id=player.user_id).first())
            turn_players.append({'turn_position': turn_position, 'player_id': player.user_id})
            if app.debug:
                print('Player "' + str(
                    User.query.filter_by(id=player.user_id).first().username) + "'s position is " + str(turn_position))
        if app.debug:
            print("Players' sorted positions in turn #" + str(self.id) + ":")
        if len(turn_players) == 0:
            return []
        result = sorted(turn_players, key = lambda tp: tp['turn_position'])
        if app.debug:
            print(result)
        if user_id:
            for player in result:
                if player['player_id'] == user_id:
                    return player['turn_position']
        return result


class DealtCards(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hand_id = db.Column(db.Integer, db.ForeignKey('hand.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    card_id = db.Column(db.String(1), nullable=False)
    card_suit = db.Column(db.String(1), nullable=False)

    def __repr__(self):
        return '<Card {} dealt to player {} in hand {}>'.format(self.card_id, User.query.filter_by(id=self.player_id).first().username, self.hand_id)


class HandScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hand_id = db.Column(db.Integer, db.ForeignKey('hand.id'))
    bet_size = db.Column(db.Integer)
    player_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    score = db.Column(db.Integer, default=None)
    bonus = db.Column(db.Integer, default=None)

    def __repr__(self):
        return "<Player {}'s score in hand {}>".format(User.query.filter_by(id=self.player_id).first().username, self.hand_id)

    def took_turns(self):
        return Turn.query.filter_by(hand_id=self.hand_id, took_user_id=self.player_id).count()

    def calculate_current_score(self):
        took_turns = Turn.query.filter_by(hand_id=self.hand_id, took_user_id=self.player_id).count()
        score = took_turns
        if took_turns == self.bet_size:
            score = score + 10
            self.bonus = 1
        else:
            self.bonus = 0
        self.score = score
        db.session.commit()
        return score


class Turn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hand_id = db.Column(db.Integer, db.ForeignKey('hand.id'), nullable=False)
    serial_no = db.Column(db.Integer)
    took_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def get_starting_suit(self):
        first_card = TurnCard.query.filter_by(turn_id=self.id).order_by(TurnCard.id).first()
        if first_card:
            return first_card.card_suit
        return None

    def if_put_card(self, user):
        return TurnCard.query.filter_by(turn_id=self.id, player_id=user.id).count() > 0

    def stroke_cards(self):
        return TurnCard.query.filter_by(turn_id=self.id).all()

    def highest_card(self):
        turn_cards = TurnCard.query.filter_by(turn_id=self.id).order_by(TurnCard.id).all()
        turn_suit = self.get_starting_suit()
        trump = Hand.query.filter_by(id=self.hand_id).first().trump
        if trump:
            trump = trump.casefold()
        highest_card = {}
        cards_hierarchy = ['2', '3', '4', '5', '6', '7', '8', '9', 't', 'j', 'q', 'k', 'a']
        trump_hierarchy = ['2', '3', '4', '5', '6', '7', '8', 't', 'q', 'k', 'a', '9', 'j']
        for card in turn_cards:
            if not highest_card:
                # if card is first to be checked it becomes highest automatically
                if app.debug:
                    print(str(card) + ' is first to analyze - it becomes highest')
                highest_card['id'] = card.card_id.casefold()
                highest_card['suit'] = card.card_suit.casefold()
            else:
                card_suit = str(card.card_suit).casefold()
                card_score = str(card.card_id).casefold()
                if card_suit == trump:
                    if highest_card['suit'] != trump or trump_hierarchy.index(str(highest_card['id'])) < trump_hierarchy.index(str(card_score)):
                        if app.debug:
                            print(str(card) + ' is trump and is higher than ' + str(highest_card['id']) + str(highest_card['suit']))
                        highest_card['id'] = card_score
                        highest_card['suit'] = card_suit
                elif turn_suit == card_suit and cards_hierarchy.index(str(highest_card['id'])) < cards_hierarchy.index(card_score) and highest_card['suit'] != trump:
                    # if card is in the same suit with turn and is higher than the highest card within analyzed it becomes highest in turn within analyzed
                    if app.debug:
                        print(str(card) + ' is same suit as turn starting card and is higher than ' + str(highest_card['id']) + str(highest_card['suit']))
                    highest_card['id'] = card_score
                    highest_card['suit'] = card_suit
            if app.debug:
                print('Highest turn card within analyzed ones is ' + str(highest_card))
        return highest_card

    def __repr__(self):
        return "<Turn #{} in hand {}>".format(self.serial_no, self.hand_id)


class TurnCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hand_id = db.Column(db.Integer, db.ForeignKey('hand.id'), nullable=False)
    turn_id = db.Column(db.Integer, db.ForeignKey('turn.id'), nullable=False)
    card_id = db.Column(db.String(1), nullable=False)
    card_suit = db.Column(db.String(1), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def __repr__(self):
        return "<Card {}{} in hand {} put by player {}>".format(self.card_id, self.card_suit, self.hand_id, User.query.filter_by(id=self.player_id).first().username)

class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(10), nullable=False)

    def burn(self):
        self.status = 'used'
        db.session.commit()

class Stats(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    games_played = db.Column(db.Integer, default=None)
    games_won = db.Column(db.Integer, default=None)
    total_score = db.Column(db.Integer, default=None)
    sum_of_bets = db.Column(db.Integer, default=0)
    bonuses = db.Column(db.Integer, default=0)