import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

class CLIContract(unittest.TestCase):
    def test_bounded_experiment_cli_and_artifact_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'experiment'
            r=subprocess.run([sys.executable,'-m','click_once','train','--output',str(out),'--episodes','100','--eval-count','10'],capture_output=True,text=True,timeout=60)
            self.assertEqual(r.returncode,0,r.stderr)
            config=json.loads((out/'config.json').read_text())
            self.assertEqual(config['episodes'],100)
            records=json.loads((out/'provenance.json').read_text())
            self.assertEqual(len(records),12)
            for record in records:self.assertEqual(len(record['checkpoint_sha256']),64)
            summaries=json.loads((out/'summary.json').read_text())
            self.assertEqual(summaries['test/verify']['overall']['episodes'],10)
            self.assertTrue((out/'traces.jsonl').exists())
            self.assertTrue((out/'audits-private.jsonl').exists())
            self.assertTrue(Path(str(out)+'-resources/resources.csv').exists())
    def test_invalid_action_budget_rejected(self):
        from click_once.experiment import run_experiment
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):run_experiment(Path(d)/'bad',episodes=0)
