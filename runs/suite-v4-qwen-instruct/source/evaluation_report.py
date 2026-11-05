"""Audit old scores and publish the controlled RL study without broad claims."""
import csv,gzip,hashlib,json,statistics
from collections import defaultdict
from pathlib import Path
from .reference import ReferenceWorld
from .evaluation import SEEDS,seed_interval
from .hardening import EvidenceLearner
from .memory_control import ElapsedLearner
from .env import ACTIONS


def load_rows(folder):return list(csv.DictReader((folder/'episodes.csv').open()))
def trace_lines(folder):
    raw=folder/'traces.jsonl';compressed=folder/'traces.jsonl.gz'
    with (gzip.open(compressed,'rt') if compressed.exists() else raw.open()) as f:yield from f

def publish(root=None):
    root=Path(root or Path.cwd());a=root/'runs/evaluation-v3';b=root/'runs/evaluation-v3-memory-control';out=root/'reports/evaluation';out.mkdir(parents=True,exist_ok=True)
    legacy=json.loads((a/'legacy_audit.json').read_text());primary=json.loads((a/'statistics.json').read_text());secondary=json.loads((b/'statistics.json').read_text())
    summaries=json.loads((a/'summary.json').read_text())|json.loads((b/'summary.json').read_text())
    rows=load_rows(a)+load_rows(b);lookup={(r['partition'],r['policy'],r['case_id']):r for r in rows}
    if len(lookup)!=len(rows):raise AssertionError('Duplicate evaluation episode IDs')
    configs=[json.loads((x/'config.json').read_text()) for x in (a,b)]
    models={};coverage=defaultdict(lambda:dict(steps=0,unseen_steps=0,episodes=0,unseen_episodes=0));verified=0
    for folder in (a,b):
        frozen=json.loads((folder/'FROZEN.json').read_text())
        for name,digest in frozen.items():
            checkpoint=folder/name/'checkpoint-100000.json'
            if hashlib.sha256(checkpoint.read_bytes()).hexdigest()!=digest:raise AssertionError('Frozen checkpoint changed')
            models[name]=(ElapsedLearner if name.startswith('elapsed_') else EvidenceLearner).load(checkpoint)
        for line in trace_lines(folder):
            rec=json.loads(line);key=(rec['partition'],rec['policy'],rec['case']['case_id']);row=lookup[key];trace=rec['steps']
            oracle=ReferenceWorld(rec['case'],trace[0]['observation']['goal'],40)
            policy=models.get(rec['policy']);unseen=False
            if policy:policy.reset()
            group=rec['policy'].rsplit('_',1)[0] if policy else rec['policy'];cov=coverage[rec['partition']+'/'+group]
            for step in trace:
                if step['observation']!=oracle.observe():raise AssertionError('Saved observation failed independent replay')
                expected=oracle.step(step['action'])
                if abs(expected[1]-step['reward'])>1e-10:raise AssertionError('Saved reward failed independent replay')
                if policy:
                    missing=policy.state(step['observation']) not in policy.q
                    cov['steps']+=1;cov['unseen_steps']+=missing;unseen|=missing
                    policy.remember(step['observation'],ACTIONS.index(step['action']))
            actual=oracle.outcome()
            for k,v in actual.items():
                if v!=int(row[k]) or v!=rec['outcome'][k]:raise AssertionError('Recorded score disagrees with independent replay')
            if policy:cov['episodes']+=1;cov['unseen_episodes']+=unseen
            verified+=1
    table=[]
    for part in ('domain','composition','timing'):
        for arm in ('target_only','freshness','elapsed'):
            metric=primary[part][arm] if arm!='elapsed' else secondary[part]
            per_seed=[summaries[f'{part}/{arm}_{s}']['strict_success'] for s in SEEDS]
            group_rows=[r for r in rows if r['partition']==part and r['policy'] in [f'{arm}_{s}' for s in SEEDS]]
            vectors=[];behaviors=[]
            for seed in SEEDS:
                rs=sorted([r for r in group_rows if r['policy']==f'{arm}_{seed}'],key=lambda r:r['case_id'])
                vectors.append(tuple(r['strict_success'] for r in rs));behaviors.append(tuple(r['action_fingerprint'] for r in rs))
            cov=coverage[part+'/'+arm]
            table.append(dict(partition=part,arm=arm,**metric,per_seed=per_seed,unique_outcome_vectors=len(set(vectors)),unique_behavior_vectors=len(set(behaviors)),
                unseen_episode_rate=cov['unseen_episodes']/cov['episodes'],unseen_step_rate=cov['unseen_steps']/cov['steps']))
    payload=dict(legacy_audit=legacy,statistics=table,independently_replayed_episodes=verified,coverage=coverage,
                 scope='one synthetic booking task family; engineered public-state RL, not Qwen task solving',post_hoc_arm='elapsed',
                 perfect_seed_probability_exact_lower_95=.025**.1)
    (out/'analysis.json').write_text(json.dumps(payload,indent=2))
    md=['# Evaluation audit and repair','','## What was wrong with the old evaluation','',
        f'The old 200 test worlds contained only {legacy["unique_control_cells"]["test"]} distinct control configurations; {legacy["test_cells_seen_in_train"]} were represented in training. Request IDs were not new problems for this policy. The repeated 71.5% values were not fabricated: model files differ, action counts differ, but the same cases pass/fail. The old tables were inadequate evidence of generalization.','',
        'The actual learned component is a small tabular policy. Those percentages were never Qwen solving real web tasks. The new five-family browser suite is a separate evaluation.','',
        '## Repaired protocol','',
        'Ten training seeds per arm, 100000 transitions each, fixed final checkpoint, 40 actions per episode. The primary two-arm study uses 2 million transitions. An explicitly post-hoc action-age-memory control adds 1 million transitions; no original seed is replaced.','',
        'Unique control-cell census: 35 familiar-domain cells, 45 unseen combinations of individually familiar failure/lag values, and 80 unfamiliar-delay cells. No renamed copies are counted as independent tasks. Training/composition/timing control keys are disjoint. This is still one task family.','',
        '## Results','',
        '| Partition | Policy | Mean success | Empirical 95% seed-bootstrap interval | Min–max across seeds |','|---|---|---:|---:|---:|']
    labels={'target_only':'Target-only, one-step memory','freshness':'Visible freshness, one-step memory','elapsed':'Own action-age memory, no freshness (post hoc)'}
    for r in table:md.append(f'| {r["partition"]} | {labels[r["arm"]]} | {r["mean"]:.1%} | {r["low"]:.1%}–{r["high"]:.1%} | {r["minimum"]:.1%}–{r["maximum"]:.1%} |')
    md+=['','## Interpretation and alternative explanations','',
        'Additional action-count memory recovers nearly all composition performance without reading freshness. Therefore the old freshness-versus-no-freshness comparison partly confounded information with memory capacity.','The action-age control fails on unfamiliar delays. Inspection of state coverage reports how often evaluation produces unseen tabular keys. Such failures can reflect support mismatch/default tie-breaking, not a VLM failing to reason about time.','The timestamp-free conservative scripted reference solves every cell by using the publicly specified maximum cache lag. Freshness metadata is not necessary for safe completion in this environment; it can reduce waiting/checking and simplify the learned state representation.','The freshness-aware policy remains perfect across these ten training seeds. We do not lower or perturb the score to make the project look harder. This is a ceiling for a small engineered-state problem. It is not evidence of general computer use.','',
        'The bootstrap intervals describe training-seed uncertainty conditional on this finite grid, not uncertainty across real websites. A degenerate 100%–100% bootstrap interval does not prove zero risk: even 10/10 perfect independent seed trials give only a 69.2% two-sided exact 95% lower bound on the probability of a perfect seed.','',
        f'All {verified} saved episodes were replayed through an independently implemented transition interpreter: every observation, reward and terminal outcome was checked. Mutation tests deliberately corrupt rewards/history and verify rejection. Hashes verify frozen checkpoints.','',
        '## Every seed, not three rounded copies','',
        '| Partition / arm | Seeds 101 through 110 | Unique outcome vectors | Unique action-sequence vectors | Episodes visiting unseen state keys |','|---|---|---:|---:|---:|']
    for r in table:md.append(f'| {r["partition"]} / {r["arm"]} | '+', '.join(f'{v:.1%}' for v in r['per_seed'])+f' | {r["unique_outcome_vectors"]} | {r["unique_behavior_vectors"]} | {r["unseen_episode_rate"]:.1%} |')
    md+=['','## What a larger task suite must add','','More scenario instances alone cannot supply task diversity. The separate browser suite adds math puzzles, actual Wikipedia hyperlink navigation, cross-page email drafting and constrained offer comparison. Those are actual Qwen screenshot evaluations, with separate task-specific checks. Do not pool their scores with this tabular study.','','## Reproduce','','```sh','uv run python -m click_once.evaluation --output runs/new-evaluation --budget 100000','uv run python -m click_once.memory_control --output runs/new-memory-control --budget 100000','```','','Primary artifacts: runs/evaluation-v3. Secondary artifacts: runs/evaluation-v3-memory-control. Frozen protocols: docs/EVALUATION_V3.md and docs/EVALUATION_V3_MEMORY_CONTROL.md. Full per-case outcomes and action traces remain available.']
    (out/'REPORT.md').write_text('\n'.join(md))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(14,4.5),sharey=True)
    for ax,part in zip(axes,('domain','composition','timing')):
        rs=[r for r in table if r['partition']==part]
        for i,r in enumerate(rs):
            ax.bar(i,100*r['mean'],color=['#d39a78','#4d9d85','#788fb8'][i],alpha=.8)
            ax.errorbar(i,100*r['mean'],yerr=[[max(0,100*(r['mean']-r['low']))],[max(0,100*(r['high']-r['mean']))]],fmt='none',color='black',capsize=4)
            for j,v in enumerate(r['per_seed']):ax.plot(i+(j-4.5)*.025,100*v,'.',color='black',markersize=4)
        ax.set_title(part);ax.set_xticks([0,1,2],['Target only','Freshness','Action age*'],rotation=20);ax.set_ylim(0,105)
    axes[0].set_ylabel('Strict success on unique control cells (%)');fig.suptitle('Conditional grid results, not general computer-use ability')
    fig.text(.05,.01,'Each dot is one training seed; intervals bootstrap the 10 seeds. *Action-age control was added post hoc.',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.94));fig.savefig(out/'outcomes.png',dpi=160);plt.close(fig)
    htmlrows=''.join(f'<tr><td>{r["partition"]}</td><td>{labels[r["arm"]]}</td><td>{r["mean"]:.1%}</td><td>{r["low"]:.1%}–{r["high"]:.1%}</td><td>{r["minimum"]:.1%}–{r["maximum"]:.1%}</td></tr>' for r in table)
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>ClickOnce evaluation audit</title><style>body{max-width:1150px;margin:45px auto;padding:20px;background:#10151b;color:#e5edf4;font:16px system-ui}p{line-height:1.7;color:#adbece}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:12px;border-bottom:1px solid #3d4e61;text-align:left}a{color:#8fe8c4}img{width:100%;margin-top:30px;border-radius:10px}</style><h1>The old evaluation was too narrow.</h1><p>200 nominal cases hid only 56 control configurations, 51 already represented in training. The repeated scores were real but did not establish generalization.</p><h2>Matched budgets, structural holdouts and independent checks</h2><p>10 training seeds per arm; 100000 transitions each. 35 domain cells, 45 unseen compositions, 80 unfamiliar-delay cells. The post-hoc action-age control tests the memory-capacity confound.</p><table><tr><th>Partition</th><th>Policy</th><th>Mean</th><th>Seed-bootstrap interval</th><th>Seed range</th></tr>'+htmlrows+'</table><p>The conservative timestamp-free rule also solves every cell. Freshness is not necessary here. The still-perfect freshness scores expose a ceiling of the engineered representation; they are not Qwen web-task results.</p><a href="REPORT.md">Full audit, every seed and limitations</a> · <a href="analysis.json">Machine-readable analysis</a><img src="outcomes.png" alt="All three representations across structural holdouts">')
    print('Independently verified',verified,'saved episodes. Report:',out/'index.html')

if __name__=='__main__':publish()
