import unittest
from click_once.suite_report import aggregate
class SuiteReportContract(unittest.TestCase):
    def test_infrastructure_is_visible_and_not_model_failure(self):
        r=aggregate([{'family':'math','success':False,'end_condition':'infrastructure_error'},{'family':'math','success':False,'end_condition':'agent_done'},{'family':'math','success':True,'end_condition':'agent_done'}])['math']
        self.assertEqual(r,dict(attempted=3,scorable=2,passed=1,infrastructure=1))

    def test_interrupted_episode_not_lost_from_incremental_summary(self):
        import tempfile,json
        from pathlib import Path
        from click_once.suite_report import load_results
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'results.json').write_text('[]');e=p/'interrupted-case';e.mkdir();(e/'result.json').write_text(json.dumps(dict(id='interrupted-case',end_condition='interrupted')))
            self.assertEqual(len(load_results(p)),1)
