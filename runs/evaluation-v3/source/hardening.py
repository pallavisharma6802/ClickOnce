"""New V2 protocol: compound uncertainty and representation ablations."""
import argparse
import csv
import json
import random
import time
from pathlib import Path
from .challenge import ChallengeEnv,ChallengeRule,make_cases,TIERS
from .env import ACTIONS
from .learning import QLearner,Baseline
from .evaluator import evaluate_audit
from .experiment import aggregate,digest
from .resources import ResourceGuard

class EvidenceLearner(QLearner):
    def __init__(self,*args,freshness=True,**kwargs):
        super().__init__(*args,**kwargs);self.freshness=freshness
    def state(self,o):
        if set(o)!={'goal','page','notice','rows','buttons','history_meta'}:raise ValueError('Public V2 schema required')
        rows=[r for r in o['rows'] if r['target']==o['goal']]
        meta=o['history_meta']
        fresh=meta['as_of_tick']>=meta['last_submit_tick'] if self.freshness else 'omitted'
        return json.dumps([o['notice'],o['page'],min(2,sum(r['status']=='confirmed' for r in rows)),
            min(2,sum(r['status']=='pending' for r in rows)),fresh,self.last_action,self.seen_pending],separators=(',',':'))
    def save(self,path):
        super().save(path);data=json.loads(Path(path).read_text());data['freshness']=self.freshness
        Path(path).write_text(json.dumps(data,sort_keys=True))
    @classmethod
    def load(cls,path):
        d=json.loads(Path(path).read_text());obj=cls(**{k:d[k] for k in ('alpha','gamma','seed','memory','freshness')});obj.q=d['q'];return obj

class V1Adapter:
    def __init__(self,policy):self.policy=policy
    def reset(self):self.policy.reset()
    def act(self,observation):return self.policy.act({k:v for k,v in observation.items() if k!='history_meta'})

def train_v2(seed,freshness,cases,episodes=10000):
    policy=EvidenceLearner(seed=seed,freshness=freshness);rng=random.Random(seed+991)
    env=ChallengeEnv();steps=0;curve=[];wins=[]
    for ep in range(episodes):
        case=cases[rng.randrange(len(cases))];o,_=env.reset(case['seed'],case);policy.reset();ret=0
        eps=max(.04,.8*(1-ep/max(1,episodes*.85)))
        while True:
            state=policy.state(o)
            a=rng.randrange(4) if rng.random()<eps else max(range(4),key=lambda x:policy.values(state)[x])
            policy.remember(o,a)
            nxt,r,t,tr,_=env.step(ACTIONS[a]);steps+=1;ret+=r
            policy.update(state,a,r,policy.state(nxt),t,tr);o=nxt
            if t or tr:break
        wins.append(evaluate_audit(env.audit())['strict_success'])
        if (ep+1)%100==0:curve.append(dict(episode=ep+1,strict_success=sum(wins[-100:])/100,environment_steps=steps))
    return policy,curve,steps

def rollout_v2(policy,case):
    env=ChallengeEnv();o,_=env.reset(case['seed'],case);policy.reset();checks=0;ret=0;trace=[]
    while True:
        a=policy.act(o);nxt,r,t,tr,_=env.step(a);checks+=a=='CHECK_HISTORY';ret+=r
        trace.append(dict(observation=o,action=a,next_observation=nxt));o=nxt
        if t or tr:break
    audit=env.audit();evaluation=evaluate_audit(audit)
    return dict(**case,**evaluation,steps=audit['steps'],checks=checks,return_value=ret,
                proxy_exploit=int(audit['finished'] and o['notice']=='Success' and not evaluation['strict_success'])),trace,audit

def run(output,episodes=10000):
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    manifest={s:make_cases(s,500 if s=='train' else 200) for s in ('train','validation','test')}
    for split,m in manifest.items():(out/f'{split}_manifest.json').write_text(json.dumps(m,indent=2))
    config=dict(version='challenge-v2',episodes=episodes,seeds=[11,22,33],max_steps=24,alpha=.15,gamma=.95,
                observation='engineered target matching and visible history freshness, not VLM training',
                selection='All configurations fixed before validation/test; no checkpoint selection')
    (out/'config.json').write_text(json.dumps(config,indent=2))
    policies={};curves=[];provenance=[];start=time.monotonic()
    for freshness in (False,True):
        for seed in (11,22,33):
            name=f'{"freshness" if freshness else "target_only"}_{seed}'
            q,c,steps=train_v2(seed,freshness,manifest['train'],episodes)
            checkpoint=out/f'{name}.json';q.save(checkpoint);policies[name]=EvidenceLearner.load(checkpoint)
            curves.extend(dict(policy=name,**r) for r in c)
            provenance.append(dict(policy=name,seed=seed,environment_steps=steps,checkpoint_sha256=digest(checkpoint)))
            print('Trained',name,steps,'steps',flush=True)
    # Frozen v1 checkpoint is the first seed, never selected for v2 success.
    policies.update(v1_learned=V1Adapter(QLearner.load(Path(__file__).resolve().parents[1]/'runs/experiment-v2/q_strict_memory_11.json')),
                    v1_rule=V1Adapter(Baseline('verify')),target_rule=ChallengeRule('target'),fresh_rule=ChallengeRule('fresh'))
    results=[];summary={}
    for split in ('validation','test'):
        for name,policy in policies.items():
            rs=[]
            for case in manifest[split]:
                r,trace,audit=rollout_v2(policy,case);r.update(policy=name,split=split);rs.append(r)
                if split=='test':
                    with (out/'episodes-private.jsonl').open('a') as f:f.write(json.dumps(dict(policy=name,seed=case['seed'],trace=trace,audit=audit))+'\n')
            results.extend(rs);summary[f'{split}/{name}']=dict(overall=aggregate(rs),by_tier={t:aggregate([r for r in rs if r['tier']==t]) for t in TIERS})
    with (out/'episodes.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
    (out/'summary.json').write_text(json.dumps(summary,indent=2));(out/'curves.json').write_text(json.dumps(curves))
    (out/'provenance.json').write_text(json.dumps(provenance,indent=2));(out/'runtime.json').write_text(json.dumps({'seconds':time.monotonic()-start}))
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--episodes',type=int,default=10000);a=p.parse_args()
    with ResourceGuard(a.output+'-resources'):s=run(a.output,a.episodes)
    print(json.dumps({k:v['overall'] for k,v in s.items() if k.startswith('test/')},indent=2))
