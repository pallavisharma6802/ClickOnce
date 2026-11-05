"""Preregistered finite-grid evaluation; separates cell census from seed uncertainty."""
import argparse,csv,hashlib,json,random,statistics,time
from pathlib import Path
from .challenge import ChallengeEnv,ChallengeRule
from .hardening import EvidenceLearner,V1Adapter
from .learning import QLearner,Baseline
from .env import ACTIONS
from .reference import ReferenceWorld,assert_transition
from .resources import ResourceGuard

SEEDS=list(range(101,111))

def control_key(c):return (c['failures'],c['lag'],bool(c['pending']),c['delay'] if c['pending'] else 0)

def grid(part):
    if part not in ('domain','composition','timing'):raise ValueError('Unknown partition')
    cases=[]
    for f in range(4):
        for lag in range(4):
            if part=='domain' and f>0 and lag>0:continue
            if part=='composition' and not(f>0 and lag>0):continue
            completion=[(True,d) for d in range(6,11)] if part=='timing' else [(False,2)]+[(True,d) for d in range(2,6)]
            for pending,delay in completion:
                i=len(cases);case_id=f'{part}-f{f}-l{lag}-'+('p'+str(delay) if pending else 'direct')
                cases.append(dict(case_id=case_id,seed={'domain':410000,'composition':510000,'timing':610000}[part]+i,
                                  failures=f,lag=lag,pending=pending,delay=delay,distractors=1))
    return cases

def seed_interval(values,resamples=10000):
    values=list(values);rng=random.Random(901)
    samples=sorted(statistics.mean(rng.choices(values,k=len(values))) for _ in range(resamples))
    return dict(mean=statistics.mean(values),std=statistics.stdev(values) if len(values)>1 else 0,
                minimum=min(values),maximum=max(values),low=samples[int(.025*resamples)],high=samples[min(resamples-1,int(.975*resamples))],n_training_seeds=len(values))

def paired_summary(without,with_fresh):
    ds=[b-a for a,b in zip(without,with_fresh)]
    return dict(difference=seed_interval(ds),wins=sum(d>1e-12 for d in ds),losses=sum(d< -1e-12 for d in ds),ties=sum(abs(d)<=1e-12 for d in ds))

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def fit(seed,freshness,cases,budget,path,learner_class=EvidenceLearner):
    policy=learner_class(seed=seed,freshness=freshness);choice_rng=random.Random(seed+881);explore_rng=random.Random(seed+991)
    env=ChallengeEnv(max_steps=40);steps=0;episode=0;curve=[];returns=[];wins=[]
    while steps<budget:
        case=cases[choice_rng.randrange(len(cases))]
        presentation=dict(case,seed=710000+choice_rng.randrange(1000000))
        o,_=env.reset(presentation['seed'],presentation);policy.reset();ret=0
        while steps<budget:
            state=policy.state(o);eps=max(.04,.8*(1-steps/max(1,budget*.85)))
            coin=explore_rng.random();proposal=explore_rng.randrange(4) # Fixed RNG consumption even on greedy actions.
            action=proposal if coin<eps else max(range(4),key=lambda a:policy.values(state)[a])
            policy.remember(o,action);nxt,r,t,tr,_=env.step(ACTIONS[action]);steps+=1;ret+=r
            policy.update(state,action,r,policy.state(nxt),t,tr);o=nxt
            if steps in (20000,50000,budget):
                policy.save(path/f'checkpoint-{steps}.json')
                curve.append(dict(steps=steps,completed_episodes=episode,last_100_success=statistics.mean(wins[-100:]) if wins else None))
            if t or tr:break
        if t or tr:
            episode+=1;wins.append(env.audit()['strict_success']);returns.append(ret)
    return policy,dict(seed=seed,freshness=freshness,steps=steps,completed_episodes=episode,curve=curve)

def assess(policy,case):
    e=ChallengeEnv(max_steps=40);o,_=e.reset(case['seed'],case);reference=ReferenceWorld(case,o['goal'],40)
    if o!=reference.observe():raise AssertionError('Reset disagrees with independent interpreter')
    policy.reset();trace=[];ret=0;checks=0
    while True:
        a=policy.act(o);actual=e.step(a);expected=reference.step(a);assert_transition(actual,expected)
        nxt,r,t,tr,_=actual;trace.append(dict(observation=o,action=a,reward=r));ret+=r;checks+=a=='CHECK_HISTORY';o=nxt
        if t or tr:break
    from .evaluator import evaluate_audit
    outcome=reference.outcome()
    if outcome!=evaluate_audit(e.audit()):raise AssertionError('Independent terminal evaluator disagrees')
    row=dict(case_id=case['case_id'],**outcome,steps=len(trace),checks=checks,return_value=ret,
             action_fingerprint=hashlib.sha256(json.dumps([x['action'] for x in trace]).encode()).hexdigest())
    return row,trace

def legacy_audit(root):
    p=root/'runs/challenge-v2';man={s:json.loads((p/f'{s}_manifest.json').read_text()) for s in ('train','validation','test')}
    sets={s:{control_key(c) for c in cases} for s,cases in man.items()}
    rows=list(csv.DictReader((p/'episodes.csv').open()));paired=[]
    first={r['seed']:r for r in rows if r['split']=='test' and r['policy']=='target_only_11'}
    for seed in (22,33):
        other={r['seed']:r for r in rows if r['split']=='test' and r['policy']==f'target_only_{seed}'}
        paired.append(dict(seed=seed,outcome_agreement=sum(first[k]['strict_success']==other[k]['strict_success'] for k in first),different_action_counts=sum(first[k]['steps']!=other[k]['steps'] for k in first),cases=len(first)))
    return dict(episode_counts={s:len(v) for s,v in man.items()},unique_control_cells={s:len(v) for s,v in sets.items()},test_cells_seen_in_train=len(sets['test']&sets['train']),seed_comparison=paired,
                checkpoint_sha256={str(s):sha(p/f'target_only_{s}.json') for s in (11,22,33)})

def run(output,budget=100000):
    if budget<1000:raise ValueError('Budget must be at least 1000 transitions')
    root=Path(__file__).resolve().parents[1];out=Path(output);out.mkdir(parents=True,exist_ok=False)
    protocol=root/'docs/EVALUATION_V3.md'
    config=dict(version='evaluation-repair-v3',training_seeds=SEEDS,transitions_per_seed_per_arm=budget,max_steps=40,
                alpha=.15,gamma=.95,selection='fixed final checkpoint',protocol_sha256=sha(protocol),
                source_sha256={f.name:sha(f) for f in (root/'click_once').glob('*.py')},observation='engineered public UI state; one booking task family; no VLM training')
    (out/'config.json').write_text(json.dumps(config,indent=2));(out/'protocol.md').write_text(protocol.read_text())
    (out/'legacy_audit.json').write_text(json.dumps(legacy_audit(root),indent=2))
    cases={part:grid(part) for part in ('domain','composition','timing')}
    for part,cs in cases.items():(out/f'{part}_manifest.json').write_text(json.dumps(cs,indent=2))
    # Solvability is checked without using learned results.
    for cs in cases.values():
        for case in cs:
            row,_=assess(ChallengeRule('fresh'),case)
            if not row['strict_success']:raise AssertionError('Unsolvable reference case '+case['case_id'])
    trained={};training=[];start=time.monotonic()
    for freshness in (False,True):
        for seed in SEEDS:
            name=f'{"freshness" if freshness else "target_only"}_{seed}';folder=out/name;folder.mkdir()
            p,info=fit(seed,freshness,cases['domain'],budget,folder);checkpoint=folder/f'checkpoint-{budget}.json'
            info.update(policy=name,checkpoint_sha256=sha(checkpoint));training.append(info)
            trained[name]=EvidenceLearner.load(checkpoint)
            print('Trained',name,info['steps'],'transitions',flush=True)
    (out/'training.json').write_text(json.dumps(training,indent=2))
    # All models are frozen before either new holdout partition is assessed.
    (out/'FROZEN.json').write_text(json.dumps({n:sha(out/n/f'checkpoint-{budget}.json') for n in trained},indent=2))
    baselines=dict(target_rule=ChallengeRule('target'),fresh_rule=ChallengeRule('fresh'),
                   naive=V1Adapter(Baseline('naive')),random=V1Adapter(Baseline('random',seed=32)),
                   frozen_v2_target=EvidenceLearner.load(root/'runs/challenge-v2/target_only_11.json'),
                   frozen_v2_fresh=EvidenceLearner.load(root/'runs/challenge-v2/freshness_11.json'))
    all_rows=[];summary={}
    with (out/'traces.jsonl').open('w') as tracefile:
        for part,cs in cases.items():
            for name,policy in (trained|baselines).items():
                rs=[]
                for case in cs:
                    row,trace=assess(policy,case);row.update(partition=part,policy=name);rs.append(row)
                    tracefile.write(json.dumps(dict(partition=part,policy=name,case=case,steps=trace,outcome={k:row[k] for k in ('strict_success','duplicate','false_completion','truncated')}))+'\n')
                all_rows+=rs
                summary[part+'/'+name]={k:statistics.mean(r[k] for r in rs) for k in ('strict_success','duplicate','false_completion','truncated','steps','checks','return_value')}
                summary[part+'/'+name]['failed_cells']=[r['case_id'] for r in rs if not r['strict_success']]
    with (out/'episodes.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(all_rows[0]));w.writeheader();w.writerows(all_rows)
    inference={}
    for part in cases:
        a=[summary[f'{part}/target_only_{seed}']['strict_success'] for seed in SEEDS]
        b=[summary[f'{part}/freshness_{seed}']['strict_success'] for seed in SEEDS]
        inference[part]=dict(target_only=seed_interval(a),freshness=seed_interval(b),paired=paired_summary(a,b))
    (out/'summary.json').write_text(json.dumps(summary,indent=2));(out/'statistics.json').write_text(json.dumps(inference,indent=2))
    (out/'runtime.json').write_text(json.dumps(dict(seconds=time.monotonic()-start,total_transitions=sum(r['steps'] for r in training))))
    print(json.dumps(inference,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--budget',type=int,default=100000);a=p.parse_args()
    with ResourceGuard(a.output+'-resources'):run(a.output,a.budget)
