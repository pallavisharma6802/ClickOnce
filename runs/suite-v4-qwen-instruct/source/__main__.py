import argparse
import json
from pathlib import Path
from .resources import ResourceGuard


def main():
    p=argparse.ArgumentParser(description='ClickOnce local RL environment and experiments')
    sub=p.add_subparsers(dest='command',required=True)
    t=sub.add_parser('train');t.add_argument('--output',required=True);t.add_argument('--episodes',type=int,default=10000);t.add_argument('--eval-count',type=int,default=200)
    d=sub.add_parser('demo');d.add_argument('--output',required=True);d.add_argument('--scenario',default='committed_timeout');d.add_argument('--policy',default='verify');d.add_argument('--checkpoint');d.add_argument('--vision',action='store_true')
    v=sub.add_parser('vision');v.add_argument('--output',required=True)
    r=sub.add_parser('report');r.add_argument('--experiment',required=True);r.add_argument('--output',default='reports')
    s=sub.add_parser('serve');s.add_argument('--scenario',default='committed_timeout')
    args=p.parse_args()
    if args.command=='train':
        from .experiment import run_experiment
        # run_experiment owns its output directory; guard lives beside it.
        with ResourceGuard(str(args.output)+'-resources'):
            result=run_experiment(args.output,args.episodes,args.eval_count)
        print(json.dumps({k:v['overall'] for k,v in result.items() if k.startswith('test/')},indent=2))
    elif args.command=='demo':
        from .demo import record
        with ResourceGuard(Path(args.output)/'resources'):
            result=record(args.output,args.scenario,args.policy,args.checkpoint,args.vision)
        print(json.dumps(result['final_audit'],indent=2))
    elif args.command=='vision':
        from .perception import evaluate_perception
        with ResourceGuard(Path(args.output)/'resources'):
            print(json.dumps(evaluate_perception(args.output),indent=2))
    elif args.command=='report':
        from .reporting import build_report
        with ResourceGuard('runs/report-resources'):
            build_report(args.experiment,args.output)
        print(str(Path(args.output).resolve()/'index.html'))
    elif args.command=='serve':
        from .browser import BrowserSession
        from .env import ClickOnceEnv
        with ResourceGuard('runs/interactive-resources'),BrowserSession(headless=False) as browser:
            env=ClickOnceEnv();env.reset(seed=17,options={'scenario':args.scenario});browser.set_env(env)
            print(browser.url,flush=True)
            print('Interactive synthetic environment. Ctrl+C stops browser and server.',flush=True)
            try:
                while True:browser.page.wait_for_timeout(1000)
            except KeyboardInterrupt:pass

if __name__=='__main__':main()
