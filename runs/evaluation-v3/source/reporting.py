"""Evidence-based report and offline results/replay viewer."""
import csv
import html
import json
import statistics
from pathlib import Path

LABELS={'q_strict_memory':'Outcome reward + memory','q_strict_memoryless':'Outcome reward, no memory',
        'q_ui_proxy_memory':'UI reward + memory','q_ui_proxy_memoryless':'UI reward, no memory',
        'naive':'Retry / trust success baseline','verify':'Scripted verification (not learned)',
        'random':'Random baseline','untrained':'Untrained Q policy'}


def group_name(name):
    return name.rsplit('_',1)[0] if name.startswith('q_') else name


def summarize_groups(rows):
    grouped={}
    for r in rows:grouped.setdefault(group_name(r['policy']),{}).setdefault(r['policy'],[]).append(r)
    result={}
    for name,seeds in grouped.items():
        values={p:statistics.mean(float(r['strict_success']) for r in rs) for p,rs in seeds.items()}
        mean=lambda k:statistics.mean(statistics.mean(float(r[k]) for r in rs) for rs in seeds.values())
        result[name]=dict(label=LABELS[name],success_mean=statistics.mean(values.values()),
                         seed_success={p.rsplit('_',1)[-1] if p.startswith('q_') else p:v for p,v in values.items()},
                         seed_std=statistics.stdev(values.values()) if len(values)>1 else 0,
                         duplicate=mean('duplicate'),proxy_exploit=mean('proxy_exploit'),steps=mean('steps'))
    return result


def build_report(experiment,output,project=None):
    experiment=Path(experiment);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    project=Path(project or Path.cwd())
    rows=list(csv.DictReader((experiment/'episodes.csv').open()))
    groups={split:summarize_groups([r for r in rows if r['split']==split]) for split in ('validation','test','stress')}
    config=json.loads((experiment/'config.json').read_text())
    runtime=json.loads((experiment/'runtime.json').read_text())
    provenance=json.loads((experiment/'provenance.json').read_text())
    vision_path=project/'runs/vision-v2/gate.json'
    vision=json.loads(vision_path.read_text()) if vision_path.exists() else {'passed':False,'status':'not completed'}
    visual_demo_path=project/'runs/demo-vision-pending/trace.json'
    visual_demo=json.loads(visual_demo_path.read_text()) if visual_demo_path.exists() else None
    visual_result=visual_demo['final_audit'] if visual_demo else None
    data=dict(groups=groups,config=config,runtime=runtime,vision=vision,visual_demo=visual_result,
              total_training_episodes=config['episodes']*len(provenance),
              total_training_steps=sum(p['environment_steps'] for p in provenance),
              evaluation_rows=len(rows),interpretation='Structured-observation RL, not VLM fine-tuning')
    (out/'analysis.json').write_text(json.dumps(data,indent=2))
    md=['# ClickOnce: ambiguous outcomes and reward exploitation','',
        'A controlled local browser environment and CPU RL study. All bookings are synthetic. This is not an OSWorld result or a claim of a novel algorithm.','',
        '## Experiment','',
        f'{data["total_training_episodes"]:,} training episodes, {data["total_training_steps"]:,} environment steps, three seeds (11/22/33), two reward designs, and memory/no-memory ablations. Each frozen policy sees the same 200 held-out test worlds. Validation and test seeds are disjoint from training. Stress evaluation reuses test identities with pending delays increased to 6–8 ticks. No post-test hyperparameter selection.','',
        f'CPU experiment wall time: {runtime["wall_seconds"]:.2f} seconds, excluding browser replays, VLM inference and plotting. The tabular policy receives structured public UI observations. It does not learn from pixels.','',
        '## Held-out outcomes','',
        '| Policy | Strict success | Individual training seeds | Duplicate episodes | Proxy-positive / true failure | Mean actions |',
        '|---|---:|---|---:|---:|---:|']
    for name,g in groups['test'].items():
        seedvals=', '.join(f'{s}: {v:.0%}' for s,v in g['seed_success'].items())
        md.append(f'| {g["label"]} | {g["success_mean"]:.1%} | {seedvals} | {g["duplicate"]:.1%} | {g["proxy_exploit"]:.1%} | {g["steps"]:.2f} |')
    md += ['', '## What this supports','',
        '- On this small environment, outcome reward with finite action memory learned successful behavior across all three runs. UI-proxy training produced fast behavior that accepted false success or created duplicates. This is operational proxy exploitation, not evidence of deliberate cheating.',
        '- The scripted verification baseline also succeeds. Learned behavior is not superior to a hand-coded solution here; the result is about reward design and learning stability.',
        '- Memoryless training is unstable: seeds 11 and 22 succeed, while seed 33 succeeds only on committed/pending timeouts and fails the other three scenarios. Do not hide this behind the mean.',
        '- Observation aliasing is verified at both JSON and screenshot levels: failed, committed and pending submissions display the same timeout before inspection.',
        '- Strict evaluation is recomputed independently from private record identity/status. It ignores the environment reward flag and reported count fields.',
        '', '## Visual model gate','',json.dumps(vision,indent=2),
        '', 'The optional visual bridge uses the installed frozen Qwen3-VL 2B model. It extracts visible status/page/row counts from actual browser screenshots. Neither VLM weights nor a VLM adapter were trained. Its 20-frame check is a small engineering smoke set; labels were visually reviewed but are not an independent large benchmark.',
        '', 'The recorded screenshot-driven pending-timeout episode completed in six actions: one submission, four history checks, and Finish. The evaluator found one confirmed booking and no duplicates. It used four fresh VLM calls and two cached observations; this is one smoke episode, not a visual-agent success-rate estimate.' if visual_result and visual_result['strict_success'] else 'No successful visual-control episode is claimed.',
        '', '## Limitations','',
        '- One synthetic booking application, four bounded actions, five fault types. The first submission alone is faulty; later submissions succeed. This makes the task substantially easier than real web interaction.',
        '- Task identities differ across splits, but the learned state abstraction ignores identity and layout. Held-out success measures control under new seeds/delays, not semantic or visual generalization.',
        '- The memory policy adds previous-action and observed-pending indicators. No recurrent neural network, full VLM RL or large model training is claimed.',
        '- The weak proxy is deliberately misspecified. The observed exploitation gap cannot estimate its frequency in deployed agents.',
        '- Action-driven simulation removes wall-clock races. Stress tests change delays, not the task family. UI layout robustness remains unmeasured.',
        '- Reward arms have equal episode budgets, not equal transition counts; both counts are retained. A transition-matched study is future work.',
        '- Three training seeds and a balanced 200-instance synthetic test suite support a bounded demonstration, not broad statistical claims. Per-seed values are reported instead of an inflated significance claim.',
        '- The evaluator boundary is a software interface, not a hardened security sandbox. Browser routes exclude private data, but trusted in-process experiment code can access it.',
        '', '## Reproduce','',
        'See README.md for installation, full tests, training, live browser and replay commands. Primary results are in runs/experiment-v2; experiment-v1 and vision-v1 are retained as development attempts. See docs/DECISIONS.md for corrections.','']
    (out/'REPORT.md').write_text('\n'.join(md))
    plot(experiment,out,groups)
    # Pre-recorded, actual browser trajectories; no policy simulation in the viewer.
    replay={}
    for label,folder in [('Naive retry → duplicate','demo-naive'),('Learned outcome policy','demo-learned'),('Learned UI reward → false success','demo-proxy'),('Memoryless seed 33 → failure','demo-memoryless-failure-normal'),('Frozen Qwen + learned policy','demo-vision-pending')]:
        src=project/'runs'/folder/'trace.json'
        if src.exists():
            d=json.loads(src.read_text())
            cp=Path(d['checkpoint']) if d.get('checkpoint') else None
            if cp is not None:
                cp=cp if cp.is_absolute() else project/cp
                if cp.resolve().parent != experiment.resolve():continue
            for f in d['frames']:f['image']='../runs/'+folder+'/'+f['frame']
            replay[label]=d
    payload=json.dumps(dict(**data,replays=replay)).replace('</','<\\/')
    template=Path(__file__).with_name('dashboard.html').read_text()
    (out/'index.html').write_text(template.replace('/*DATA*/',payload))
    return data


def plot(experiment,out,groups):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'figure.facecolor':'#10151b','axes.facecolor':'#19222c','text.color':'#e8edf3',
                         'axes.labelcolor':'#b5c5d4','xtick.color':'#b5c5d4','ytick.color':'#b5c5d4',
                         'axes.edgecolor':'#3c4d60','font.size':10})
    names=list(groups['test']);values=[groups['test'][n]['success_mean']*100 for n in names]
    fig,ax=plt.subplots(figsize=(10,5.5));ax.barh([LABELS[n] for n in names],values,color=['#83dfba' if 'strict' in n or n=='verify' else '#f2ad8c' for n in names])
    ax.set_xlim(0,110);ax.set_xlabel(f'Strict task success (%) · {json.loads((experiment/"config.json").read_text())["eval_count"]} paired test worlds per policy')
    ax.invert_yaxis()
    for i,n in enumerate(names):
        for v in groups['test'][n]['seed_success'].values():ax.plot(v*100,i,'o',color='#18282b',markersize=5)
        ax.text(values[i]+1,i,f'{values[i]:.1f}%',va='center',fontsize=9)
    ax.set_title('Reward design changes what the agent learns',loc='left',pad=16)
    fig.tight_layout();fig.savefig(out/'outcomes.png',dpi=160);plt.close(fig)
    curves=json.loads((experiment/'learning_curves.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for name in sorted(set(r['policy'] for r in curves)):
        rs=[r for r in curves if r['policy']==name]
        color='#83dfba' if 'q_strict_' in name else '#f2ad8c'
        style='-' if '_memory_' in name else '--'
        axes[0].plot([r['episode'] for r in rs],[r['strict_success_mean'] for r in rs],style,color=color,alpha=.55)
        axes[1].plot([r['episode'] for r in rs],[r['return_mean'] for r in rs],style,color=color,alpha=.55)
    axes[0].set_title('Actual success during exploration');axes[1].set_title('Training return (different objectives)')
    for ax in axes:ax.set_xlabel('Training episode');ax.set_ylim(-.15,1.05)
    fig.text(.08,.005,'Green: outcome reward · Orange: UI reward · Solid: memory · Dashed: no memory · Each line is one training seed',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(out/'learning.png',dpi=160);plt.close(fig)
