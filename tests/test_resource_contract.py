import unittest
from click_once.resources import PressureGate
class ResourceContract(unittest.TestCase):
    def test_two_consecutive_critical_samples_stop_work(self):
        g=PressureGate()
        self.assertFalse(g.sample(4));self.assertTrue(g.sample(4))
    def test_normal_sample_resets_counter(self):
        g=PressureGate()
        self.assertFalse(g.sample(4));self.assertFalse(g.sample(2));self.assertFalse(g.sample(4))

    def test_pressure_query_timeout_is_unavailable_sample(self):
        from unittest.mock import patch
        import subprocess
        from click_once.resources import pressure
        with patch('click_once.resources.platform.system',return_value='Darwin'), patch('click_once.resources.subprocess.run',side_effect=subprocess.TimeoutExpired('sysctl',3)):
            self.assertEqual(pressure(),-1)
    def test_unavailable_monitor_stops_work(self):
        self.assertTrue(PressureGate().sample(-1))
