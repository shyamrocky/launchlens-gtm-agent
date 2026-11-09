"""Explicit, bounded Nebius-only Writer comparison; injected one-shot transports.

Normal LinkedInWriter/controller are untouched. No imports trigger inference,
credentials, source reads or filesystem writes. Contract acceptance is not review.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from threading import Lock
import time

from launchlens.linkedin_drafting import admit_output, digest, DraftValidationError
from launchlens.live_research import dumps, load_prompt, strict_json, MAX_REQUEST_BYTES, MODEL
from launchlens.writer_context import project_writer_input

CONFIG = Path(__file__).resolve().parents[2]/'data/templates/gtm/writer_models.json'
# The default registry remains baseline-only. Hermes is available solely through
# its explicit offline-prepared profile; live execution needs a fresh authorization.
HERMES_CONFIG = CONFIG.with_name('writer_models_hermes.json')
REGISTERED_MODELS = {'qwen30':MODEL, 'hermes':'NousResearch/Hermes-4-405B'}


class ComparisonError(ValueError):
    """Fixed application messages only; never raw exception/provider text."""


def require(ok, message):
    if not ok: raise ComparisonError(message)


def money(value):
    require(type(value) is str and re.fullmatch(r'\d+(?:\.\d{1,8})?',value) is not None,'Invalid cost information')
    try: result=Decimal(value)
    except InvalidOperation: raise ComparisonError('Invalid cost information') from None
    require(result.is_finite() and result>0,'Missing positive cost information')
    return result


def load_config(path=CONFIG):
    config=strict_json(Path(path).read_bytes())
    check_config(config)
    return config


def check_config(config):
    require(type(config) is dict and set(config)=={'version','default_mode','single_selected_model',
        'max_requests','output_tokens','aggregate_cost_ceiling_usd','models'},'Unknown configuration fields')
    require(config['version']=='2.0' and config['default_mode']=='single' and
        type(config['max_requests']) is int and config['max_requests'] in {1,3} and config['output_tokens']==2048,'Unreviewed comparison limits')
    money(config['aggregate_cost_ceiling_usd'])
    require(type(config['models']) is list and 1<=len(config['models'])<=config['max_requests'],'Reviewed Nebius profiles exceed request limit')
    expected={'key','name','provider','model_id','enabled','public_status','access_status','pricing',
        'per_model_cost_ceiling_usd','input_token_ceiling','settings_differences','sources'}
    keys=[];identities=[]
    for model in config['models']:
        require(type(model) is dict and set(model)==expected,'Unknown model configuration fields')
        require(model['provider']=='nebius' and model['key'] in REGISTERED_MODELS and
            model['model_id']==REGISTERED_MODELS[model['key']],'Unreviewed Nebius model or provider')
        require(type(model['enabled']) is bool and type(model['input_token_ceiling']) is int and
            0<model['input_token_ceiling']<=32768,'Invalid enabled flag or input ceiling')
        require(type(model['name']) is str and 0<len(model['name'])<=80 and
            model['access_status']=='unverified' and type(model['public_status']) is str and
            type(model['settings_differences']) is list and type(model['sources']) is list,'Unreviewed model metadata')
        money(model['per_model_cost_ceiling_usd'])
        require(type(model['pricing']) is dict and set(model['pricing'])=={'input_per_million_usd',
            'output_per_million_usd','status','checked_date'},'Unknown pricing fields')
        require(model['pricing']['status'] in {'published','unresolved'},'Unverified pricing status')
        for name in ['input_per_million_usd','output_per_million_usd']:
            if model['pricing'][name] is not None:money(model['pricing'][name])
        keys.append(model['key']);identities.append(model['model_id'])
    require(len(set(keys))==len(keys) and len(set(identities))==len(identities) and config['single_selected_model'] in keys,'Duplicate/missing model selection')


def assemble(original, *, projector=project_writer_input):
    """Project exactly once, retaining an independent copy of original authority."""
    authority=deepcopy(original)
    projection=projector(deepcopy(authority));model=projection['model_input']
    require(set(model)==set(authority) and all(model[k]==authority[k] for k in authority if k!='research_context'),
        'Projection changed non-context contract')
    require(projection['manifest']['authoritative_input_sha256']==digest(authority) and
        projection['manifest']['model_input_sha256']==digest(model),'Projection binding differs')
    logical={'system':load_prompt('linkedin_writer'),'user':dumps(model)}
    return {'authoritative':authority,'projected':deepcopy(model),'projection_manifest':deepcopy(projection['manifest']),
        'logical':logical,'logical_input_sha256':digest(logical),'authoritative_input_sha256':digest(authority)}


def translate(logical, model):
    """Use the existing Nebius Writer envelope, without prompt/evidence rewriting."""
    require(model['provider']=='nebius' and model['key'] in REGISTERED_MODELS and
        model['model_id']==REGISTERED_MODELS[model['key']],'Unreviewed Nebius profile')
    payload={'model':model['model_id'],'messages':[{'role':'system','content':logical['system']},
        {'role':'user','content':logical['user']}],'temperature':0,'max_tokens':2048,'stream':False,'store':False}
    require(len(dumps(payload).encode())<=MAX_REQUEST_BYTES,'Request exceeds byte bound; no truncation')
    return payload


def normalized_logical(payload,provider):
    require(provider=='nebius','Only Nebius routing is supported')
    return {'system':payload['messages'][0]['content'],'user':payload['messages'][1]['content']}


def plan(bundle, config, *, mode=None, selected=None):
    require(digest(bundle['logical'])==bundle['logical_input_sha256'] and
        digest(bundle['authoritative'])==bundle['authoritative_input_sha256'] and
        bundle['logical']=={'system':load_prompt('linkedin_writer'),'user':dumps(bundle['projected'])} and
        bundle['projection_manifest']['model_input_sha256']==digest(bundle['projected']) and
        bundle['projection_manifest']['authoritative_input_sha256']==digest(bundle['authoritative']) and
        set(bundle['projected'])==set(bundle['authoritative']) and all(bundle['projected'][k]==bundle['authoritative'][k]
            for k in bundle['authoritative'] if k!='research_context'), 'Logical/evidence binding differs')
    check_config(config);config=deepcopy(config);mode=config['default_mode'] if mode is None else mode
    require(mode in {'single','comparison'},'Unknown execution mode')
    if selected is None:
        selected=[config['single_selected_model']] if mode=='single' else [m['key'] for m in config['models'] if m['enabled']]
    require(type(selected) is list and 0<len(selected)<=config['max_requests'] and len(set(selected))==len(selected),'Invalid model selection')
    require(mode!='single' or len(selected)==1,'Single mode cannot fan out')
    by_key={m['key']:m for m in config['models']}
    require(all(k in by_key and by_key[k]['enabled'] for k in selected),'Disabled or unknown model selected')
    entries=[]
    for key in selected:
        model=by_key[key];payload=translate(bundle['logical'],model)
        require(normalized_logical(payload,model['provider'])==bundle['logical'],'Provider translation changed logical task')
        entries.append({'model':model,'payload':payload,'provider_request_sha256':hashlib.sha256(dumps(payload).encode()).hexdigest()})
    return {'mode':mode,'config_sha256':digest(config),'logical_input_sha256':bundle['logical_input_sha256'],
        'authoritative_input_sha256':bundle['authoritative_input_sha256'],'entries':entries,
        'aggregate_cost_ceiling_usd':config['aggregate_cost_ceiling_usd']}


class Reservation:
    """Reserve all models atomically before dispatch; one attempt each, no refunds.

Unknown billing retains the entire reservation. This is a one-run ledger; a
consumed protected output directory is the durable replay guard across processes.
"""
    def __init__(self):
        self.lock=Lock();self.reserved=False;self.attempts=set();self.amounts={};self.total=Decimal(0)

    def reserve(self, prepared, approval):
        with self.lock:
            require(not self.reserved,'Comparison run already reserved')
            expected={'owner_authorized','authorization_reference','config_sha256','logical_input_sha256','mode',
                'selected_models','aggregate_cost_ceiling_usd','acknowledge_setting_differences','models'}
            require(type(approval) is dict and set(approval)==expected and approval['owner_authorized'] is True and
                type(approval['authorization_reference']) is str and bool(approval['authorization_reference'].strip()) and
                approval['acknowledge_setting_differences'] is True,'Separate owner authorization required')
            keys=[e['model']['key'] for e in prepared['entries']]
            require(approval['config_sha256']==prepared['config_sha256'] and
                approval['logical_input_sha256']==prepared['logical_input_sha256'] and approval['mode']==prepared['mode'] and
                approval['selected_models']==keys and type(approval['models']) is dict and set(approval['models'])==set(keys),
                'Authorization scope/bindings differ')
            aggregate=money(approval['aggregate_cost_ceiling_usd'])
            require(aggregate<=money(prepared['aggregate_cost_ceiling_usd']),'Aggregate ceiling expanded')
            amounts={};qualifications={}
            for entry in prepared['entries']:
                model=entry['model'];key=model['key'];info=approval['models'][key];pricing=model['pricing']
                require(type(info) is dict and set(info)=={'provider_request_sha256','access_confirmed','source_permissions_confirmed',
                    'input_token_upper_bound','token_bound_evidence','per_model_cost_ceiling_usd'},'Missing qualification fields')
                require(info['provider_request_sha256']==entry['provider_request_sha256'] and info['access_confirmed'] is True and
                    info['source_permissions_confirmed'] is True,'Provider access or source permission unresolved')
                bound=info['input_token_upper_bound']
                require(type(bound) is int and 0<bound<=model['input_token_ceiling'] and
                    type(info['token_bound_evidence']) is str and bool(info['token_bound_evidence'].strip()),'Verified provider token bound required')
                require(pricing['status']=='published' and pricing['input_per_million_usd'] is not None and
                    pricing['output_per_million_usd'] is not None,'Provider pricing unresolved; entire run blocked')
                cap=money(info['per_model_cost_ceiling_usd'])
                require(cap<=money(model['per_model_cost_ceiling_usd']),'Per-model ceiling expanded')
                amount=(Decimal(bound)*money(pricing['input_per_million_usd'])+Decimal(2048)*money(pricing['output_per_million_usd']))/Decimal(1_000_000)
                require(amount<=cap,'Per-model reservation exceeds ceiling')
                amounts[key]=amount;qualifications[key]=deepcopy(info)
            require(sum(amounts.values())<=aggregate,'Aggregate reservation exceeds ceiling')
            self.amounts=amounts;self.total=sum(amounts.values());self.qualifications=qualifications;self.reserved=True
            return {'per_model_usd':{k:str(v) for k,v in amounts.items()},'total_usd':str(self.total),
                'unknown_billing_policy':'Retain full reservation; no retry or further dispatch'}

    def claim(self,key):
        with self.lock:
            require(self.reserved and key in self.amounts and key not in self.attempts,'Attempt denied')
            self.attempts.add(key)


@dataclass(frozen=True)
class WireResponse:
    status: int
    body: bytes
    headers: dict
    credential_redacted: bool = False
    truncated: bool = False


class ProtectedStore:
    def __init__(self,path):
        self.path=Path(path)
        self.path.mkdir(parents=True,mode=0o700,exist_ok=False)
    def write(self,name,value, *, raw=False):
        require(re.fullmatch(r'[a-z0-9_-]+\.(?:json|bin|md)',name) is not None,'Unsafe artifact name')
        path=self.path/name
        with path.open('xb') as f:
            path.chmod(0o600)
            f.write(value if raw else (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())


def citation_inventory(candidate,allowed):
    if type(candidate) is not dict or type(candidate.get('claim_references')) is not list:return None
    refs=candidate['claim_references'];fields=[];empty=[];ineligible=[]
    for i,ref in enumerate(refs):
        if type(ref) is not dict:continue
        if type(ref.get('content_field')) is str:fields.append(ref['content_field'])
        ids=ref.get('claim_ids')
        if ids==[]:empty.append(i)
        if type(ids) is list:ineligible += [v for v in ids if type(v) is str and v not in allowed]
    return {'empty_entry_indexes':empty,'duplicate_fields':sorted({f for f in fields if fields.count(f)>1}),
        'ineligible_ids':sorted(set(ineligible)),'inspection_only':'Inventory, not additional reached validation rules'}


def text_and_usage(value,model):
    require(type(value) is dict and value.get('model')==model['model_id'],'Response model identity differs')
    usage=value.get('usage');require(type(usage) is dict,'Usage missing')
    require(model['provider']=='nebius','Only Nebius routing is supported')
    choices=value.get('choices')
    require(type(choices) is list and len(choices)==1,'Invalid response choices')
    choice=choices[0];message=choice.get('message',{})
    require(choice.get('finish_reason')=='stop' and message.get('role')=='assistant' and
        not message.get('tool_calls') and not message.get('refusal') and type(message.get('content')) is str,'Incomplete/nontext response')
    text=message['content'];n=usage.get('prompt_tokens');out=usage.get('completion_tokens')
    reason=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens')
    require(all(type(v) is int and v>=0 for v in [n,out]) and (reason is None or type(reason) is int and reason>=0),'Invalid usage counters')
    return text,{'input_tokens':n,'output_tokens':out,'reasoning_tokens':reason,'reasoning_counter_reported':reason is not None,'provider_usage':deepcopy(usage)}


def inspect_wording(candidate):
    """Literal flags only, never an independent semantic Reviewer result."""
    content=candidate.get('content',{}) if type(candidate) is dict else {}
    text=' '.join(v for v in content.values() if type(v) is str) if type(content) is dict else ''
    return {'method':'literal triage only; human evidence review required',
        'manufacturer_voice_flag':bool(re.search(r'\bour\b|\bwe\b',text,re.I)),
        'ice_cream_detail_flag':bool(re.search(r'ice[ -]cream',text,re.I)),
        'semantic_acceptance':'not_assessed','human_review_required':True}


def run(bundle,config, *, mode=None,selected=None,execute=False,approval=None,transport_factory=None,output=None,transport_kind=None):
    # Freeze copies before concurrency. Neither workers nor transports receive original authority.
    bundle=deepcopy(bundle);prepared=plan(bundle,config,mode=mode,selected=selected)
    if not execute:
        return {'status':'OFFLINE_ONLY','mode':prepared['mode'],'config_sha256':prepared['config_sha256'],
            'logical_input_sha256':prepared['logical_input_sha256'],'provider_calls':0,
            'proposed_aggregate_cost_ceiling_usd':prepared['aggregate_cost_ceiling_usd'],'results':[
            {'key':e['model']['key'],'provider':e['model']['provider'],'model_id':e['model']['model_id'],
             'execution_status':'not_executed','contract_status':'not_tested','provider_request_sha256':e['provider_request_sha256'],
             'proposed_per_model_cost_ceiling_usd':e['model']['per_model_cost_ceiling_usd'],
             'pricing':e['model']['pricing'],'settings_differences':e['model']['settings_differences'],
             'blockers':['Separate owner authorization','Account/source access and model-specific token qualification']+
                (['Current model pricing unresolved'] if e['model']['pricing']['status']!='published' else [])}
            for e in prepared['entries']]}
    require(transport_factory is not None and output is not None and transport_kind in {'mock','live'},'Explicit transport kind and protected output required')
    ledger=Reservation();reserved=ledger.reserve(prepared,approval)
    store=ProtectedStore(output)  # Exclusive durable run claim before dispatch; never reuse after a failure.
    store.write('reservation.json',{'authorization':deepcopy(approval),'reservation':reserved,'plan':prepared,
        'logical_input_sha256':bundle['logical_input_sha256']})
    store.write('authoritative-input.json',bundle['authoritative']);store.write('projected-input.json',bundle['projected'])
    store.write('projection-manifest.json',bundle['projection_manifest'])
    def worker(entry):
        model=entry['model'];key=model['key'];start=time.monotonic()
        result={'key':key,'provider':model['provider'],'model_id':model['model_id'],
            'logical_input_sha256':bundle['logical_input_sha256'],'provider_request_sha256':entry['provider_request_sha256'],
            'execution_status':'not_sent','contract_status':'not_tested','candidate':None,'diagnostic':None,
            'citation_findings':None,'usage':None,'estimated_cost_usd':None,'billing_status':'unknown_reservation_retained',
            'semantic_findings':{'semantic_acceptance':'not_assessed','human_review_required':True}}
        phase='transport'
        try:
            ledger.claim(key);store.write(key+'-attempt.json',{'attempt':1,'request_sha256':entry['provider_request_sha256']})
            # Construct only the selected provider after all aggregate checks and durable attempt record.
            wire=transport_factory(model)(deepcopy(entry['payload']))
            require(type(wire) is WireResponse and type(wire.body) is bytes,'Invalid transport result')
            store.write(key+'-response.bin',wire.body,raw=True)  # Before parsing or any admission.
            result.update(http_status=wire.status,telemetry=wire.headers,response_sha256=hashlib.sha256(wire.body).hexdigest(),
                credential_redacted=wire.credential_redacted,response_truncated=wire.truncated)
            require(not wire.credential_redacted and not wire.truncated,'Redacted or oversized response unusable')
            require(wire.status==200,'Provider request failed')
            phase='provider_response'
            value=strict_json(wire.body);result['provider_response']=deepcopy(value)
            text,usage=text_and_usage(value,model);result.update(response_content=text,usage=usage,execution_status='returned')
            phase='usage_qualification'
            info=ledger.qualifications[key]
            require(usage['input_tokens']<=info['input_token_upper_bound'] and usage['output_tokens']<=2048 and
                usage['reasoning_tokens'] in {None,0},'Usage/budget or reasoning deviation; reservation retained')
            cost=(Decimal(usage['input_tokens'])*money(model['pricing']['input_per_million_usd'])+
                Decimal(usage['output_tokens'])*money(model['pricing']['output_per_million_usd']))/Decimal(1_000_000)
            require(cost<=ledger.amounts[key],'Observed cost exceeds reservation')
            result.update(estimated_cost_usd=str(cost),billing_status='uncached_list_rate_estimate_not_invoice')
            phase='candidate_json'
            candidate=strict_json(text);result['candidate']=deepcopy(candidate)
            result['citation_findings']=citation_inventory(candidate,set(bundle['authoritative']['draft_constraints']['allowed_claim_ids']))
            result['semantic_findings']=inspect_wording(candidate)
            phase='draft_validation'
            try:
                admitted=admit_output(candidate,deepcopy(bundle['authoritative']))
                result.update(contract_status='accepted_unreviewed',draft=admitted)
            except DraftValidationError as error:
                result.update(contract_status='rejected',diagnostic={'stage':'draft_validation','code':error.code,**error.diagnostic})
        except Exception:
            if result['execution_status']=='not_sent':result['execution_status']='failed_or_unknown'
            if phase=='candidate_json':result['contract_status']='invalid_json'
            if result['diagnostic'] is None:
                result['diagnostic']={'stage':phase,'code':'unusable_response_or_unknown_billing',
                    'field_path':None,'rule':'unknown_validation_failure'}
        finally:
            result['elapsed_seconds']=round(time.monotonic()-start,3)
            # Each result survives independently; later models never erase it.
            store.write(key+'-result.json',result)
        return result
    results={}
    with ThreadPoolExecutor(max_workers=len(prepared['entries'])) as pool:
        futures={pool.submit(worker,e):e['model']['key'] for e in prepared['entries']}
        for future in as_completed(futures):results[futures[future]]=future.result()
    report={'status':'COMPLETED_FOR_REVIEW','execution_kind':transport_kind,'mode':prepared['mode'],'config_sha256':prepared['config_sha256'],
        'logical_input_sha256':bundle['logical_input_sha256'],'reservation':reserved,
        'attempted_models':sorted(ledger.attempts),'provider_calls_max':len(ledger.attempts),'automatic_retries':0,'automatic_repairs':0,
        'results':[results[e['model']['key']] for e in prepared['entries']]}
    store.write('report.json',report);store.write('review.md',render(report).encode(),raw=True)
    return report


def render(report):
    lines=['# Writer comparison — human review required','',
        'MOCKED PROVIDERS — not live compatibility or quality evidence.' if report.get('execution_kind')=='mock' else 'Execution: '+report.get('execution_kind',report.get('status','unknown')),
        '','Contract acceptance is not semantic acceptance. No independent Reviewer findings.','',
        '| Model / provider | Execution | Contract | Empty / duplicate / ineligible refs | Input / output | Estimated USD | Seconds | Human review |',
        '|---|---|---|---|---|---|---|---|']
    for r in report['results']:
        inv=r.get('citation_findings');usage=r.get('usage') or {}
        refs='not inspected' if inv is None else '/'.join(str(len(inv[k])) for k in ['empty_entry_indexes','duplicate_fields','ineligible_ids'])
        lines.append(f"| {r['model_id']} / {r['provider']} | {r['execution_status']} | {r['contract_status']} | {refs} | {usage.get('input_tokens','?')} / {usage.get('output_tokens','?')} | {r.get('estimated_cost_usd') or 'unknown'} | {r.get('elapsed_seconds','?')} | required |")
    for r in report['results']:
        lines+=['','## '+r['key'],'','Precise diagnostic: '+json.dumps(r.get('diagnostic')),
            '','Evidence/voice triage: '+json.dumps(r.get('semantic_findings',{'semantic_acceptance':'not_assessed'})),
            '','Exact returned output (untrusted):','```text',r.get('response_content','No usable text; inspect protected raw response if present.'),'```']
    return '\n'.join(lines)+'\n'
