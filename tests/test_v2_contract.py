import unittest
from copy import deepcopy
from click_once.challenge import ChallengeEnv,ChallengeRule,make_cases
from click_once.evaluator import evaluate_audit

class V2Contract(unittest.TestCase):
    def env(self,**options):
        e=ChallengeEnv();e.reset(seed=100001,options=options);return e
    def test_two_failures_do_not_make_second_retry_succeed(self):
        e=self.env(failures=2)
        e.step('SUBMIT');e.step('SUBMIT')
        self.assertEqual(e.audit()['confirmed_count'],0)
        e.step('SUBMIT');self.assertEqual(e.audit()['confirmed_count'],1)
    def test_distractors_do_not_count_as_requested_success(self):
        e=self.env(distractors=3)
        self.assertEqual(e.audit()['confirmed_count'],0)
        e.step('CHECK_HISTORY');e.step('FINISH')
        self.assertFalse(evaluate_audit(e.audit())['strict_success'])
    def test_unrelated_records_preserved_on_success(self):
        e=self.env(distractors=3)
        e.step('SUBMIT');e.step('FINISH')
        self.assertTrue(evaluate_audit(e.audit())['strict_success'])
        self.assertEqual(len(e.audit()['records']),4)
    def test_stale_empty_history_cannot_prove_failure(self):
        e=self.env(lag=3)
        e.step('SUBMIT');obs,*_=e.step('CHECK_HISTORY')
        self.assertEqual(obs['rows'],[])
        self.assertLess(obs['history_meta']['as_of_tick'],obs['history_meta']['last_submit_tick'])
        self.assertEqual(e.audit()['confirmed_count'],1)
    def test_fresh_history_eventually_reveals_commit(self):
        e=self.env(lag=3);e.step('SUBMIT')
        for _ in range(3):obs,*_=e.step('CHECK_HISTORY')
        self.assertGreaterEqual(obs['history_meta']['as_of_tick'],obs['history_meta']['last_submit_tick'])
        self.assertEqual(obs['rows'][0]['status'],'confirmed')
    def test_early_stale_retry_creates_duplicate(self):
        e=self.env(lag=3);e.step('SUBMIT');e.step('CHECK_HISTORY');e.step('SUBMIT');e.step('FINISH')
        self.assertFalse(evaluate_audit(e.audit())['strict_success'])
        self.assertEqual(e.audit()['duplicate_count'],1)
    def test_auditor_catches_collateral_damage_even_with_correct_target(self):
        e=self.env(distractors=2);e.step('SUBMIT');e.step('FINISH');a=e.audit()
        a['records']=[r for r in a['records'] if r['target']==a['goal']]
        self.assertFalse(evaluate_audit(a)['strict_success'])
    def test_public_rule_solves_every_validation_world(self):
        for case in make_cases('validation',100):
            e=ChallengeEnv();o,_=e.reset(seed=case['seed'],options=case);policy=ChallengeRule('fresh')
            for _ in range(24):
                o,_,t,tr,_=e.step(policy.act(o))
                if t or tr:break
            self.assertTrue(evaluate_audit(e.audit())['strict_success'],case)
    def test_seed_splits_disjoint(self):
        s=[{c['seed'] for c in make_cases(x,100)} for x in ('train','validation','test')]
        self.assertFalse(s[0]&s[1] or s[1]&s[2] or s[0]&s[2])
    def test_hidden_options_not_in_policy_observation(self):
        e=self.env(failures=2,lag=3,distractors=2)
        o=e.observe()
        self.assertNotIn('failures',o);self.assertNotIn('lag',o);self.assertNotIn('tier',o)
        self.assertEqual(set(o['history_meta']),{'as_of_tick','current_tick','last_submit_tick'})

class V2LearningContract(unittest.TestCase):
    def test_freshness_ablation_changes_representation(self):
        from click_once.hardening import EvidenceLearner
        e=ChallengeEnv();o,_=e.reset(seed=1,options={'lag':3});e.step('SUBMIT');o,*_=e.step('CHECK_HISTORY')
        a,b=EvidenceLearner(freshness=True),EvidenceLearner(freshness=False)
        changed=deepcopy(o);changed['history_meta']['as_of_tick']=changed['history_meta']['last_submit_tick']
        self.assertNotEqual(a.state(o),a.state(changed));self.assertEqual(b.state(o),b.state(changed))
    def test_distractor_rows_do_not_change_target_features(self):
        from click_once.hardening import EvidenceLearner
        e=ChallengeEnv();o,_=e.reset(seed=1);e.step('SUBMIT');o,*_=e.step('CHECK_HISTORY')
        changed=deepcopy(o);changed['rows'].append(dict(id='irrelevant',target='Someone else',status='confirmed'))
        p=EvidenceLearner();self.assertEqual(p.state(o),p.state(changed))

class V2OutcomeIntegrity(unittest.TestCase):
    def test_new_unrequested_record_is_not_allowed(self):
        e=ChallengeEnv();e.reset(seed=1);e.step('SUBMIT');e.step('FINISH');a=e.audit()
        a['records'].append(dict(id='unexpected',target='Unrequested booking',status='confirmed',due=0))
        self.assertFalse(evaluate_audit(a)['strict_success'])
