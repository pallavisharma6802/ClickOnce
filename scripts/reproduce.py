"""One bounded end-to-end reproduction; no paid services or implicit model download."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

p=argparse.ArgumentParser()
p.add_argument('--output',required=True,type=Path)
p.add_argument('--episodes',type=int,default=10000)
p.add_argument('--vision',action='store_true',help='Use installed local Qwen; no download')
a=p.parse_args()
root=Path(__file__).resolve().parents[1]
os.chdir(root)
if a.output.exists():raise SystemExit('Use a fresh output directory')
a.output.mkdir(parents=True)
def run(*args,env=None,timeout=120):
 subprocess.run([sys.executable,*args],check=True,env=env,timeout=timeout)
run('-m','unittest','discover','-s','tests','-v',env=dict(os.environ,CLICKONCE_BROWSER_TESTS='1'))
experiment=a.output/'experiment'
run('-m','click_once','train','--output',str(experiment),'--episodes',str(a.episodes),'--eval-count','200')
run('-m','click_once','demo','--output',str(a.output/'demo'),'--scenario','committed_timeout','--policy','outcome-memory-seed11','--checkpoint',str(experiment/'q_strict_memory_11.json'))
if a.vision:
 run('-m','click_once','vision','--output',str(a.output/'vision'),timeout=2100)
run('-m','click_once','report','--experiment',str(experiment),'--output',str(a.output/'report'))
print('Complete:',(a.output/'report/index.html').resolve())
