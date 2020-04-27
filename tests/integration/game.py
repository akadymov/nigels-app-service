import unittest
from app import app
from tests.base_case import BaseCase
import json


class GameMethodsCase(BaseCase):

    def test_games(self):
        # Given
        email = "matroskin@prostokvashino.ussr"
        username = "matroskin"
        password = "prettyStrongPassword!"
        room_name1 = "Prostokvashino"
        create_host_payload = json.dumps({
            "email": email,
            "username": username,
            "password": password
        })
        host_auth_payload = json.dumps({
            "username": username,
            "password": password
        })


        # register user
        create_host_response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                                 headers={"Content-Type": "application/json"}, data=create_host_payload)

        self.assertEqual(201, create_host_response.status_code, msg="Failed to create host user! Response code is {}".format(create_host_response.status_code))

        # host auth
        host_token_response = self.app.post('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']),
                                       headers={"Content-Type": "application/json"}, data=host_auth_payload)

        host_token_payload = json.dumps({
            "token": host_token_response.json['token']
        })

        # create room
        create_room_payload = json.dumps({
            "token": host_token_response.json['token'],
            "room_name": room_name1
        })
        create_room_response = self.app.post('{base_path}/room'.format(base_path=app.config['API_BASE_PATH']),
                                             headers={"Content-Type": "application/json"}, data=create_room_payload)

        self.assertEqual(201, create_room_response.status_code, msg="Failed to create room ({})!".format(create_room_response.status_code))

        # start with one player (not allowed)
        start_insufficient_players_response=self.app.post('{base_path}/game/start'.format(base_path=app.config['API_BASE_PATH']),
                                             headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(403, start_insufficient_players_response.status_code,
                         msg="Bad response code when starting game with insufficient players! Response code is {}".format(
                             start_insufficient_players_response.status_code))

        # finish game when one is not started
        finish_b4_start_response = self.app.post('{base_path}/game/finish'.format(base_path=app.config['API_BASE_PATH']),
                                             headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(403, finish_b4_start_response.status_code,
                         msg="Bad response code when finishing game with insufficient players! Response code is {}".format(
                             finish_b4_start_response.status_code))

        # create more users
        email3 = "pechkin@prostokvashino.ussr"
        username3 = "pechkin"
        email4 = "sharik@prostokvashino.ussr"
        username4 = "sharik"
        create_user2_payload = json.dumps({
            "email": email3,
            "username": username3,
            "password": password
        })
        auth_user2_payload = json.dumps({
            "username": username3,
            "password": password
        })
        create_user3_payload = json.dumps({
            "email": email4,
            "username": username4,
            "password": password
        })
        auth_user3_payload = json.dumps({
            "username": username4,
            "password": password
        })

        create_user2_response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                                              headers={"Content-Type": "application/json"}, data=create_user2_payload)

        self.assertEqual(201, create_user2_response.status_code,
                         msg="Failed to create user Pechkin! Response code is {}".format(
                             create_user2_response.status_code))

        # auth
        token_response2 = self.app.post('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']),
                                        headers={"Content-Type": "application/json"}, data=auth_user2_payload)
        user2_token_payload = json.dumps({
            "token": token_response2.json['token']
        })

        # connect user2 to room
        connect_to_room2_response = self.app.post(
            '{base_path}/room/{room_id}/connect'.format(base_path=app.config['API_BASE_PATH'],
                                                        room_id=create_room_response.json['room_id']),
            headers={"Content-Type": "application/json"}, data=user2_token_payload)

        self.assertEqual(200, connect_to_room2_response.status_code,
                         msg="Failed to connect Pechkin to room! Response code is {}".format(
                             connect_to_room2_response.status_code))

        create_user3_response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                                              headers={"Content-Type": "application/json"}, data=create_user3_payload)

        self.assertEqual(201, create_user3_response.status_code,
                         msg="Failed to create user Sharik! Response code is {}".format(
                             create_user3_response.status_code))

        # auth
        token_response3 = self.app.post('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']),
                                        headers={"Content-Type": "application/json"}, data=auth_user3_payload)
        user3_token_payload = json.dumps({
            "token": token_response3.json['token']
        })

        # connect user3 to room
        connect_to_room3_response = self.app.post(
            '{base_path}/room/{room_id}/connect'.format(base_path=app.config['API_BASE_PATH'],
                                                        room_id=create_room_response.json['room_id']),
            headers={"Content-Type": "application/json"}, data=user3_token_payload)

        self.assertEqual(200, connect_to_room3_response.status_code,
                         msg="Failed to connect Sharik to room! Response code is {}".format(
                             connect_to_room3_response.status_code))

        # start by non-host (not allowed)
        start_by_non_host_response = self.app.post('{base_path}/game/start'.format(base_path=app.config['API_BASE_PATH']),
                                             headers={"Content-Type": "application/json"}, data=user2_token_payload)

        self.assertEqual(403, start_by_non_host_response.status_code,
                         msg="Bad response code when starting game with insufficient players! Response code is {}".format(
                             start_by_non_host_response.status_code))

        # successful game start
        successful_start_response = self.app.post('{base_path}/game/start'.format(base_path=app.config['API_BASE_PATH']),
                                             headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(200, successful_start_response.status_code,
                         msg="Failed to start game by host! Response code is {}".format(
                             successful_start_response.status_code))

        # starting game when one is already started
        repeat_start_response = self.app.post('{base_path}/game/start'.format(base_path=app.config['API_BASE_PATH']),
                                             headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(403, repeat_start_response.status_code,
                         msg="Bad response code when starting second game in a row! Response code is {}".format(
                             repeat_start_response.status_code))

        # finish by non-host (not allowed)
        finish_by_non_host_response = self.app.post('{base_path}/game/finish'.format(base_path=app.config['API_BASE_PATH']),
                                             headers={"Content-Type": "application/json"}, data=user2_token_payload)

        self.assertEqual(403, finish_by_non_host_response.status_code,
                         msg="Bad response code when finishing game with insufficient players! Response code is {}".format(
                             finish_by_non_host_response.status_code))

        # successful game finish
        successful_finish_response = self.app.post('{base_path}/game/finish'.format(base_path=app.config['API_BASE_PATH']),
                                             headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(200, successful_finish_response.status_code,
                         msg="Failed to finish game by host! Response code is {}".format(
                             successful_finish_response.status_code))

        # finishing game when one is already finished
        repeat_finish_response = self.app.post('{base_path}/game/finish'.format(base_path=app.config['API_BASE_PATH']),
                                             headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(403, repeat_finish_response.status_code,
                         msg="Bad response code when finishing second game in a row! Response code is {}".format(
                             repeat_finish_response.status_code))


if __name__ == '__main__':
    unittest.main(verbosity=2)
