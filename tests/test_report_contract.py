import unittest
from click_once.reporting import group_name,summarize_groups
class ReportContract(unittest.TestCase):
    def test_training_seed_not_hidden_in_aggregate(self):
        rows=[dict(policy=f'q_strict_memory_{s}',strict_success=v,duplicate=0,proxy_exploit=0,steps=3) for s,v in [(11,1),(22,1),(33,0)]]
        groups=summarize_groups(rows)
        self.assertAlmostEqual(groups['q_strict_memory']['success_mean'],2/3)
        self.assertEqual(groups['q_strict_memory']['seed_success'],{'11':1,'22':1,'33':0})
    def test_baseline_label_is_preserved(self):
        self.assertEqual(group_name('verify'),'verify')
        self.assertEqual(group_name('q_strict_memoryless_33'),'q_strict_memoryless')
