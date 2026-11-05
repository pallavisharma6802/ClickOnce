import unittest
from click_once.perception import validate_prediction,public_from_prediction
class PerceptionContract(unittest.TestCase):
    def test_valid_visible_prediction(self):
        p={'notice':'Timeout','page':'booking','confirmed':0,'pending':0}
        self.assertEqual(validate_prediction(p),p)
    def test_reject_extra_hidden_fields(self):
        with self.assertRaises(ValueError):validate_prediction(dict(notice='Timeout',page='booking',confirmed=0,pending=0,scenario='failed_timeout'))
    def test_reject_wrong_types_and_out_of_range(self):
        for count in (-1,4,'1',True):
            with self.assertRaises(ValueError):validate_prediction(dict(notice='Timeout',page='booking',confirmed=count,pending=0))
    def test_prediction_projection_has_only_public_fields(self):
        p={'notice':'History refreshed','page':'history','confirmed':1,'pending':0}
        obs=public_from_prediction(p)
        self.assertEqual(set(obs),{'goal','page','notice','rows','buttons'})
        self.assertEqual(obs['rows'][0]['status'],'confirmed')
