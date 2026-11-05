"""Budgeted actual-Qwen evaluation. No privileged task fields are agent inputs."""
import argparse,hashlib,json,time,urllib.request
from pathlib import Path
from .tasks import catalog
from .suite_env import BrowserTaskEnv
from .suite_browser import TaskEpisode,reference_interaction
from .screenshot_agent import QwenScreenshotAgent,PROMPT,SCHEMA,MODEL
from .resources import ResourceGuard


def write(path,data):Path(path).write_text(json.dumps(data,indent=2))
def model_metadata():
    req=urllib.request.Request('http://127.0.0.1:11434/api/show',data=json.dumps({'model':MODEL}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as r:d=json.load(r)
    with urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=10) as r:tags=json.load(r)
    return dict(name=MODEL,details=d['details'],renderer=d.get('renderer'),parser=d.get('parser'),
                digest=next(x['digest'] for x in tags['models'] if x['name']==MODEL))


def validate_suite(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=False);results=[]
    with ResourceGuard(out/'resources'):
        for case in catalog():
            try:
                with TaskEpisode(case) as e:
                    result=reference_interaction(e)
                    (out/(case['id']+'.png')).write_bytes(e.screenshot())
                row=dict(id=case['id'],valid=True,evidence=result)
            except Exception as exc:row=dict(id=case['id'],valid=False,error=str(exc))
            results.append(row);write(out/'validation.json',results);print(case['id'],row['valid'],flush=True)
    if not all(r['valid'] for r in results):raise RuntimeError('Invalid cases must be repaired before evaluation')


def run_episode(case,out,agent,wall_limit=300):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);write(out/'task-private.json',case)
    write(out/'task-public.json',dict(id=case['id'],family=case['family'],level=case['level'],instruction=case['instruction']))
    env=BrowserTaskEnv(max_steps=24);agent.reset();trace=[];history=[];start=time.monotonic();status='action_budget';same=0;last_pair=None
    try:
        obs,_=env.reset(seed=case['seed'],options={'case':case})
        for index in range(24):
            if time.monotonic()-start>=wall_limit:status='wall_budget';break
            png=env.last_png;name=f'{index:02}.png';(out/name).write_bytes(png)
            public=dict(instruction=obs['instruction'],tabs=json.loads(obs['tabs']),active=obs['active_tab'])
            try:
                action,timing=agent.act(png,public['instruction'],public['tabs'],public['active'],history)
            except ValueError as exc:
                status='agent_protocol_error';write(out/f'{index:02}-error.json',dict(error=str(exc),responses=getattr(exc,'records',[])));break
            except Exception as exc:
                status='infrastructure_error';write(out/f'{index:02}-error.json',dict(error=repr(exc)));break
            pair=(hashlib.sha256(png).hexdigest(),json.dumps({k:v for k,v in action.items() if k!='memory'},sort_keys=True))
            same=same+1 if pair==last_pair else 1;last_pair=pair
            row=dict(step=index+1,image=name,public=public,action=action,timing=timing)
            trace.append(row);history.append(action)
            obs,reward,t,tr,_=env.step(json.dumps(action))
            row['execution_error']=env.last_execution_error
            with (out/'trace.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
            print(case['id'],index+1,action['action'],f'{timing["seconds"]:.1f}s',flush=True)
            if t:status='agent_done';break
            if tr:status='action_budget';break
            if same>=5:status='no_progress_loop';break
        (out/'final.png').write_bytes(env.last_png)
        grade=env.episode.grade()
        evidence=dict(saved_state=env.episode.state,submissions=env.episode.submissions,
                      final_url=env.episode.page.url,navigation=env.episode.navigation,wikipedia=env.episode.wiki_evidence)
        result=dict(id=case['id'],family=case['family'],level=case['level'],end_condition=status,success=grade['success'],
                    grade=grade,actions=len(trace),wall_seconds=time.monotonic()-start,
                    model_seconds=sum(r['timing']['seconds'] for r in trace),generated_tokens=sum(sum(x.get('generated_tokens',0) or 0 for x in r['timing']['responses']) for r in trace))
        write(out/'evaluator-private.json',evidence)
    except KeyboardInterrupt:
        write(out/'result.json',dict(id=case['id'],family=case['family'],level=case['level'],success=False,end_condition='interrupted',actions=len(trace)))
        raise
    except Exception as exc:
        result=dict(id=case['id'],family=case['family'],level=case['level'],success=False,end_condition='setup_or_browser_error',error=repr(exc),actions=len(trace),wall_seconds=time.monotonic()-start)
    finally:env.close()
    write(out/'result.json',result);return result


def run_suite(output,calibration=False):
    out=Path(output);out.mkdir(parents=True,exist_ok=False);agent=QwenScreenshotAgent()
    cases=catalog()
    if calibration:
        from copy import deepcopy
        case=deepcopy(next(c for c in cases if c['family']=='math'));case['id']='development-math';case['numbers']=[1,1,4,6];cases=[case]
    config=dict(protocol='TASK_SUITE_V4.md',model=model_metadata(),prompt=PROMPT,schema=SCHEMA,temperature=0,model_seed=42,
                context=3072,image_max_dimension=768,prompt_batch=64,generated_token_cap=768,max_actions=24,wall_limit=300,calibration=calibration,
                cases=len(cases),observation='current screenshot, explicit self-written memory, last six actions, public tab metadata',
                source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')})
    source=out/'source';source.mkdir()
    for p in Path(__file__).parent.glob('*.py'):(source/p.name).write_bytes(p.read_bytes())
    write(out/'config.json',config);write(out/'catalog-private.json',cases)
    write(out/'FROZEN.json',dict(catalog_sha256=hashlib.sha256((out/'catalog-private.json').read_bytes()).hexdigest(),config_sha256=hashlib.sha256((out/'config.json').read_bytes()).hexdigest()))
    results=[]
    try:
        with ResourceGuard(out/'resources'):
            for case in cases:
                result=run_episode(case,out/case['id'],agent)
                results.append(result);write(out/'results.json',results)
                print('RESULT',case['id'],'PASS' if result['success'] else 'FAIL',result['end_condition'],flush=True)
    finally:agent.close()
    write(out/'run-status.json',dict(completed=len(results),planned=len(cases),finished=len(results)==len(cases)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['validate','run','calibrate']);p.add_argument('--output',required=True);a=p.parse_args()
    if a.command=='validate':validate_suite(a.output)
    else:run_suite(a.output,a.command=='calibrate')
