import unittest
from app import app
from tests.base_case import BaseCase
import json


class HandTurnMethodsCase(BaseCase):

    def test_hands(self):  # Given
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

        self.assertEqual(201, create_host_response.status_code,
                         msg="Failed to create host user! Response code is {}".format(create_host_response.status_code))

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

        self.assertEqual(201, create_room_response.status_code,
                         msg="Failed to create room ({})!".format(create_room_response.status_code))

        # create more users
        email3 = "pechkin@prostokvashino.ussr"
        username2 = "pechkin"
        email4 = "sharik@prostokvashino.ussr"
        username3 = "sharik"
        create_user2_payload = json.dumps({
            "email": email3,
            "username": username2,
            "password": password
        })
        auth_user2_payload = json.dumps({
            "username": username2,
            "password": password
        })
        create_user3_payload = json.dumps({
            "email": email4,
            "username": username3,
            "password": password
        })
        auth_user3_payload = json.dumps({
            "username": username3,
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

        # successful game start
        successful_start_response = self.app.post(
            '{base_path}/game/start'.format(base_path=app.config['API_BASE_PATH']),
            headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(200, successful_start_response.status_code,
                         msg="Failed to start game by host! Response code is {}".format(
                             successful_start_response.status_code))
        self.assertIsNotNone(successful_start_response.json['game_id'], msg="No game id in response after starting")
        game_id = successful_start_response.json['game_id']

        # define positions
        define_pos_by_host_response = self.app.post(
            '{base_path}/game/{game_id}/positions'.format(base_path=app.config['API_BASE_PATH'], game_id=game_id),
            headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(200, define_pos_by_host_response.status_code,
                         msg="Failed to define positions! Response code is {}".format(
                             define_pos_by_host_response.status_code))

        # deal cards by non host
        deal_by_non_host_response = self.app.post('{base_path}/game/{game_id}/hand/deal'.format(
            base_path=app.config['API_BASE_PATH'], game_id=game_id),
            headers={"Content-Type": "application/json"}, data=user2_token_payload)

        self.assertEqual(403, deal_by_non_host_response.status_code,
                         msg="Bad response code when dealing by nonhost! Response code is {}".format(
                             deal_by_non_host_response.status_code))

        # deal cards by host
        deal_by_host_response = self.app.post('{base_path}/game/{game_id}/hand/deal'.format(
            base_path=app.config['API_BASE_PATH'], game_id=game_id),
            headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(200, deal_by_host_response.status_code,
                         msg="Failed to deal cards! Response code is {}".format(
                             deal_by_host_response.status_code))
        self.assertIsNotNone(deal_by_host_response.json['dealt_cards_per_player'],
                             msg="Failed to get number of dealt cards")
        self.assertEqual(game_id, deal_by_host_response.json['game_id'],
                         msg="Bad game id ({}) in deal cards response!".format(deal_by_host_response.json['game_id']))
        self.assertIsNotNone(deal_by_host_response.json['hand_id'], msg="No hand id in deal cards response!")
        hand_id = deal_by_host_response.json['hand_id']
        self.assertEqual(define_pos_by_host_response.json['players'][0]['username'],
                         deal_by_host_response.json['starting_player'],
                         msg="Starting player after dealing ({}) differs with defined first player in game!".format(
                             deal_by_host_response.json['starting_player']))
        self.assertEqual('d', deal_by_host_response.json['trump'],
                         msg="First hand trump is not diamonds ({})!".format(deal_by_host_response.json['trump']))

        # deal when already dealt and hand is not finished (not allowed)
        repeat_deal_by_host_response = self.app.post('{base_path}/game/{game_id}/hand/deal'.format(
            base_path=app.config['API_BASE_PATH'], game_id=game_id),
            headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(403, repeat_deal_by_host_response.status_code,
                         msg="Bad response code when repeating dealing cards before hand is finished! Response code is {}".format(
                             repeat_deal_by_host_response.status_code))

        # get cards on hand
        cards_on__host_hand_response = self.app.post(
            '{base_path}/game/{game_id}/hand/{hand_id}/get'.format(base_path=app.config['API_BASE_PATH'],
                                                                   game_id=game_id, hand_id=hand_id),
            headers={"Content-Type": "application/json"}, data=host_token_payload)

        self.assertEqual(200, cards_on__host_hand_response.status_code,
                         msg="Failed to get cards on hand for host! Response code is {}".format(
                             cards_on__host_hand_response.status_code))
        self.assertEqual(deal_by_host_response.json['dealt_cards_per_player'],
                         len(cards_on__host_hand_response.json['cards_in_hand']),
                         msg="Dealt cards number ({}) is invalid".format(
                             len(cards_on__host_hand_response.json['cards_in_hand'])))

        # get leaderboard before putting cards
        leaderboard_response = self.app.get(
            '{base_path}/game/{game_id}/score'.format(base_path=app.config['API_BASE_PATH'],
                                                      game_id=game_id), headers={"Content-Type": "application/json"})

        self.assertEqual(200, leaderboard_response.status_code,
                         msg="Failed to get leaderboard! Response code is {}".format(leaderboard_response.status_code))

        # making bet not being first player
        betting_player_token_payload = host_token_payload
        if define_pos_by_host_response.json['players'][0]['username'] == username:
            betting_player_token_payload = user2_token_payload

        betting_player_token_payload = json.loads(betting_player_token_payload)
        betting_player_token_payload['bet_size'] = 1
        betting_player_token_payload = json.dumps(betting_player_token_payload)

        bet_out_of_bad_position_response = self.app.post('{base_path}/game/{game_id}/hand/{hand_id}/turn/bet'.format(
            base_path=app.config['API_BASE_PATH'], game_id=game_id, hand_id=hand_id),
            headers={"Content-Type": "application/json"}, data=betting_player_token_payload)

        self.assertEqual(403, bet_out_of_bad_position_response.status_code,
                         msg="Bad response code ({}) when making bet out of bad position!".format(
                             bet_out_of_bad_position_response.status_code))

        # make correct bet
        betting_player_token_payload = host_token_payload
        if define_pos_by_host_response.json['players'][0]['username'] == username2:
            betting_player_token_payload = user2_token_payload
        elif define_pos_by_host_response.json['players'][0]['username'] == username3:
            betting_player_token_payload = user3_token_payload

        cards_on_first_player_hand_response = self.app.post(
            '{base_path}/game/{game_id}/hand/{hand_id}/get'.format(base_path=app.config['API_BASE_PATH'],
                                                                   game_id=game_id, hand_id=hand_id),
            headers={"Content-Type": "application/json"}, data=betting_player_token_payload)
        cards_on_first_player_hand = cards_on_first_player_hand_response.json['cards_in_hand']

        betting_player_token_payload = json.loads(betting_player_token_payload)
        betting_player_token_payload['bet_size'] = 1
        betting_player_token_payload = json.dumps(betting_player_token_payload)

        make_bet_response = self.app.post('{base_path}/game/{game_id}/hand/{hand_id}/turn/bet'.format(
            base_path=app.config['API_BASE_PATH'], game_id=game_id, hand_id=hand_id),
            headers={"Content-Type": "application/json"}, data=betting_player_token_payload)

        self.assertEqual(200, make_bet_response.status_code,
                         msg="Failed to make bet! Response code is {}".format(make_bet_response.status_code))

        # put first card before making all bets
        put_card_b4_bets_response = self.app.post(
            '{base_path}/game/{game_id}/hand/{hand_id}/turn/card/put/{card_id}'.format(
                base_path=app.config['API_BASE_PATH'], game_id=game_id, hand_id=hand_id,
                card_id=cards_on_first_player_hand[0]),
            headers={"Content-Type": "application/json"}, data=betting_player_token_payload)

        self.assertEqual(403, put_card_b4_bets_response.status_code,
                         "Bad response code ({}) when putting card before all bets are made!".format(
                             put_card_b4_bets_response.status_code
                         ))

        # repeat bet
        repeat_bet_response = self.app.post('{base_path}/game/{game_id}/hand/{hand_id}/turn/bet'.format(
            base_path=app.config['API_BASE_PATH'], game_id=game_id, hand_id=hand_id),
            headers={"Content-Type": "application/json"}, data=betting_player_token_payload)

        self.assertEqual(403, repeat_bet_response.status_code,
                         msg="Bad response code ({}) when repeating bet!".format(repeat_bet_response.status_code))

        # checking "someone should stay unhappy" rule
        second_betting_player_token_payload = host_token_payload
        if define_pos_by_host_response.json['players'][1]['username'] == username2:
            second_betting_player_token_payload = user2_token_payload
        elif define_pos_by_host_response.json['players'][1]['username'] == username3:
            second_betting_player_token_payload = user3_token_payload

        cards_on_second_player_hand_response = self.app.post(
            '{base_path}/game/{game_id}/hand/{hand_id}/get'.format(base_path=app.config['API_BASE_PATH'],
                                                                   game_id=game_id, hand_id=hand_id),
            headers={"Content-Type": "application/json"}, data=second_betting_player_token_payload)
        cards_on_second_player_hand = cards_on_second_player_hand_response.json['cards_in_hand']

        second_betting_player_token_payload = json.loads(second_betting_player_token_payload)
        second_betting_player_token_payload['bet_size'] = 1
        second_betting_player_token_payload = json.dumps(second_betting_player_token_payload)

        make_second_bet_response = self.app.post('{base_path}/game/{game_id}/hand/{hand_id}/turn/bet'.format(
            base_path=app.config['API_BASE_PATH'], game_id=game_id, hand_id=hand_id),
            headers={"Content-Type": "application/json"}, data=second_betting_player_token_payload)

        self.assertEqual(200, make_second_bet_response.status_code,
                         msg="Failed to make second bet! Response code is {}".format(
                             make_second_bet_response.status_code))

        last_betting_player_token_payload = host_token_payload
        if define_pos_by_host_response.json['players'][2]['username'] == username2:
            last_betting_player_token_payload = user2_token_payload
        elif define_pos_by_host_response.json['players'][2]['username'] == username3:
            last_betting_player_token_payload = user3_token_payload

        cards_on_last_player_hand_response = self.app.post(
            '{base_path}/game/{game_id}/hand/{hand_id}/get'.format(base_path=app.config['API_BASE_PATH'],
                                                                   game_id=game_id, hand_id=hand_id),
            headers={"Content-Type": "application/json"}, data=last_betting_player_token_payload)
        cards_on_last_player_hand = cards_on_last_player_hand_response.json['cards_in_hand']

        last_betting_player_token_payload = json.loads(last_betting_player_token_payload)
        last_betting_player_token_payload['bet_size'] = int(deal_by_host_response.json['dealt_cards_per_player']) - 2
        last_betting_player_token_payload = json.dumps(last_betting_player_token_payload)

        make_last_bet_response = self.app.post('{base_path}/game/{game_id}/hand/{hand_id}/turn/bet'.format(
            base_path=app.config['API_BASE_PATH'], game_id=game_id, hand_id=hand_id),
            headers={"Content-Type": "application/json"}, data=last_betting_player_token_payload)

        self.assertEqual(400, make_last_bet_response.status_code,
                         msg="Bad response code when trying to make invalid bet by last player! Response code is {}".format(
                             make_last_bet_response.status_code))

        last_betting_player_token_payload = json.loads(last_betting_player_token_payload)
        last_betting_player_token_payload['bet_size'] = last_betting_player_token_payload['bet_size'] + 1
        last_betting_player_token_payload = json.dumps(last_betting_player_token_payload)

        make_last_bet_response = self.app.post('{base_path}/game/{game_id}/hand/{hand_id}/turn/bet'.format(
            base_path=app.config['API_BASE_PATH'], game_id=game_id, hand_id=hand_id),
            headers={"Content-Type": "application/json"}, data=last_betting_player_token_payload)

        self.assertEqual(200, make_last_bet_response.status_code,
                         msg="Failed to make last bet! Response code is {}".format(make_last_bet_response.status_code))

        # Put card out of defined position
        put_card_out_of_position_response = self.app.post(
            '{base_path}/game/{game_id}/hand/{hand_id}/turn/card/put/{card_id}'.format(
                base_path=app.config['API_BASE_PATH'], game_id=game_id, hand_id=hand_id,
                card_id=cards_on_second_player_hand[0]),
            headers={"Content-Type": "application/json"}, data=second_betting_player_token_payload)

        self.assertEqual(403, put_card_out_of_position_response.status_code,
                         "Bad response code ({}) when putting card out of defined position!".format(
                             put_card_out_of_position_response.status_code
                         ))

        # Put card that is not on hand
        put_absent_card_response = self.app.post(
            '{base_path}/game/{game_id}/hand/{hand_id}/turn/card/put/{card_id}'.format(
                base_path=app.config['API_BASE_PATH'], game_id=game_id, hand_id=hand_id,
                card_id=cards_on_second_player_hand[0]),
            headers={"Content-Type": "application/json"}, data=betting_player_token_payload)

        self.assertEqual(403, put_absent_card_response.status_code,
                         "Bad response code ({}) when putting absent card!".format(
                             put_absent_card_response.status_code
                         ))

        # Put valid first card
        card_id = cards_on_first_player_hand[0]
        for card in cards_on_first_player_hand:
            if card[1:] != 'd':  # first card is tested out of trump-suit
                card_id = card
                break
        put_first_card_response = self.app.post(
            '{base_path}/game/{game_id}/hand/{hand_id}/turn/card/put/{card_id}'.format(
                base_path=app.config['API_BASE_PATH'], game_id=game_id, hand_id=hand_id, card_id=card_id),
            headers={"Content-Type": "application/json"}, data=betting_player_token_payload)
        first_turn_suit = cards_on_first_player_hand[0][1:]

        self.assertEqual(200, put_first_card_response.status_code,
                         "Failed to put first card! Response code is {}".format(
                             put_first_card_response.status_code
                         ))

        # Put invalid second card
        card_id = cards_on_second_player_hand[0]
        i = 0
        for card in cards_on_second_player_hand:
            if card[1:] != first_turn_suit and card[1:] != 'd':
                card_id = card
                i = i + 1
        if i < len(cards_on_second_player_hand):  # means that player has at least one suited card
            put_invalid_second_card_response = self.app.post(
                '{base_path}/game/{game_id}/hand/{hand_id}/turn/card/put/{card_id}'.format(
                    base_path=app.config['API_BASE_PATH'], game_id=game_id, hand_id=hand_id, card_id=card_id),
                headers={"Content-Type": "application/json"}, data=second_betting_player_token_payload)

            self.assertEqual(403, put_invalid_second_card_response.status_code,
                             "Bad response code ({}) when putting invalid second card ({}) when turn suit is {}!".format(
                                 put_invalid_second_card_response.status_code, card_id, first_turn_suit
                             ))

        # Put valid second card
        card_id = cards_on_second_player_hand[0]
        i = 0
        for card in cards_on_second_player_hand:
            if card[1:] == first_turn_suit and card[1:] != 'd':
                card_id = card
                i = i + 1
        if i > 0:  # means that player has at least one suited card
            put_valid_second_card_response = self.app.post(
                '{base_path}/game/{game_id}/hand/{hand_id}/turn/card/put/{card_id}'.format(
                    base_path=app.config['API_BASE_PATH'], game_id=game_id, hand_id=hand_id, card_id=card_id),
                headers={"Content-Type": "application/json"}, data=second_betting_player_token_payload)

            self.assertEqual(200, put_valid_second_card_response.status_code,
                             "Failed to put second valid card ({}) having '{}' suit in turn! Response code is {}".format(
                                 card_id, first_turn_suit, put_valid_second_card_response.status_code
                             ))


if __name__ == '__main__':
    unittest.main(verbosity=2)