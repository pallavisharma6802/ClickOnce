"""Record actual browser actions from a checkpoint or an explicitly labeled baseline."""
import html
import json
from pathlib import Path
from .env import ClickOnceEnv
from .browser import BrowserSession
from .learning import QLearner,Baseline


def record(output,scenario,policy_name,checkpoint=None,vision=False):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    policy=QLearner.load(checkpoint) if checkpoint else Baseline(policy_name)
    policy.reset();env=ClickOnceEnv();env.reset(seed=17,options={'scenario':scenario,'delay':4})
    frames=[];perception=None
    if vision:
        from .perception import LocalPerception,public_from_prediction
        perception=LocalPerception(out/'perception-cache')
    try:
        with BrowserSession() as browser:
            browser.set_env(env)
            for tick in range(13):
                png=browser.screenshot();file=f'{tick:02}.png';(out/file).write_bytes(png)
                visible=browser.public_observation()
                ended=env.audit()['finished'] or env.audit()['truncated']
                timing=None
                if perception and not ended:
                    pred,timing=perception.read(png);input_obs=public_from_prediction(pred)
                else:input_obs=visible
                action=None if ended else policy.act(input_obs)
                frames.append(dict(frame=file,observation=visible,policy_observation=input_obs,action=action,
                                   perception=timing,audit=env.audit()))
                if ended:break
                browser.execute(action)
    finally:
        if perception:perception.close()
    data=dict(policy=policy_name,checkpoint=str(checkpoint) if checkpoint else None,vision=vision,
              scenario=scenario,frames=frames,final_audit=env.audit())
    (out/'trace.json').write_text(json.dumps(data,indent=2))
    # Offline replay; private outcome is labeled and never fed into a policy.
    cards=[]
    for i,f in enumerate(frames):
        a=f['audit'];cards.append(f'<section><h3>Step {i} · {html.escape(f["action"] or "Episode ended")}</h3><img src="{f["frame"]}"><p>Evaluator-only backend: {a["confirmed_count"]} confirmed · {a["pending_count"]} pending · {a["duplicate_count"]} duplicates</p></section>')
    title=f'{policy_name} · {scenario}'
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>ClickOnce replay</title><style>body{background:#10151b;color:#e3eef5;font:16px system-ui;max-width:1120px;margin:40px auto}img{width:100%;border-radius:12px}section{margin:32px 0}p{color:#a9b8c8}</style><h1>ClickOnce / '+html.escape(title)+'</h1><p>Recorded browser execution. Backend panels are evaluator-only.</p>'+''.join(cards))
    return data
