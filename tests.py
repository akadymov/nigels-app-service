import unittest
from app import app, db
from app.models import User, Room
from app.routes import get_rooms


class UserModelCase(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def testRoomConnection(self):
        u1 = User(username='kot Matroskin')
        u2 = User(username='dyadya Fedor')
        r = Room(room_name='Prostokvashino', host=u1)
        db.session.add(u1)
        db.session.add(u2)
        db.session.add(r)
        db.session.commit()
        self.assertEqual(u1.connected_rooms.all(), [])
        self.assertEqual(r.connected_users.all(), [])

        r.connect(u1)
        db.session.commit()
        self.assertTrue(r.is_connected(u1))
        self.assertTrue(u1.is_connected_to_room(r))
        self.assertEqual(u1.connected_rooms.count(), 1)
        self.assertEqual(u1.connected_rooms.first().room_name, 'Prostokvashino')
        self.assertEqual(r.connected_users.count(), 1)
        self.assertEqual(r.connected_users.first().username, 'kot Matroskin')
        self.assertTrue(r.is_connected(u1))
        self.assertFalse(r.is_connected(u2))

        r.disconnect(u1)
        db.session.commit()
        self.assertFalse(r.is_connected(u1))
        self.assertEqual(r.connected_users.count(), 0)
        self.assertEqual(u1.connected_rooms.count(), 0)

    # TODO
    """def testGetRoomsMethod(self):
        u1 = User(username='kot Matroskin')
        u2 = User(username='dyadya Fedor')
        u3 = User(username='pochtalyon Pechkin')
        r1 = Room(room_name='Prostokvashino', host=u1)
        r2 = Room(room_name='City', host=u2)
        db.session.add(u1)
        db.session.add(u2)
        db.session.add(u3)
        db.session.add(r1)
        db.session.add(r2)
        db.session.commit()
        r1.connect(u1)
        r1.connect(u2)
        r1.connect(u3)
        r2.connect(u2)
        db.session.commit()
        with app.app_context():
            rooms = get_rooms()
        self.assertEqual(rooms.count(), 2)
        self.assertEqual(rooms[0]['connected_users'], 3)
        self.assertEqual(rooms[0]['host'], 'kot Matroskin')
        self.assertEqual(rooms[0]['room_name'], 'Prostokvashino')
        self.assertEqual(rooms[1]['connected_users'], 1)
        self.assertEqual(rooms[1]['host'], 'dyadya Fedor')
        self.assertEqual(rooms[1]['room_name'], 'City')"""


if __name__ == '__main__':
    unittest.main(verbosity=2)
