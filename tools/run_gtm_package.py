"""Prepare/execute one explicitly authorized full GTM package; default is offline.

No inference permission is embedded. An owner-created private authorization and a
whole-run reservation are required. No retries, automatic repairs or Git changes.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from launchlens.live_package import AUTHORIZATION,authorization_template,create_live_run,preflight


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorization-template',action='store_true')
    parser.add_argument('--authorization',type=Path,default=AUTHORIZATION)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if args.authorization_template:
        if args.execute:raise ValueError('Template mode cannot execute')
        print(json.dumps(authorization_template(),indent=2));return
    plan=preflight()
    if not args.execute:print(json.dumps(plan,indent=2));return
    run=create_live_run(plan['request'],authorization_path=args.authorization)
    state=run.execute(run.snapshot()['run_id'])
    print(json.dumps({'status':state['status'],'formats':list(state['drafts']),
        'review_status':state['review'].get('review_status'),'human_accepted':state['human_accepted'],
        'publishing_allowed':False,'spending':run.guard.summary()},indent=2))
    print('Protected results:',run.store.path)


if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('Live package blocked/stopped. Inspect protected records; no automatic retry.') from None
