from app import db
from datetime import datetime


connections = db.Table(
    'connections',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('room_id', db.Integer, db.ForeignKey('room.id'))
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    rooms = db.relationship('Room', backref='host', lazy='dynamic')
    connected_rooms_bad = db.relationship(
        'Room',
        secondary=connections,
        backref=db.backref('connected_users', lazy='dynamic')
    )

    def __repr__(self):
        return '<User {} (email: {})>'.format(self.username, self.email)

    def is_connected_to_room(self, room):
        return self.connected_rooms.filter(
            connections.c.room_id == room.id).count() > 0


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_name = db.Column(db.String(64), index=True, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created = db.Column(db.DateTime, default=datetime.utcnow)
    finished = db.Column(db.DateTime)
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
