"""Dataset generation, reward-driven training, paired independent evaluation."""
import csv
import hashlib
import json
import random
import statistics
import time
from pathlib import Path
from .env import ClickOnceEnv, SCENARIOS, ACTIONS
from .learning import QLearner, Baseline
from .evaluator import evaluate_audit

RANGES = {'train':(0,10000), 'validation':(10000,11000), 'test':(20000,21000)}


def make_manifest(split, count):
    if split not in RANGES: raise ValueError('Unknown split')
    lo, hi = RANGES[split]
    if not 0 < count <= hi-lo: raise ValueError('Invalid split count')
    seeds = list(range(lo,hi))
    random.Random(83).shuffle(seeds)
    return [dict(seed=seed, scenario=SCENARIOS[i%5], delay=random.Random(seed+731).randint(2,4))
            for i,seed in enumerate(seeds[:count])]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def train(seed, mode, episodes, manifest, memory=True):
    policy = QLearner(seed=seed, memory=memory)
    rng = random.Random(seed+991)
    curve, returns, successes, steps = [], [], [], 0
    env = ClickOnceEnv(mode)
    for episode in range(episodes):
        case = manifest[rng.randrange(len(manifest))]
        obs,_ = env.reset(seed=case['seed'], options=case)
        policy.reset()
        total = 0
        epsilon = max(0.04, 0.8*(1-episode/max(1,episodes*0.85)))
        while True:
            state = policy.state(obs)
            if rng.random() < epsilon: action = rng.randrange(4)
            else: action = max(range(4), key=lambda a: policy.values(state)[a])
            policy.remember(obs, action)
            nxt, reward, term, trunc, _ = env.step(ACTIONS[action])
            policy.update(state, action, reward, policy.state(nxt), term, trunc)
            total += reward; steps += 1; obs = nxt
            if term or trunc: break
        returns.append(total); successes.append(env.audit()['strict_success'])
        if (episode+1)%100 == 0:
            curve.append(dict(episode=episode+1, environment_steps=steps,
                              return_mean=statistics.mean(returns[-100:]),
                              strict_success_mean=statistics.mean(successes[-100:]),epsilon=epsilon))
    return policy, curve, steps


def rollout(policy, case, mode='strict', trace=False):
    env = ClickOnceEnv(mode)
    obs,_ = env.reset(seed=case['seed'],options=case)
    policy.reset()
    rows, total, checks = [],0,0
    while True:
        action = policy.act(obs)
        nxt,reward,term,trunc,_ = env.step(action)
        if trace: rows.append(dict(observation=obs, action=action, reward=reward, next_observation=nxt))
        total += reward; checks += action == 'CHECK_HISTORY'; obs = nxt
        if term or trunc: break
    audit = env.audit()
    # Evaluation uses independent outcomes and a common counterfactual proxy signal,
    # never the training arm's reward as an agent observation.
    evaluated = evaluate_audit(audit)
    result = dict(**case, **evaluated, steps=audit['steps'], checks=checks,
                  return_value=total,
                  proxy_exploit=int(audit['finished'] and obs['notice']=='Success' and not evaluated['strict_success']))
    return result, rows, audit


def aggregate(rows):
    keys = ('strict_success','duplicate','false_completion','truncated','steps','checks','return_value','proxy_exploit')
    return {k:statistics.mean(r[k] for r in rows) for k in keys} | {'episodes':len(rows)}


def run_experiment(output, episodes=10000, eval_count=200, seeds=(11,22,33)):
    if episodes < 100 or eval_count < 5 or eval_count % 5:
        raise ValueError('At least 100 training episodes; eval count must be a positive multiple of five')
    output = Path(output); output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    manifests={s:make_manifest(s, 1000 if s=='train' else eval_count) for s in RANGES}
    for split, manifest in manifests.items():
        (output/f'{split}_manifest.json').write_text(json.dumps(manifest,indent=2))
    config=dict(episodes=episodes,eval_count=eval_count,seeds=list(seeds),alpha=.15,gamma=.95,
                learner='tabular finite-memory Q-learning',observation='public structured UI, not pixels',
                heldout_status='validation evaluated before locked test; no automatic hyperparameter selection')
    (output/'config.json').write_text(json.dumps(config,indent=2))
    policies={}; curves=[]; provenance=[]
    for memory in (False,True):
        for mode in ('strict','ui_proxy'):
            for seed in seeds:
                name=f'q_{mode}_{"memory" if memory else "memoryless"}_{seed}'
                learner, curve, steps=train(seed,mode,episodes,manifests['train'],memory)
                checkpoint=output/f'{name}.json';learner.save(checkpoint)
                policies[name]=QLearner.load(checkpoint)
                curves += [dict(policy=name,**row) for row in curve]
                provenance.append(dict(policy=name,training_reward=mode,training_seed=seed,
                                       environment_steps=steps,checkpoint_sha256=digest(checkpoint)))
                print(f'Trained {name}: {steps} steps',flush=True)
    policies |= {name:Baseline(name,seed=71) for name in ('random','naive','verify')}
    policies['untrained']=QLearner(seed=71)
    summaries={}; all_rows=[]
    for split in ('validation','test','stress'):
        manifest=manifests['test'] if split=='stress' else manifests[split]
        if split=='stress': manifest=[dict(c,delay=6+c['seed']%3) for c in manifest]
        for name, policy in policies.items():
            results=[]
            for case in manifest:
                result,trace,audit=rollout(policy,case,trace=split=='test')
                result.update(policy=name,split=split);results.append(result)
                if split=='test':
                    # One JSONL line per episode; private audit is segregated.
                    with (output/'traces.jsonl').open('a') as f:
                        f.write(json.dumps(dict(policy=name,seed=case['seed'],trace=trace))+'\n')
                    with (output/'audits-private.jsonl').open('a') as f:
                        f.write(json.dumps(dict(policy=name,seed=case['seed'],audit=audit))+'\n')
            all_rows+=results
            summaries[f'{split}/{name}']=dict(overall=aggregate(results),
                by_scenario={s:aggregate([r for r in results if r['scenario']==s]) for s in SCENARIOS})
    with (output/'episodes.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(all_rows[0]));w.writeheader();w.writerows(all_rows)
    (output/'learning_curves.json').write_text(json.dumps(curves))
    (output/'provenance.json').write_text(json.dumps(provenance,indent=2))
    (output/'summary.json').write_text(json.dumps(summaries,indent=2))
    (output/'runtime.json').write_text(json.dumps(dict(wall_seconds=time.monotonic()-started)))
    return summaries
