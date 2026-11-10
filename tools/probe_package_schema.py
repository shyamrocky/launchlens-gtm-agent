"""Owner-scoped M2-D024 probes. Default is offline; --execute consumes one guard.

No full agent run, no retries, no original authorization reuse. Raw receipts are
private generated artifacts. Same production schema; safe canonical source facts.
"""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from launchlens.package_content import package_schema, load_package_prompt, FORMATS
from launchlens.content_contracts import model_output_schema, validate_draft
from launchlens.offline_fixtures import ReviewFixtureTools
from launchlens.live_research import dumps, strict_json
from launchlens.writer_providers import ProviderHTTP, read_selected_keys
from launchlens.writer_comparison import ProtectedStore
from launchlens.linkedin_drafting import digest

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'data/generated/d024-schema-probes-v1'
AUTHORIZED_OUTPUT=ROOT/'data/generated/d024-schema-audit-probes-v2'
PRIOR_RESERVATION=Decimal('0.0278528')
CAP=Decimal('0.18')
MODELS=[('qwen','Qwen/Qwen3-30B-A3B-Instruct-2507',262144,Decimal('.1'),Decimal('.3')),
        ('hermes','NousResearch/Hermes-4-405B',131072,Decimal('1'),Decimal('3'))]

from launchlens.structured_output import response_format

def request(model, channel=False):
    schema=model_output_schema('linkedin') if channel else package_schema()
    brief={'task':'Provider-schema qualification only. Write the shortest complete internal draft, not a full campaign.',
        'product':'Coca-Cola Cherry Float','market':'US','objective':'flavor_discovery',
        'claims':{'PROD-002':'Cherry with vanilla flavor notes. Flavor description does not establish actual ingredients or intensity.',
                  'PROD-003':'Inspired by classic soda floats. Inspiration does not establish ice cream or dairy content.'},
        'sources':{'PROD-002':['https://www.coca-cola.com/us/en/brands/coca-cola/products/coca-cola-flavors','https://www.coca-cola.com/gb/en/media-center/coca-cola-introduces-cherry-float-flavour'],
                   'PROD-003':['https://www.coca-colacompany.com/media-center/coca-cola-cherry-float-and-diet-coke-cherry-launch-nationwide.html','https://www.coca-cola.com/gb/en/media-center/coca-cola-introduces-cherry-float-flavour']},
        'constraints':'No availability, offers, superiority, ingredient or intensity assertions. Neutral brief; simulated brand channels. Both IDs must be referenced in each format; nonfactual CTA needs no reference. Nested objects, never escaped JSON strings.',
        'exact_linkedin_cta':"What would you like to know about Cherry Float's flavor inspiration?",'output_schema':schema}
    return {'model':model[1],'messages':[{'role':'system','content':load_package_prompt('package_writer') if not channel else 'Return only one LinkedIn JSON object matching the supplied schema and evidence constraints.'},
        {'role':'user','content':dumps(brief)}], 'temperature':0,'max_tokens':8192,'max_completion_tokens':8192,
        'stream':False,'store':False,'response_format':response_format(schema)}

def schema_keywords(schema):
    """Walk keyword positions; property names and enum values are not keywords."""
    from collections import Counter
    result=Counter()
    def visit(node):
        result.update(node.keys())
        for child in node.get('properties',{}).values():visit(child)
        if 'items' in node:visit(node['items'])
    visit(schema)
    return dict(sorted(result.items()))


def schema_audit():
    """Offline independent Draft2020-12 check; uses existing UI environment only."""
    from importlib.metadata import version
    from jsonschema import Draft202012Validator
    schemas={'package_writer':package_schema(),'package_reviewer':package_schema(True),
             **{f:model_output_schema(f) for f in FORMATS}}
    records={}
    for name,backend in schemas.items():
        provider=response_format(backend)['json_schema']['schema']
        Draft202012Validator.check_schema(backend)
        Draft202012Validator.check_schema(provider)
        removed=[]
        def compare(before,after,path='$'):
            assert set(before)-set(after) <= {'uniqueItems'}
            for key in set(before)-set(after):removed.append(path+'.'+key)
            for key in after:
                if key=='properties':
                    assert set(before[key])==set(after[key])
                    for field in after[key]:compare(before[key][field],after[key][field],path+'.properties.'+field)
                elif key=='items':compare(before[key],after[key],path+'.items')
                else:assert before[key]==after[key]
        compare(backend,provider)
        records[name]={'backend_sha256':digest(backend),'provider_sha256':digest(provider),
            'backend_keywords':schema_keywords(backend),'provider_keywords':schema_keywords(provider),
            'removed_keyword_paths':sorted(removed),'metaschema_pass':True}
    return {'validator':'jsonschema '+version('jsonschema'),'draft':'2020-12',
        'schemas':records,'network_calls':0,'backend_changed':False}


def inspect(value, channel=False, *, schema_check=False):
    result={'structure_pass':False,'semantic_acceptance':False}
    try:
        assert value['choices'][0]['finish_reason']=='stop'
        candidate=strict_json(value['choices'][0]['message']['content'])
        result['response_shape']={k:type(v).__name__ for k,v in candidate.items()} if type(candidate) is dict else type(candidate).__name__
        if schema_check:
            from jsonschema import Draft202012Validator
            original=model_output_schema('linkedin') if channel else package_schema()
            for label,schema in [('provider_schema',response_format(original)['json_schema']['schema']),('backend_schema',original)]:
                errors=list(Draft202012Validator(schema).iter_errors(candidate))
                result[label+'_pass']=not errors
                result[label+'_errors']=[{'path':list(e.absolute_path),'keyword':e.validator} for e in errors]
        assert type(candidate) is dict
        assert set(candidate)==({'format','content','claim_references'} if channel else set(FORMATS))
        from launchlens.writer_comparison import citation_inventory
        records=ReviewFixtureTools().search('Flavor','public_product_facts')['records']
        result['citation_findings']={}
        for name in (['linkedin'] if channel else FORMATS):
            item=candidate if channel else candidate[name]
            result['citation_findings'][name]=citation_inventory(item,{'PROD-002','PROD-003'})
        for name in (['linkedin'] if channel else FORMATS):
            item=candidate if channel else candidate[name]
            validate_draft(item,format_name=name,evidence_records=records)
            if {c for ref in item['claim_references'] for c in ref['claim_ids']}!={'PROD-002','PROD-003'}:
                result['diagnostic']={'field_path':'claim_references','rule':'objective_claim_coverage','format':name}
                return result
        result['structure_pass']=True
    except Exception as error:
        result['diagnostic']=getattr(error,'diagnostic',{'field_path':'$','rule':'schema_or_coverage_mismatch'})
    return result


def execute(*, audited=False):
    # New explicit authorization has its own immutable guard; the old receipt is
    # preserved and its unknown charge stays reserved within the SAME total cap.
    output=AUTHORIZED_OUTPUT if audited else OUTPUT
    held=PRIOR_RESERVATION if audited else Decimal(0)
    audit=schema_audit() if audited else None  # Must pass BEFORE credentials/HTTP.
    if audited:
        prior=json.loads((OUTPUT/'stopped.json').read_text())
        assert prior['reason']=='unknown_transport_or_billing'
        assert Decimal(prior['reservation_retained_usd'])==held
    store=ProtectedStore(output)
    if audited:
        store.write('schema-audit.json',audit)
        store.write('authorization.json',{'scope':'Owner authorized corrected Qwen then Hermes; conditional single Hermes channel; stop after probes',
            'maximum_requests':3,'attempts_per_model_and_shape':1,'automatic_retries':0,
            'cap_usd':str(CAP),'prior_reservation_retained_usd':str(held),'prior_receipts':'data/generated/d024-schema-probes-v1',
            'full_agent_run':False})
    key=read_selected_keys({'NEBIUS_API_KEY'},ROOT/'.env')['NEBIUS_API_KEY']
    spent=Decimal(0);results=[];fallback=False;attempted=0;new_unknown=Decimal(0)
    for model,channel in [(MODELS[0],False),(MODELS[1],False),(MODELS[1],True)]:
        if channel and not fallback:break
        reserve=(Decimal(model[2]-8192)*model[3]+Decimal(8192)*model[4])/Decimal(1000000)
        if held+spent+reserve>CAP:
            store.write('stopped.json',{'reason':'insufficient_remaining_reservation','spent_usd':str(spent),
                'prior_held_usd':str(held),'next_reservation_usd':str(reserve)})
            break
        payload=request(model,channel);attempted+=1;prefix=f'probe-{attempted:02}'
        store.write(prefix+'-request.json',payload)
        store.write(prefix+'-reservation.json',{'reserved_usd':str(reserve),'aggregate_ceiling_usd':str(CAP),
            'spent_before_usd':str(spent),'prior_held_usd':str(held),'request_sha256':digest(payload),
            'logical_messages_sha256':digest(payload['messages']),
            'provider_schema_sha256':digest(payload['response_format']['json_schema']['schema'])})
        started=time.monotonic()
        try:
            response=ProviderHTTP({'provider':'nebius','model_id':model[1]},key,request_validator=lambda p:p==payload)(payload)
            store.write(prefix+'-response.bin',response.body,raw=True)
            store.write(prefix+'-http.json',{'status':response.status,'headers':response.headers,'elapsed_seconds':round(time.monotonic()-started,6),'redacted':response.credential_redacted,'truncated':response.truncated})
            assert response.status==200 and not response.credential_redacted and not response.truncated
            value=strict_json(response.body);assert value['model']==model[1]
            usage=value['usage'];i,o,t=[usage[k] for k in ['prompt_tokens','completion_tokens','total_tokens']]
            assert all(type(v) is int and v>=0 for v in [i,o,t]) and i+o==t and i<=model[2]-8192 and o<=8192
            cost=(Decimal(i)*model[3]+Decimal(o)*model[4])/Decimal(1000000)
            assert cost<=reserve
        except Exception:
            new_unknown=reserve
            store.write('stopped.json',{'reason':'unknown_transport_or_billing','reservation_retained_usd':str(reserve),
                'prior_held_usd':str(held),'no_retry':True})
            break
        spent+=cost
        item={'model':model[1],'channel':channel,**inspect(value,channel,schema_check=audited),'usage':usage,
            'estimated_usd':str(cost),'elapsed_seconds':round(time.monotonic()-started,6)}
        results.append(item);store.write(prefix+'-result.json',item)
        print(dumps({'probe_completed':attempted,'model':model[1],'structure_pass':item['structure_pass'],
                     'estimated_usd':str(cost)}),flush=True)
        if model[0]=='hermes' and not channel:
            fallback=(item.get('provider_schema_pass') is False or item.get('backend_schema_pass') is False) if audited else not item['structure_pass']
    accounted=held+spent+new_unknown
    assert accounted<=CAP
    result={'results':results,'estimated_known_spend_usd':str(spent),'prior_reservation_retained_usd':str(held),
        'new_unknown_reservation_usd':str(new_unknown),'total_accounted_usd':str(accounted),
        'remaining_unreserved_usd':str(CAP-accounted),'ceiling_usd':str(CAP),'requests_attempted':attempted,'full_agent_run':False}
    store.write('summary.json',result);print(dumps(result),flush=True)


def historical_review_schema():
    from launchlens.content_review import review_schema
    return {'type':'object','required':list(FORMATS),'additionalProperties':False,'properties':{f:review_schema() for f in FORMATS}}


REVIEWER_OUTPUT=ROOT/'data/generated/d024-hermes-reviewer-probe-v3'


def reviewer_request(source_request=None, source_response=None):
    """One isolated review of the exact preserved probe; never a fresh agent run."""
    if source_request is None and source_response is None:
        identities=json.loads((AUTHORIZED_OUTPUT/'request-response-identities.json').read_text())
        identity=next(i for i in identities if i['model']==MODELS[1][1])
        source_request=json.loads((AUTHORIZED_OUTPUT/'probe-02-request.json').read_text())
        raw=(AUTHORIZED_OUTPUT/'probe-02-response.bin').read_bytes()
        import hashlib
        assert digest(source_request)==identity['request_sha256']
        assert hashlib.sha256(raw).hexdigest()==identity['response_sha256']
        source_response=strict_json(raw)
    assert type(source_request) is dict and type(source_response) is dict
    assert source_request['model']==source_response['model']==MODELS[1][1]
    assert source_request['messages'][0]['content']==load_package_prompt('package_writer')
    assert source_response['choices'][0]['finish_reason']=='stop'
    candidate=strict_json(source_response['choices'][0]['message']['content'])
    from launchlens.content_contracts import COMMON_REVIEW_CRITERIA
    evidence=ReviewFixtureTools().search('Flavor','public_product_facts')['records']
    warnings={}
    for name in FORMATS:
        warnings[name]=validate_draft(candidate[name],format_name=name,evidence_records=evidence)['editorial_warnings']
    brief=strict_json(source_request['messages'][1]['content'])
    # Make the original probe's stated restrictions explicit in the production
    # brief location. No new facts, permission, or target-finding hints are added.
    brief['draft_constraints']={'allowed_claim_ids':sorted(brief['claims']),
        'internal_draft_only':True,'exact_cta':brief['exact_linkedin_cta'],
        'urls_allowed':False,'availability_wording_allowed':False,'offers_allowed':False}
    binding={'run_id':'isolated-hermes-reviewer-probe-v3','draft_version':1,
        'draft_sha256':digest(candidate),'authoritative_input_sha256':digest(brief),
        'creative_anchor_sha256':digest(candidate['campaign_brief'])}
    inputs={'binding':binding,'writer_brief':brief,'projection_manifest':None,
        'output_schema':historical_review_schema(),'package':candidate,
        'writing_instructions':load_package_prompt('package_writer'),
        'editorial_warnings':warnings,'review_criteria':list(COMMON_REVIEW_CRITERIA)}
    # Use the actual role's configured 4096-token bound, not the Writer's8192.
    # Historical consumed Hermes probe stays pinned to its original role profile.
    role=strict_json((ROOT/'data/templates/gtm/live_package_profile_v3.json').read_text())['roles']['package_reviewer']
    assert role['model_id']==MODELS[1][1] and role['max_completion_tokens']==4096
    payload={'model':role['model_id'],'messages':[{'role':'system','content':(ROOT/'src/launchlens/prompts/package_reviewer_v2.txt').read_text()},
        {'role':'user','content':dumps(inputs)}],'temperature':0,'max_tokens':4096,'max_completion_tokens':4096,
        'stream':False,'store':False,'response_format':response_format(inputs['output_schema'])}
    return payload,inputs


def inspect_review(value, inputs):
    """Report raw findings even on rejection; acceptance uses unchanged validators."""
    from collections import Counter
    from jsonschema import Draft202012Validator
    from launchlens.content_review import validate_assessment
    from launchlens.package_content import resolve_field
    result={'schema_pass':False,'backend_pass':False,'content_accepted':False}
    try:
        candidate=strict_json(value['choices'][0]['message']['content'])
        result['response_shape']={k:type(v).__name__ for k,v in candidate.items()} if type(candidate) is dict else type(candidate).__name__
        for label,schema in [('provider_schema',response_format(historical_review_schema())['json_schema']['schema']),('backend_schema',historical_review_schema())]:
            errors=list(Draft202012Validator(schema).iter_errors(candidate))
            result[label+'_pass']=not errors
            result[label+'_errors']=[{'path':list(e.absolute_path),'keyword':e.validator} for e in errors]
        result['schema_pass']=result['provider_schema_pass'] and result['backend_schema_pass']
        assert type(candidate) is dict and set(candidate)==set(FORMATS)
        findings=[{'format':name,**finding} for name in FORMATS for finding in candidate[name].get('findings',[])]
        result['findings']=findings
        result['findings_by_severity']=dict(Counter(f.get('severity','unknown') for f in findings))
        # Descriptive checks AFTER inference only; never prime the Reviewer.
        terms=['Try it today','sure to become a new favorite','unique twist','innovative','Introducing','new flavor']
        result['requested_phrase_coverage']={}
        for term in terms:
            occurrences=[];flagged=[]
            from launchlens.package_content import text_fields
            for name in FORMATS:
                for field,text in text_fields(inputs['package'][name]['content']):
                    if term.casefold() in text.casefold():occurrences.append({'format':name,'content_field':field})
            for f in findings:
                if term.casefold() in f.get('quote','').casefold():
                    flagged.append({'format':f['format'],'content_field':f.get('content_field'),'severity':f.get('severity'),'quote':f.get('quote')})
            result['requested_phrase_coverage'][term]={'present_in_input':bool(occurrences),'input_occurrences':occurrences,'explicitly_quoted_findings':flagged}
        assert value['choices'][0]['finish_reason']=='stop' and result['schema_pass']
        checks={}
        for name in FORMATS:
            try:
                checks[name]=validate_assessment(candidate[name],inputs['writer_brief'],{'draft':inputs['package'][name]},
                    inputs['binding'],resolve_field=resolve_field)['review_status']
            except Exception as error:
                result['backend_diagnostic']={'format':name,**getattr(error,'diagnostic',{'code':'invalid_structure','field_path':'$'})}
                return result
        result['backend_pass']=True;result['format_review_status']=checks
    except Exception:
        result.setdefault('backend_diagnostic',{'code':'invalid_review_response','field_path':'$'})
    return result


def execute_reviewer():
    """Exactly one new owner-authorized call, sharing the original0.18 ceiling."""
    from jsonschema import Draft202012Validator
    payload,inputs=reviewer_request()
    for schema in (inputs['output_schema'],payload['response_format']['json_schema']['schema']):
        Draft202012Validator.check_schema(schema)
    previous=json.loads((AUTHORIZED_OUTPUT/'summary.json').read_text())
    assert previous['requests_attempted']==2 and previous['total_accounted_usd']=='0.0335936'
    accounted=Decimal(previous['total_accounted_usd']);model=MODELS[1];cap=payload['max_completion_tokens']
    reserve=(Decimal(model[2]-cap)*model[3]+Decimal(cap)*model[4])/Decimal(1000000)
    assert accounted+reserve<=CAP
    store=ProtectedStore(REVIEWER_OUTPUT)
    store.write('authorization-reservation.json',{'scope':'One Hermes production Reviewer probe of the preserved Hermes package; no retries or full run',
        'maximum_requests':1,'automatic_retries':0,'cap_usd':str(CAP),'prior_accounted_usd':str(accounted),
        'prior_unknown_reserve_usd':str(PRIOR_RESERVATION),'reserved_usd':str(reserve),
        'request_sha256':digest(payload),'schema_sha256':digest(payload['response_format']['json_schema']['schema']),
        'package_sha256':digest(inputs['package']),'reviewer_prompt_sha256':__import__('hashlib').sha256(payload['messages'][0]['content'].encode()).hexdigest(),
        'timeout_seconds':120,'note':'Probe-only read timeout; production default remains45 seconds; no request or token-limit change'})
    store.write('request.json',payload)
    key=read_selected_keys({'NEBIUS_API_KEY'},ROOT/'.env')['NEBIUS_API_KEY']
    started=time.monotonic()
    try:
        response=ProviderHTTP({'provider':'nebius','model_id':model[1]},key,request_validator=lambda p:p==payload,timeout_seconds=120)(payload)
        store.write('response.bin',response.body,raw=True)
        elapsed=round(time.monotonic()-started,6)
        store.write('http.json',{'status':response.status,'headers':response.headers,'elapsed_seconds':elapsed,
            'redacted':response.credential_redacted,'truncated':response.truncated})
        assert response.status==200 and not response.credential_redacted and not response.truncated
        value=strict_json(response.body);assert value['model']==model[1]
        usage=value['usage'];i,o,t=[usage[k] for k in ['prompt_tokens','completion_tokens','total_tokens']]
        assert all(type(v) is int and v>=0 for v in [i,o,t]) and i+o==t and i<=model[2]-cap and o<=cap
        cost=(Decimal(i)*model[3]+Decimal(o)*model[4])/Decimal(1000000);assert cost<=reserve
    except Exception:
        result={'requests_attempted':1,'reason':'unknown_transport_or_billing','reservation_retained_usd':str(reserve),
            'total_accounted_usd':str(accounted+reserve),'cap_usd':str(CAP),'no_retry':True,'full_agent_run':False}
        store.write('result.json',result);print(dumps(result));return
    result={'requests_attempted':1,**inspect_review(value,inputs),'model':model[1],'usage':usage,
        'estimated_usd':str(cost),'elapsed_seconds':elapsed,'total_accounted_usd':str(accounted+cost),
        'prior_unknown_reservation_retained_usd':str(PRIOR_RESERVATION),'remaining_unreserved_usd':str(CAP-accounted-cost),
        'cap_usd':str(CAP),'no_retry':True,'full_agent_run':False}
    store.write('result.json',result)
    print(dumps(result),flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--execute-reviewer-v3']:execute_reviewer()
    elif sys.argv[1:]==['--reviewer-preflight']:
        payload,inputs=reviewer_request()
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(payload['response_format']['json_schema']['schema'])
        print(dumps({'mode':'offline','request_sha256':digest(payload),'package_sha256':digest(inputs['package']),'schema_pass':True,'model':payload['model'],'completion_cap':payload['max_completion_tokens'],'provider_calls':0}))
    elif sys.argv[1:]==['--execute']:execute()
    elif sys.argv[1:]==['--execute-authorized-audit-v2']:execute(audited=True)
    elif sys.argv[1:]==['--audit']:print(dumps(schema_audit()))
    elif not sys.argv[1:]:print(dumps({'mode':'offline_preparation','maximum_requests':3,'aggregate_ceiling_usd':str(CAP),'models':[m[1] for m in MODELS],'request_hashes':[digest(request(m)) for m in MODELS]}))
    else:raise SystemExit('Use no arguments, --audit, --execute, or --execute-authorized-audit-v2')
