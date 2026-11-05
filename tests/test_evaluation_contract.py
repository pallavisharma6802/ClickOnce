import unittest
from copy import deepcopy
from click_once.evaluation import grid,control_key,seed_interval,paired_summary
from click_once.reference import ReferenceWorld,assert_transition
from click_once.challenge import ChallengeEnv,ChallengeRule

class EvaluationContract(unittest.TestCase):
    def test_grid_counts_and_structural_disjointness(self):
        a,b,c=[grid(s) for s in ('domain','composition','timing')]
        self.assertEqual([len(a),len(b),len(c)],[35,45,80])
        sets=[{control_key(x) for x in xs} for xs in (a,b,c)]
        self.assertEqual([len(x) for x in sets],[35,45,80])
        self.assertFalse(sets[0]&sets[1] or sets[1]&sets[2] or sets[0]&sets[2])
    def test_composition_values_seen_individually_but_never_together(self):
        train=grid('domain')
        for case in grid('composition'):
            self.assertIn(case['failures'],{c['failures'] for c in train})
            self.assertIn(case['lag'],{c['lag'] for c in train})
            self.assertFalse(any(c['failures']==case['failures'] and c['lag']==case['lag'] for c in train))
    def test_delay_aliases_not_counted_as_new_nonpending_cases(self):
        a=dict(failures=0,lag=1,pending=False,delay=2)
        b=dict(a,delay=9)
        self.assertEqual(control_key(a),control_key(b))
    def test_reference_interpreter_checks_all_unique_cells(self):
        for split in ('domain','composition','timing'):
            for case in grid(split):
                e=ChallengeEnv(max_steps=40);o,_=e.reset(case['seed'],case)
                oracle=ReferenceWorld(case,o['goal'],40);p=ChallengeRule('fresh')
                self.assertEqual(o,oracle.observe())
                while True:
                    action=p.act(o);actual=e.step(action);expected=oracle.step(action)
                    assert_transition(actual,expected);o=actual[0]
                    if actual[2] or actual[3]:break
                self.assertTrue(oracle.outcome()['strict_success'],case)
    def test_checker_rejects_corrupted_reward(self):
        case=grid('domain')[0];e=ChallengeEnv(max_steps=40);o,_=e.reset(case['seed'],case)
        r=ReferenceWorld(case,o['goal'],40);actual=list(e.step('SUBMIT'));expected=r.step('SUBMIT');actual[1]+=1
        with self.assertRaises(AssertionError):assert_transition(tuple(actual),expected)
    def test_checker_rejects_corrupted_visible_history(self):
        case=grid('domain')[0];e=ChallengeEnv(max_steps=40);o,_=e.reset(case['seed'],case);r=ReferenceWorld(case,o['goal'],40)
        actual=list(e.step('CHECK_HISTORY'));expected=r.step('CHECK_HISTORY');actual[0]=deepcopy(actual[0]);actual[0]['rows']=[]
        with self.assertRaises(AssertionError):assert_transition(tuple(actual),expected)
    def test_bootstrap_zero_variance_is_reported_honestly(self):
        d=seed_interval([.715]*10)
        self.assertAlmostEqual(d['mean'],.715);self.assertAlmostEqual(d['low'],.715);self.assertAlmostEqual(d['high'],.715)
    def test_pairing_not_unpaired_difference(self):
        d=paired_summary([.1,.9],[.2,1.0])
        self.assertEqual(d['wins'],2);self.assertEqual(d['losses'],0)
        self.assertAlmostEqual(d['difference']['mean'],.1)

class MemoryControlContract(unittest.TestCase):
    def test_action_age_does_not_read_freshness_metadata(self):
        from click_once.memory_control import ElapsedLearner
        from click_once.env import ACTIONS
        case=grid('domain')[0];e=ChallengeEnv(max_steps=40);o,_=e.reset(case['seed'],case)
        p=ElapsedLearner();changed=deepcopy(o);changed['history_meta']={'current_tick':999,'last_submit_tick':999,'as_of_tick':-99}
        self.assertEqual(p.state(o),p.state(changed))
        before=p.state(o);p.remember(o,ACTIONS.index('SUBMIT'));self.assertNotEqual(before,p.state(o))
    def test_conservative_rule_solves_without_timestamp_access(self):
        from click_once.memory_control import ConservativeRule
        for part in ('domain','composition','timing'):
            for case in grid(part):
                e=ChallengeEnv(max_steps=40);o,_=e.reset(case['seed'],case);p=ConservativeRule();p.reset()
                while True:
                    public=deepcopy(o);public.pop('history_meta')
                    o,_,t,tr,_=e.step(p.act(public))
                    if t or tr:break
                self.assertTrue(e.audit()['strict_success'],case)
