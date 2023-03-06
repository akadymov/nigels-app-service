from datetime import datetime
from app import db, login, app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
# from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
from flask import url_for, jsonify
from time import time
import jwt
from sqlalchemy import text



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
        # s = Serializer(app.config['SECRET_KEY']) #, expires_in=app.config['TOKEN_LIFETIME'])
        return jwt.encode(
            {'username': self.username, 'email': self.email},
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        # return s.dumps({'username': self.username, 'email': self.email})

    @staticmethod
    def verify_auth_token(token):
        # s = Serializer(app.config['SECRET_KEY'])
        try:
            #print(token)
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            #print(data)
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidIssuerError:
            return None
        except jwt.InvalidTokenError:
            return None
        #print(data['username'])
        user = User.query.filter_by(username=data['username']).first()
        return user

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
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
        return result[0]


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False, index=True)
    started = db.Column(db.DateTime, nullable=True, default=datetime.utcnow())
    finished = db.Column(db.DateTime, nullable=True, default=None)
    winner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    hands = db.relationship('Hand', backref='game', lazy='dynamic')

    def __repr__(self):
        return '<Game {}, room {}, started on {}>'.format(self.id, self.room_id, self.started)

    def connect(self, user):
        self.players.append(user)

    def get_starter(self):
        game_players = Player.query.filter_by(game_id=self.id).all()
        for gp in game_players:
            if gp.position == 1:
                return User.query.filter_by(id=gp.user_id).first()

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
        game_scores = {}
        played_hands = Hand.query.filter_by(game_id=self.id).all()
        game_scores['total'] = {}
        for player in self.players.all():
            username = User.query.filter_by(id=player.id).first().username
            game_scores['total'][username] = {}
            game_scores['total'][username]['score'] = 0
        for hand in played_hands:
            game_scores['hand #' + str(hand.serial_no)] = {}
            game_scores['hand #' + str(hand.serial_no)]['cards_per_player'] = hand.cards_per_player
            game_scores['hand #' + str(hand.serial_no)]['trump'] = hand.trump
            for player in self.players.all():
                username = User.query.filter_by(id=player.id).first().username
                hand_score = HandScore.query.filter_by(hand_id=hand.id, player_id=player.id).first()
                print(hand_score)
                game_scores['hand #' + str(hand.serial_no)][username] = {}
                game_scores['hand #' + str(hand.serial_no)][username]['bet_size'] = hand_score.bet_size if hand_score.bet_size else None
                game_scores['hand #' + str(hand.serial_no)][username]['score'] = hand_score.score if hand_score.score else None
                game_scores['hand #' + str(hand.serial_no)][username]['bonus'] = hand_score.bonus if hand_score.bonus else None
                game_scores['total'][username]['score'] = game_scores['total'][username]['score'] + hand_score.score if hand_score.score else 0
        return game_scores


class Player(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, primary_key=True)
    game_id = db.Column(db.Integer, nullable=False, index=True, primary_key=True)
    position = db.Column(db.Integer, nullable=True, default=None, index=True)

    def __repr__(self):
        return '<Player {} on position {} in game {}>'.format(User.query.filter_by(id=self.id).first().username, self.position, self.game_id)


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

    def get_user_initial_hand(self, user):
        possible_suits_ordered = ['d', 's', 'h', 'c']
        initial_hand = []
        for suit in possible_suits_ordered:
            player_cards_suited = DealtCards.query.filter_by(hand_id=self.id, player_id=user.id, card_suit=suit).all()
            for card in player_cards_suited:
                initial_hand.append(str(card.card_id) + card.card_suit)
        return initial_hand

    def get_user_current_hand(self, user):
        initial_cards = self.get_user_initial_hand(user)
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
            print(last_turn.took_user_id)
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
            if hand_turn.took_user_id:
                finished_hand_turns =+ 1
        print(finished_hand_turns)
        print(self.cards_per_player)
        return finished_hand_turns >= self.cards_per_player

    def get_current_turn(self, closed=False):
        players_count = Player.query.filter_by(game_id=self.game_id).count()
        hand_turns = Turn.query.filter_by(hand_id=self.id).order_by(Turn.serial_no.desc()).all()
        # print(hand_turns)
        if not hand_turns:
            return None
        if closed:
            return hand_turns[0]
        for ht in hand_turns:
            turn_cards_count = TurnCard.query.filter_by(turn_id=ht.id).count()
            if turn_cards_count != players_count:
                return Turn.query.filter_by(id=ht.id).first()
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

    def next_card_putting_user(self):
        curr_turn = self.get_current_turn()
        last_turn = self.get_last_turn()
        game_players = Player.query.filter_by(game_id=self.game_id).all()
        players_count = Player.query.filter_by(game_id=self.game_id).count()
        turn_players = {}
        if last_turn and curr_turn:
            last_turn_took_player_pos = self.get_position(User.query.filter_by(id=last_turn.took_user_id).first())
            for player in game_players:
                turn_position = (self.get_position(User.query.filter_by(id=player.user_id).first()) + last_turn_took_player_pos) % players_count
                turn_players[turn_position] = player.user_id
            turn_players_ordered = []
            for index in sorted(turn_players):
                turn_players_ordered.append(turn_players[index])
            for player_id in turn_players_ordered:
                player_card = TurnCard.query.filter_by(turn_id=curr_turn.id, player_id=player_id).first()
                if not player_card:
                    return User.query.filter_by(id=player_id).first()
            return User.query.filter_by(id=last_turn.took_user_id).first()
        elif curr_turn:
            for player in game_players:
                turn_position = self.get_position(User.query.filter_by(id=player.user_id).first())
                turn_players[turn_position] = player.user_id
            turn_players_ordered = []
            for index in sorted(turn_players):
                turn_players_ordered.append(turn_players[index])
            for player_id in turn_players_ordered:
                player_card = TurnCard.query.filter_by(turn_id=curr_turn.id, player_id=player_id).first()
                if not player_card:
                    return User.query.filter_by(id=player_id).first()
        elif last_turn:
            print(last_turn.took_user_id)
            return User.query.filter_by(id=last_turn.took_user_id).first()
        return self.get_starter()


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
        trump = Hand.query.filter_by(id=self.hand_id).first().trump.casefold()
        highest_card = {}
        turn_suit = self.get_starting_suit().casefold()
        cards_hierarchy = ['2', '3', '4', '5', '6', '7', '8', '9', 't', 'j', 'q', 'k', 'a']
        trump_hierarchy = ['2', '3', '4', '5', '6', '7', '8', 't', 'q', 'k', 'a', '9', 'j']
        for card in turn_cards:
            if not highest_card:
                highest_card['id'] = card.card_id.casefold()
                highest_card['suit'] = card.card_suit.casefold()
            else:
                card_suit = str(card.card_suit).casefold()
                card_score = str(card.card_id).casefold()
                if card_suit == trump:
                    if highest_card['suit'] != trump or trump_hierarchy.index(str(highest_card['id'])) < trump_hierarchy.index(card_score):
                        highest_card['id'] = card_score
                        highest_card['suit'] = card_suit
                elif cards_hierarchy.index(str(highest_card['id'])) \
                        < cards_hierarchy.index(card_score):
                    highest_card['id'] = card_score
                    highest_card['suit'] = card_suit
                elif turn_cards.index(card) == 0:
                    highest_card['id'] = card_score
                    highest_card['suit'] = card_suit
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
