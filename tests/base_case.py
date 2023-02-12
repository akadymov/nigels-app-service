import unittest
from app import app, db


class BaseCase(unittest.TestCase):
    def setUp(self):
        with app.app_context():
            app.config['ENVIRONMENT'] = 'TEST'
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
            self.app = app.test_client()
            self.db = db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
