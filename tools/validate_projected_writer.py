#!/usr/bin/env python3
"""One owner-authorized projected-context Writer experiment; default is offline.

Frozen source snapshots are explicit optional experiment inputs. The application
and tests do not require them. No controller/source calls, retries or repairs.
Existing baseline runner and default Writer behavior remain unchanged.
"""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import time
from uuid import uuid4
from zoneinfo import ZoneInfo

from validate_linkedin_writer import (ROOT, REQUEST, SOURCE_RUN, INPUT_SHA256,
    STATE_SHA256, verified_inputs, write_and_validate, render)
from validate_live_research import read_keys
from prepare_writer_context import baseline_identity
from launchlens.linkedin_drafting import LinkedInWriter, digest, writer_request
from launchlens.live_research import MODEL, PROMPTS, NebiusHTTP, dumps, strict_json
from launchlens.writer_context import project_writer_input

OUTPUT = ROOT/'data/generated/m23b-us-writer-only-projected-v1'
BASELINE_RECEIPT_SHA = 'd8f0c8169a245157eced0781c74886746409da95db4845a964a3958e04b18ecb'
PROJECTED_REQUEST_SHA = 'fa6c1d36f4b19f7fba5e2a48977a2e5397bdbe8f699e8380def87930eb8dfc05'


def verified_context(input_path, state_path, baseline_path):
    inputs = verified_inputs(input_path, state_path)
    raw = Path(baseline_path).read_bytes()
    if len(raw)>2_000_000 or hashlib.sha256(raw).hexdigest()!=BASELINE_RECEIPT_SHA:
        raise ValueError('Original comparison receipt differs; no call')
    _, baseline = baseline_identity(strict_json(raw), inputs)
    projection = project_writer_input(inputs)
    payload = writer_request(projection['model_input'])
    if hashlib.sha256(dumps(payload).encode()).hexdigest()!=PROJECTED_REQUEST_SHA:
        raise ValueError('Request differs from accepted offline projection; no call')
    original = writer_request(inputs)
    if any(payload[k]!=original[k] for k in original if k!='messages') or payload['messages'][0]!=original['messages'][0]:
        raise ValueError('Non-context provider configuration differs; no call')
    return inputs, baseline, projection, payload


class SingleCallCapture:
    """Claim the sole attempt before side effects; preserve full parsed response."""
    def __init__(self, transport, receipt, save):
        self.transport, self.receipt, self.save = transport, receipt, save
        self.attempted = False

    def __call__(self, payload):
        if self.attempted:
            raise ValueError('Single attempt already consumed')
        if hashlib.sha256(dumps(payload).encode()).hexdigest()!=PROJECTED_REQUEST_SHA:
            raise ValueError('Unexpected provider request; no call')
        self.attempted = True
        self.receipt['sole_attempt_claimed'] = True
        self.save()
        response = self.transport(payload)
        self.receipt['provider_response'] = deepcopy(response)
        self.save()
        return response


def execute(input_path, state_path, baseline_path):
    # Complete deterministic source/request checks before reading credentials.
    inputs, baseline, projection, payload = verified_context(input_path,state_path,baseline_path)
    OUTPUT.mkdir(parents=True,mode=0o700,exist_ok=False)  # Consumed even on failure.
    receipt = {'status':'IN_PROGRESS','experiment_id':str(uuid4()),'kind':'projected_context_writer_only',
        'source_run_id':SOURCE_RUN,'request':dict(REQUEST),'model':MODEL,'prompt_hashes':dict(PROMPTS),
        'started_local':datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(),
        'limits':{'model_calls':1,'writing_attempts':1,'output_tokens':2048},
        'source_input_sha256':INPUT_SHA256,'source_state_sha256':STATE_SHA256,
        'baseline_receipt_sha256':BASELINE_RECEIPT_SHA,'baseline':baseline,
        'input_sha256':digest(inputs),'projected_request_sha256':PROJECTED_REQUEST_SHA,
        'notion_calls':0,'pinecone_calls':0,'controller_calls':0,'automatic_retries':0,'automatic_repairs':0}
    def save():
        path=OUTPUT/'receipt.json'
        path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');path.chmod(0o600)
    save()
    path=OUTPUT/'provider-request.json'
    path.write_bytes(dumps(payload).encode());path.chmod(0o600)
    started=time.monotonic()
    try:
        keys=read_keys(ROOT/'.env')
        http=NebiusHTTP(keys['NEBIUS_API_KEY'],allow_linkedin=True,on_event=save)
        capture=SingleCallCapture(http,receipt,save)
        writer=LinkedInWriter(capture,context_projector=project_writer_input)
        receipt.update(model_http_events=http.events,writing_calls=writer.calls)
        receipt.update(write_and_validate(inputs,writer))  # Original evidence, not projected view.
        if len(writer.calls)!=1 or len(http.events)!=1 or http.events[0]['kind']!='writing':
            raise ValueError('Single Writer attempt condition not satisfied')
        receipt['usage']=http.events[0].get('usage',{})
    except Exception:
        receipt.update(status='STOPPED',failure='Experiment/audit failed; no retry or fallback')
    finally:
        receipt.update(finished_local=datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(),
            elapsed_seconds=round(time.monotonic()-started,3))
        save()
    report=OUTPUT/'review.md'
    report.write_text(render({**receipt,'writing_calls':receipt.get('writing_calls') or [{}]}));report.chmod(0o600)
    receipt['review.md_sha256']=hashlib.sha256(report.read_bytes()).hexdigest();save()
    print(json.dumps({k:receipt.get(k) for k in ['status','experiment_id','elapsed_seconds','usage','diagnostic']},indent=2))
    print('Protected result:',OUTPUT)
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--source-state',type=Path,required=True)
    parser.add_argument('--baseline-receipt',type=Path,required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if args.execute:
        execute(args.input,args.source_state,args.baseline_receipt)
    else:
        inputs,baseline,projection,payload=verified_context(args.input,args.source_state,args.baseline_receipt)
        print(json.dumps({'status':'OFFLINE_PREFLIGHT_PASS','baseline':baseline,
            'projected_request_sha256':PROJECTED_REQUEST_SHA,'projected_request_bytes':len(dumps(payload).encode()),
            'writer_prompt_sha256':PROMPTS['linkedin_writer'],'credentials_read':False,'live_calls':0},indent=2))
