import unittest
from click_once.screenshot_agent import validate_action
class ScreenshotAgentContract(unittest.TestCase):
    def test_action_must_be_allowlisted(self):
        for a in [{'action':'execute_python','memory':''},{'action':'click','x':2001,'y':1,'memory':''},{'action':'key','text':'Meta+L','memory':''}]:
            with self.assertRaises(ValueError):validate_action(a)
    def test_click_and_explicit_memory_accepted(self):
        a={'action':'click','x':500,'y':400,'memory':'Observed confirmed date: 2026-11-18'}
        self.assertEqual(validate_action(a),a)
    def test_private_solution_fields_rejected(self):
        with self.assertRaises(ValueError):validate_action({'action':'done','memory':'','expected_solution':'24'})

class AgentPayloadContract(unittest.TestCase):
    def test_agent_only_receives_public_goal_image_tabs_and_own_history(self):
        import json
        from unittest.mock import patch
        from click_once.screenshot_agent import QwenScreenshotAgent
        class Reply:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self):return json.dumps({'message':{'content':json.dumps({'action':'done','memory':'seen facts'})},'eval_count':8}).encode()
        seen=[]
        def fake(req,**kwargs):seen.append(json.loads(req.data));return Reply()
        with patch('click_once.screenshot_agent.urllib.request.urlopen',side_effect=fake):
            from PIL import Image
            import io
            image=io.BytesIO();Image.new('RGB',(1120,820),'white').save(image,format='PNG')
            a=QwenScreenshotAgent();a.act(image.getvalue(),'public goal',[{'index':0,'title':'Source','url':'http://localhost'}],0,[])
        public=json.loads(seen[0]['messages'][1]['content'])
        self.assertEqual(set(public),{'task','active_tab','tabs','memory','recent_actions'})
        self.assertNotIn('case',public);self.assertNotIn('solution',public);self.assertNotIn('grade',public)

        import base64,io
        from PIL import Image
        self.assertEqual(Image.open(io.BytesIO(base64.b64decode(seen[0]['messages'][1]['images'][0]))).size,(768,562))
        self.assertEqual(seen[0]['options']['num_batch'],64)
