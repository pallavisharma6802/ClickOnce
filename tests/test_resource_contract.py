import unittest
from click_once.resources import PressureGate
class ResourceContract(unittest.TestCase):
    def test_two_consecutive_critical_samples_stop_work(self):
        g=PressureGate()
        self.assertFalse(g.sample(4));self.assertTrue(g.sample(4))
    def test_normal_sample_resets_counter(self):
        g=PressureGate()
        self.assertFalse(g.sample(4));self.assertFalse(g.sample(2));self.assertFalse(g.sample(4))
