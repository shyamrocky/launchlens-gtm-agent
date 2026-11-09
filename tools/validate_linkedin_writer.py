#!/usr/bin/env python3
"""Optional M2.3b Writer-only experiment; never a production input path.

Default preflight is offline. --execute requires explicit, checksum-pinned prior
input/state files and atomically claims a fixed output directory before any call.
Only one Writer call is made; no controller, Notion/Pinecone read, retry or repair.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import time
from uuid import uuid4
from zoneinfo import ZoneInfo

from validate_live_research import ROOT, REQUEST, read_keys
from launchlens.linkedin_drafting import LinkedInWriter, DraftValidationError, admit_output, digest, prepare_input
from launchlens.live_research import MODEL, PROMPTS, MAX_WRITER_OUTPUT_TOKENS, NebiusHTTP, load_prompt, strict_json

OUTPUT = ROOT/'data/generated/m23b-us-writer-only-hashtag-v1'
INPUT_SHA256 = 'f294c332d5a2a9cdb17c175975294e83e8d0b20e1c32dd4b2a262ff1d7b8b3b9'
STATE_SHA256 = '6ba71a0685bad5a6924f93d77e68de97dfb3675a1e2f8a6b8ae5423c15411b2b'
SOURCE_RUN = '6ba652cf-fc35-44be-bd66-aa518b1b6b4f'


def preflight():
    load_prompt('linkedin_writer')
    return {'status':'OFFLINE_PREFLIGHT_PASS','request':REQUEST,'model':MODEL,
            'writer_prompt_sha256':PROMPTS['linkedin_writer'],
            'limits':{'model_calls':1,'writing_attempts':1,'output_tokens':MAX_WRITER_OUTPUT_TOKENS},
            'credentials_read':False,'live_calls':0,'research_rerun':False}


def verified_inputs(input_path, state_path):
    values=[]
    for path, expected in [(input_path,INPUT_SHA256),(state_path,STATE_SHA256)]:
        raw=Path(path).read_bytes()
        if len(raw)>2_000_000 or hashlib.sha256(raw).hexdigest()!=expected:
            raise ValueError('Snapshot checksum differs; no fallback')
        values.append(strict_json(raw))
    inputs,state=values
    if state.get('run_id')!=SOURCE_RUN or state.get('request')!=REQUEST or prepare_input(state)!=inputs:
        raise ValueError('Saved scope/evidence/permission reconstruction differs; no call')
    return inputs


def write_and_validate(inputs, writer):
    stage='writing'
    try:
        candidate=writer(inputs)
        stage='draft_validation'
        return {'status':'WRITER_PASS_UNREVIEWED','draft':admit_output(candidate,inputs),'diagnostic':None}
    except DraftValidationError as error:
        return {'status':'WRITER_REJECTED','draft':None,
                'diagnostic':{'stage':stage,'code':error.code,**error.diagnostic}}
    except Exception:
        return {'status':'WRITER_FAILED','draft':None,'diagnostic':{'stage':stage,
                'code':'operation_failed','field_path':None,'rule':'unknown_validation_failure'}}


def render(receipt):
    draft=receipt.get('draft');candidate=receipt.get('writing_calls',[{}])[0].get('candidate')
    lines=['# M2.3b — controlled Writer-only experiment','',
        'Independent fictional educational simulation. No review, human approval or publishing.','',
        'Outcome: '+receipt['status'],
        'One model request; no autonomous controller, Notion or Pinecone calls. Frozen research reused.','',
        'Diagnostic: '+json.dumps(receipt.get('diagnostic')),'',
        '## '+('Admitted draft — unreviewed' if draft else 'Rejected candidate — not admitted'),'']
    if candidate:
        c=candidate.get('content') if isinstance(candidate,dict) else None
        if isinstance(c,dict) and all(isinstance(c.get(k),str) for k in ['hook','body','cta']):
            lines += [c['hook'],'',c['body'],'',c['cta'],'']
            if isinstance(c.get('hashtags'),list) and all(isinstance(v,str) for v in c['hashtags']):
                lines += [' '.join(c['hashtags']),'']
        lines += ['Exact returned JSON:','```json',json.dumps(candidate,ensure_ascii=False,indent=2),'```','']
    lines += ['## Usage and limits','',json.dumps(receipt.get('usage',{})),
        'Elapsed seconds: '+str(receipt.get('elapsed_seconds')),'',
        'This tests Writer output against existing deterministic gates. No new end-to-end agent success, '
        'semantic grounding or independent Reviewer result is established. Stop for owner review.','']
    return '\n'.join(lines)


def execute(input_path,state_path):
    preflight()
    if OUTPUT.exists():raise ValueError('Execution output already exists; no rerun without owner approval')
    OUTPUT.mkdir(parents=True,mode=0o700)
    receipt={'status':'IN_PROGRESS','experiment_id':str(uuid4()),'kind':'writer_only',
        'source_run_id':SOURCE_RUN,'model':MODEL,'prompt_hashes':dict(PROMPTS),'request':dict(REQUEST),
        'started_local':datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(),
        'limits':preflight()['limits'],'source_input_sha256':INPUT_SHA256,'source_state_sha256':STATE_SHA256,
        'notion_calls':0,'pinecone_calls':0,'controller_calls':0,'automatic_retries':0}
    def save():
        (OUTPUT/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
        (OUTPUT/'receipt.json').chmod(0o600)
    save();started=time.monotonic()
    try:
        if not input_path or not state_path:raise ValueError('Explicit provisioned snapshots required')
        inputs=verified_inputs(input_path,state_path)
        receipt['input_sha256']=digest(inputs)
        keys=read_keys(ROOT/'.env')
        http=NebiusHTTP(keys['NEBIUS_API_KEY'],allow_linkedin=True,on_event=save)
        writer=LinkedInWriter(http)
        receipt.update(model_http_events=http.events,writing_calls=writer.calls)
        receipt.update(write_and_validate(inputs,writer))
        if len(writer.calls)!=1 or len(http.events)!=1 or http.events[0]['kind']!='writing':
            raise ValueError('Single Writer call condition not met')
        receipt.update(finished_local=datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(),
            elapsed_seconds=round(time.monotonic()-started,3),usage=http.events[0].get('usage',{}))
        save()
        (OUTPUT/'review.md').write_text(render(receipt));(OUTPUT/'review.md').chmod(0o600)
        receipt['review.md_sha256']=hashlib.sha256((OUTPUT/'review.md').read_bytes()).hexdigest()
        save()
        print(json.dumps({k:receipt[k] for k in ['status','experiment_id','elapsed_seconds','usage','diagnostic']},indent=2))
        print('Readable report:',OUTPUT/'review.md')
    except Exception:
        receipt.update(status='STOPPED',failure='Experiment or audit failed; no retry or fallback')
        save()
        raise ValueError(receipt['failure']) from None


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--input',type=Path)
    parser.add_argument('--source-state',type=Path)
    args=parser.parse_args()
    if args.execute:execute(args.input,args.source_state)
    else:print(json.dumps(preflight(),indent=2))
