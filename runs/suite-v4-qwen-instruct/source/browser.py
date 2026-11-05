"""Loopback-only web UI. Routes expose public UI, never reward or audit."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import threading
from .env import ACTIONS

class BrowserSession:
    def __init__(self,headless=True):self.headless=headless;self.env=None;self.layout=0
    def __enter__(self):
        from playwright.sync_api import sync_playwright
        outer=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def send(self,code,body,content_type='application/json'):
                raw=body.encode();self.send_response(code);self.send_header('Content-Type',content_type)
                self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)))
                self.end_headers();self.wfile.write(raw)
            def do_GET(self):
                if self.path=='/':self.send(200,Path(__file__).with_name('web.html').read_text(),'text/html; charset=utf-8')
                elif self.path=='/api/state' and outer.env:self.send(200,json.dumps(outer.public_payload()))
                else:self.send(404,'{}')
            def do_POST(self):
                if self.path!='/api/action' or outer.env is None:self.send(404,'{}');return
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if length>1000:raise ValueError('Too large')
                    body=json.loads(self.rfile.read(length))
                    if set(body)!={'action'}:raise ValueError('Invalid fields')
                    outer.env.step(body['action'])
                    self.send(200,json.dumps(outer.public_payload()))
                except (ValueError,RuntimeError,KeyError):self.send(400,'{"error":"Invalid action or episode ended"}')
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        self.pw=sync_playwright().start()
        try:
            # Installed Chrome avoids another large browser download.
            chrome=Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
            options={'executable_path':str(chrome)} if chrome.exists() else {}
            self.browser=self.pw.chromium.launch(headless=self.headless,**options)
            self.context=self.browser.new_context(viewport={'width':1120,'height':820},device_scale_factor=1,
                                                  reduced_motion='reduce')
            self.page=self.context.new_page()
            return self
        except BaseException:
            self.__exit__(None,None,None);raise
    def public_payload(self):
        return dict(observation=self.env.observe(),ended=self.env._finished or self.env._truncated)
    def set_env(self,env):
        self.env=env;self.page.goto(self.url);self.wait_ready()
    def wait_ready(self):self.page.wait_for_function('window.ready===true',timeout=10000)
    def public_observation(self):
        self.wait_ready()
        # Same serialized visible projection that the page renders. No audit.
        return self.page.evaluate('window.publicObservation')
    def execute(self,action):
        if action not in ACTIONS:raise ValueError('Not an allowlisted action')
        button=self.page.locator(f'button[data-action="{action}"]')
        button.click();self.wait_ready()
    def screenshot(self):
        self.wait_ready();return self.page.screenshot(animations='disabled')
    def __exit__(self,*args):
        if hasattr(self,'context'):self.context.close()
        if hasattr(self,'browser'):self.browser.close()
        if hasattr(self,'pw'):self.pw.stop()
        if hasattr(self,'server'):self.server.shutdown();self.server.server_close()
        if hasattr(self,'thread'):self.thread.join(timeout=3)
