import unittest
from click_once.env import ClickOnceEnv
from click_once.evaluator import evaluate_audit
class EvaluatorContract(unittest.TestCase):
    def test_does_not_trust_success_flag(self):
        e=ClickOnceEnv();e.reset(seed=1,options={"scenario":"normal"});e.step('FINISH');a=e.audit();a['strict_success']=True
        self.assertFalse(evaluate_audit(a)['strict_success'])
    def test_does_not_trust_count_fields(self):
        e=ClickOnceEnv();e.reset(seed=1,options={"scenario":"normal"});e.step('SUBMIT');e.step('SUBMIT');e.step('FINISH');a=e.audit()
        a.update(confirmed_count=1,duplicate_count=0,strict_success=True)
        self.assertFalse(evaluate_audit(a)['strict_success'])
    def test_wrong_target_cannot_pass(self):
        e=ClickOnceEnv();e.reset(seed=1,options={"scenario":"normal"});e.step('SUBMIT');e.step('FINISH');a=e.audit()
        a['records'][0]['target']='Other request'
        self.assertFalse(evaluate_audit(a)['strict_success'])
