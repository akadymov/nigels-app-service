import unittest
from app import app
from app.models import User
from tests.base_case import BaseCase
import json


class UserMethodsCase(BaseCase):

    def test_successful_signup(self):
        # Given
        email = "matroskin@prostokvashino.ussr"
        username = "Matroskin"
        password = "prettyStrongPassword!"
        payload1 = json.dumps({
            "email": email,
            "username": username,
            "password": password
        })
        payload2 = json.dumps({
            "username": username,
            "password": password
        })

        # When
        response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                                 headers={"Content-Type": "application/json"}, data=payload1)
        get_user_response = self.app.get(
            '{base_path}/user/{username}'.format(base_path=app.config['API_BASE_PATH'], username=username),
            headers={"Content-Type": "application/json"})
        token_response = self.app.post('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']),
                                       headers={"Content-Type": "application/json"}, data=payload2)

        # Then
        print()

        print('POST {base_path}/user'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(201, response.status_code,
                         msg='Invalid create user response code ({})!'.format(response.status_code))
        self.assertEqual(email, response.json['email'], msg='Invalid email in response body!')
        self.assertIsNone(response.json['about_me'], msg='About me is not None in response body!')
        self.assertEqual(str, type(response.json['last_seen']), msg='No last seen timestamp in response body!')
        self.assertEqual(app.config['DEFAULT_LANG'], response.json['preferred_lang'],
                         msg='Preferred lang is not set to default for signed up user!')
        self.assertEqual(str, type(response.json['registered']), msg='No registered timestamp in response body!')
        self.assertEqual('matroskin', response.json['username'], msg='Invalid username in response body!')

        print('GET {base_path}/user/{username}'.format(base_path=app.config['API_BASE_PATH'], username=username))
        self.assertEqual(200, get_user_response.status_code,
                         msg='Invalid response code ({}) in get user response!'.format(get_user_response.status_code))
        self.assertEqual(email, get_user_response.json['email'],
                         msg='Invalid email in get user response body!')
        self.assertIsNone(get_user_response.json['about_me'], msg='About me is not None in get user response body!')
        self.assertEqual(str, type(get_user_response.json['last_seen']),
                         msg='No last seen timestamp in get user response body!')
        self.assertEqual(app.config['DEFAULT_LANG'], get_user_response.json['preferred_lang'],
                         msg='Preferred lang is not set to default for signed up user!')
        self.assertEqual(str, type(get_user_response.json['registered']),
                         msg='No registered timestamp in response body!')
        self.assertEqual('matroskin', get_user_response.json['username'],
                         msg='Invalid username in get user response body!')

        print('POST {base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(201, token_response.status_code,
                         msg='Invalid response code ({}) in post token response!'.format(token_response.status_code))
        self.assertIsNotNone(token_response.json['expires_in'], msg='No expiration time in post token response body!')
        self.assertIsNotNone(token_response.json['token'], msg='No jwt-token time in post token response body!')

    def test_bad_email_signup(self):
        # Given
        email = "matroskin@prostokvashino"
        username = "Matroskin"
        password = "prettyStrongPassword!"
        payload = json.dumps({
            "email": email,
            "username": username,
            "password": password
        })

        # When
        response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                                 headers={"Content-Type": "application/json"}, data=payload)
        u_count = User.query.filter_by(email=email).count()
        get_user_response = self.app.get(
            '{base_path}/user/{username}'.format(base_path=app.config['API_BASE_PATH'], username=username),
            headers={"Content-Type": "application/json"})

        # Then
        print()

        print('POST {base_path}/user'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(400, response.status_code, msg='Invalid create user code ({})!'.format(response.status_code))
        self.assertEqual(0, u_count, msg='User with bad email was created in DB!')

        print('GET {base_path}/user/{username}'.format(base_path=app.config['API_BASE_PATH'], username=username))
        self.assertEqual(404, get_user_response.status_code,
                         msg='Invalid get user response code ({})!'.format(get_user_response.status_code))

    def test_used_email_signup(self):
        # Given
        email = "matroskin@prostokvashino.ussr"
        username1 = "Matroskin"
        username2 = "kot_matroskin"
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
        self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                      headers={"Content-Type": "application/json"}, data=payload1)
        response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                                 headers={"Content-Type": "application/json"}, data=payload2)
        u_count = User.query.filter_by(email=email).count()
        get_user_response = self.app.get(
            '{base_path}/user/{username}'.format(base_path=app.config['API_BASE_PATH'], username=username2),
            headers={"Content-Type": "application/json"})

        # Then
        print()

        print('POST {base_path}/user'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(400, response.status_code,
                         msg='Invalid create user response code ({})!'.format(response.status_code))
        self.assertTrue(u_count < 2, msg="More than one user with specified email were created in DB!")
        self.assertTrue(u_count > 0, msg="User was not created in DB!")

        print('GET {base_path}/user/{username}'.format(base_path=app.config['API_BASE_PATH'], username=username2))
        self.assertEqual(404, get_user_response.status_code,
                         msg='Invalid get user response code ({})!'.format(get_user_response.status_code))

    def test_used_login_signup(self):
        # Given
        email1 = "matroskin@prostokvashino.ussr"
        email2 = "matroskin@prostokvashino.com"
        username = "Matroskin"
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
        self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                      headers={"Content-Type": "application/json"}, data=payload1)
        response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                                 headers={"Content-Type": "application/json"}, data=payload2)
        u_count = User.query.filter_by(username=username.casefold()).count()
        get_user_response = self.app.get(
            '{base_path}/user/{username}'.format(base_path=app.config['API_BASE_PATH'], username=username),
            headers={"Content-Type": "application/json"})

        # Then
        print()

        print('POST {base_path}/user'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(400, response.status_code,
                         msg='Invalid create user response code ({})!'.format(response.status_code))
        self.assertTrue(u_count < 2, msg="More than one user with specified username were created in DB!")
        self.assertTrue(u_count > 0, msg="User was not created in DB!")

        print('GET {base_path}/user/{username}'.format(base_path=app.config['API_BASE_PATH'], username=username))
        self.assertEqual(200, get_user_response.status_code,
                         msg='Invalid get user response code ({})!'.format(get_user_response.status_code))

    def test_weak_password_signup(self):
        # Given
        email = "matroskin@prostokvashino"
        username = "Matroskin"
        password = "weak"
        payload = json.dumps({
            "email": email,
            "username": username,
            "password": password
        })

        # When
        response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                                 headers={"Content-Type": "application/json"}, data=payload)
        u_count = User.query.filter_by(email=email).count()
        get_user_response = self.app.get(
            '{base_path}/user/{username}'.format(base_path=app.config['API_BASE_PATH'], username=username),
            headers={"Content-Type": "application/json"})

        # Then
        print()

        print('POST {base_path}/user'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(400, response.status_code,
                         msg='Invalid create user response code ({})!'.format(response.status_code))
        self.assertEqual(0, u_count, msg='User with weak password was created in DB!')

        print('GET {base_path}/user/{username}'.format(base_path=app.config['API_BASE_PATH'], username=username))
        self.assertEqual(404, get_user_response.status_code,
                         msg='Invalid get user response code ({})!'.format(get_user_response.status_code))

    def test_incorrect_password_auth(self):
        # Given
        email = "matroskin@prostokvashino.ussr"
        username = "Matroskin"
        password = "rightPassword!"
        incorrect_password = "wrongPassword!"
        payload1 = json.dumps({
            "email": email,
            "username": username,
            "password": password
        })
        payload2 = json.dumps({
            "username": username,
            "password": incorrect_password
        })

        # When
        response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                                 headers={"Content-Type": "application/json"}, data=payload1)
        token_response = self.app.post('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']),
                                       headers={"Content-Type": "application/json"}, data=payload2)

        # Then
        print()

        print('POST {base_path}/user'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(201, response.status_code,
                         msg='Invalid create user response code ({})!'.format(response.status_code))

        print('POST {base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(401, token_response.status_code,
                         msg='Invalid response code ({}) in post token response!'.format(token_response.status_code))

    def test_update_profile(self):
        # Given
        email = "matroskin@prostokvashino.ussr"
        username = "Matroskin"
        password = "prettyStrongPassword!"
        about_me = "I am cool cat who can milk cow in countryside! Простоквашино рулеззз!"
        payload1 = json.dumps({
            "email": email,
            "username": username,
            "password": password
        })
        payload2 = json.dumps({
            "username": username,
            "password": password
        })

        # When
        response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                                 headers={"Content-Type": "application/json"}, data=payload1)
        token_response = self.app.post('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']),
                                       headers={"Content-Type": "application/json"}, data=payload2)

        # Then
        print()

        print('POST {base_path}/user'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(201, response.status_code,
                         msg='Invalid create user response code ({})!'.format(response.status_code))

        print('POST {base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(201, token_response.status_code,
                         msg='Invalid response code ({}) in post token response!'.format(token_response.status_code))
        self.assertIsNotNone(token_response.json['expires_in'], msg='No expiration time in post token response body!')
        self.assertIsNotNone(token_response.json['token'], msg='No jwt-token time in post token response body!')

        payload3 = json.dumps({
            "email": email,
            "about_me": about_me,
            "token": token_response.json['token'],
            "preferred_lang": "ru"
        })

        update_profile_response = self.app.put('{base_path}/user/{username}'.format(base_path=app.config['API_BASE_PATH'], username=username),
                        headers={"Content-Type": "application/json"}, data=payload3)

        print('PUT {base_path}/user/<username>'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(200, update_profile_response.status_code,
                         msg='Invalid response code ({}) in get profile response!'.format(update_profile_response.status_code))
        self.assertEqual(email, update_profile_response.json['email'], msg='Invalid email in get profile response body!')
        self.assertEqual(about_me, update_profile_response.json['about_me'], msg='About me is incorrect in get profile response body!')
        self.assertEqual(str, type(update_profile_response.json['last_seen']), msg='No last seen timestamp in get profile response body!')
        self.assertEqual("ru", update_profile_response.json['preferred_lang'],
                         msg='Preferred lang is not changed!')
        self.assertEqual(str, type(update_profile_response.json['registered']), msg='No registered timestamp in get profile response body!')
        self.assertEqual('matroskin', update_profile_response.json['username'], msg='Invalid username in get profile response body!')

    def test_update_profile_default(self):
        # Given
        email = "matroskin@prostokvashino.ussr"
        email2 = "matroskin@prostokvashi.no"
        username = "Matroskin"
        password = "prettyStrongPassword!"
        payload1 = json.dumps({
            "email": email,
            "username": username,
            "password": password
        })
        payload2 = json.dumps({
            "username": username,
            "password": password
        })

        # When
        response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                                 headers={"Content-Type": "application/json"}, data=payload1)
        token_response = self.app.post('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']),
                                       headers={"Content-Type": "application/json"}, data=payload2)

        # Then
        print()

        print('POST {base_path}/user'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(201, response.status_code,
                         msg='Invalid create user response code ({})!'.format(response.status_code))

        print('POST {base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(201, token_response.status_code,
                         msg='Invalid response code ({}) in post token response!'.format(token_response.status_code))
        self.assertIsNotNone(token_response.json['expires_in'], msg='No expiration time in post token response body!')
        self.assertIsNotNone(token_response.json['token'], msg='No jwt-token time in post token response body!')

        payload3 = json.dumps({
            "email": email2,
            "token": token_response.json['token']
        })

        update_profile_response = self.app.put('{base_path}/user/{username}'.format(base_path=app.config['API_BASE_PATH'], username=username),
                        headers={"Content-Type": "application/json"}, data=payload3)

        print('PUT {base_path}/user/<username>'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(200, update_profile_response.status_code,
                         msg='Invalid response code ({}) in get profile response!'.format(update_profile_response.status_code))
        self.assertEqual(email2, update_profile_response.json['email'], msg='Invalid email in get profile response body!')
        self.assertIsNone(update_profile_response.json['about_me'], msg='About me is not None in response body!')
        self.assertEqual(str, type(update_profile_response.json['last_seen']), msg='No last seen timestamp in get profile response body!')
        self.assertEqual(app.config['DEFAULT_LANG'], update_profile_response.json['preferred_lang'],
                         msg='Preferred lang is not set to default for signed up user!')
        self.assertEqual(str, type(update_profile_response.json['registered']), msg='No registered timestamp in get profile response body!')
        self.assertEqual('matroskin', update_profile_response.json['username'], msg='Invalid username in get profile response body!')

    def test_update_profile_with_invalid_token(self):
        # Given
        email = "matroskin@prostokvashino.ussr"
        username = "Matroskin"
        password = "prettyStrongPassword!"
        payload1 = json.dumps({
            "email": email,
            "username": username,
            "password": password
        })
        payload2 = json.dumps({
            "username": username,
            "password": password
        })

        # When
        response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                                 headers={"Content-Type": "application/json"}, data=payload1)
        token_response = self.app.post('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']),
                                       headers={"Content-Type": "application/json"}, data=payload2)

        # Then
        print()

        print('POST {base_path}/user'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(201, response.status_code,
                         msg='Invalid create user response code ({})!'.format(response.status_code))

        print('POST {base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(201, token_response.status_code,
                         msg='Invalid response code ({}) in post token response!'.format(token_response.status_code))
        self.assertIsNotNone(token_response.json['expires_in'], msg='No expiration time in post token response body!')
        self.assertIsNotNone(token_response.json['token'], msg='No jwt-token time in post token response body!')

        payload3 = json.dumps({
            "email": email,
            "token": "invalidJwtToken"
        })

        update_profile_response = self.app.put('{base_path}/user/{username}'.format(base_path=app.config['API_BASE_PATH'], username=username),
                        headers={"Content-Type": "application/json"}, data=payload3)

        print('POST {base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']))
        self.assertEqual(401, update_profile_response.status_code,
                         msg='Invalid response code ({}) in post token response!'.format(update_profile_response.status_code))


if __name__ == '__main__':
    unittest.main(verbosity=2)
