"""Record the two first-seed policies on the same fixed validation challenge."""
import html,json
from pathlib import Path
from click_once.challenge import ChallengeEnv,make_cases
from click_once.hardening import EvidenceLearner
from click_once.browser import BrowserSession
from click_once.resources import ResourceGuard
from click_once.evaluator import evaluate_audit

root=Path(__file__).resolve().parents[1]
# Mechanism-focused diagnostic, not selected from the locked test outcomes.
case=dict(seed=200017,tier='combined',failures=2,distractors=2,lag=3,pending=True,delay=4)
base=root/'runs/challenge-v2'
with ResourceGuard(base/'browser-resources'),BrowserSession() as b:
 for name in ('target_only_11','freshness_11'):
    policy=EvidenceLearner.load(base/f'{name}.json');policy.reset()
    e=ChallengeEnv();e.reset(case['seed'],case);b.set_env(e)
    out=base/f'demo-{name}';out.mkdir(exist_ok=True);frames=[]
    for tick in range(25):
        obs=b.public_observation();audit=e.audit();done=audit['finished'] or audit['truncated']
        action=None if done else policy.act(obs)
        file=f'{tick:02}.png';(out/file).write_bytes(b.screenshot())
        frames.append(dict(image=file,observation=obs,action=action,audit=audit))
        if done:break
        b.execute(action)
    data=dict(policy=name,case=case,frames=frames,evaluation=evaluate_audit(e.audit()))
    (out/'trace.json').write_text(json.dumps(data,indent=2))
    cards=''.join(f'<section><h3>Step {i}: {html.escape(f["action"] or "Ended")}</h3><img src="{f["image"]}"><p>Evaluator only: {f["audit"]["confirmed_count"]} target bookings, {f["audit"]["duplicate_count"]} duplicates</p></section>' for i,f in enumerate(frames))
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><style>body{background:#10151b;color:#eee;font:16px system-ui;max-width:1120px;margin:40px auto}img{width:100%;border-radius:10px}section{margin-bottom:30px}</style><h1>V2 actual browser replay: '+name+'</h1><p>Structured observations, not VLM control.</p>'+cards)
    print(name,data['evaluation'])
