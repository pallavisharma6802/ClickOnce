"""Summarize all V2 seeds and tiers without changing experiment outputs."""
import json,statistics,csv,argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from click_once.evaluator import evaluate_audit
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--experiment',type=Path,default=root/'runs/challenge-v2');p.add_argument('--output',type=Path,default=root/'reports/v2');args=p.parse_args()
base=args.experiment;out=args.output;out.mkdir(parents=True,exist_ok=True)
s=json.loads((base/'summary.json').read_text());config=json.loads((base/'config.json').read_text())
names=[k.split('/',1)[1] for k in s if k.startswith('test/')]
rows=list(csv.DictReader((base/'episodes.csv').open()));indexed={(r['policy'],int(r['seed'])):r for r in rows if r['split']=='test'}
for line in (base/'episodes-private.jsonl').read_text().splitlines():
 r=json.loads(line);actual=evaluate_audit(r['audit']);logged=indexed[r['policy'],r['seed']]
 for key,value in actual.items():assert int(logged[key])==value
md=['# ClickOnce V2: why the first benchmark was too easy','','The V1 result is retained as a unit-scale learnability demonstration. V2 adds repeated failures, unrelated bookings and visibly stale history. No target failure percentage was used. Configurations were frozen before new test evaluation.','','## Held-out outcomes','','| Policy | Overall | Clean | Repeated faults | Distractors | Stale history | Combined |','|---|---:|---:|---:|---:|---:|---:|']
for n in names:
 d=s['test/'+n];vals=[d['overall']['strict_success']]+[v['strict_success'] for v in d['by_tier'].values()]
 md.append('| '+n+' | '+' | '.join(f'{v:.1%}' for v in vals)+' |')
fresh=[s['test/freshness_'+str(seed)]['overall']['strict_success'] for seed in [11,22,33]]
blind=[s['test/target_only_'+str(seed)]['overall']['strict_success'] for seed in [11,22,33]]
md+=['','## Interpretation','',f'The frozen V1 learned policy transfers at {s["test/v1_learned"]["overall"]["strict_success"]:.1%}, down from 100% on V1. That is an environment/representation limitation, not a regression in the preserved checkpoint.',f'Target-aware RL without freshness: mean {statistics.mean(blind):.1%}; seeds '+', '.join(f'{v:.1%}' for v in blind)+'.',f'Freshness-aware RL: mean {statistics.mean(fresh):.1%}; seeds '+', '.join(f'{v:.1%}' for v in fresh)+'. Seed 11 remains imperfect; it is not replaced by the best seed.','The difference is an ablation of engineered visible freshness features under the same training budget; it is not proof of a new architecture or general visual reasoning.','The freshness-aware scripted baseline is still 100%. The environment has a valid, publicly observable solution. The study identifies missing evidence handling, not superiority over scripting.','','## Protocol and limits','','Three seeds, 10000 training episodes per arm, 200 paired test cases (40 per tier). New disjoint seed ranges; train/validation/test all sample the specified tier generator. New seeds are not held-out app templates or composition-OOD generalization.','V2 still uses bounded semantic actions and engineered target equality/freshness features. No V2 VLM training or pixel-control result is claimed. The frozen visual-model smoke test in V1 does not establish V2 perception accuracy.','Training reward is outcome-based in both ablation arms. Raw counts, private audits, checkpoints and validation results are preserved. Wrong-target additions and alteration/removal of unrelated initial records fail independent evaluation.','','## Reproduce','','`uv run python -m click_once.hardening --output runs/new-v2 --episodes 10000`','`uv run --extra report python scripts/report_v2.py`','','See docs/V2_PROTOCOL.md for the frozen design.']
(out/'REPORT.md').write_text('\n'.join(md))
fig,ax=plt.subplots(figsize=(11,5));vals=[s['test/'+n]['overall']['strict_success']*100 for n in names]
ax.barh(names,vals,color=['#3b9f7c' if n.startswith('freshness') else '#e5a47f' for n in names]);ax.invert_yaxis();ax.set_xlim(0,110);ax.set_xlabel('Strict success on 200 paired V2 worlds (%)');ax.set_title('V2 exposes limits hidden by the first environment')
for i,v in enumerate(vals):ax.text(v+1,i,f'{v:.1f}%',va='center')
fig.tight_layout();fig.savefig(out/'outcomes.png',dpi=150);plt.close(fig)
trs=''.join('<tr><td>'+n+'</td><td>'+f'{s["test/"+n]["overall"]["strict_success"]:.1%}'+'</td>'+''.join('<td>'+f'{d["strict_success"]:.1%}'+'</td>' for d in s['test/'+n]['by_tier'].values())+'</tr>' for n in names)
links=''.join(f'<li><a href="../../runs/challenge-v2/demo-{n}/index.html">Actual browser replay: {n}</a></li>' for n in ['target_only_11','freshness_11'])
(out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>ClickOnce V2</title><style>body{max-width:1150px;margin:50px auto;background:#10151b;color:#e6edf4;font:16px system-ui;padding:20px}h1{font-size:38px;letter-spacing:-1px}p{color:#b0c1d0;line-height:1.7}table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:12px 6px;border-bottom:1px solid #354555;text-align:left}a{color:#8fe8c4}img{width:100%;background:white;border-radius:10px;margin-top:30px}</style><h1>ClickOnce V2: from clicking to checking evidence.</h1><p>The old learned policy drops from 100% to 46% on compound challenges. Target-aware RL without freshness reaches 71.5%; adding visible freshness reaches 95.3% on average, with an imperfect seed retained. This is a structured-state control experiment, not VLM fine-tuning.</p><table><tr><th>Policy / seed</th><th>Overall</th><th>Clean</th><th>Repeated</th><th>Distractors</th><th>Stale</th><th>Combined</th></tr>'+trs+'</table><p>The scripted freshness-aware rule still solves every case. Lowering scores alone is not the goal: identifying the missing information and measuring its effect is.</p><ul>'+links+'</ul><a href="REPORT.md">Full report and limitations</a> · <a href="../index.html">Original V1 study</a><img src="outcomes.png" alt="Per-seed V2 outcome comparison">')
(out/'summary.json').write_text(json.dumps(s,indent=2));print('Independently checked',len(indexed),'new held-out outcomes; report:',out/'index.html')
