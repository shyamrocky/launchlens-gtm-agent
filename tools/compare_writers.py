#!/usr/bin/env python3
"""Nebius-only comparison CLI. Default preflight is offline; no keys/network.

Future --execute requires separately reviewed authorization, token qualifications,
current prices, credentials and a new fixed protected directory. No source refresh.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
for name in ['src','tools']:sys.path.insert(0,str(ROOT/name))
from launchlens.writer_comparison import assemble,load_config,plan,run,Reservation,ComparisonError,REGISTERED_MODELS,HERMES_CONFIG
from launchlens.writer_providers import ProviderHTTP,read_provider_keys
from launchlens.live_research import strict_json
from validate_linkedin_writer import verified_inputs

OUTPUT=ROOT/'data/generated/m23b-nebius-writer-comparison-v1'
HERMES_OUTPUT=ROOT/'data/generated/m23b-nebius-hermes-writer-v1'


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--source-state',type=Path,required=True)
    parser.add_argument('--profile',choices=['baseline','hermes'],default='baseline')
    parser.add_argument('--mode',choices=['single','comparison'],default='single')
    parser.add_argument('--select',nargs='+',choices=sorted(REGISTERED_MODELS))
    parser.add_argument('--authorization',type=Path)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args(argv)
    if args.profile=='hermes' and (args.mode!='single' or args.select not in (None,['hermes'])):
        raise ComparisonError('Hermes preparation permits one selected Writer only')
    config=load_config(HERMES_CONFIG) if args.profile=='hermes' else load_config()
    output=HERMES_OUTPUT if args.profile=='hermes' else OUTPUT
    original=verified_inputs(args.input,args.source_state)
    bundle=assemble(original)  # Exactly once per invocation, never once per provider.
    if not args.execute:
        result=run(bundle,config,mode=args.mode,selected=args.select)
        print(json.dumps(result,indent=2));return result
    if output.exists():raise ComparisonError('Comparison directory consumed; new owner authorization required')
    if args.authorization is None:raise ComparisonError('Separate owner authorization required')
    require_path=args.authorization
    if require_path.stat().st_mode&0o077:raise ComparisonError('Authorization file must be private')
    approval=strict_json(require_path.read_bytes());prepared=plan(bundle,config,mode=args.mode,selected=args.select)
    Reservation().reserve(prepared,approval)  # Fail before credentials if permissions/pricing/bounds unresolved.
    models=[entry['model'] for entry in prepared['entries']]
    keys=read_provider_keys(models,ROOT/'.env')
    # Prevent accidental credential inclusion in task/authorization. Never print values.
    strings=json.dumps({'bundle':bundle,'approval':approval})
    if any(value in strings for value in keys.values()):raise ComparisonError('Credential present in execution data')
    result=run(bundle,config,mode=args.mode,selected=args.select,execute=True,approval=approval,
        transport_kind='live',transport_factory=lambda m:ProviderHTTP(m,keys['NEBIUS_API_KEY']),output=output)
    print('Protected comparison:',output)
    print(json.dumps({'status':result['status'],'models':[r['key'] for r in result['results']]},indent=2))
    return result


if __name__=='__main__':
    try:main()
    except Exception:
        raise SystemExit('Comparison blocked or unavailable. No automatic retry; inspect protected artifacts if a run was claimed.') from None
