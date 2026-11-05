import json,os,unittest
from click_once.tasks import catalog
from click_once.suite_env import BrowserTaskEnv
from click_once.suite_browser import TaskEpisode,reference_interaction
@unittest.skipUnless(os.environ.get('CLICKONCE_BROWSER_TESTS')=='1','Enable actual Chrome tests')
class SuiteUIContract(unittest.TestCase):
    def test_local_task_interfaces_and_private_boundaries(self):
        for family in ('math','email','offers'):
            case=next(c for c in catalog() if c['family']==family and c['level']=='hard')
            with TaskEpisode(case) as e:
                for site in e.sites:
                    self.assertEqual(e.page.request.get(site.url+'api/grade').status,404)
                self.assertFalse(e.page.get_by_role('button',name='Send',exact=True).count())
                if family!='math':self.assertNotEqual(e.pages[0].url,e.pages[-1].url)
                self.assertTrue(reference_interaction(e)['success'])
    def test_gym_observation_contains_pixels_not_answers(self):
        env=BrowserTaskEnv(max_steps=2)
        try:
            obs,info=env.reset(seed=1,options={'case_id':'math-easy-0'})
            self.assertEqual(info,{})
            self.assertTrue(env.observation_space.contains(obs))
            self.assertEqual(set(obs),{'image','instruction','tabs','active_tab'})
            _,reward,term,trunc,info=env.step(json.dumps({'action':'done','memory':''}))
            self.assertEqual(info,{});self.assertTrue(term);self.assertFalse(trunc);self.assertLess(reward,0)
        finally:env.close()
