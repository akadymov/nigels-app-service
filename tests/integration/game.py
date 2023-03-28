import unittest
from app import app
from tests.base_case import BaseCase
import json
from config import get_settings


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
            "password": password,
            "repeatPassword": password
        })
        host_auth_payload = json.dumps({
            "username": username,
            "password": password
        })


        # register user
        create_host_response = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                 headers={"Content-Type": "application/json"}, data=create_host_payload)

        self.assertEqual(201, create_host_response.status_code, msg="Failed to create host user! Response code is {}".format(create_host_response.status_code))

        # host auth
        host_token_response = self.app.post('{base_path}/user/token'.format(base_path=get_settings('API_BASE_PATH')),
                                       headers={"Content-Type": "application/json"}, data=host_auth_payload)

        host_token_payload = json.dumps({
            "token": host_token_response.json['token']
        })

        # create room
        create_room_payload = json.dumps({
            "token": host_token_response.json['token'],
            "roomName": room_name1
        })
        create_room_response = self.app.post('{base_path}/room'.format(base_path=get_settings('API_BASE_PATH')),
                                             headers={"Content-Type": "application/json"}, data=create_room_payload)

        self.assertEqual(201, create_room_response.status_code, msg="Failed to create room ({})!".format(create_room_response.status_code))

        # start with one player (not allowed)
        start_insufficient_players_response=self.app.post('{base_path}/game/start'.format(base_path=get_settings('API_BASE_PATH')),
                                             headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(403, start_insufficient_players_response.status_code,
                         msg="Bad response code when starting game with insufficient players! Response code is {}".format(
                             start_insufficient_players_response.status_code))

        # finish game when one is not started
        finish_b4_start_response = self.app.post('{base_path}/game/finish'.format(base_path=get_settings('API_BASE_PATH')),
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
            "password": password,
            "repeatPassword": password
        })
        auth_user2_payload = json.dumps({
            "username": username3,
            "password": password
        })
        create_user3_payload = json.dumps({
            "email": email4,
            "username": username4,
            "password": password,
            "repeatPassword": password
        })
        auth_user3_payload = json.dumps({
            "username": username4,
            "password": password
        })

        create_user2_response = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                              headers={"Content-Type": "application/json"}, data=create_user2_payload)

        self.assertEqual(201, create_user2_response.status_code,
                         msg="Failed to create user Pechkin! Response code is {}".format(
                             create_user2_response.status_code))

        # auth
        token_response2 = self.app.post('{base_path}/user/token'.format(base_path=get_settings('API_BASE_PATH')),
                                        headers={"Content-Type": "application/json"}, data=auth_user2_payload)
        user2_token_payload = json.dumps({
            "token": token_response2.json['token']
        })

        # connect user2 to room
        connect_to_room2_response = self.app.post(
            '{base_path}/room/{room_id}/connect'.format(base_path=get_settings('API_BASE_PATH'),
                                                        room_id=create_room_response.json['roomId']),
            headers={"Content-Type": "application/json"}, data=user2_token_payload)

        self.assertEqual(200, connect_to_room2_response.status_code,
                         msg="Failed to connect Pechkin to room! Response code is {}".format(
                             connect_to_room2_response.status_code))

        create_user3_response = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                              headers={"Content-Type": "application/json"}, data=create_user3_payload)

        self.assertEqual(201, create_user3_response.status_code,
                         msg="Failed to create user Sharik! Response code is {}".format(
                             create_user3_response.status_code))

        # auth
        token_response3 = self.app.post('{base_path}/user/token'.format(base_path=get_settings('API_BASE_PATH')),
                                        headers={"Content-Type": "application/json"}, data=auth_user3_payload)
        user3_token_payload = json.dumps({
            "token": token_response3.json['token']
        })

        # connect user3 to room
        connect_to_room3_response = self.app.post(
            '{base_path}/room/{room_id}/connect'.format(base_path=get_settings('API_BASE_PATH'),
                                                        room_id=create_room_response.json['roomId']),
            headers={"Content-Type": "application/json"}, data=user3_token_payload)

        self.assertEqual(200, connect_to_room3_response.status_code,
                         msg="Failed to connect Sharik to room! Response code is {}".format(
                             connect_to_room3_response.status_code))

        # start by non-host (not allowed)
        start_by_non_host_response = self.app.post('{base_path}/game/start'.format(base_path=get_settings('API_BASE_PATH')),
                                             headers={"Content-Type": "application/json"}, data=user2_token_payload)

        self.assertEqual(403, start_by_non_host_response.status_code,
                         msg="Bad response code when starting game with insufficient players! Response code is {}".format(
                             start_by_non_host_response.status_code))

        # define positions before starting game
        define_pos_b4_start_response = self.app.post(
            '{base_path}/game/<game_id>/positions'.format(base_path=get_settings('API_BASE_PATH')),
            headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(400, define_pos_b4_start_response.status_code,
                         msg="Bad response code when defining positions before game start! Response code is {}".format(
                             define_pos_b4_start_response.status_code))

        # successful game start
        successful_start_response = self.app.post('{base_path}/game/start'.format(base_path=get_settings('API_BASE_PATH')),
                                             headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(200, successful_start_response.status_code,
                         msg="Failed to start game by host! Response code is {}".format(
                             successful_start_response.status_code))
        self.assertEqual('active', successful_start_response.json['status'], msg="Invalid game status ({}) after starting".format(successful_start_response.json['status']))
        self.assertEqual(3, len(successful_start_response.json['players']), msg="Incorrect game players list after starting")
        self.assertIsNotNone(successful_start_response.json['gameId'], msg="No game id in response after starting")
        game_id = successful_start_response.json['gameId']

        # starting game when one is already started
        repeat_start_response = self.app.post('{base_path}/game/start'.format(base_path=get_settings('API_BASE_PATH')),
                                             headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(403, repeat_start_response.status_code,
                         msg="Bad response code when starting second game in a row! Response code is {}".format(
                             repeat_start_response.status_code))

        # define positions by non-host (not allowed)
        define_pos_by_nonhost_response = self.app.post('{base_path}/game/{game_id}/positions'.format(base_path=get_settings('API_BASE_PATH'), game_id=game_id),
                                             headers={"Content-Type": "application/json"}, data=user3_token_payload)

        self.assertEqual(403, define_pos_by_nonhost_response.status_code, msg="Bad response code ({}) when defining positions by non host!".format(define_pos_by_nonhost_response.status_code))

        # define positions by host
        define_pos_by_host_response = self.app.post('{base_path}/game/{game_id}/positions'.format(base_path=get_settings('API_BASE_PATH'), game_id=game_id),
                                             headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(200, define_pos_by_host_response.status_code, msg="Failed to define positions! Response code is {}".format(define_pos_by_host_response.status_code))
        self.assertEqual(
            len(successful_start_response.json['players']), len(define_pos_by_host_response.json['players']),
            msg="Players count after defining positions ({}) differs with game players count!".format(len(define_pos_by_host_response.json['players']))
        )

        # repeat define positions
        repeat_define_pos_response = self.app.post(
            '{base_path}/game/{game_id}/positions'.format(base_path=get_settings('API_BASE_PATH'), game_id=game_id),
            headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(403, repeat_define_pos_response.status_code,
                         msg="Bad response code when repeating defining positions! Response code is {}".format(
                             repeat_define_pos_response.status_code))
        self.assertEqual(
            len(successful_start_response.json['players']), len(define_pos_by_host_response.json['players']),
            msg="Players count after defining positions ({}) differs with game players count!".format(
                len(define_pos_by_host_response.json['players']))
        )

        # game status
        game_status_response = self.app.get('{base_path}/game/{game_id}'.format(
                base_path=get_settings('API_BASE_PATH'),
                game_id=game_id
            ), headers={"Content-Type": "application/json"})

        self.assertEqual(200, game_status_response.status_code, msg="Failed to get game status! Response code is {}".format(game_status_response.status_code))
        self.assertIsNone(game_status_response.json['currentHandId'],
                          msg="Invalid field 'currentHandId' in game status after defining positions!")
        self.assertIsNone(game_status_response.json['currentHandSerialNo'],
                          msg="Invalid field 'currentHandSerialNo' in game status after defining positions!")
        self.assertIsNone(game_status_response.json['finished'],
                          msg="Invalid field 'finished' in game status after defining positions!")
        self.assertEqual(game_id, game_status_response.json['gameId'],
                          msg="Invalid field 'gameId' in game status after defining positions!")
        self.assertEqual(len(successful_start_response.json['players']), len(game_status_response.json['players']),
                          msg="Invalid field 'players' in game status after defining positions!")
        self.assertEqual(create_room_response.json['roomId'], game_status_response.json['roomId'],
                          msg="Invalid field 'roomId' in game status after defining positions!")
        self.assertIsNotNone(game_status_response.json['started'],
                          msg="Invalid field 'started' in game status after defining positions!")
        self.assertEqual('open', game_status_response.json['status'],
                          msg="Invalid field 'status' in game status after defining positions!")
        self.assertEqual(0, game_status_response.json['playedHandsCount'],
                          msg="Invalid field 'playedHandsCount' in game status after defining positions!")


        # finish by non-host (not allowed)
        finish_by_non_host_response = self.app.post('{base_path}/game/finish'.format(base_path=get_settings('API_BASE_PATH')),
                                             headers={"Content-Type": "application/json"}, data=user2_token_payload)

        self.assertEqual(403, finish_by_non_host_response.status_code,
                         msg="Bad response code when finishing game with insufficient players! Response code is {}".format(
                             finish_by_non_host_response.status_code))

        # successful game finish
        successful_finish_response = self.app.post('{base_path}/game/finish'.format(base_path=get_settings('API_BASE_PATH')),
                                             headers={"Content-Type": "application/json"}, data=host_token_payload)
        self.assertEqual('finished', successful_finish_response.json['status'], msg="Invalid game status ({}) after finishing".format(successful_finish_response.json['status']))

        self.assertEqual(200, successful_finish_response.status_code,
                         msg="Failed to finish game by host! Response code is {}".format(
                             successful_finish_response.status_code))

        # finishing game when one is already finished
        repeat_finish_response = self.app.post('{base_path}/game/finish'.format(base_path=get_settings('API_BASE_PATH')),
                                             headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(403, repeat_finish_response.status_code,
                         msg="Bad response code when finishing second game in a row! Response code is {}".format(
                             repeat_finish_response.status_code))

        # game status
        game_status_response = self.app.get('{base_path}/game/{game_id}'.format(
                base_path=get_settings('API_BASE_PATH'),
                game_id=game_id
            ), headers={"Content-Type": "application/json"})

        self.assertEqual(200, game_status_response.status_code, msg="Failed to get game status! Response code is {}".format(game_status_response.status_code))
        self.assertIsNone(game_status_response.json['currentHandId'],
                          msg="Invalid field 'currentHandId' in game status after defining positions!")
        self.assertIsNone(game_status_response.json['currentHandSerialNo'],
                          msg="Invalid field 'currentHandSerialNo' in game status after defining positions!")
        self.assertIsNotNone(game_status_response.json['finished'],
                          msg="Invalid field 'finished' in game status after defining positions!")
        self.assertEqual(game_id, game_status_response.json['gameId'],
                          msg="Invalid field 'gameId' in game status after defining positions!")
        self.assertEqual(len(successful_start_response.json['players']), len(game_status_response.json['players']),
                          msg="Invalid field 'players' in game status after defining positions!")
        self.assertEqual(create_room_response.json['roomId'], game_status_response.json['roomId'],
                          msg="Invalid field 'roomId' in game status after defining positions!")
        self.assertIsNotNone(game_status_response.json['started'],
                          msg="Invalid field 'started' in game status after defining positions!")
        self.assertEqual('finished', game_status_response.json['status'],
                          msg="Invalid field 'status' in game status after defining positions!")
        self.assertEqual(0, game_status_response.json['playedHandsCount'],
                          msg="Invalid field 'playedHandsCount' in game status after defining positions!")


if __name__ == '__main__':
    unittest.main(verbosity=2)
