"""Secondary control for the memory-capacity confound, explicitly post hoc."""
import argparse,hashlib,json,statistics,time
from pathlib import Path
from .evaluation import SEEDS,grid,fit,assess,sha,seed_interval
from .hardening import EvidenceLearner
from .resources import ResourceGuard

class ElapsedLearner(EvidenceLearner):
    def __init__(self,*args,**kwargs):
        kwargs['freshness']=False;super().__init__(*args,**kwargs)
    def reset(self):super().reset();self.action_age=12
    def state(self,o):
        return super().state(o)+'|own_action_age='+str(self.action_age)
    def remember(self,o,action):
        super().remember(o,action)
        self.action_age=0 if action==0 else min(12,self.action_age+1)

class ConservativeRule:
    def reset(self):self.started=False;self.age=0
    def act(self,o):
        # No history_meta read: maximum lag=3 is public task-contract knowledge.
        if not self.started:self.started=True;self.age=0;return 'SUBMIT'
        self.age+=1
        if o['page']!='history' or self.age<=3:return 'CHECK_HISTORY'
        rows=[r for r in o['rows'] if r['target']==o['goal']]
        if any(r['status']=='pending' for r in rows):return 'CHECK_HISTORY'
        if rows:return 'FINISH'
        self.age=0;return 'SUBMIT'

def run(out,budget=100000):
    root=Path(__file__).resolve().parents[1];out=Path(out);out.mkdir(parents=True,exist_ok=False)
    config=dict(training_seeds=SEEDS,budget=budget,post_hoc=True,protocol_sha256=sha(root/'docs/EVALUATION_V3_MEMORY_CONTROL.md'),
                observation='public target counts plus own action-age counter; history timestamps omitted',source_sha256={f.name:sha(f) for f in (root/'click_once').glob('*.py')})
    (out/'config.json').write_text(json.dumps(config,indent=2));start=time.monotonic();models={};training=[]
    for seed in SEEDS:
        name=f'elapsed_{seed}';folder=out/name;folder.mkdir()
        model,record=fit(seed,False,grid('domain'),budget,folder,learner_class=ElapsedLearner)
        # Reload subclass; checkpoint schema is shared, action_age resets each episode.
        model=ElapsedLearner.load(folder/f'checkpoint-{budget}.json');models[name]=model
        record['checkpoint_sha256']=sha(folder/f'checkpoint-{budget}.json');training.append(record)
        print('Trained',name,record['steps'],'transitions',flush=True)
    (out/'training.json').write_text(json.dumps(training,indent=2))
    (out/'FROZEN.json').write_text(json.dumps({n:sha(out/n/f'checkpoint-{budget}.json') for n in models},indent=2))
    models['conservative_rule']=ConservativeRule();summary={};rows=[]
    with (out/'traces.jsonl').open('w') as f:
        for part in ('domain','composition','timing'):
            cases=grid(part)
            for name,policy in models.items():
                rs=[]
                for case in cases:
                    row,trace=assess(policy,case);row.update(partition=part,policy=name);rs.append(row)
                    f.write(json.dumps(dict(partition=part,policy=name,case=case,steps=trace,outcome={k:row[k] for k in ('strict_success','duplicate','false_completion','truncated')}))+'\n')
                rows+=rs;summary[part+'/'+name]={k:statistics.mean(r[k] for r in rs) for k in ('strict_success','duplicate','false_completion','truncated','steps','checks','return_value')}
    import csv
    with (out/'episodes.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    (out/'statistics.json').write_text(json.dumps({p:seed_interval(summary[f'{p}/elapsed_{s}']['strict_success'] for s in SEEDS) for p in ('domain','composition','timing')},indent=2))
    (out/'runtime.json').write_text(json.dumps(dict(seconds=time.monotonic()-start,total_transitions=sum(r['steps'] for r in training))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--budget',type=int,default=100000);a=p.parse_args()
    with ResourceGuard(a.output+'-resources'):run(a.output,a.budget)
