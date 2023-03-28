import unittest
from app import app
from tests.base_case import BaseCase
from config import get_settings


class GeneralMethodsCase(BaseCase):

    def test_rules(self):
        rules_response = self.app.get('{base_path}/rules'.format(base_path=get_settings('API_BASE_PATH')),
                                             headers={"Content-Type": "application/json"})

        self.assertEqual(200, rules_response.status_code,
                         msg="Failed to get game rules! Response code is {}".format(rules_response.status_code))
        self.assertIsNotNone(rules_response.json['rules'], msg="Rules field is empty in response!")

    def test_info(self):
        info_response = self.app.get('{base_path}/info'.format(base_path=get_settings('API_BASE_PATH')),
                                             headers={"Content-Type": "application/json"})

        self.assertEqual(200, info_response.status_code,
                         msg="Failed to get game info! Response code is {}".format(info_response.status_code))
        self.assertIsNotNone(info_response.json['info'], msg="Info field is empty in response!")


if __name__ == '__main__':
    unittest.main(verbosity=2)
