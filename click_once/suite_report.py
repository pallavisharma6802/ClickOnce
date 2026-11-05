"""Publish screenshot evidence without merging infrastructure errors into agent accuracy."""
import argparse,html,json
from pathlib import Path
from .tasks import FAMILIES
INFRA={'infrastructure_error','setup_or_browser_error','interrupted'}
def load_results(root):
    rows={r['id']:r for r in json.loads((root/'results.json').read_text())} if (root/'results.json').exists() else {}
    for p in root.glob('*/result.json'):
        r=json.loads(p.read_text());rows[r['id']]=r
    return list(rows.values())

def aggregate(rows):
    result={}
    for family in FAMILIES:
        cases=[r for r in rows if r['family']==family];infra=sum(r['end_condition'] in INFRA for r in cases)
        result[family]=dict(attempted=len(cases),scorable=len(cases)-infra,passed=sum(bool(r['success']) for r in cases),infrastructure=infra)
    return result
STYLE='body{font:17px system-ui;max-width:1150px;margin:40px auto;padding:0 24px;color:#183047}table{border-collapse:collapse;width:100%}td,th{padding:12px;text-align:left;border-bottom:1px solid #ccd5df}img{max-width:100%;border:1px solid #ccc}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eff3f7;padding:16px}a{color:#115eb0}.note{background:#fff5dc;padding:20px}'
def publish(experiment,output):
    root=Path(experiment);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    cases=json.loads((root/'catalog-private.json').read_text());rows=load_results(root)
    stats=aggregate(rows);esc=html.escape
    lines=['# Five-family screenshot-agent pilot','',f'{len(rows)} of {len(cases)} planned cases have a recorded outcome. One actual frozen-Qwen attempt per case; no RL or VLM training in this suite.','',
      'Math, booking, email and offer sites are local benchmark applications on separate origins. Wikipedia navigation uses the live external site. Email is a synthetic local saved draft, not Gmail.','',
      '| Family | Passed / scorable | Infrastructure | Attempted / planned |','|---|---|---|---|']
    for f,s in stats.items():lines.append(f"| {f} | {s['passed']} / {s['scorable']} | {s['infrastructure']} | {s['attempted']} / 6 |")
    status=json.loads((root/'run-status.json').read_text()) if (root/'run-status.json').exists() else {}
    if status.get('stop_reason'):lines+=['', '**Run stopped:** '+status['stop_reason'], '']
    lines+=['','Infrastructure errors and interrupted runs cannot establish model capability. Budget exhaustion, malformed actions and premature completion are agent failures. Thirty curated cases are a pilot, not a general reliability estimate. Difficulty labels are authored bands, not calibrated human difficulty.','', '## Per-case evidence','', '| Case | Outcome | End condition | Actions |','|---|---|---|---|']
    table=[]
    for r in rows:
        cid=r['id'];episode=root/cid;dest=out/cid;dest.mkdir(exist_ok=True)
        import shutil
        for image in episode.glob('*.png'):shutil.copy2(image,dest/image.name)
        trace=[json.loads(x) for x in (episode/'trace.jsonl').read_text().splitlines()] if (episode/'trace.jsonl').exists() else []
        details=['<h1>'+esc(cid)+'</h1><p><a href="../index.html">All outcomes</a></p>']
        public=json.loads((episode/'task-public.json').read_text());details+=['<p>'+esc(public['instruction'])+'</p>','<pre>'+esc(json.dumps(r,indent=2))+'</pre>']
        for step in trace:
            details+=['<h2>Step '+str(step['step'])+'</h2><img src="'+step['image']+'"><pre>'+esc(json.dumps(step,indent=2))+'</pre>']
        for error in episode.glob('*-error.json'):details+=['<h2>Execution error</h2><pre>'+esc(error.read_text())+'</pre>']
        if (dest/'final.png').exists():details+=['<h2>Final screenshot</h2><img src="final.png">']
        if (episode/'evaluator-private.json').exists():details+=['<details><summary>Evaluator-only saved artifact</summary><pre>'+esc((episode/'evaluator-private.json').read_text())+'</pre></details>']
        (dest/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>'+esc(cid)+'</title><style>'+STYLE+'</style>'+''.join(details))
        label='PASS' if r['success'] else ('INFRASTRUCTURE' if r['end_condition'] in INFRA else 'FAIL')
        lines.append(f"| [{cid}]({cid}/index.html) | {label} | {r['end_condition']} | {r['actions']} |")
        table.append('<tr><td><a href="'+cid+'/index.html">'+esc(cid)+'</a></td><td>'+label+'</td><td>'+esc(r['end_condition'])+'</td><td>'+str(r['actions'])+'</td></tr>')
    lines+=['','## Interpretation','', 'Inspect recorded actions and independent checks before assigning a cause. Any failure labels derived from traces are analyst candidates, not human ground truth. No unsuccessful result is automatically a near miss. The historical tabular RL study is reported separately in ../evaluation/REPORT.md.','', 'Reproduce after Ollama has qwen3-vl:2b-instruct installed:','', '```sh','uv run python -m click_once.suite_eval validate --output runs/new-validation','uv run python -m click_once.suite_eval run --output runs/new-suite','uv run python -m click_once.suite_report --experiment runs/new-suite --output reports/new-suite','```']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n');(out/'summary.json').write_text(json.dumps(dict(planned=len(cases),recorded=len(rows),families=stats),indent=2))
    summary=''.join('<tr><td>'+f+'</td><td>'+str(s['passed'])+' / '+str(s['scorable'])+'</td><td>'+str(s['infrastructure'])+'</td><td>'+str(s['attempted'])+' / 6</td></tr>' for f,s in stats.items())
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>ClickOnce browser suite</title><style>'+STYLE+'</style><h1>Five families. Independent checks.</h1><p>Frozen local Qwen screenshot agent. 30 planned cases. No VLM training.</p><p class="note">Local math, booking, draft-only email and vendor sites; live Wikipedia. Infrastructure failures do not establish model capability. Historical engineered-state RL scores are separate.</p><table><tr><th>Family</th><th>Passed / scorable</th><th>Infrastructure</th><th>Attempted / planned</th></tr>'+summary+'</table><p class="note">'+esc(status.get('stop_reason',''))+'</p><h2>Recorded attempts</h2><table><tr><th>Case</th><th>Outcome</th><th>End condition</th><th>Actions</th></tr>'+''.join(table)+'</table><p><a href="REPORT.md">Full report</a> · <a href="../evaluation/index.html">Tabular evaluation audit</a></p>')
    return stats
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--experiment',required=True);p.add_argument('--output',required=True);a=p.parse_args();publish(a.experiment,a.output)
