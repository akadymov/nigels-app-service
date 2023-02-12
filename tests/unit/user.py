import unittest
from app import db, app
from app.models import User
from tests.base_case import BaseCase


class UserModelCase(BaseCase):

    def test_create_user(self):
        with app.app_context():
            # Given
            email = "matroskin@prostokvashino.ussr"
            username = "Matroskin"
            password = "prettyStrongPassword!"

            # When
            u = User(email=email, username=username)
            u.set_password(password)
            db.session.add(u)
            db.session.commit()

            # Then
            self.assertEqual(1, User.query.filter_by(email=email).count(), msg='User with specified email was not created in DB!')
            self.assertEqual(1, User.query.filter_by(username=username).count(), msg='User with specified username was not created in DB!')
            self.assertTrue(u.check_password(password), msg='Password is set incorrectly!')

    def test_edit_user(self):
        with app.app_context():
            # Given
            u = User(email="matroskin@prostokvashino.ussr", username="Matroskin")
            db.session.add(u)
            db.session.commit()
            email = "matroskin@prostokvashino.ru"
            username = "kot_matroskin"

            # When
            u = User.query.filter_by(username="Matroskin").first()
            u.email = email
            u.username = username
            db.session.commit()

            # Then
            self.assertEqual(1, User.query.filter_by(email=email).count(), msg='User with specified email was not created in DB!')
            self.assertEqual(1, User.query.filter_by(username=username).count(), msg='User with specified username was not created in DB!')


if __name__ == '__main__':
    unittest.main(verbosity=2)
