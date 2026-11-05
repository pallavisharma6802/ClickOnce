"""Independent evaluator-side transition model; no environment/model imports.

This interpreter uses the public goal plus the evaluator's case specification.
Neither the case specification nor this interpreter is passed to an agent.
"""
from copy import deepcopy

BUTTONS=['SUBMIT','CHECK_HISTORY','WAIT','FINISH']
class ReferenceWorld:
    def __init__(self,case,goal,limit=40):
        self.case=case;self.goal=goal;self.limit=limit
        self.tick=self.attempts=self.last_submit=self.asof=0
        self.ended=self.cut=False;self.notice='Ready';self.page='booking';self.rows=[]
        self.initial=[dict(id=f'OLD{i}',target=goal+f' / different request {i}',status='confirmed',due=0) for i in range(case['distractors'])]
        self.records=deepcopy(self.initial);self.snapshots={0:deepcopy(self.records)}
    def observe(self):
        return deepcopy(dict(goal=self.goal,page=self.page,notice=self.notice,rows=self.rows,buttons=BUTTONS,
            history_meta=dict(as_of_tick=self.asof,current_tick=self.tick,last_submit_tick=self.last_submit)))
    def outcome(self):
        target=[r for r in self.records if r['target']==self.goal]
        pending=sum(r['status']=='pending' for r in target)
        success=self.ended and not self.cut and len(target)==1 and target[0]['status']=='confirmed' and all(r in self.records for r in self.initial)
        return dict(strict_success=int(success),duplicate=int(len(target)>1),false_completion=int(self.ended and not success),truncated=int(self.cut))
    def step(self,action):
        if self.ended or self.cut:raise RuntimeError('Episode already ended')
        if action not in BUTTONS:raise ValueError('Unknown action')
        self.tick+=1
        for record in self.records:
            if record['status']=='pending' and record['due']<=self.tick:record['status']='confirmed'
        reward=-.01
        if action=='SUBMIT':
            self.attempts+=1;self.last_submit=self.tick
            failed=self.attempts<=self.case['failures']
            if not failed:
                pending=self.case['pending']
                self.records.append(dict(id=f'B{len(self.records)+1:03}',target=self.goal,status='pending' if pending else 'confirmed',due=self.tick+self.case['delay']))
                self.notice='Timeout'
            else:self.notice='Success' if self.attempts%2==0 else 'Timeout'
            self.page='booking';self.rows=[]
        elif action=='CHECK_HISTORY':self.page='history';self.notice='History refreshed'
        elif action=='FINISH':
            self.ended=True
            if self.outcome()['strict_success']:reward+=1
        self.cut=self.tick>=self.limit and not self.ended
        self.snapshots[self.tick]=deepcopy(self.records)
        if action=='CHECK_HISTORY':
            self.asof=max(0,self.tick-self.case['lag'])
            self.rows=[{k:r[k] for k in ('id','target','status')} for r in self.snapshots[self.asof]]
        return self.observe(),reward,self.ended,self.cut,{}

def assert_transition(actual,expected):
    if actual[0]!=expected[0]:raise AssertionError('Visible observation disagrees with independent transition model')
    if abs(actual[1]-expected[1])>1e-10:raise AssertionError('Reward disagrees with independent transition model')
    if actual[2:]!=expected[2:]:raise AssertionError('Episode flags or info disagree with independent transition model')
