#!/usr/bin/env python3
"""One separately authorized repair comparison; default is strictly offline.

The original execution directory stays protected. Fixed comparison output refuses
reruns; no new source, index or general integration. Baseline metrics are preserved
in the canonical M2.2a review, so runtime needs no historical ignored audit files.
"""
import argparse
import json
from pathlib import Path
from validate_live_research import ROOT, REQUEST, execute
from launchlens.live_research import MODEL, load_prompt, tool_schemas
from launchlens.gtm_registry import validate_request

OUTPUT = ROOT / 'data/generated/m22a-us-research-repair-v1'
BASELINE_INPUT_TOKENS = 188689
BASELINE_RECEIPT_SHA256 = '5ba04139473b2453929146770a41aac59880c1773be17b099dacfadebe37232d'


def run():
    execute(output=OUTPUT)
    receipt = json.loads((OUTPUT/'receipt.json').read_text())
    actual = receipt['usage']['prompt_tokens']
    comparison = {'baseline_input_tokens': BASELINE_INPUT_TOKENS,
        'baseline_receipt_sha256': BASELINE_RECEIPT_SHA256,
        'actual_input_tokens': actual,
        'reduction_percent': round(100*(BASELINE_INPUT_TOKENS-actual)/BASELINE_INPUT_TOKENS,2),
        'baseline_model_turns':5, 'actual_model_turns':len(receipt['model_http_events']),
        'note':'One observed comparison; model may choose different actions/queries. Not a controlled accuracy benchmark.'}
    (OUTPUT/'comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
    print(json.dumps(comparison,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if args.execute:run()
    else:
        load_prompt();validate_request(REQUEST)
        print(json.dumps({'status':'OFFLINE_PREFLIGHT_PASS','model':MODEL,
            'actions':len(tool_schemas()),'baseline_input_tokens':BASELINE_INPUT_TOKENS,
            'live_calls':0,'credentials_read':False},indent=2))
