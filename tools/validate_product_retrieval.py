#!/usr/bin/env python3
"""One approved eight-case live run through the maintained retrieval tool.

Default is offline preparation/replay; --execute requires owner approval and refuses
existing output. Frozen expectations are evaluator-only, never tool inputs.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from launchlens.evidence_payload import encode_packet
from launchlens.retrieval import (PineconeHTTP, MODEL, NAMESPACE, HOST, INDEX,
                                  API_VERSION, retrieve_product_evidence)

CASES = ROOT / 'tools/gtm_retrieval_cases.json'
CASE_HASH = '87fc5d94341f2f6c491bf6240f62b265639fdbde7d6f0d8dc9e0fec350d9105d'
PROJECTION = ROOT / 'data/generated/m15b-embedding-projection/projection.jsonl'
PROJECTION_HASH = 'ededee8bf3679af87f87b2f191632797f960b02c26ffcb1d68e9707550bf2093'
OUTPUT = ROOT / 'data/generated/product-evidence-retrieval'


def load_inputs():
    assert hashlib.sha256(CASES.read_bytes()).hexdigest() == CASE_HASH, 'Fixed cases changed'
    assert hashlib.sha256(PROJECTION.read_bytes()).hexdigest() == PROJECTION_HASH, 'Projection changed'
    rows = [json.loads(line) for line in PROJECTION.read_bytes().splitlines()]
    assert len(rows) == 45
    return json.loads(CASES.read_text())['cases'], {r['chunk_id']: r['evidence_payload'] for r in rows}


def evaluate(case, result, originals):
    # An ID is covered only if its returned evidence has been verified unchanged.
    for row in result['records']:
        assert row['chunk_id'] in originals, 'Unexpected evidence ID'
        assert encode_packet(row['evidence_payload']) == encode_packet(originals[row['chunk_id']]), 'Evidence changed'
    ranks = {row['unit_id']: row['rank'] for row in result['search_ranking']}
    units = {row['unit_id'] for row in result['records']}
    return {'case_id': case['id'], 'purpose': case['purpose'],
            'direct_expected_ranks': {u: ranks.get(u) for u in case['expected_units']},
            'direct_top_three_pass': all(ranks.get(u, 999) <= 3 for u in case['expected_units']),
            'combined_expected_evidence_pass': all(u in units for u in case['expected_units']),
            'tool_status': result['status'], 'record_count': len(result['records']),
            'reference_count': sum(r['origin'] == 'reference' for r in result['records']),
            'issue_codes': [i['code'] for i in result['issues']]}


def read_key():
    path = ROOT / '.env'
    assert path.stat().st_mode & 0o077 == 0, 'Local credential file must be private'
    values = []
    for line in path.read_text().splitlines():
        if '=' not in line or line.lstrip().startswith('#'):
            continue
        name, value = line.split('=', 1)
        if name.strip().removeprefix('export ').strip() == 'PINECONE_API_KEY':
            values.append(value.strip().strip('\"\''))
    assert len(values) == 1 and values[0], 'Missing or ambiguous Pinecone key'
    return values[0]


def execute(cases, originals):
    assert not OUTPUT.exists(), 'Receipt exists; refusing unapproved rerun'
    key = read_key()
    client = PineconeHTTP(key)
    OUTPUT.mkdir(parents=True)
    receipt = {'status': 'IN_PROGRESS', 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'index': INDEX, 'host': HOST, 'namespace': NAMESPACE, 'api_version': API_VERSION,
        'model': MODEL, 'cases_sha256': CASE_HASH, 'projection_sha256': PROJECTION_HASH,
        'events': client.events, 'results': []}
    def save():
        (OUTPUT/'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    save()
    try:
        with (OUTPUT/'responses.jsonl').open('w') as stream:
            for case in cases:
                result = retrieve_product_evidence(case['query'], case['authority'], transport=client)
                summary = evaluate(case, result, originals)
                receipt['results'].append(summary)
                stream.write(json.dumps({'case_id':case['id'], 'result':result}, ensure_ascii=False)+'\n')
                stream.flush()
                save()
                if result['status'] == 'error':
                    raise ValueError('Retrieval failed; stop without retry')
                if any(i['code'] in {'invalid_search_evidence','invalid_reference','unresolved_reference',
                                    'reference_fetch_failed'} for i in result['issues']):
                    raise ValueError('Evidence validation failed; stop without dropping fields')
        receipt['direct_passed'] = sum(r['direct_top_three_pass'] for r in receipt['results'])
        receipt['combined_passed'] = sum(r['combined_expected_evidence_pass'] for r in receipt['results'])
        receipt['incomplete_cases'] = [r['case_id'] for r in receipt['results'] if r['tool_status']!='evidence_found']
        receipt['status'] = 'PASS' if receipt['combined_passed']==8 and not receipt['incomplete_cases'] else 'REVIEW_REQUIRED'
        receipt['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
        print(json.dumps({k: receipt[k] for k in ('status','direct_passed','combined_passed','incomplete_cases','results')},indent=2))
    except Exception:
        receipt['status'] = 'STOPPED'
        receipt['failure'] = 'Execution or evidence validation failed; inspect recorded safe results. No automatic rerun.'
        save()
        raise ValueError(receipt['failure']) from None


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    cases, originals=load_inputs()
    if args.execute:
        execute(cases, originals)
    else:
        print(json.dumps({'status':'OFFLINE_PREFLIGHT_PASS','fixed_cases':len(cases),'frozen_records':len(originals)}))
