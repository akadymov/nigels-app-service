import unittest
from app import app
from tests.base_case import BaseCase
import json
from config import get_settings


class RoomMethodsCase(BaseCase):

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

        # auth
        host_token_response = self.app.post('{base_path}/user/token'.format(base_path=get_settings('API_BASE_PATH')),
                                       headers={"Content-Type": "application/json"}, data=host_auth_payload)

        #get open rooms list when no one is created
        no_rooms_list = self.app.get('{base_path}/room/all'.format(base_path=get_settings('API_BASE_PATH')))

        self.assertEqual(0, len(no_rooms_list.json['rooms']), msg="Incorrect number of open rooms ({}) in list when rooms are not created yet!".format(len(no_rooms_list.json['rooms'])))

        # create room
        create_room_payload = json.dumps({
            "token": host_token_response.json['token'],
            "roomName": room_name1
        })
        create_room_response = self.app.post('{base_path}/room'.format(base_path=get_settings('API_BASE_PATH')),
                                    headers={"Content-Type": "application/json"}, data=create_room_payload)

        self.assertEqual(username, create_room_response.json['host'], msg="Room host is invalid!")
        self.assertEqual(room_name1, create_room_response.json["roomName"], msg="Room name is invalid!")
        self.assertEqual("open", create_room_response.json['status'], msg="Room status is invalid!")
        self.assertEqual(1, create_room_response.json['connectedUsers'], msg="Room connected users param is invalid!")
        self.assertIsNotNone(create_room_response.json['roomId'], msg='Room id is invalid!')
        self.assertIsNotNone(create_room_response.json['created'], msg='Room created date is invalid!')

        # get open room status
        closed_room_status_response = self.app.get('{base_path}/room/{room_id}'.format(
            base_path=get_settings('API_BASE_PATH'),
            room_id=create_room_response.json['roomId']
        ), headers={"Content-Type": "application/json"})

        self.assertEqual(200, closed_room_status_response.status_code, msg="Failed to get room status after creating! Response code is {}".format(closed_room_status_response.status_code))
        self.assertEqual(create_room_response.json['roomId'], closed_room_status_response.json['roomId'],
                         msg="Invalid field 'roomId' in room status after creating!")
        self.assertEqual(room_name1, closed_room_status_response.json["roomName"],
                         msg="Invalid field 'roomName' in room status after creating!")
        self.assertEqual(username, closed_room_status_response.json['host'],
                         msg="Invalid field 'host' in room status after creating!")
        self.assertEqual('open', closed_room_status_response.json['status'],
                         msg="Invalid field 'status' in room status after creating!")
        self.assertIsNotNone(closed_room_status_response.json['created'],
                         msg="Invalid field 'created' in room status after creating!")
        self.assertIsNone(closed_room_status_response.json['closed'],
                         msg="Invalid field 'closed' in room status after creating!")
        self.assertEqual(1, len(closed_room_status_response.json['connectedUserList']),
                         msg="Invalid field 'connectedUserList' in room status after creating!")
        self.assertIsNotNone(closed_room_status_response.json['connect'],
                         msg="Invalid field 'connect' in room status after creating!")
        self.assertEqual(0, len(closed_room_status_response.json['games']),
                         msg="Invalid field 'games' in room status after creating!")

        # create another room before closing previous (not allowed)
        repeat_create_room_response = self.app.post('{base_path}/room'.format(base_path=get_settings('API_BASE_PATH')),
                                    headers={"Content-Type": "application/json"}, data=create_room_payload)

        self.assertEqual(403, repeat_create_room_response.status_code, msg='Bad response code ({}) when creating room having open one!'.format(repeat_create_room_response.status_code))

        # connecting to hosted room (not allowed)
        connect_to_hosted_room_response = self.app.post('{base_path}/room/{room_id}/connect'.format(base_path=get_settings('API_BASE_PATH'), room_id=create_room_response.json['roomId']),
                                       headers={"Content-Type": "application/json"}, data=host_auth_payload)

        self.assertEqual(401, connect_to_hosted_room_response.status_code, msg="Bad response code ({}) when connecting to hosted room!".format(connect_to_hosted_room_response.status_code))

        # create pseudo host
        pseudo_host_username = "matroskin_twin"
        pseudo_host_email = "twin@hack.org"
        pseudo_room_name = "Prostokvashino_fishing"
        pseudo_host_create_payload = json.dumps({
            "email": pseudo_host_email,
            "username": pseudo_host_username,
            "password": password,
            "repeatPassword": password
        })
        pseudo_host_auth_payload = json.dumps({
            "username": pseudo_host_username,
            "password": password
        })

        pseudo_host_create_response = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                 headers={"Content-Type": "application/json"}, data=pseudo_host_create_payload)

        self.assertEqual(201, pseudo_host_create_response.status_code, msg="Failed to create pseudo host user! Response code is {}".format(create_host_response.status_code))

        # pseudo host auth
        pseudo_host_token_response = self.app.post('{base_path}/user/token'.format(base_path=get_settings('API_BASE_PATH')),
                                       headers={"Content-Type": "application/json"}, data=pseudo_host_auth_payload)

        # create pseudo room
        create_pseudo_room_payload = json.dumps({
            "token": pseudo_host_token_response.json['token'],
            "roomName": pseudo_room_name
        })
        create_pseudo_room_response = self.app.post('{base_path}/room'.format(base_path=get_settings('API_BASE_PATH')),
                                    headers={"Content-Type": "application/json"}, data=create_pseudo_room_payload)

        self.assertEqual(201, create_pseudo_room_response.status_code, msg="Failed to create pseudo room! Response code is {}".format(create_pseudo_room_response.status_code))

        # connect to room being a host of open room (not allowed)
        connect_to_hosted_room_response = self.app.post('{base_path}/room/{room_id}/connect'.format(base_path=get_settings('API_BASE_PATH'), room_id=create_pseudo_room_response.json['roomId']),
                                       headers={"Content-Type": "application/json"}, data=host_auth_payload)

        self.assertEqual(401, connect_to_hosted_room_response.status_code, msg="Bad response code ({}) when connecting to room having open hosted one!".format(connect_to_hosted_room_response.status_code))


        # close room
        host_token_payload = json.dumps({
            "token": host_token_response.json['token']
        })
        close_room_response = self.app.post('{base_path}/room/{room_id}/close'.format(base_path=get_settings('API_BASE_PATH'),
                                        room_id=create_room_response.json['roomId']), headers={"Content-Type": "application/json"},
                                        data=host_token_payload)

        self.assertEqual(username, close_room_response.json['host'], msg="Room host is invalid!")
        self.assertEqual(room_name1, close_room_response.json["roomName"], msg="Room name is invalid!")
        self.assertEqual("closed", close_room_response.json['status'], msg="Room status is invalid!")
        self.assertIsNotNone(close_room_response.json['closed'], msg='Room closed date is invalid!')
        self.assertIsNotNone(create_room_response.json['roomId'], msg='Room id is invalid!')

        # get closed room status
        closed_room_status_response = self.app.get('{base_path}/room/{room_id}'.format(
            base_path=get_settings('API_BASE_PATH'),
            room_id=create_room_response.json['roomId']
        ), headers={"Content-Type": "application/json"})

        self.assertEqual(200, closed_room_status_response.status_code, msg="Failed to get room status after closing! Response code is {}".format(closed_room_status_response.status_code))
        self.assertEqual(create_room_response.json['roomId'], closed_room_status_response.json['roomId'],
                         msg="Invalid field 'roomId' in room status after closing!")
        self.assertEqual(room_name1, closed_room_status_response.json["roomName"],
                         msg="Invalid field 'roomName' in room status after closing!")
        self.assertEqual(username, closed_room_status_response.json['host'],
                         msg="Invalid field 'host' in room status after closing!")
        self.assertEqual('closed', closed_room_status_response.json['status'],
                         msg="Invalid field 'status' in room status after closing!")
        self.assertIsNotNone(closed_room_status_response.json['created'],
                         msg="Invalid field 'created' in room status after closing!")
        self.assertIsNotNone(closed_room_status_response.json['closed'],
                         msg="Invalid field 'closed' in room status after closing!")
        self.assertIsNotNone(closed_room_status_response.json['connect'],
                         msg="Invalid field 'connect' in room status after closing!")
        self.assertEqual(0, len(closed_room_status_response.json['games']),
                         msg="Invalid field 'games' in room status after closing!")

        # create another room
        host_token_payload = json.dumps({
            "token": host_token_response.json['token'],
            "roomName": room_name2
        })
        create_another_room_response = self.app.post('{base_path}/room'.format(base_path=get_settings('API_BASE_PATH')),
                                    headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(201, create_another_room_response.status_code, msg="Failed to create second room! Response code is {}".format(create_another_room_response.status_code))

        #get open rooms list
        open_rooms_response = self.app.get('{base_path}/room/all'.format(base_path=get_settings('API_BASE_PATH')))

        self.assertEqual(2, len(open_rooms_response.json['rooms']), msg="Incorrect number of open rooms ({}) in list!".format(len(open_rooms_response.json['rooms'])))
        self.assertEqual(room_name2, open_rooms_response.json['rooms'][1]["roomName"], msg="Bad open room name ({})!".format(open_rooms_response.json['rooms'][0]["roomName"]))

        #get all rooms list
        all_rooms_response = self.app.get('{base_path}/room/all?closed=Y'.format(base_path=get_settings('API_BASE_PATH')))

        self.assertEqual(3, len(all_rooms_response.json['rooms']), msg="Incorrect number of rooms ({}) in list!".format(len(all_rooms_response.json['rooms'])))

        # create another user
        email2 = "Fedor@prostokvashino.ussr"
        username2 = "dyadya_fedor"
        create_user2_payload = json.dumps({
            "email": email2,
            "username": username2,
            "password": password,
            "repeatPassword": password
        })
        auth_user2_payload = json.dumps({
            "username": username2,
            "password": password
        })

        create_user2_response = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                 headers={"Content-Type": "application/json"}, data=create_user2_payload)

        self.assertEqual(201, create_user2_response.status_code,
                         msg="Failed to create host user! Response code is {}".format(create_user2_response.status_code))

        # auth
        token_response2 = self.app.post('{base_path}/user/token'.format(base_path=get_settings('API_BASE_PATH')),
                                       headers={"Content-Type": "application/json"}, data=auth_user2_payload)
        user2_token_payload = json.dumps({
            "token": token_response2.json['token']
        })

        # connect to room
        connect_to_room2_response = self.app.post('{base_path}/room/{room_id}/connect'.format(base_path=get_settings('API_BASE_PATH'), room_id=create_another_room_response.json['roomId']),
                                       headers={"Content-Type": "application/json"}, data=user2_token_payload)

        self.assertEqual(200, connect_to_room2_response.status_code, msg="Failed to connect dyadya Fedor to room! Response code is {}".format(connect_to_room2_response.status_code))

        # connect to second room (not allowed)
        connect_to_second_room_response = self.app.post('{base_path}/room/{room_id}/connect'.format(base_path=get_settings('API_BASE_PATH'), room_id=create_pseudo_room_response.json['roomId']),
                                       headers={"Content-Type": "application/json"}, data=user2_token_payload)

        self.assertEqual(403, connect_to_second_room_response.status_code, msg="Bad response code ({}) when connecting to second room!".format(connect_to_second_room_response.status_code))

        # check room status
        # TODO (get-one-room-method is not ready)

        # close another player's room
        close_room_response2 = self.app.post('{base_path}/room/{room_id}/close'.format(base_path=get_settings('API_BASE_PATH'),
                                        room_id=create_another_room_response.json['roomId']), headers={"Content-Type": "application/json"},
                                        data=user2_token_payload)

        self.assertEqual(403, close_room_response2.status_code, msg="Invalid response code while closing another player's room ({})!".format(close_room_response2.status_code))

        # disconnect from room
        disconnect_from_room2_response = self.app.post('{base_path}/room/{room_id}/disconnect'.format(base_path=get_settings('API_BASE_PATH'), room_id=create_another_room_response.json['roomId']),
                                       headers={"Content-Type": "application/json"}, data=user2_token_payload)

        self.assertEqual(200, disconnect_from_room2_response.status_code, msg="Failed to disconnect from room! Response code is {}".format(disconnect_from_room2_response.status_code))

        # repeat disconnect from room (allowed)
        repeat_disconnect_from_room2_response = self.app.post('{base_path}/room/{room_id}/disconnect'.format(base_path=get_settings('API_BASE_PATH'), room_id=create_another_room_response.json['roomId']),
                                       headers={"Content-Type": "application/json"}, data=user2_token_payload)

        self.assertEqual(200, repeat_disconnect_from_room2_response.status_code, msg="Failed to repeat disconnect from room! Response code is {}".format(repeat_disconnect_from_room2_response.status_code))
        
        # create more users
        email3 = "pechkin@prostokvashino.ussr"
        username3 = "pechkin"
        email4 = "sharik@prostokvashino.ussr"
        username4 = "sharik"
        create_user3_payload = json.dumps({
            "email": email3,
            "username": username3,
            "password": password,
            "repeatPassword": password
        })
        auth_user3_payload = json.dumps({
            "username": username3,
            "password": password
        })
        create_user4_payload = json.dumps({
            "email": email4,
            "username": username4,
            "password": password,
            "repeatPassword": password
        })
        auth_user4_payload = json.dumps({
            "username": username4,
            "password": password
        })

        create_user3_response = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                 headers={"Content-Type": "application/json"}, data=create_user3_payload)

        self.assertEqual(201, create_user3_response.status_code,
                         msg="Failed to create user Pechkin! Response code is {}".format(create_user3_response.status_code))

        # auth
        token_response3 = self.app.post('{base_path}/user/token'.format(base_path=get_settings('API_BASE_PATH')),
                                       headers={"Content-Type": "application/json"}, data=auth_user3_payload)
        user3_token_payload = json.dumps({
            "token": token_response3.json['token']
        })

        # connect to room
        connect_to_room2_response = self.app.post('{base_path}/room/{room_id}/connect'.format(base_path=get_settings('API_BASE_PATH'), room_id=create_another_room_response.json['roomId']),
                                       headers={"Content-Type": "application/json"}, data=user3_token_payload)

        self.assertEqual(200, connect_to_room2_response.status_code, msg="Failed to connect Pechkin to room! Response code is {}".format(connect_to_room2_response.status_code))

        create_user4_response = self.app.post('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')),
                                 headers={"Content-Type": "application/json"}, data=create_user4_payload)

        self.assertEqual(201, create_user4_response.status_code,
                         msg="Failed to create user Sharik! Response code is {}".format(create_user4_response.status_code))

        # auth
        token_response4 = self.app.post('{base_path}/user/token'.format(base_path=get_settings('API_BASE_PATH')),
                                       headers={"Content-Type": "application/json"}, data=auth_user4_payload)
        user4_token_payload = json.dumps({
            "token": token_response4.json['token']
        })

        # connect to room
        connect_to_room3_response = self.app.post('{base_path}/room/{room_id}/connect'.format(base_path=get_settings('API_BASE_PATH'), room_id=create_another_room_response.json['roomId']),
                                       headers={"Content-Type": "application/json"}, data=user4_token_payload)

        self.assertEqual(200, connect_to_room3_response.status_code, msg="Failed to connect Sharik to room! Response code is {}".format(connect_to_room3_response.status_code))

        # get connected room status
        closed_room_status_response = self.app.get('{base_path}/room/{room_id}'.format(
            base_path=get_settings('API_BASE_PATH'),
            room_id=create_another_room_response.json['roomId']
        ), headers={"Content-Type": "application/json"})

        self.assertEqual(200, closed_room_status_response.status_code, msg="Failed to get room status after connecting users! Response code is {}".format(closed_room_status_response.status_code))
        self.assertEqual(create_another_room_response.json['roomId'], closed_room_status_response.json['roomId'],
                         msg="Invalid field 'roomId' in room status after connecting users!")
        self.assertEqual(room_name2, closed_room_status_response.json["roomName"],
                         msg="Invalid field 'roomName' in room status after connecting users!")
        self.assertEqual(username, closed_room_status_response.json['host'],
                         msg="Invalid field 'host' in room status after connecting users!")
        self.assertEqual('open', closed_room_status_response.json['status'],
                         msg="Invalid field 'status' in room status after connecting users!")
        self.assertIsNotNone(closed_room_status_response.json['created'],
                         msg="Invalid field 'created' in room status after connecting users!")
        self.assertIsNone(closed_room_status_response.json['closed'],
                         msg="Invalid field 'closed' in room status after connecting users!")
        self.assertEqual(3, len(closed_room_status_response.json['connectedUserList']),
                         msg="Invalid field 'connectedUserList' in room status after connecting users!")
        self.assertIsNotNone(closed_room_status_response.json['connect'],
                         msg="Invalid field 'connect' in room status after connecting users!")
        self.assertEqual(0, len(closed_room_status_response.json['games']),
                         msg="Invalid field 'games' in room status after connecting users!")

        # disconnect from room by host
        disconnect_host_from_room2_response = self.app.post('{base_path}/room/{room_id}/disconnect'.format(base_path=get_settings('API_BASE_PATH'), room_id=create_another_room_response.json['roomId']),
                                       headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(403, disconnect_host_from_room2_response.status_code, msg="Bad response code when disconnecting host from room! Response code is {}".format(disconnect_host_from_room2_response.status_code))

        # disconnect from closed room
        close_room2_response = self.app.post('{base_path}/room/{room_id}/close'.format(base_path=get_settings('API_BASE_PATH'),
                                        room_id=create_another_room_response.json['roomId']), headers={"Content-Type": "application/json"},
                                        data=host_token_payload)

        self.assertEqual(201, close_room2_response.status_code, msg="Failed to close second room! Response code is {}".format(close_room2_response.status_code))

        disconnect_from_closed_room_response = self.app.post('{base_path}/room/{room_id}/disconnect'.format(base_path=get_settings('API_BASE_PATH'), room_id=create_another_room_response.json['roomId']),
                                       headers={"Content-Type": "application/json"}, data=user2_token_payload)

        self.assertEqual(400, disconnect_from_closed_room_response.status_code, msg="Bad response code when disconnecting from closed room! Response code is {}".format(disconnect_from_closed_room_response.status_code))

        # close already closed room
        close_already_closed_response = self.app.post('{base_path}/room/{room_id}/close'.format(base_path=get_settings('API_BASE_PATH'),
                                        room_id=create_another_room_response.json['roomId']), headers={"Content-Type": "application/json"},
                                        data=host_token_payload)

        self.assertEqual(400, close_already_closed_response.status_code, msg="Bad response code when closing already closed room! Response code is {}".format(close_room2_response.status_code))


    if __name__ == '__main__':
        unittest.main(verbosity=2)
