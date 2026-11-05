"""Frozen Qwen browser actor: pixels and its own memory; no task-private inputs."""
import base64,io,json,time,urllib.request
from PIL import Image

MODEL='qwen3-vl:2b-instruct'
PROMPT='''You operate a browser using screenshots. Complete the user's task carefully. Return exactly one JSON action. Choose only the NEXT action; keep reasoning brief. Coordinates are normalized 0..1000, not pixels. Tools: click(x,y), type(text) into the currently focused field, key(text) where text is enter/tab/escape/backspace/select_all, scroll(y) in pixels (positive down, negative up), switch_tab(tab) by index, wait, done. First click the intended field before typing. Read saved status after submitting. Do not declare done until the requested artifact exists. You cannot execute code, inspect DOM, use a calculator, or navigate directly to URLs. For Wikipedia only clicks on article hyperlinks and scrolling are allowed. Use memory to retain facts you actually saw, especially before switching tabs; relevant memory is carried into the next step. Do not invent facts. Do not erase useful memory when switching tabs. A screenshot shows only the active tab. Include all JSON fields: action, x, y, text, tab, memory. For a click provide actual x and y coordinates. Use 0 for unused numbers and an empty string for unused text. Example: {"action":"click","x":500,"y":450,"text":"","tab":0,"memory":"Observed facts"}.'''
SCHEMA={'type':'object','properties':{'action':{'type':'string','enum':['click','type','key','scroll','switch_tab','wait','done']},'x':{'type':'integer','minimum':0,'maximum':1000},'y':{'type':'integer','minimum':-1200,'maximum':1200},'text':{'type':'string','maxLength':2000},'tab':{'type':'integer','minimum':0,'maximum':3},'memory':{'type':'string','maxLength':1200}},'required':['action','memory','x','y','text','tab'],'additionalProperties':False}


def validate_action(a):
    if not isinstance(a,dict) or set(a)-set(SCHEMA['properties']) or a.get('action') not in SCHEMA['properties']['action']['enum']:raise ValueError('Invalid action schema')
    if not isinstance(a.get('memory'),str) or len(a['memory'])>1200:raise ValueError('Invalid memory')
    act=a['action']
    if act=='click' and any(type(a.get(k)) is not int or not 0<=a[k]<=1000 for k in ('x','y')):raise ValueError('Invalid click coordinates')
    if act=='scroll' and (type(a.get('y')) is not int or not -1200<=a['y']<=1200):raise ValueError('Invalid scroll')
    if act=='switch_tab' and (type(a.get('tab')) is not int or not 0<=a['tab']<=3):raise ValueError('Invalid tab')
    if act=='type' and (not isinstance(a.get('text'),str) or len(a['text'])>2000):raise ValueError('Invalid typed text')
    if act=='key' and a.get('text') not in ('enter','tab','escape','backspace','select_all'):raise ValueError('Unapproved key')
    return a


class AgentProtocolError(ValueError):
    def __init__(self,message,records):super().__init__(message);self.records=records


class QwenScreenshotAgent:
    def __init__(self):self.memory=''
    def reset(self):self.memory=''
    def act(self,png,instruction,tabs,active,history):
        recent=[{k:(v[:180] if isinstance(v,str) else v) for k,v in row.items() if k!='memory'} for row in history[-6:]]
        public=dict(task=instruction,active_tab=active,tabs=tabs,memory=self.memory,recent_actions=recent)
        image=Image.open(io.BytesIO(png)).convert('RGB');image.thumbnail((768,768))
        resized=io.BytesIO();image.save(resized,format='PNG')
        payload=dict(model=MODEL,stream=False,think=False,keep_alive='2m',format=SCHEMA,
            messages=[dict(role='system',content=PROMPT),dict(role='user',content=json.dumps(public),images=[base64.b64encode(resized.getvalue()).decode()])],
            options=dict(num_ctx=3072,num_batch=64,num_predict=768,temperature=0,seed=42))
        start=time.monotonic();records=[]
        for attempt in range(2):
            req=urllib.request.Request('http://127.0.0.1:11434/api/chat',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=60) as response:data=json.load(response)
            raw=data.get('message',{}).get('content','')
            records.append(dict(raw_content=raw,done_reason=data.get('done_reason'),generated_tokens=data.get('eval_count'),
                                thinking_characters=len(data.get('message',{}).get('thinking','')),load_seconds=data.get('load_duration',0)/1e9))
            try:
                a=validate_action(json.loads(raw));self.memory=a['memory']
                return a,dict(seconds=time.monotonic()-start,attempts=attempt+1,responses=records)
            except (ValueError,json.JSONDecodeError) as exc:
                if attempt:raise AgentProtocolError('Invalid model action after bounded retry: '+str(exc),records)
                payload['messages'].append(dict(role='user',content='The prior output was invalid: '+str(exc)+'. Return one concise valid action JSON with the required memory field.'))
        raise AssertionError('Unreachable')
    def close(self):
        try:
            req=urllib.request.Request('http://127.0.0.1:11434/api/generate',data=json.dumps(dict(model=MODEL,keep_alive=0)).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=15) as r:r.read()
        except Exception:pass
