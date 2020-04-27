import unittest
from app import app
from app.models import User
from tests.base_case import BaseCase
import json


class UserMethodsCase(BaseCase):

    def test_rooms(self):
        # Given
        email = "matroskin@prostokvashino.ussr"
        username = "matroskin"
        password = "prettyStrongPassword!"
        room_name1 = "Prostokvashino"
        room_name2 = "dyadya_Fyodor_lounge"
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

        # auth
        token_response = self.app.post('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']),
                                       headers={"Content-Type": "application/json"}, data=host_auth_payload)
        # create room
        create_room1_payload = json.dumps({
            "token": token_response.json['token'],
            "room_name": room_name1
        })
        create_room_response = self.app.post('{base_path}/room'.format(base_path=app.config['API_BASE_PATH']),
                                    headers={"Content-Type": "application/json"}, data=create_room1_payload)

        self.assertEqual(username, create_room_response.json['host'], msg="Room host is invalid!")
        self.assertEqual(room_name1, create_room_response.json['room_name'], msg="Room name is invalid!")
        self.assertEqual("open", create_room_response.json['status'], msg="Room status is invalid!")
        self.assertEqual(1, create_room_response.json['connected_users'], msg="Room connected users param is invalid!")
        self.assertIsNotNone(create_room_response.json['room_id'], msg='Room id is invalid!')
        self.assertIsNotNone(create_room_response.json['created'], msg='Room created date is invalid!')

        # close room
        host_token_payload = json.dumps({
            "token": token_response.json['token']
        })
        close_room_response = self.app.post('{base_path}/room/{room_id}/close'.format(base_path=app.config['API_BASE_PATH'],
                                        room_id=create_room_response.json['room_id']), headers={"Content-Type": "application/json"},
                                        data=host_token_payload)

        self.assertEqual(username, close_room_response.json['host'], msg="Room host is invalid!")
        self.assertEqual(room_name1, close_room_response.json['room_name'], msg="Room name is invalid!")
        self.assertEqual("closed", close_room_response.json['status'], msg="Room status is invalid!")
        self.assertIsNotNone(close_room_response.json['closed'], msg='Room closed date is invalid!')
        self.assertIsNotNone(create_room_response.json['room_id'], msg='Room id is invalid!')

        # create another room
        host_token_payload = json.dumps({
            "token": token_response.json['token'],
            "room_name": room_name2
        })
        create_another_room_response = self.app.post('{base_path}/room'.format(base_path=app.config['API_BASE_PATH']),
                                    headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(201, create_another_room_response.status_code, msg="Failed to create second room! Response code is {}".format(create_another_room_response.status_code))

        #get open rooms list
        open_rooms_response = self.app.get('{base_path}/room/all'.format(base_path=app.config['API_BASE_PATH']))

        self.assertEqual(1, len(open_rooms_response.json['rooms']), msg="Incorrect number of open rooms ({}) in list!".format(len(open_rooms_response.json['rooms'])))
        self.assertEqual(room_name2, open_rooms_response.json['rooms'][0]['room_name'], msg="Bad open room name ({})!".format(open_rooms_response.json['rooms'][0]['room_name']))

        #get all rooms list
        all_rooms_response = self.app.get('{base_path}/room/all?closed=Y'.format(base_path=app.config['API_BASE_PATH']))

        self.assertEqual(2, len(all_rooms_response.json['rooms']), msg="Incorrect number of rooms ({}) in list!".format(len(all_rooms_response.json['rooms'])))

        # create another user
        email2 = "Fedor@prostokvashino.ussr"
        username2 = "dyadya_fedor"
        create_user2_payload = json.dumps({
            "email": email2,
            "username": username2,
            "password": password
        })
        auth_user2_payload = json.dumps({
            "username": username2,
            "password": password
        })

        create_user2_response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                                 headers={"Content-Type": "application/json"}, data=create_user2_payload)

        self.assertEqual(201, create_user2_response.status_code,
                         msg="Failed to create host user! Response code is {}".format(create_user2_response.status_code))

        # auth
        token_response2 = self.app.post('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']),
                                       headers={"Content-Type": "application/json"}, data=auth_user2_payload)
        user2_token_payload = json.dumps({
            "token": token_response2.json['token']
        })

        # connect to room
        connect_to_room2_response = self.app.post('{base_path}/room/{room_id}/connect'.format(base_path=app.config['API_BASE_PATH'], room_id=create_another_room_response.json['room_id']),
                                       headers={"Content-Type": "application/json"}, data=user2_token_payload)

        self.assertEqual(200, connect_to_room2_response.status_code, msg="Failed to connect dyadya Fedor to room! Response code is {}".format(connect_to_room2_response.status_code))

        # check room status
        # TODO (get-one-room-method is not ready)

        # close another player's room
        close_room_response2 = self.app.post('{base_path}/room/{room_id}/close'.format(base_path=app.config['API_BASE_PATH'],
                                        room_id=create_another_room_response.json['room_id']), headers={"Content-Type": "application/json"},
                                        data=user2_token_payload)

        self.assertEqual(403, close_room_response2.status_code, msg="Invalid response code while closing another player's room ({})!".format(close_room_response2.status_code))

        # disconnect from room
        disconnect_from_room2_response = self.app.post('{base_path}/room/{room_id}/disconnect'.format(base_path=app.config['API_BASE_PATH'], room_id=create_another_room_response.json['room_id']),
                                       headers={"Content-Type": "application/json"}, data=user2_token_payload)

        self.assertEqual(200, disconnect_from_room2_response.status_code, msg="Failed to disconnect from room! Response code is {}".format(disconnect_from_room2_response.status_code))
        
        # create more users
        email3 = "pechkin@prostokvashino.ussr"
        username3 = "pechkin"
        email4 = "sharik@prostokvashino.ussr"
        username4 = "sharik"
        create_user3_payload = json.dumps({
            "email": email3,
            "username": username3,
            "password": password
        })
        auth_user3_payload = json.dumps({
            "username": username3,
            "password": password
        })
        create_user4_payload = json.dumps({
            "email": email4,
            "username": username4,
            "password": password
        })
        auth_user4_payload = json.dumps({
            "username": username4,
            "password": password
        })

        create_user3_response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                                 headers={"Content-Type": "application/json"}, data=create_user3_payload)

        self.assertEqual(201, create_user3_response.status_code,
                         msg="Failed to create host user! Response code is {}".format(create_user3_response.status_code))

        # auth
        token_response3 = self.app.post('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']),
                                       headers={"Content-Type": "application/json"}, data=auth_user3_payload)
        user3_token_payload = json.dumps({
            "token": token_response3.json['token']
        })

        # connect to room
        connect_to_room2_response = self.app.post('{base_path}/room/{room_id}/connect'.format(base_path=app.config['API_BASE_PATH'], room_id=create_another_room_response.json['room_id']),
                                       headers={"Content-Type": "application/json"}, data=user3_token_payload)

        self.assertEqual(200, connect_to_room2_response.status_code, msg="Failed to connect Pechkin to room! Response code is {}".format(connect_to_room2_response.status_code))

        create_user4_response = self.app.post('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']),
                                 headers={"Content-Type": "application/json"}, data=create_user4_payload)

        self.assertEqual(201, create_user4_response.status_code,
                         msg="Failed to create host user! Response code is {}".format(create_user4_response.status_code))

        # auth
        token_response4 = self.app.post('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']),
                                       headers={"Content-Type": "application/json"}, data=auth_user4_payload)
        user4_token_payload = json.dumps({
            "token": token_response4.json['token']
        })

        # connect to room
        connect_to_room2_response = self.app.post('{base_path}/room/{room_id}/connect'.format(base_path=app.config['API_BASE_PATH'], room_id=create_another_room_response.json['room_id']),
                                       headers={"Content-Type": "application/json"}, data=user4_token_payload)

        self.assertEqual(200, connect_to_room2_response.status_code, msg="Failed to connect Sharik to room! Response code is {}".format(connect_to_room2_response.status_code))

        # disconnect from room by host
        disconnect_host_from_room2_response = self.app.post('{base_path}/room/{room_id}/disconnect'.format(base_path=app.config['API_BASE_PATH'], room_id=create_another_room_response.json['room_id']),
                                       headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(403, disconnect_host_from_room2_response.status_code, msg="Bad response code when disconnecting host from room! Response code is {}".format(disconnect_host_from_room2_response.status_code))


    if __name__ == '__main__':
        unittest.main(verbosity=2)
