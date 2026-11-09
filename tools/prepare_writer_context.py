#!/usr/bin/env python3
"""OFFLINE ONLY: reproduce recorded request identities and inspect Writer projection.

No credentials, HTTP clients or inference. Explicit prior receipt is optional audit
input; application/tests never require it. Fixed caller-chosen output must be new.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from launchlens.linkedin_drafting import digest,writer_request
from launchlens.live_research import dumps,load_prompt,PROMPTS
from launchlens.writer_context import project_writer_input,identity,ProjectionError


def baseline_identity(receipt, inputs):
    event=next(e for e in receipt['model_http_events'] if e['kind']=='writing')
    if digest(inputs)!=receipt['input_sha256']:
        raise ProjectionError('Recorded assembled-input digest differs')
    if receipt['prompt_hashes']['linkedin_writer']!=PROMPTS['linkedin_writer']:
        raise ProjectionError('Original system prompt unavailable in current registered asset')
    raw=dumps(writer_request(inputs)).encode()
    recorded=event.get('request_sha256')
    if recorded is not None and hashlib.sha256(raw).hexdigest()!=recorded:
        raise ProjectionError('Reconstructed provider request differs from recorded full-request digest')
    if recorded is not None and len(raw)!=event['request_bytes']:
        raise ProjectionError('Reconstructed request byte count differs')
    return raw,{'assembled_input_sha256':receipt['input_sha256'],
        'assembled_input_hash_scope':'Canonical JSON (sorted keys), not complete provider request',
        'recorded_provider_request_sha256':recorded,
        'reconstructed_provider_request_sha256':hashlib.sha256(raw).hexdigest(),
        'original_wire_bytes_retained':False,
        'recorded_full_request_hash_available':recorded is not None,
        'reconstruction_matches_recorded_full_request':True if recorded else None,
        'baseline_limit':'Original wire bytes were not saved; reconstructed serialization matches recorded digest/length' if recorded
                         else 'No full-request digest or original wire bytes: reconstruction is a new baseline, not verified original bytes',
        'baseline_request_bytes':len(raw),'recorded_provider_input_tokens':event.get('usage',{}).get('prompt_tokens')}


def readable(model,manifest,baseline):
    c=model['research_context'];rows=[
        '# M2.3b — Writer context assembly (offline)', '',
        '**No inference performed. Correct assembly does not establish model compliance or semantic completeness.**','',
        '## Recorded baseline identity','',baseline['baseline_limit'],
        f"Canonical assembled input: `{baseline['assembled_input_sha256']}`.",
        f"Recorded full provider request: `{baseline['recorded_provider_request_sha256']}`.",
        f"Baseline/projected serialized request bytes: {manifest['baseline_request_bytes']} / {manifest['projected_request_bytes']}.",
        'Historical provider token count: '+str(baseline['recorded_provider_input_tokens'])+
        '; projected token count NOT MEASURED. Bytes are not model tokens.','',
        '## Exact projected research brief','',
        'The system prompt and every outer task/template/schema/review/constraint field remain identical. '
        'The following is the model-facing research_context; full JSON is also saved for audit.','',
        '### PMM guidance — synthetic strategy, not product truth','']
    for g in c['pmm']['guidance']:
        rows += ['**'+g['purpose']+'**']+[f'- {text}' for text in g['text']]+['']
    rows += ['### Launch permission and restrictions — synthetic','',
             '```json',json.dumps(c['launch'],ensure_ascii=False,indent=2),'```','',
             '### Material caveats/conflicts','']+['- '+v for v in c['material_boundaries']]+['',
             '### Eligible claims and exact direct source mappings','']
    for claim in c['claims']:
        rows += ['**'+claim['claim_id']+'**: '+claim['text'],
                 'Authority: '+claim['authority'],
                 'Source roles: '+json.dumps(claim['source_references'],ensure_ascii=False),
                 'Source mappings:','```json',json.dumps(claim['claim_source_mappings'],ensure_ascii=False,indent=2),'```',
                 'Required/shared context references: '+', '.join(claim['context_refs']),'']
    rows += ['### Shared statement/qualification/source text — exact once','']
    for key,value in c['claim_context'].items():
        rows += ['**'+key+' / '+value['role']+'**',value['text'],'']
    rows += ['## Traceability and exclusions','',
        'The manifest records source fields/spans, inclusion/exclusion reasons, evidence identities and policy digest. '
        'The complete authoritative bundle remains separate and is still used for output validation. '
        'No silent truncation, automatic citation cleanup, new source evidence or changed launch permission.','',
        'Keep original pre-February simulation wording and PMM TBD restrictions visible alongside the scoped '
        'December fictional decision. Review these caveats before any live comparison.','',
        '## Complete selection ledger','',
        '| Source | Range | Decision | Reason |','|---|---|---|---|']
    for row in manifest['included_excluded']:
        rows.append('| '+row['source']+' | '+str(row.get('range','whole field'))+' | '+row['decision']+' | '+row['reason']+' |')
    return '\n'.join(rows)+'\n'


def prepare(receipt_path, output):
    receipt_bytes=receipt_path.read_bytes();receipt=json.loads(receipt_bytes)
    inputs=receipt['writing_calls'][0]['input'];original=dumps(inputs)
    baseline_raw,baseline=baseline_identity(receipt,inputs)
    projected=project_writer_input(inputs);model=projected['model_input'];manifest=projected['manifest']
    projected_raw=dumps(writer_request(model)).encode()
    manifest.update(baseline_identity=baseline,source_receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest(),
        baseline_request_bytes=len(baseline_raw),projected_request_bytes=len(projected_raw),
        projected_request_sha256=hashlib.sha256(projected_raw).hexdigest(),
        components_before={k:len(dumps(v).encode()) for k,v in inputs.items()},
        components_after={k:len(dumps(v).encode()) for k,v in model.items()},
        non_context_fields_unchanged=all(model[k]==inputs[k] for k in inputs if k!='research_context'),
        source_input_unchanged=dumps(inputs)==original,credentials_read=False,network_calls=0)
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    for name,raw in [('baseline-request.json',baseline_raw),('projected-request.json',projected_raw),
                     ('authoritative-input.json',json.dumps(inputs,ensure_ascii=False,indent=2).encode()),
                     ('projection-manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode()),
                     ('review.md',readable(model,manifest,baseline).encode())]:
        p=output/name;p.write_bytes(raw);p.chmod(0o600)
    print(json.dumps({k:manifest[k] for k in ['baseline_request_bytes','projected_request_bytes',
        'projected_request_sha256','non_context_fields_unchanged','source_input_unchanged','network_calls']},indent=2))
    print('Readable audit:',output/'review.md')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--receipt',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args();prepare(args.receipt,args.output)
