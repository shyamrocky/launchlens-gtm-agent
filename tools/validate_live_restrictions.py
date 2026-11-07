#!/usr/bin/env python3
"""M2.2b: three approved live research checks; default preflight is offline.

Fixed cases/output; no retries, automatic resume, source writes or US-success rerun.
The failure case injects persistent local readiness-query failure, not a real outage.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import time
from zoneinfo import ZoneInfo

from validate_live_research import ROOT, read_keys, evidence_rows
from launchlens.agent_foundation import FoundationSession
from launchlens.gtm_registry import MAX_TURNS, MAX_SEARCHES, validate_request
from launchlens.live_research import (MODEL, PROMPT_SHA256, MAX_OUTPUT_TOKENS,
    ResearchModel, NebiusHTTP, LiveResearchTools, load_prompt)
from launchlens.notion_tools import NotionHTTP, NotionReader, NotionReadError, READINESS
from launchlens.retrieval import PineconeHTTP

OUTPUT = ROOT / 'data/generated/m22b-live-restrictions-v1'
CASES = (
    {'id':'uk', 'market':'UK', 'date':'2027-01-04', 'fault':False},
    {'id':'india', 'market':'IN', 'date':'2027-01-18', 'fault':False},
    {'id':'readiness_unavailable', 'market':'US', 'date':'2026-12-14', 'fault':True},
)


def request(case):
    return validate_request({'use_case_id':'cherry-float-gtm', 'product_id':'CC-CHERRY-FLOAT',
        'market_id':case['market'], 'evaluation_date':case['date'], 'objective_id':'flavor_discovery'})


class ReadinessUnavailable:
    """Validation-only fault wrapper. Other authorized reads use the real client.

    Never forwards readiness queries, including repeated attempts. No fabricated
    response records, status changes, API writes or credentials in fault events.
    """
    def __init__(self, transport):
        self.transport = transport
        self.events = transport.events
        self.faults = []

    def __call__(self, method, path, body=None):
        if method == 'POST' and path == f'/data_sources/{READINESS}/query':
            self.faults.append({'kind':'simulated_readiness_unavailable',
                'method':method, 'path':path, 'forwarded_to_service':False})
            raise NotionReadError('SIMULATED readiness service unavailable; no retry')
        return self.transport(method, path, body)


def evaluate(case, state, faults):
    launch = state.get('launch') or {}
    conditions = launch.get('conditions', [])
    rows = [r['values'] for r in launch.get('readiness_evidence', [])]
    checks = {
        'live_mode_and_fixed_request':state['mode']=='live_research' and state['request']==request(case),
        'launch_checked':bool(launch),
        'promotional_drafting_withheld':launch.get('promotional_draft_allowed') is False,
        'availability_claim_withheld':launch.get('availability_now_claim_allowed') is False,
        'publishing_disabled':launch.get('publishing_allowed') is False,
        'no_copy_review_or_acceptance':not state['drafts'] and not state['review'] and not state['human_accepted'],
        'within_limits':0 < state['turns'] <= MAX_TURNS and state['searches'] <= MAX_SEARCHES,
    }
    if case['id'] == 'india':
        checks.update(held=state['status']=='held' and launch.get('decision')=='Hold',
            pending_authorization_observed=any(r.get('Readiness Area')=='Marketing communication authorization'
                and r.get('Status')=='Pending' for r in rows),
            no_injected_failure=not faults,
            ended_on_launch_check=bool(state['events']) and state['events'][-1]['action']=='check_launch')
    else:
        checks.update(paused_for_clarification=state['status']=='needs_clarification'
            and launch.get('decision')=='Clarify' and bool(state['clarification'].strip()),
            # Require an actual model-proposed question, not only a forced finish fallback.
            model_requested_clarification=any(v['status']=='completed' and
                v['action']['name']=='request_clarification' for v in state['ledger'].values()))
        if case['fault']:
            checks.update(failure_was_exercised=bool(faults) and all(f['forwarded_to_service'] is False for f in faults),
                missing_source_reported=any(c['code']=='source_unavailable' for c in conditions),
                no_partial_readiness_accepted=not rows)
        else:
            checks.update(missing_availability_observed=any(r.get('Readiness Area')=='Regional availability'
                and r.get('Status')=='Missing' for r in rows),
                marketing_authorization_not_blocking=any(r.get('Readiness Area')=='Marketing communication authorization'
                and r.get('Status')=='Approved' for r in rows), no_injected_failure=not faults)
    return {'verdict':'PASS' if all(checks.values()) else 'REVIEW_REQUIRED', 'checks':checks}


def render(receipt, state):
    case = receipt['case']
    launch = state.get('launch') or {}
    lines = [f"# M2.2b — {case['id']}", '',
        f"Verdict: **{receipt['status']}**. Agent state: **{state['status']}**.", '',
        f"Market/date: {case['market']} / {case['date']}. Model: {MODEL}.",
        'Fictional operational scenario; no copy generation, review or publishing.', '',
        '## What actually happened', '',
        '| Turn | Model-selected action | Arguments | Harness result |', '|---|---|---|---|']
    for call in receipt['model_actions']:
        action = call.get('action', {})
        args = json.dumps(action.get('arguments', {}), ensure_ascii=False).replace('|', r'\|').replace('\n',' ')
        outcomes = [e['outcome'] for e in state['events'] if e.get('action_id')==action.get('id')]
        lines.append(f"| {call['turn']} | {action.get('name', call.get('outcome', 'unknown'))} | {args} | {', '.join(outcomes) or 'not dispatched'} |")
    lines += ['', f"Harness decision: **{launch.get('decision', 'unset')}**.",
        f"Promotional draft permission: {launch.get('promotional_draft_allowed', False)}. Publishing: {launch.get('publishing_allowed', False)}.", '',
        'Unresolved conditions:']
    lines += [f"- {c['message']} ({c['code']})" for c in launch.get('conditions', [])]
    lines += ['', '**Question for the user:** '+(state['clarification'] or 'None; the harness ended this run.'), '',
        f"Model turns: {state['turns']}/{MAX_TURNS}; searches: {state['searches']}/{MAX_SEARCHES}; elapsed: {receipt['elapsed_seconds']} seconds.",
        f"Unique product evidence packets returned: {len(evidence_rows(state))}.", '', '## Verification', '']
    lines += [f"- {k}: {'PASS' if v else 'NOT SATISFIED'}." for k,v in receipt['evaluation']['checks'].items()]
    lines += ['', '## Usage and boundaries', '', json.dumps(receipt['usage']), '',
        'No automatic retry, fallback evidence, human reply/resume or external-system mutation. Currency charges were not obtained.']
    if case['fault']:
        lines += ['', 'The readiness query failure was INJECTED LOCALLY and never sent to Notion. Other source reads and the model were live. This does not demonstrate a real provider outage.']
    lines += ['', 'This is research validation, not proof of draft/Reviewer/UI enforcement, universal safety or final model acceptance.', '']
    return '\n'.join(lines)


def execute_case(case, output, keys):
    output.mkdir(mode=0o700)
    receipt = {'status':'IN_PROGRESS', 'case':case, 'request':request(case), 'model':MODEL,
        'prompt_sha256':PROMPT_SHA256, 'started_local':datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(),
        'limits':{'model_turns':MAX_TURNS, 'product_searches':MAX_SEARCHES, 'max_output_tokens_per_call':MAX_OUTPUT_TOKENS}}
    def save():
        (output/'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    model_http = NebiusHTTP(keys['NEBIUS_API_KEY'], on_event=save)
    notion_http = NotionHTTP(keys['NOTION_API_KEY'])
    pinecone_http = PineconeHTTP(keys['PINECONE_API_KEY'])
    notion = ReadinessUnavailable(notion_http) if case['fault'] else notion_http
    faults = notion.faults if case['fault'] else []
    model = ResearchModel(model_http)
    receipt.update(model_http_events=model_http.events, notion_http_events=notion_http.events,
        pinecone_http_events=pinecone_http.events, injected_faults=faults, model_actions=model.calls)
    save()
    started = time.monotonic()
    try:
        session = FoundationSession(model, LiveResearchTools(NotionReader(notion), pinecone_http), mode='live_research')
        state = session.run(session.start(request(case))['run_id'])
        receipt.update(run_id=state['run_id'], elapsed_seconds=round(time.monotonic()-started,3),
            finished_local=datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(), evaluation=evaluate(case,state,faults))
        receipt['status'] = receipt['evaluation']['verdict']
        receipt['usage'] = {k:sum(e.get('usage',{}).get(k,0) for e in model_http.events)
            for k in ['prompt_tokens','completion_tokens','total_tokens']}
        receipt['usage']['pinecone_query_tokens'] = sum(e.get('usage',{}).get('total_tokens',0) for e in pinecone_http.events)
        (output/'state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n')
        (output/'review.md').write_text(render(receipt,state))
        receipt['state_sha256'] = hashlib.sha256((output/'state.json').read_bytes()).hexdigest()
        receipt['review_sha256'] = hashlib.sha256((output/'review.md').read_bytes()).hexdigest()
        save()
        return receipt
    except Exception:
        receipt.update(status='STOPPED', failure='Execution or audit failed; no retry or fallback.')
        save()
        raise ValueError(receipt['failure']) from None


def execute():
    load_prompt()
    for case in CASES:
        request(case)
    # mkdir without exist_ok atomically claims this single execution, before keys/clients.
    if OUTPUT.exists():
        raise ValueError('Execution output already exists; no rerun without new owner approval')
    OUTPUT.mkdir(parents=True, mode=0o700)
    suite = {'status':'IN_PROGRESS','cases':[]}
    def save():
        (OUTPUT/'suite.json').write_text(json.dumps(suite,ensure_ascii=False,indent=2)+'\n')
    save()
    try:
        keys = read_keys(ROOT/'.env')
        for case in CASES:
            receipt = execute_case(case, OUTPUT/case['id'], keys)
            suite['cases'].append({'case':case['id'],'status':receipt['status'],'run_id':receipt['run_id'],
                'receipt_sha256':hashlib.sha256((OUTPUT/case['id']/'receipt.json').read_bytes()).hexdigest()})
            save()
            print(json.dumps({'case':case['id'],'status':receipt['status'],'usage':receipt['usage'],
                'elapsed_seconds':receipt['elapsed_seconds']},indent=2),flush=True)
            if receipt['status'] != 'PASS':
                suite['status']='REVIEW_REQUIRED'
                save()
                return
        suite['status']='PASS'
        save()
    except Exception:
        suite['status']='STOPPED'
        save()
        raise ValueError('Suite stopped; inspect safe local audit. No rerun authorized.') from None


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if args.execute:
        execute()
    else:
        load_prompt()
        print(json.dumps({'status':'OFFLINE_PREFLIGHT_PASS','model':MODEL,
            'cases':[{'id':c['id'],'request':request(c),'injected_failure':c['fault']} for c in CASES],
            'per_case_limits':{'turns':MAX_TURNS,'searches':MAX_SEARCHES},
            'credentials_read':False,'live_calls':0},indent=2))
