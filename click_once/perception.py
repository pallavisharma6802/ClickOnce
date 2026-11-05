"""Optional frozen local VLM. No policy training or privileged state in requests."""
import base64
import hashlib
import json
import subprocess
import time
import urllib.request
from pathlib import Path
from .env import ClickOnceEnv,ACTIONS
from .browser import BrowserSession

MODEL='qwen3-vl:2b'
PROMPT='''Read ONLY what is currently visible in this booking interface. Return JSON with notice, page, confirmed, pending. notice is the exact main Visible status: Ready, Success, Timeout, or History refreshed. page is history ONLY when the Booking history header says Latest inspected snapshot; otherwise booking. confirmed and pending are the counts of VISIBLE table rows with State CONFIRMED or PENDING, capped at 2. If no table rows are visible, both are 0. Never infer whether a booking exists from Success or Timeout. Do not count words outside the history table. No explanation.'''
SCHEMA={'type':'object','properties':{'notice':{'type':'string','enum':['Ready','Success','Timeout','History refreshed']},'page':{'type':'string','enum':['booking','history']},'confirmed':{'type':'integer','minimum':0,'maximum':2},'pending':{'type':'integer','minimum':0,'maximum':2}},'required':['notice','page','confirmed','pending'],'additionalProperties':False}


def validate_prediction(p):
    if not isinstance(p,dict) or set(p)!=set(SCHEMA['required']):raise ValueError('Invalid prediction fields')
    if p['notice'] not in SCHEMA['properties']['notice']['enum'] or p['page'] not in ('booking','history'):raise ValueError('Invalid visible labels')
    if any(type(p[k]) is not int or not 0<=p[k]<=2 for k in ('confirmed','pending')):raise ValueError('Invalid visible counts')
    return p


def public_from_prediction(p):
    p=validate_prediction(p)
    rows=[dict(id=f'visible-{i}',target='Visible booking',status=status)
          for status,count in [('confirmed',p['confirmed']),('pending',p['pending'])] for i in range(count)]
    return dict(goal='Complete the visible booking exactly once',page=p['page'],notice=p['notice'],rows=rows,buttons=list(ACTIONS))


def labels(obs):
    return dict(notice=obs['notice'],page=obs['page'],confirmed=min(2,sum(r['status']=='confirmed' for r in obs['rows'])),pending=min(2,sum(r['status']=='pending' for r in obs['rows'])))


class LocalPerception:
    def __init__(self,cache):self.cache=Path(cache);self.cache.mkdir(parents=True,exist_ok=True)
    def read(self,png):
        key=hashlib.sha256(png+MODEL.encode()+PROMPT.encode()+json.dumps(SCHEMA,sort_keys=True).encode()).hexdigest()
        dest=self.cache/f'{key}.json'
        if dest.exists():return validate_prediction(json.loads(dest.read_text())),dict(cached=True,seconds=0,raw='cached')
        payload=dict(model=MODEL,stream=False,think=False,keep_alive='2m',format=SCHEMA,
                     messages=[dict(role='user',content=PROMPT,images=[base64.b64encode(png).decode()])],
                     options=dict(num_ctx=4096,num_predict=1024,temperature=0))
        started=time.monotonic();last_error=None
        for attempt in range(2):
            try:
                req=urllib.request.Request('http://127.0.0.1:11434/api/chat',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(req,timeout=90) as r:data=json.load(r)
                raw=data.get('message',{}).get('content','')
                prediction=validate_prediction(json.loads(raw))
                dest.write_text(json.dumps(prediction))
                return prediction,dict(cached=False,seconds=time.monotonic()-started,raw=raw,attempts=attempt+1,
                                      load_seconds=data.get('load_duration',0)/1e9, generated_tokens=data.get('eval_count',0),
                                      reasoning_present=bool(data.get('message',{}).get('thinking')))
            except (ValueError,json.JSONDecodeError) as exc:
                last_error=str(exc)
                (self.cache/f'{key}-failure-{attempt}.json').write_text(json.dumps(data,indent=2))
        raise ValueError(f'Malformed local VLM response after bounded retry: {last_error}')
    def close(self):
        # Unload only the model this adapter used; never stop the Ollama daemon.
        payload=dict(model=MODEL,keep_alive=0)
        try:
            req=urllib.request.Request('http://127.0.0.1:11434/api/generate',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=15) as r:r.read()
        except Exception:pass


def collect_fixtures(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    specs=[('normal',[]),('normal',['SUBMIT']),('failed_timeout',['SUBMIT']),
           ('failed_timeout',['SUBMIT','CHECK_HISTORY']),('committed_timeout',['SUBMIT','CHECK_HISTORY']),
           ('pending_timeout',['SUBMIT','CHECK_HISTORY']),('normal',['SUBMIT','SUBMIT','CHECK_HISTORY'])]
    fixtures=[]
    with BrowserSession() as browser:
        for i in range(20):
            scenario,actions=specs[i%len(specs)]
            env=ClickOnceEnv();env.reset(seed=50000+i,options={'scenario':scenario,'delay':4})
            browser.set_env(env)
            for action in actions:browser.execute(action)
            browser.page.mouse.move(0,0)
            file=f'frame-{i:02}.png';(output/file).write_bytes(browser.screenshot())
            fixtures.append(dict(file=file,expected=labels(browser.public_observation())))
    (output/'labels.json').write_text(json.dumps(fixtures,indent=2))
    return fixtures


def evaluate_perception(output):
    output=Path(output);frames=output/'frames'
    fixtures=collect_fixtures(frames)
    adapter=LocalPerception(output/'cache');results=[]
    try:
        for i,f in enumerate(fixtures):
            try:
                prediction,timing=adapter.read((frames/f['file']).read_bytes())
                result=dict(**f,prediction=prediction,correct=prediction==f['expected'],**timing)
            except Exception as exc:result=dict(**f,correct=False,error=str(exc))
            results.append(result)
            (output/'perception.json').write_text(json.dumps(results,indent=2))
            print(f'Vision {i+1}/20: {"correct" if result["correct"] else "incorrect"} ({result.get("seconds",0):.1f}s)',flush=True)
    finally:adapter.close()
    accuracy=sum(r['correct'] for r in results)/len(results)
    gate=dict(model=MODEL,accuracy=accuracy,passed=accuracy>=.9 and all('error' not in r for r in results),
              samples=len(results),trained=False,observation='actual browser screenshots',
              note='Small engineering smoke set, not a general perception benchmark')
    (output/'gate.json').write_text(json.dumps(gate,indent=2))
    return gate
