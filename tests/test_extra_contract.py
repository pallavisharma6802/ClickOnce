import json
import unittest
from click_once.env import ClickOnceEnv
from click_once.learning import QLearner,features
from click_once.experiment import train,make_manifest,aggregate

class ExtraContract(unittest.TestCase):
    def test_truncation_bootstraps_but_termination_does_not(self):
        p=QLearner(alpha=1,gamma=.9)
        p.update('next',0,1,'terminal',True,False)
        p.update('truncated',0,0,'next',False,True)
        p.update('terminated',0,0,'next',True,False)
        self.assertAlmostEqual(p.values('truncated')[0],.9)
        self.assertEqual(p.values('terminated')[0],0)
    def test_policy_rejects_private_fields(self):
        obs,_=ClickOnceEnv().reset(seed=1)
        with self.assertRaises(ValueError):features(dict(obs,audit={'correct':True}))
    def test_training_reproducible_and_changes_q_values(self):
        a,_,_=train(5,'strict',100,make_manifest('train',20))
        b,_,_=train(5,'strict',100,make_manifest('train',20))
        self.assertEqual(a.q,b.q)
        self.assertTrue(any(any(v!=0 for v in row) for row in a.q.values()))
    def test_metric_denominators_include_failures(self):
        rows=[dict(strict_success=x,duplicate=0,false_completion=0,truncated=1-x,steps=2,checks=0,return_value=0,proxy_exploit=0) for x in [1,0]]
        self.assertEqual(aggregate(rows)['strict_success'],.5)
    def test_audit_cannot_mutate_environment(self):
        e=ClickOnceEnv();e.reset(seed=1);e.step('SUBMIT')
        a=e.audit();a['events'].clear()
        self.assertTrue(e.audit()['events'])
    def test_gym_api_and_spaces(self):
        from gymnasium.utils.env_checker import check_env
        from click_once.gym_env import ClickOnceGym
        env=ClickOnceGym();check_env(env,skip_render_check=True)
        obs,_=env.reset(seed=17,options={'scenario':'normal'})
        self.assertTrue(env.observation_space.contains(obs))
        self.assertEqual(json.loads(obs)['notice'],'Ready')
