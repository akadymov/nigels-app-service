from datetime import datetime
from app import db, login, app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)


connections = db.Table(
    'connections',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('room_id', db.Integer, db.ForeignKey('room.id'))
)


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
        backref=db.backref('connected_users', lazy='dynamic')
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
        s = Serializer(app.config['SECRET_KEY'], expires_in=app.config['TOKEN_LIFETIME'])
        return s.dumps({'username': self.username, 'email': self.email})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None
        except BadSignature:
            return None
        user = User.query.filter_by(username=data['username']).first()
        return user


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_name = db.Column(db.String(64), index=True, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    games = db.relationship('Game', backref='room', lazy='dynamic')
    closed = db.Column(db.DateTime)
    connected_users_bad = db.relationship(
        'User',
        secondary=connections,
        backref=db.backref('connected_rooms', lazy='dynamic')
    )

    def __repr__(self):
        return '<Room {} (created by {} at {})>'.format(self.room_name, self.host.username, self.created)

    def connect(self, user):
        self.connected_users.append(user)

    def disconnect(self, user):
        self.connected_users.remove(user)

    def is_connected(self, user):
        return self.connected_users.filter(
            connections.c.user_id == user.id).count() > 0


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False, index=True)
    started = db.Column(db.DateTime, nullable=True, default=datetime.utcnow())
    finished = db.Column(db.DateTime, nullable=True, default=None)
    winner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)

    def connect(self, user):
        self.players.append(user)


class Player(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, primary_key=True)
    game_id = db.Column(db.Integer, nullable=False, index=True, primary_key=True)
    position = db.Column(db.Integer, nullable=True, default=None, index=True)
