"""Real browser integration: run with CLICKONCE_BROWSER_TESTS=1."""
import os
import tempfile
import unittest
from pathlib import Path

@unittest.skipUnless(os.environ.get('CLICKONCE_BROWSER_TESTS')=='1','Enable real browser integration explicitly')
class BrowserContract(unittest.TestCase):
    def test_all_scenarios_and_private_boundary(self):
        from click_once.browser import BrowserSession
        from click_once.env import ClickOnceEnv,SCENARIOS
        from click_once.learning import Baseline
        with BrowserSession() as session:
            for scenario in SCENARIOS:
                with self.subTest(scenario=scenario):
                    env=ClickOnceEnv();obs,_=env.reset(seed=17,options={'scenario':scenario,'delay':3})
                    session.set_env(env)
                    self.assertEqual(session.public_observation(),obs)
                    for private_path in ('/audit','/api/audit','/reset','/api/reset'):
                        self.assertEqual(session.page.request.get(session.url+private_path).status,404)
                    policy=Baseline('verify')
                    while not (env.audit()['finished'] or env.audit()['truncated']):
                        action=policy.act(session.public_observation())
                        session.execute(action)
                        self.assertEqual(session.public_observation(),env.observe())
                    self.assertTrue(env.audit()['strict_success'])
                    self.assertNotIn(scenario,session.page.content())
    def test_ambiguous_timeout_screenshots_are_pixel_identical(self):
        from click_once.browser import BrowserSession
        from click_once.env import ClickOnceEnv
        images=[]
        with BrowserSession() as s:
            for scenario in ('failed_timeout','committed_timeout','pending_timeout'):
                e=ClickOnceEnv();e.reset(seed=17,options={'scenario':scenario,'delay':3});s.set_env(e)
                s.execute('SUBMIT');s.page.mouse.move(0,0)
                images.append(s.screenshot())
        self.assertEqual(images[0],images[1]);self.assertEqual(images[1],images[2])
    def test_reload_does_not_reset_backend(self):
        from click_once.browser import BrowserSession
        from click_once.env import ClickOnceEnv
        with BrowserSession() as s:
            e=ClickOnceEnv();e.reset(seed=17,options={'scenario':'committed_timeout'});s.set_env(e)
            s.execute('SUBMIT');s.page.reload();s.wait_ready()
            s.execute('CHECK_HISTORY')
            self.assertEqual(s.public_observation()['rows'][0]['status'],'confirmed')
    def test_invalid_action_not_executed(self):
        from click_once.browser import BrowserSession
        from click_once.env import ClickOnceEnv
        with BrowserSession() as s:
            e=ClickOnceEnv();e.reset(seed=1);s.set_env(e)
            with self.assertRaises(ValueError):s.execute('eval("danger")')
            self.assertEqual(e.audit()['steps'],0)

@unittest.skipUnless(os.environ.get('CLICKONCE_BROWSER_TESTS')=='1','Enable real browser integration explicitly')
class V2BrowserContract(unittest.TestCase):
    def test_staleness_metadata_is_actually_visible(self):
        from click_once.browser import BrowserSession
        from click_once.challenge import ChallengeEnv,ChallengeRule
        with BrowserSession() as b:
            e=ChallengeEnv();e.reset(seed=100001,options={'lag':3,'failures':2,'distractors':2,'pending':True,'delay':4})
            b.set_env(e);policy=ChallengeRule('fresh')
            while not(e.audit()['finished'] or e.audit()['truncated']):
                b.execute(policy.act(b.public_observation()))
                self.assertTrue(b.page.locator('#freshness').is_visible())
                self.assertIn('History snapshot tick',b.page.locator('#freshness').inner_text())
                self.assertEqual(b.public_observation(),e.observe())
            self.assertTrue(e.audit()['strict_success'])
