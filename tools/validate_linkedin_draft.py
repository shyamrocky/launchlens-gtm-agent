#!/usr/bin/env python3
"""M2.3b: one authorized US LinkedIn case. Default is offline, no credentials.

--execute atomically claims a fixed protected output directory before keys or any
network call. No retries, source writes, Reviewer, publishing or historical-run inputs.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import time
from zoneinfo import ZoneInfo

from validate_live_research import ROOT, REQUEST, read_keys
from launchlens.agent_foundation import FoundationSession
from launchlens.gtm_registry import MAX_TURNS, MAX_SEARCHES, validate_request
from launchlens.linkedin_drafting import LinkedInWriter, CTA, digest, evidence_records
from launchlens.live_research import (MODEL, PROMPTS, MAX_OUTPUT_TOKENS, MAX_WRITER_OUTPUT_TOKENS,
    LiveResearchTools, NebiusHTTP, ResearchModel, load_prompt)
from launchlens.notion_tools import NotionHTTP, NotionReader
from launchlens.retrieval import PineconeHTTP
from launchlens.content_contracts import load_template

OUTPUT = ROOT/'data/generated/m23b-us-linkedin-v3'


def evaluate(state, writer, http):
    draft=state['drafts'].get('linkedin',{})
    writing=[e for e in http.events if e.get('kind')=='writing']
    checks={
        'scoped_request_unchanged':state['request']==REQUEST,
        'drafting_run_completed':state['mode']=='live_linkedin' and state['status']=='draft_complete',
        'one_writing_attempt':state['writing_attempts']==1 and len(writer.calls)==1 and len(writing)==1,
        'model_selected_drafting':any(call.get('action',{}).get('name')=='generate_linkedin' for call in state.get('ledger',{}).values()),
        'harness_permission':bool(state['launch'] and state['launch']['decision']=='Proceed'
            and state['launch']['promotional_draft_allowed'] and not state['launch']['publishing_allowed']),
        'unreviewed_and_unapproved':draft.get('review_status')=='unreviewed' and draft.get('version')==1
            and draft.get('human_accepted') is False and draft.get('publishing_allowed') is False
            and state['review']=={} and state['human_accepted'] is False,
        'structural_validation':draft.get('validation',{}).get('structural_validation')=='passed',
        'within_shared_limits':len(http.events)<=MAX_TURNS and state['turns']==len(http.events)
            and state['searches']<=MAX_SEARCHES,
        'input_binding':bool(writer.calls and draft.get('input_sha256')==digest(writer.calls[0]['input'])),
        'both_claim_bindings':{e['unit_id'] for e in draft.get('evidence_bindings',[])}=={'PROD-002','PROD-003'},
        'all_model_http_200':bool(http.events) and all(e.get('http_status')==200 for e in http.events),
    }
    return {'verdict':'PASS' if all(checks.values()) else 'REVIEW_REQUIRED','checks':checks,
        'semantic_review':'NOT PERFORMED — M2.3c remains separate',
        'editorial_warnings':draft.get('validation',{}).get('editorial_warnings',[])}


def render(receipt,state,writer):
    record=state['drafts'].get('linkedin');lines=['# M2.3b — US LinkedIn run','',
        'Independent fictional educational simulation. Internal, unreviewed draft; not approved for publication.','',
        f"Technical verdict: **{receipt['status']}**. Agent status: **{state['status']}**.",
        f"Run: {state['run_id']}; model: {MODEL}; scenario: US / 2026-12-14.",
        f"Executed: {receipt['started_local']} to {receipt['finished_local']}; {receipt['elapsed_seconds']} seconds.",'']
    if record:
        content=record['draft']['content']
        lines+=['## Actual draft — unreviewed','',content['hook'],'',content['body'],'',content['cta'],'',
            ' '.join(content['hashtags']),'','## Evidence references','',
            '| Text field | Supporting claim IDs |','|---|---|']
        for ref in record['draft']['claim_references']:
            lines.append('| '+ref['content_field']+' | '+', '.join(ref['claim_ids'])+' |')
        lines+=['','## Complete supporting evidence — readable highlights','']
        for row in evidence_records(writer.calls[0]['input']):
            p=row['evidence_payload']
            lines+=[f"### {row['unit_id']}",'',p['primary_text'],'',
                f"Authority: {p['authority']}; Product Brief v{p['document_version']}; PDF pages {p['page_numbers']}; reference status {row['reference_status']}.",
                f"Evidence SHA-256: {row['evidence_sha256']}.",'']
            for source in p['claim_source_mappings']:
                lines.append(f"- Direct source {source.get('source_id')}: {source.get('source_url')}. "
                    f"Scope: {source.get('market_scope')}. Limitation: {source.get('notes_or_limitations')} "
                    f"Temporal scope: {source.get('temporal_scope')}.")
        lines+=['','Full qualifiers, citations/source roles, source hashes and provenance remain in the exact input JSON; highlights above do not replace complete evidence.','']
    else:
        lines+=['No draft admitted. Failure or unmet prerequisites were not treated as approval.','',
                'Safe diagnostic: '+json.dumps(state.get('draft_failure')),'']
        if writer.calls and 'candidate' in writer.calls[0]:
            lines+=['## Rejected candidate — not an admitted draft','',
                    'Untrusted model output retained for debugging; not reviewed or approved.','',
                    '```json',json.dumps(writer.calls[0]['candidate'],ensure_ascii=False,indent=2),'```','']
    lines+=['## Actual model-selected action log','','| Model call | Action | Arguments | Harness outcome |','|---|---|---|---|']
    for call in receipt['model_actions']:
        action=call.get('action',{})
        outcomes=[e['outcome'] for e in state['events'] if e.get('action_id')==action.get('id')]
        args=json.dumps(action.get('arguments',{}),ensure_ascii=False).replace('|',r'\|').replace('\n',' ')
        lines.append(f"| {call['turn']} | {action.get('name',call['outcome'])} | {args} | {', '.join(outcomes) or 'not dispatched'} |")
    lines+=['','The writing call is executed inside the model-selected generate_linkedin action and consumes the shared model-call budget. No private chain-of-thought is recorded.','',
        '## Verification and limitations','']
    lines += [f"- {k}: {'PASS' if v else 'NOT SATISFIED'}." for k,v in receipt['evaluation']['checks'].items()]
    for warning in receipt['evaluation']['editorial_warnings']:
        lines.append('- Editorial advisory: '+json.dumps(warning,ensure_ascii=False))
    issues=[i for result in state['evidence'] for i in result['issues']]
    for issue in issues:lines.append('- Research limitation retained: '+json.dumps(issue,ensure_ascii=False))
    lines+=['','Schema/reference/known-marker checks do not prove prose entailment, taste claims, tone quality or all unsupported promotion. Independent Reviewer and human acceptance remain outstanding.','',
        '## Actual usage','',json.dumps(receipt['usage'],ensure_ascii=False),'',
        'No currency billing or cache-hit claim. No retry, source edit, Reviewer, UI, Git sync or publication.','']
    return '\n'.join(lines)


def preflight():
    validate_request(REQUEST);load_template('linkedin')
    for name in ['research','linkedin_controller','linkedin_writer']:load_prompt(name)
    return {'status':'OFFLINE_PREFLIGHT_PASS','request':REQUEST,'model':MODEL,
        'limits':{'total_model_calls':MAX_TURNS,'searches':MAX_SEARCHES,'writing_attempts':1,
                  'action_output_tokens':MAX_OUTPUT_TOKENS,'writing_output_tokens':MAX_WRITER_OUTPUT_TOKENS},
        'cta':CTA,'credentials_read':False,'live_calls':0}


def execute():
    preflight()
    if OUTPUT.exists():raise ValueError('Execution output already exists; no rerun without new owner approval')
    OUTPUT.mkdir(parents=True,mode=0o700)  # Atomic claim before any credential/model/source access.
    os.chmod(OUTPUT,0o700)
    receipt={'status':'IN_PROGRESS','request':REQUEST,'model':MODEL,'prompt_hashes':PROMPTS,
        'started_local':datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(),
        'limits':preflight()['limits']}
    def save():
        (OUTPUT/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    save();started=time.monotonic()
    try:
        keys=read_keys(ROOT/'.env')
        http=NebiusHTTP(keys['NEBIUS_API_KEY'],allow_linkedin=True,on_event=save)
        notion=NotionHTTP(keys['NOTION_API_KEY']);pinecone=PineconeHTTP(keys['PINECONE_API_KEY'])
        controller=ResearchModel(http,mode='live_linkedin');writer=LinkedInWriter(http)
        receipt.update(model_http_events=http.events,notion_http_events=notion.events,
            pinecone_http_events=pinecone.events,model_actions=controller.calls,writing_calls=writer.calls)
        save()
        session=FoundationSession(controller,LiveResearchTools(NotionReader(notion),pinecone),
                                  mode='live_linkedin',writer=writer)
        state=session.run(session.start(REQUEST)['run_id'])
        receipt.update(run_id=state['run_id'],finished_local=datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(),
            elapsed_seconds=round(time.monotonic()-started,3),evaluation=evaluate(state,writer,http))
        receipt['status']=receipt['evaluation']['verdict']
        receipt['usage']={k:sum(e.get('usage',{}).get(k,0) for e in http.events)
                          for k in ['prompt_tokens','completion_tokens','total_tokens']}
        receipt['usage']['writing']= {k:sum(e.get('usage',{}).get(k,0) for e in http.events if e.get('kind')=='writing')
                                     for k in ['prompt_tokens','completion_tokens','total_tokens']}
        receipt['usage']['pinecone_query_tokens']=sum(e.get('usage',{}).get('total_tokens',0) for e in pinecone.events)
        if writer.calls:
            (OUTPUT/'writer-input.json').write_text(json.dumps(writer.calls[0]['input'],ensure_ascii=False,indent=2)+'\n')
        (OUTPUT/'state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
        (OUTPUT/'review.md').write_text(render(receipt,state,writer))
        for name in ['state.json','review.md','writer-input.json']:
            if (OUTPUT/name).exists():receipt[name+'_sha256']=hashlib.sha256((OUTPUT/name).read_bytes()).hexdigest()
        save()
        print(json.dumps({k:receipt[k] for k in ['status','run_id','elapsed_seconds','usage','evaluation']},indent=2))
        print('Readable report:',OUTPUT/'review.md')
    except Exception:
        receipt.update(status='STOPPED',failure='Execution or audit failed; no retry or fallback.')
        save()
        raise ValueError(receipt['failure']) from None


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if args.execute:execute()
    else:print(json.dumps(preflight(),indent=2))
