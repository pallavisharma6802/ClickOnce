"""V2 compound uncertainty. V1 observations/rewards/results remain unchanged."""
from copy import deepcopy
import random
from .env import ClickOnceEnv,ACTIONS

TIERS=('clean','repeated','distractors','stale','combined')

def make_cases(split,count):
    starts={'train':100000,'validation':200000,'test':300000}
    if split not in starts or count<5 or count%5:raise ValueError('Valid split and balanced count required')
    rng=random.Random(873);seeds=list(range(starts[split],starts[split]+(10000 if split=='train' else 1000)))
    if count>len(seeds):raise ValueError('Too many cases')
    rng.shuffle(seeds);rows=[]
    for i,seed in enumerate(seeds[:count]):
        r=random.Random(seed);tier=TIERS[i%5]
        rows.append(dict(seed=seed,tier=tier,failures=r.randint(1,3) if tier in ('repeated','combined') else 0,
            distractors=r.randint(1,3) if tier in ('distractors','combined') else 0,
            lag=r.randint(1,3) if tier in ('stale','combined') else 0,
            pending=r.choice([False,True]),delay=r.randint(2,5)))
    return rows


class ChallengeEnv(ClickOnceEnv):
    def __init__(self,reward_mode='strict',max_steps=24):super().__init__(reward_mode,max_steps)
    def reset(self,seed=None,options=None):
        opts=options or {};self.failures=opts.get('failures',0);self.lag=opts.get('lag',0)
        self.pending=opts.get('pending',False);self.distractors=opts.get('distractors',0)
        if not 0<=self.failures<=3 or not 0<=self.lag<=3 or not 0<=self.distractors<=3:raise ValueError('Invalid V2 bounds')
        self._asof=self._last_submit=0
        super().reset(seed,dict(scenario='normal',delay=opts.get('delay',3)))
        self._initial_records=[dict(id=f'OLD{i}',target=self._goal+f' / different request {i}',status='confirmed',due=0) for i in range(self.distractors)]
        self._records=deepcopy(self._initial_records);self._snapshots={0:deepcopy(self._records)}
        return self.observe(),{}
    def _submission_fault(self):
        if self._attempts<=self.failures:return 'false_success' if self._attempts%2==0 else 'failed_timeout'
        return 'pending_timeout' if self.pending else 'committed_timeout'
    def observe(self):
        o=super().observe();o['history_meta']=dict(as_of_tick=self._asof,current_tick=self._steps,last_submit_tick=self._last_submit)
        return o
    def step(self,action):
        _,r,t,tr,info=super().step(action)
        if action=='SUBMIT':self._last_submit=self._steps
        self._snapshots[self._steps]=deepcopy(self._records)
        if action=='CHECK_HISTORY':
            self._asof=max(0,self._steps-self.lag)
            self._rows=[{k:r[k] for k in ('id','target','status')} for r in self._snapshots[self._asof]]
        return self.observe(),r,t,tr,info
    def audit(self):
        a=super().audit();target=[r for r in self._records if r['target']==self._goal]
        a.update(confirmed_count=sum(r['status']=='confirmed' for r in target),
                 pending_count=sum(r['status']=='pending' for r in target),duplicate_count=max(0,len(target)-1),
                 initial_records=deepcopy(getattr(self,'_initial_records',[])))
        a['strict_success']=bool(self._finished and a['confirmed_count']==1 and a['pending_count']==0 and a['duplicate_count']==0)
        return a


class ChallengeRule:
    def __init__(self,mode='fresh'):self.mode=mode
    def reset(self):pass
    def act(self,o):
        if o['history_meta']['last_submit_tick']==0:return 'SUBMIT'
        if o['page']!='history':return 'CHECK_HISTORY'
        if self.mode=='fresh' and o['history_meta']['as_of_tick']<o['history_meta']['last_submit_tick']:return 'CHECK_HISTORY'
        rows=[r for r in o['rows'] if r['target']==o['goal']]
        if any(r['status']=='pending' for r in rows):return 'CHECK_HISTORY'
        return 'FINISH' if rows else 'SUBMIT'
