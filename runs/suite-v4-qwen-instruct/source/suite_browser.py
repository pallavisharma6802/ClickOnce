"""Real-browser task episodes. Private graders never appear in agent observations."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import hashlib,html,json,threading,time
from pathlib import Path
from urllib.parse import urlparse
from .browser import BrowserSession
from .challenge import ChallengeEnv
from .evaluator import evaluate_audit
from .tasks import render,evaluate,arithmetic,article

class LocalSite:
    def __init__(self,episode,kind):self.episode=episode;self.kind=kind
    def __enter__(self):
        outer=self
        class H(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def reply(self,status,body,kind='application/json'):
                raw=body.encode();self.send_response(status);self.send_header('Content-Type',kind)
                self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def do_GET(self):
                if self.path=='/':self.reply(200,render(outer.episode.case,outer.kind),'text/html; charset=utf-8')
                else:self.reply(404,'{}')
            def do_POST(self):
                if self.path!='/api/submit' or outer.kind!='answer':self.reply(404,'{}');return
                try:
                    n=int(self.headers.get('Content-Length','0'))
                    if not 0<n<=10000:raise ValueError('Invalid input length')
                    payload=json.loads(self.rfile.read(n));e=outer.episode;family=e.case['family']
                    fields={'math':{'expression'},'email':{'to','subject','body'},'offers':{'vendor','total'}}[family]
                    if set(payload)!=fields or not all(isinstance(v,str) and len(v)<=4000 for v in payload.values()):raise ValueError('Invalid fields')
                    e.state['saved']=True;e.submissions.append(deepcopy(payload))
                    if family=='math':
                        e.state['expression']=payload['expression']
                        try:notice='Correct: the expression equals 24.' if arithmetic(payload['expression'],e.case['numbers'])==24 else 'Not 24. Try again.'
                        except Exception:notice='Invalid expression. Use the four numbers exactly once.'
                    elif family=='email':e.state['draft']=payload;notice='Draft saved.'
                    else:e.state['answer']=payload;notice='Comparison saved.'
                    self.reply(200,json.dumps({'notice':notice}))
                except (ValueError,KeyError,json.JSONDecodeError):self.reply(400,'{"notice":"Submission rejected"}')
        self.server=ThreadingHTTPServer(('127.0.0.1',0),H);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}/';return self
    def __exit__(self,*args):self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)


class TaskEpisode:
    def __init__(self,case):
        self.case=case;self.state={};self.submissions=[];self.sites=[];self.navigation=[];self.violations=[];self.origins=set();self.active=0;self.wiki_evidence=[]
    def __enter__(self):
        self.browser=BrowserSession().__enter__();self.pages=[self.browser.page]
        try:
            f=self.case['family']
            if f=='booking':
                self.booking=ChallengeEnv(max_steps=40);self.booking.reset(self.case['seed'],self.case['options']);self.browser.set_env(self.booking)
                self.origins.add(urlparse(self.browser.url).netloc)
            elif f=='wiki':
                self.page.goto('https://en.wikipedia.org/wiki/'+self.case['start'],wait_until='domcontentloaded',timeout=30000)
                if article(self.page.url)!=self.case['start']:raise RuntimeError('Wikipedia start page mismatch')
                self.save_wiki_evidence()
            else:
                kinds=['answer'] if f=='math' else ['source']+(['policy'] if self.case['level']=='hard' else [])+['answer']
                for i,kind in enumerate(kinds):
                    site=LocalSite(self,kind).__enter__();self.sites.append(site);self.origins.add(urlparse(site.url).netloc)
                    page=self.pages[0] if i==0 else self.browser.context.new_page()
                    if i:self.pages.append(page)
                    page.goto(site.url,wait_until='domcontentloaded',timeout=10000)
                self.active=0;self.pages[0].bring_to_front()
            return self
        except BaseException:self.__exit__(None,None,None);raise
    @property
    def page(self):return self.pages[self.active]
    def tabs(self):return [dict(index=i,title=p.title(),url=p.url) for i,p in enumerate(self.pages)]
    def screenshot(self):return self.page.screenshot(animations='disabled')
    def save_wiki_evidence(self):
        self.wiki_evidence.append(dict(url=self.page.url,title=self.page.title(),retrieved_unix=time.time(),html_sha256=hashlib.sha256(self.page.content().encode()).hexdigest()))
    def execute(self,action):
        a=action['action'];f=self.case['family'];before=self.page.url
        if a=='done':
            if f=='booking' and not(self.booking.audit()['finished'] or self.booking.audit()['truncated']):self.booking.step('FINISH')
            return 'done'
        if a=='switch_tab':
            i=action['tab']
            if not 0<=i<len(self.pages):raise ValueError('Unknown tab')
            self.active=i;self.page.bring_to_front();return 'executed'
        if a=='type':
            if f=='wiki':self.violations.append('typing/search prohibited');raise ValueError('Typing is not permitted for hyperlink navigation')
            self.page.keyboard.insert_text(action['text'])
        elif a=='key':
            if f=='wiki' and action['text']!='escape':raise ValueError('Only Escape is permitted in hyperlink tasks')
            import platform
            keys={'enter':'Enter','tab':'Tab','escape':'Escape','backspace':'Backspace','select_all':'Meta+A' if platform.system()=='Darwin' else 'Control+A'}
            self.page.keyboard.press(keys[action['text']])
        elif a=='scroll':self.page.mouse.wheel(0,action['y'])
        elif a=='wait':
            if f=='booking' and not(self.booking.audit()['finished'] or self.booking.audit()['truncated']):
                self.page.locator('button[data-action="WAIT"]').click();self.browser.wait_ready()
            else:self.page.wait_for_timeout(400)
        elif a=='click':
            size=self.page.viewport_size;x=action['x']*size['width']/1000;y=action['y']*size['height']/1000
            href=None
            if f=='wiki':
                # Executor-side rule check, never returned as a DOM observation to the model.
                href=self.page.evaluate('([x,y])=>{const e=document.elementFromPoint(x,y);const a=e&&e.closest("a");return a?a.href:null}',[x,y])
                if href and article(href) is None:
                    self.violations.append('non-article link');raise ValueError('Only Wikipedia article links are allowed')
            self.page.mouse.click(x,y)
            self.page.wait_for_timeout(250)
            try:self.page.wait_for_load_state('domcontentloaded',timeout=10000)
            except Exception:pass
            if f=='booking':self.browser.wait_ready()
            if f=='wiki' and article(self.page.url)!=article(before):
                if not href or article(href)!=article(self.page.url):
                    self.violations.append('unverified article transition')
                self.navigation.append(dict(source=article(before),target=article(self.page.url),clicked_href=href))
                self.save_wiki_evidence()
        else:raise ValueError('Unknown action')
        return 'executed'
    def grade(self):
        if self.case['family']=='booking':
            a=self.booking.audit();r=evaluate_audit(a)
            return dict(success=bool(r['strict_success']),checks={k:bool(v) if k=='strict_success' else v for k,v in r.items()},audit=a)
        return evaluate(self.case,self.state,self.page.url,self.navigation,self.violations)
    def __exit__(self,*args):
        try:
            if hasattr(self,'browser'):self.browser.__exit__(*args)
        finally:
            for site in reversed(self.sites):site.__exit__(*args)


def reference_interaction(e):
    """Privileged solvability proof, not an agent or performance baseline."""
    from .tasks import solve24,quote_totals
    from .challenge import ChallengeRule
    c=e.case;f=c['family']
    if f=='booking':
        policy=ChallengeRule('fresh')
        while not(e.booking.audit()['finished'] or e.booking.audit()['truncated']):
            action=policy.act(e.browser.public_observation());e.page.locator(f'button[data-action="{action}"]').click();e.browser.wait_ready()
    elif f=='wiki':
        for target in c['witness'][1:]:
            before=e.page.url
            # Select by real link target, not direct URL navigation.
            links=e.page.locator('#mw-content-text a')
            index=links.evaluate_all('(els,target)=>els.findIndex(e=>{try{return decodeURIComponent(new URL(e.href).pathname)==="/wiki/"+target}catch{return false}})',target)
            if index<0:raise RuntimeError('Broken Wikipedia witness: '+str(target))
            locator=links.nth(index);href=locator.get_attribute('href');locator.click(timeout=15000)
            e.page.wait_for_load_state('domcontentloaded',timeout=15000)
            e.navigation.append(dict(source=article(before),target=article(e.page.url),clicked_href=href))
            if article(e.page.url)!=target:raise RuntimeError('Witness redirect mismatch')
    elif f=='math':
        e.page.locator('#expression').fill(solve24(c['numbers']));e.page.get_by_role('button',name='Check expression').click()
        e.page.wait_for_function('document.getElementById("notice").textContent.includes("Correct")')
    elif f=='email':
        e.active=len(e.pages)-1;e.page.bring_to_front()
        e.page.locator('#to').fill(c['recipient']);e.page.locator('#subject').fill(c['event']+' — '+c['date'])
        e.page.locator('#body').fill(f'Please attend {c["event"]} on {c["date"]} at {c["time"]} in {c["venue"]}.')
        e.page.get_by_role('button',name='Save draft').click();e.page.wait_for_function('document.getElementById("notice").textContent==="Draft saved."')
    else:
        e.active=len(e.pages)-1;e.page.bring_to_front();totals=quote_totals(c);vendor=min(totals,key=totals.get)
        e.page.locator('#vendor').fill(vendor);e.page.locator('#total').fill(f'{totals[vendor]/100:.2f}')
        e.page.get_by_role('button',name='Save comparison').click();e.page.wait_for_function('document.getElementById("notice").textContent==="Comparison saved."')
    result=e.grade()
    if not result['success']:raise AssertionError('Reference interaction did not satisfy task predicate: '+json.dumps(result))
    return result
