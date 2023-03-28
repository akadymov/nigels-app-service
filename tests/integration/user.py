import unittest
from app import app
from app.models import User
from tests.base_case import BaseCase
import json
from config import get_settings, get_environment

langs = get_environment('LANG')
env = get_environment()


class UserMethodsCase(BaseCase):

    def test_successful_signup(self):
        with app.app_context():
            # Given
            email = "matroskin@prostokvashino.ussr"
            username = "Matroskin"
            password = "prettyStrongPassword!"
            payload1 = json.dumps({
                "email": email,
                "username": username,
                "password": password,
                "repeatPassword": password
            })
            payload2 = json.dumps({
                "username": username,
                "password": password
            })

            # When
            response = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                     headers={"Content-Type": "application/json"}, data=payload1)
            get_user_response = self.app.get(
                '{base_path}/user/{username}'.format(base_path=get_settings('API_BASE_PATH'), username=username),
                headers={"Content-Type": "application/json"})
            token_response = self.app.post('{base_path}/user/token'.format(base_path=get_settings('API_BASE_PATH')),
                                           headers={"Content-Type": "application/json"}, data=payload2)

            # Then
            self.assertEqual(201, response.status_code,
                             msg='Invalid create user response code ({})!'.format(response.status_code))
            self.assertEqual(email, response.json['email'], msg='Invalid email in response body!')
            self.assertIsNone(response.json['aboutMe'], msg='About me is not None in response body!')
            self.assertEqual(str, type(response.json['lastSeen']), msg='No last seen timestamp in response body!')
            self.assertEqual(langs['DEFAULT'][env], response.json['preferredLang'],
                             msg='Preferred lang is not set to default for signed up user!')
            self.assertEqual(str, type(response.json['registered']), msg='No registered timestamp in response body!')
            self.assertEqual('matroskin', response.json['username'], msg='Invalid username in response body!')

            self.assertEqual(200, get_user_response.status_code,
                             msg='Invalid response code ({}) in get user response!'.format(get_user_response.status_code))
            self.assertEqual(email, get_user_response.json['email'],
                             msg='Invalid email in get user response body!')
            self.assertIsNone(get_user_response.json['aboutMe'], msg='About me is not None in get user response body!')
            self.assertEqual(str, type(get_user_response.json['lastSeen']),
                             msg='No last seen timestamp in get user response body!')
            self.assertEqual(langs['DEFAULT'][env], get_user_response.json['preferredLang'],
                             msg='Preferred lang is not set to default for signed up user!')
            self.assertEqual(str, type(get_user_response.json['registered']),
                             msg='No registered timestamp in response body!')
            self.assertEqual('matroskin', get_user_response.json['username'],
                             msg='Invalid username in get user response body!')

            self.assertEqual(201, token_response.status_code,
                             msg='Invalid response code ({}) in post token response!'.format(token_response.status_code))
            self.assertIsNotNone(token_response.json['expiresIn'], msg='No expiration time in post token response body!')
            self.assertIsNotNone(token_response.json['token'], msg='No jwt-token time in post token response body!')

    def test_bad_email_signup(self):
        with app.app_context():
            # Given
            email = "matroskin@prostokvashino"
            username = "Matroskin"
            password = "prettyStrongPassword!"
            payload = json.dumps({
                "email": email,
                "username": username,
                "password": password,
                "repeatPassword": password
            })

            # When
            response = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                     headers={"Content-Type": "application/json"}, data=payload)
            u_count = User.query.filter_by(email=email).count()
            get_user_response = self.app.get(
                '{base_path}/user/{username}'.format(base_path=get_settings('API_BASE_PATH'), username=username),
                headers={"Content-Type": "application/json"})

            # Then
            self.assertEqual(400, response.status_code, msg='Invalid create user code ({})!'.format(response.status_code))
            self.assertEqual(0, u_count, msg='User with bad email was created in DB!')

            self.assertEqual(404, get_user_response.status_code,
                             msg='Invalid get user response code ({})!'.format(get_user_response.status_code))

    def test_used_email_signup(self):

        with app.app_context():
            # Given
            email = "matroskin@prostokvashino.ussr"
            username1 = "Matroskin"
            username2 = "kot_matroskin"
            password = "prettyStrongPassword!"
            payload1 = json.dumps({
                "email": email,
                "username": username1,
                "password": password,
                "repeatPassword": password
            })
            payload2 = json.dumps({
                "email": email,
                "username": username2,
                "password": password,
                "repeatPassword": password
            })

            # When
            self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                          headers={"Content-Type": "application/json"}, data=payload1)
            response = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                     headers={"Content-Type": "application/json"}, data=payload2)
            u_count = User.query.filter_by(email=email).count()
            get_user_response = self.app.get(
                '{base_path}/user/{username}'.format(base_path=get_settings('API_BASE_PATH'), username=username2),
                headers={"Content-Type": "application/json"})

            # Then
            self.assertEqual(400, response.status_code,
                             msg='Invalid create user response code ({})!'.format(response.status_code))
            self.assertTrue(u_count < 2, msg="More than one user with specified email were created in DB!")
            self.assertTrue(u_count > 0, msg="User was not created in DB!")

            self.assertEqual(404, get_user_response.status_code,
                             msg='Invalid get user response code ({})!'.format(get_user_response.status_code))

    def test_used_login_signup(self):
        with app.app_context():
            # Given
            email1 = "matroskin@prostokvashino.ussr"
            email2 = "matroskin@prostokvashino.com"
            username = "Matroskin"
            password = "prettyStrongPassword!"
            payload1 = json.dumps({
                "email": email1,
                "username": username,
                "password": password,
                "repeatPassword": password
            })
            payload2 = json.dumps({
                "email": email2,
                "username": username,
                "password": password,
                "repeatPassword": password
            })

            # When
            self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                          headers={"Content-Type": "application/json"}, data=payload1)
            response = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                     headers={"Content-Type": "application/json"}, data=payload2)
            u_count = User.query.filter_by(username=username.casefold()).count()
            get_user_response = self.app.get(
                '{base_path}/user/{username}'.format(base_path=get_settings('API_BASE_PATH'), username=username),
                headers={"Content-Type": "application/json"})

            # Then
            self.assertEqual(400, response.status_code,
                             msg='Invalid create user response code ({})!'.format(response.status_code))
            self.assertTrue(u_count < 2, msg="More than one user with specified username were created in DB!")
            self.assertTrue(u_count > 0, msg="User was not created in DB!")

            self.assertEqual(200, get_user_response.status_code,
                             msg='Invalid get user response code ({})!'.format(get_user_response.status_code))

    def test_weak_password_signup(self):
        with app.app_context():
            # Given
            email = "matroskin@prostokvashino"
            username = "Matroskin"
            password = "weak"
            payload = json.dumps({
                "email": email,
                "username": username,
                "password": password,
                "repeatPassword": password
            })

            # When
            response = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                     headers={"Content-Type": "application/json"}, data=payload)
            u_count = User.query.filter_by(email=email).count()
            get_user_response = self.app.get(
                '{base_path}/user/{username}'.format(base_path=get_settings('API_BASE_PATH'), username=username),
                headers={"Content-Type": "application/json"})

            # Then
            self.assertEqual(400, response.status_code,
                             msg='Invalid create user response code ({})!'.format(response.status_code))
            self.assertEqual(0, u_count, msg='User with weak password was created in DB!')

            self.assertEqual(404, get_user_response.status_code,
                             msg='Invalid get user response code ({})!'.format(get_user_response.status_code))

    def test_incorrect_password_auth(self):
        with app.app_context():
            # Given
            email = "matroskin@prostokvashino.ussr"
            username = "Matroskin"
            password = "rightPassword!"
            incorrect_password = "wrongPassword!"
            payload1 = json.dumps({
                "email": email,
                "username": username,
                "password": password,
                "repeatPassword": password
            })
            payload2 = json.dumps({
                "username": username,
                "password": incorrect_password
            })

            # When
            response = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                     headers={"Content-Type": "application/json"}, data=payload1)
            token_response = self.app.post('{base_path}/user/token'.format(base_path=get_settings('API_BASE_PATH')),
                                           headers={"Content-Type": "application/json"}, data=payload2)

            # Then
            self.assertEqual(201, response.status_code,
                             msg='Invalid create user response code ({})!'.format(response.status_code))

            self.assertEqual(401, token_response.status_code,
                             msg='Invalid response code ({}) in post token response!'.format(token_response.status_code))

    def test_update_profile(self):
        with app.app_context():
            # Given
            email = "matroskin@prostokvashino.ussr"
            username = "Matroskin"
            password = "prettyStrongPassword!"
            about_me = "I am cool cat who can milk cow in countryside! Простоквашино рулеззз!"
            email2 = "pechkin@prostokvashino.ussr"
            username2 = "pechkin"
            payload1 = json.dumps({
                "email": email,
                "username": username,
                "password": password,
                "repeatPassword": password
            })
            payload2 = json.dumps({
                "username": username,
                "password": password
            })
            payload3 = json.dumps({
                "email": email2,
                "username": username2,
                "password": password,
                "repeatPassword": password
            })

            # When
            response = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                     headers={"Content-Type": "application/json"}, data=payload1)
            response2 = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                     headers={"Content-Type": "application/json"}, data=payload3)
            token_response = self.app.post('{base_path}/user/token'.format(base_path=get_settings('API_BASE_PATH')),
                                           headers={"Content-Type": "application/json"}, data=payload2)

            # Then
            self.assertEqual(201, response.status_code,
                             msg='Invalid create user response code ({})!'.format(response.status_code))
            self.assertEqual(201, response2.status_code,
                             msg='Invalid create user response code ({})!'.format(response2.status_code))

            self.assertEqual(201, token_response.status_code,
                             msg='Invalid response code ({}) in post token response!'.format(token_response.status_code))
            self.assertIsNotNone(token_response.json['expiresIn'], msg='No expiration time in post token response body!')
            self.assertIsNotNone(token_response.json['token'], msg='No jwt-token time in post token response body!')

            payload4 = json.dumps({
                "email": email,
                "aboutMe": about_me,
                "token": token_response.json['token'],
                "preferredLang": "ru"
            })

            update_profile_response = self.app.put('{base_path}/user/{username}'.format(base_path=get_settings('API_BASE_PATH'), username=username),
                            headers={"Content-Type": "application/json"}, data=payload4)

            payload5 = json.dumps({
                "email": email2,
                "aboutMe": about_me,
                "token": token_response.json['token'],
                "preferredLang": "ru"
            })

            update_profile_response2 = self.app.put('{base_path}/user/{username}'.format(base_path=get_settings('API_BASE_PATH'), username=username2),
                            headers={"Content-Type": "application/json"}, data=payload5)

            payload6 = json.dumps({
                "email": username,
                "aboutMe": about_me,
                "token": token_response.json['token'],
                "preferredLang": "ru"
            })

            update_profile_response3 = self.app.put('{base_path}/user/{username}'.format(base_path=get_settings('API_BASE_PATH'), username=username),
                            headers={"Content-Type": "application/json"}, data=payload6)

            payload7 = json.dumps({
                "email": email2,
                "aboutMe": about_me,
                "token": token_response.json['token'],
                "preferredLang": "ru"
            })

            update_profile_response4 = self.app.put('{base_path}/user/{username}'.format(base_path=get_settings('API_BASE_PATH'), username=username),
                            headers={"Content-Type": "application/json"}, data=payload7)

            payload8 = json.dumps({
                "email": email2,
                "aboutMe": about_me,
                "token": token_response.json['token'],
                "preferredLang": "de"
            })

            update_profile_response5 = self.app.put('{base_path}/user/{username}'.format(base_path=get_settings('API_BASE_PATH'), username=username),
                            headers={"Content-Type": "application/json"}, data=payload8)

            self.assertEqual(200, update_profile_response.status_code,
                             msg='Invalid response code ({}) in update profile response!'.format(update_profile_response.status_code))
            self.assertEqual(401, update_profile_response2.status_code,
                             msg="Invalid response code ({}) in update another user's profile response!".format(update_profile_response2.status_code))
            self.assertEqual(400, update_profile_response3.status_code,
                             msg="Invalid response code ({}) in update profile with bad email response!".format(update_profile_response3.status_code))
            self.assertEqual(400, update_profile_response4.status_code,
                             msg="Invalid response code ({}) in update profile with used email response!".format(update_profile_response4.status_code))
            self.assertEqual(400, update_profile_response5.status_code,
                             msg="Invalid response code ({}) in update profile with bad lang response!".format(update_profile_response4.status_code))
            self.assertEqual(email, update_profile_response.json['email'], msg='Invalid email in get profile response body!')
            self.assertEqual(about_me, update_profile_response.json['aboutMe'], msg='About me is incorrect in get profile response body!')
            self.assertEqual(str, type(update_profile_response.json['lastSeen']), msg='No last seen timestamp in get profile response body!')
            self.assertEqual("ru", update_profile_response.json['preferredLang'],
                             msg='Preferred lang is not changed!')
            self.assertEqual(str, type(update_profile_response.json['registered']), msg='No registered timestamp in get profile response body!')
            self.assertEqual('matroskin', update_profile_response.json['username'], msg='Invalid username in get profile response body!')

    def test_update_profile_default(self):
        with app.app_context():
            # Given
            email = "matroskin@prostokvashino.ussr"
            email2 = "matroskin@prostokvashi.no"
            username = "Matroskin"
            password = "prettyStrongPassword!"
            payload1 = json.dumps({
                "email": email,
                "username": username,
                "password": password,
                "repeatPassword": password
            })
            payload2 = json.dumps({
                "username": username,
                "password": password
            })

            # When
            response = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                     headers={"Content-Type": "application/json"}, data=payload1)
            token_response = self.app.post('{base_path}/user/token'.format(base_path=get_settings('API_BASE_PATH')),
                                           headers={"Content-Type": "application/json"}, data=payload2)

            # Then
            self.assertEqual(201, response.status_code,
                             msg='Invalid create user response code ({})!'.format(response.status_code))

            self.assertEqual(201, token_response.status_code,
                             msg='Invalid response code ({}) in post token response!'.format(token_response.status_code))
            self.assertIsNotNone(token_response.json['expiresIn'], msg='No expiration time in post token response body!')
            self.assertIsNotNone(token_response.json['token'], msg='No jwt-token time in post token response body!')

            payload3 = json.dumps({
                "email": email2,
                "token": token_response.json['token']
            })

            update_profile_response = self.app.put('{base_path}/user/{username}'.format(base_path=get_settings('API_BASE_PATH'), username=username),
                            headers={"Content-Type": "application/json"}, data=payload3)

            self.assertEqual(200, update_profile_response.status_code,
                             msg='Invalid response code ({}) in get profile response!'.format(update_profile_response.status_code))
            self.assertEqual(email2, update_profile_response.json['email'], msg='Invalid email in get profile response body!')
            self.assertIsNone(update_profile_response.json['aboutMe'], msg='About me is not None in response body!')
            self.assertEqual(str, type(update_profile_response.json['lastSeen']), msg='No last seen timestamp in get profile response body!')
            self.assertEqual(langs['DEFAULT'][env], update_profile_response.json['preferredLang'],
                             msg='Preferred lang is not set to default for signed up user!')
            self.assertEqual(str, type(update_profile_response.json['registered']), msg='No registered timestamp in get profile response body!')
            self.assertEqual('matroskin', update_profile_response.json['username'], msg='Invalid username in get profile response body!')

    def test_update_profile_with_invalid_token(self):
        with app.app_context():
            # Given
            email = "matroskin@prostokvashino.ussr"
            username = "Matroskin"
            password = "prettyStrongPassword!"
            payload1 = json.dumps({
                "email": email,
                "username": username,
                "password": password,
                "repeatPassword": password
            })
            payload2 = json.dumps({
                "username": username,
                "password": password
            })

            # When
            response = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                     headers={"Content-Type": "application/json"}, data=payload1)
            token_response = self.app.post('{base_path}/user/token'.format(base_path=get_settings('API_BASE_PATH')),
                                           headers={"Content-Type": "application/json"}, data=payload2)

            # Then
            self.assertEqual(201, response.status_code,
                             msg='Invalid create user response code ({})!'.format(response.status_code))

            self.assertEqual(201, token_response.status_code,
                             msg='Invalid response code ({}) in post token response!'.format(token_response.status_code))
            self.assertIsNotNone(token_response.json['expiresIn'], msg='No expiration time in post token response body!')
            self.assertIsNotNone(token_response.json['token'], msg='No jwt-token time in post token response body!')

            payload3 = json.dumps({
                "email": email,
                "token": "invalidJwtToken"
            })

            update_profile_response = self.app.put('{base_path}/user/{username}'.format(base_path=get_settings('API_BASE_PATH'), username=username),
                            headers={"Content-Type": "application/json"}, data=payload3)

            self.assertEqual(401, update_profile_response.status_code,
                             msg='Invalid response code ({}) in post token response!'.format(update_profile_response.status_code))


if __name__ == '__main__':
    unittest.main(verbosity=2)
