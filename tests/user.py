import unittest
from app import app, db
from app.models import User, Room
from tests.base_case import BaseCase
import json


class UserModelCase(BaseCase):

    def test_successful_signup(self):
        # Given
        email = "matroskin@prostokvashino.ussr"
        username = "kot Matroskin"
        password = "prettyStrongPassword!"
        payload = json.dumps({
            "email": email,
            "username": username,
            "password": password
        })

        # When
        response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']), headers={"Content-Type": "application/json"}, data=payload)
        u_count = User.query.filter_by(email='matroskin@prostokvashino.ussr').count()

        # Then
        self.assertEqual(1, u_count, msg='User was not created in DB!')
        self.assertEqual('matroskin@prostokvashino.ussr', response.json['email'], msg='Invalid email in response body!')
        self.assertIsNone(response.json['about_me'], msg='About me is not None in response body!')
        self.assertEqual(str, type(response.json['last_seen']), msg='No last seen timestamp in response body!')
        self.assertEqual(app.config['DEFAULT_LANG'], response.json['preferred_lang'], msg='Preferred lang is not set to default for signed up user!')
        self.assertEqual(str, type(response.json['registered']), msg='No registered timestamp in response body!')
        self.assertEqual('kot matroskin', response.json['username'], msg='Invalid username in response body!')
        self.assertEqual(201, response.status_code, msg='Invalid response code ({})!'.format(response.status_code))

    def test_bad_email_signup(self):
        # Given
        email = "matroskin@prostokvashino"
        username = "kot Matroskin"
        password = "prettyStrongPassword!"
        payload = json.dumps({
            "email": email,
            "username": username,
            "password": password
        })

        # When
        response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']), headers={"Content-Type": "application/json"}, data=payload)
        u_count = User.query.filter_by(email='matroskin@prostokvashino.ussr').count()

        # Then
        self.assertEqual(0, u_count, msg='User with bad email was created in DB!')
        self.assertEqual(400, response.status_code, msg='Invalid response code ({})!'.format(response.status_code))

    def test_used_email_signup(self):
        # Given
        email = "matroskin@prostokvashino.ussr"
        username1 = "kot Matroskin"
        username2 = "Matroskin"
        password = "prettyStrongPassword!"
        payload1 = json.dumps({
            "email": email,
            "username": username1,
            "password": password
        })
        payload2 = json.dumps({
            "email": email,
            "username": username2,
            "password": password
        })

        # When
        self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']), headers={"Content-Type": "application/json"}, data=payload1)
        response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']), headers={"Content-Type": "application/json"}, data=payload2)
        u_count = User.query.filter_by(email='matroskin@prostokvashino.ussr').count()

        # Then
        self.assertTrue(u_count < 2, msg="More than one user with specified email were created in DB!")
        self.assertTrue(u_count > 0, msg="User was not created in DB!")
        self.assertEqual(400, response.status_code, msg='Invalid response code ({})!'.format(response.status_code))

    def test_used_login_signup(self):
        # Given
        email1 = "matroskin@prostokvashino.ussr"
        email2 = "matroskin@prostokvashino.com"
        username = "kot Matroskin"
        password = "prettyStrongPassword!"
        payload1 = json.dumps({
            "email": email1,
            "username": username,
            "password": password
        })
        payload2 = json.dumps({
            "email": email2,
            "username": username,
            "password": password
        })

        # When
        self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']), headers={"Content-Type": "application/json"}, data=payload1)
        response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']), headers={"Content-Type": "application/json"}, data=payload2)
        u_count = User.query.filter_by(email='matroskin@prostokvashino.ussr').count()

        # Then
        self.assertTrue(u_count < 2, msg="More than one user with specified username were created in DB!")
        self.assertTrue(u_count > 0, msg="User was not created in DB!")
        self.assertEqual(400, response.status_code, msg='Invalid response code ({})!'.format(response.status_code))
        
    def test_weak_password_signup(self):
        # Given
        email = "matroskin@prostokvashino"
        username = "kot Matroskin"
        password = "weak"
        payload = json.dumps({
            "email": email,
            "username": username,
            "password": password
        })

        # When
        response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']), headers={"Content-Type": "application/json"}, data=payload)
        u_count = User.query.filter_by(email='matroskin@prostokvashino.ussr').count()

        # Then
        self.assertEqual(0, u_count, msg='User with weak password was created in DB!')
        self.assertEqual(400, response.status_code, msg='Invalid response code ({})!'.format(response.status_code))


if __name__ == '__main__':
    unittest.main(verbosity=2)
