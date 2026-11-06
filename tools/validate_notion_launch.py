#!/usr/bin/env python3
"""One bounded read-only live validation of approved Notion tools and launch policy.

Default preflight is offline. --execute requires owner approval, never edits Notion,
and refuses an existing output directory. No model/Pinecone calls or new dependencies.
"""
import argparse
import csv
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from launchlens.notion_tools import NotionHTTP,NotionReader,VERSION
from launchlens.launch_checks import evaluate_launch

OUTPUT=ROOT/'data/generated/notion-launch-checks'
SOURCES={
 'calendar':('data/synthetic/gtm_launch_calendar.csv','0584abcbddbfd82062e7080c1bd08300ec49ba60466053102e0104e883847cff'),
 'readiness':('data/synthetic/gtm_readiness_tracker.csv','6db90127e5c6622174491a2694448cb3dd7d1d98ac26ac64687ea454d428a7b8')}
CASES=[('US','2026-12-14','Proceed'),('UK','2027-01-04','Clarify'),('IN','2027-01-18','Hold')]


def load_inputs():
    rows={}
    for name,(path,expected) in SOURCES.items():
        actual=ROOT/path
        assert hashlib.sha256(actual.read_bytes()).hexdigest()==expected,'Accepted operational dataset changed'
        with actual.open(newline='') as stream:rows[name]=list(csv.DictReader(stream))
    assert len(rows['calendar'])==9 and len(rows['readiness'])==12
    return rows


def read_key():
    path=ROOT/'.env';assert path.stat().st_mode&0o077==0,'Credential file must be private'
    entries=[]
    for line in path.read_text().splitlines():
        if '=' not in line or line.lstrip().startswith('#'):continue
        k,v=line.split('=',1)
        if k.strip().removeprefix('export ').strip()=='NOTION_API_KEY':entries.append(v.strip().strip('\"\''))
    assert len(entries)==1 and entries[0],'Missing or ambiguous Notion key'
    return entries[0]


def flatten(nodes):
    for node in nodes:
        yield node
        yield from flatten(node['children'])


def execute(originals):
    assert not OUTPUT.exists(),'Receipt already exists; do not rerun without approval'
    client=NotionHTTP(read_key());reader=NotionReader(client)
    OUTPUT.mkdir(parents=True)
    receipt={'status':'IN_PROGRESS','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'notion_version':VERSION,'events':client.events,'results':[],'dataset_hashes':SOURCES}
    contexts={}
    def save():
        (OUTPUT/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
        (OUTPUT/'contexts.json').write_text(json.dumps(contexts,ensure_ascii=False,indent=2)+'\n')
    save()
    try:
        pmm=reader.get_pmm_brief();contexts['pmm']=pmm;save()
        assert pmm['status']=='ok','PMM complete read failed; no partial guidance accepted'
        nodes=list(flatten(pmm['blocks']))
        text=json.dumps([n['content'] for n in nodes],ensure_ascii=False)
        assert all(marker in text for marker in ['Cherry Float','Pepsi','Dr Pepper','PROD-001']),'Required PMM content markers absent'
        receipt['pmm']={'blocks':len(nodes),'headings':sum(n['type'].startswith('heading_') for n in nodes),
            'tables':sum(n['type']=='table' for n in nodes),'required_markers_present':True}
        for market,when,expected in CASES:
            context=reader.get_launch_context(market);contexts[market]=context;save()
            assert context['status']=='ok','Complete launch context failed; no permission inferred'
            checked={}
            for name in ['calendar','readiness']:
                key='Event' if name=='calendar' else 'Record ID'
                actual=sorted([r['values'] for r in context[name]],key=lambda r:r[key])
                approved=sorted([r for r in originals[name] if r['Market ID']==market],key=lambda r:r[key])
                assert actual==approved,f'{market} {name} values differ from accepted CSV; stop'
                checked[name+'_matching_values']=sum(len(r) for r in actual)
            decision=evaluate_launch(context,when)
            assert decision['decision']==expected and decision['publishing_allowed'] is False,'Decision differs from fixed case'
            assert decision['availability_now_claim_allowed']==(market=='US'),'Unexpected availability permission'
            receipt['results'].append({'market':market,'evaluation_date':when,'expected':expected,
                                       'decision':decision,**checked})
            save()
        receipt['calendar_matching_values']=sum(r['calendar_matching_values'] for r in receipt['results'])
        receipt['readiness_matching_values']=sum(r['readiness_matching_values'] for r in receipt['results'])
        receipt['status']='PASS';receipt['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
        print(json.dumps({'status':receipt['status'],'pmm':receipt['pmm'],
            'calendar_matching_values':receipt['calendar_matching_values'],
            'readiness_matching_values':receipt['readiness_matching_values'],
            'cases':[{'market':r['market'],'date':r['evaluation_date'],
                      'decision':r['decision']['decision'],
                      'draft_allowed':r['decision']['promotional_draft_allowed'],
                      'availability_allowed':r['decision']['availability_now_claim_allowed']} for r in receipt['results']]},indent=2))
    except Exception:
        receipt['status']='STOPPED';receipt['failure']='Source/readback/decision validation failed; inspect safe receipts. No automatic rerun.';save()
        raise ValueError(receipt['failure']) from None


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    rows=load_inputs()
    if args.execute:execute(rows)
    else:print('Offline preflight PASS: accepted nine calendar / twelve readiness records; three fixed scenario cases.')
