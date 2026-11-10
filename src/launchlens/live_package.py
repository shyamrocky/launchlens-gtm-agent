"""Prepared one-run live adapters for the existing harness; disabled without approval.

No credential/network/filesystem mutation at import or preflight. Same source tools,
projection, controller and content validators. One bounded citation-only retry;
no automatic evidence repairs or demo fallback.
"""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
from threading import Lock

from launchlens.content_review import ContentCall
from launchlens.gtm_registry import HarnessError, require, supported_use_cases, validate_request
from launchlens.linkedin_drafting import digest
from launchlens.live_research import (MODEL, ResearchModel, LiveResearchTools, ENDPOINT,
    MAX_REQUEST_BYTES, dumps, strict_json, tool_schemas)
from launchlens.package_content import CONFIG_SHA256, configuration, load_package_prompt
from launchlens.voice_policy import BRAND_POLICY_ID, POLICY_SHA256
from launchlens.writer_context import load_policy, project_writer_input
from launchlens.writer_comparison import ProtectedStore, money
from launchlens.writer_providers import ProviderHTTP, read_selected_keys

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT/'data/templates/gtm/live_package_profile_v11.json'
# Owner scope: registered run, explicit human revision cycles within unchanged spending.
# A fixed protected output directory consumes Start once, even with standing budget.
AUTHORIZATION = ROOT/'data/private/d037-fresh-us-authorization.json'
BUILD_LEDGER = ROOT/'data/private/build-budget-20261109.json'
PROFILE_SHA256 = 'e2606a87d3bae59e61db295a00e4c949fe189460b4eb4e5d032bf7ba5d75bae0'
ROLES = ('controller','package_writer','package_reviewer','package_revision')


class LiveGateError(HarnessError):
    """Fixed messages only; no provider/credential content."""


def gate(ok, message):
    if not ok: raise LiveGateError(message)


def profile():
    raw = PROFILE.read_bytes()
    gate(hashlib.sha256(raw).hexdigest() == PROFILE_SHA256, 'Live profile changed; owner review required')
    value = strict_json(raw)
    gate(set(value['roles']) == set(ROLES) and value['max_model_calls'] == 12 and value['max_required_review_calls'] is None and value['revision_policy']=='explicit_human_max_three_v1' and value['roles']['package_revision']['max_attempts']==configuration()['limits']['revision_attempts']==3 and value['max_searches'] == 4,
         'Unreviewed live execution limits')
    configuration()  # Verify package prompt/template bindings as well.
    return value


def preflight():
    cfg = profile(); amounts = {}
    for role, model in cfg['roles'].items():
        output = model['max_completion_tokens']; bound = model['context_tokens'] - output
        one = (Decimal(bound)*money(model['input_per_million_usd'])+
               Decimal(output)*money(model['output_per_million_usd']))/Decimal(1_000_000)
        amounts[role] = {'max_attempts':model['max_attempts'],'input_token_upper_bound':bound,
            'completion_token_cap':output,'per_call_reservation_usd':str(one),
            'role_reservation_usd':str(one*(0 if role=='package_revision' else 1 if role=='package_reviewer' else model['max_attempts'])),'model_id':model['model_id']}
    total = sum(Decimal(v['role_reservation_usd']) for v in amounts.values())
    scope = {'profile_sha256':PROFILE_SHA256,'package_sha256':CONFIG_SHA256,
        'voice_policy_sha256':POLICY_SHA256,'projection_sha256':digest(load_policy()),
        'registry':supported_use_cases(),'request':cfg['request']}
    return {'status':'PREPARED_NOT_AUTHORIZED','scope_sha256':digest(scope),'profile_sha256':PROFILE_SHA256,
        'request':deepcopy(cfg['request']),'roles':amounts,'reservation_total_usd':str(total),
        'proposal_ceiling_usd':cfg['proposal_ceiling_usd'],'max_model_calls':12,'max_required_review_calls':None,
        'automatic_retries':1,'automatic_retry_policy':'missing_citations_only_known_usage_standing_budget','automatic_repairs':0,'generation_calls':0,'credentials_read':False,
        'token_method':cfg['qualification']['token_reservation_method']}


def authorization_template():
    plan = preflight()
    return {'owner_authorized':False,'authorization_id':'OWNER-SET-UNIQUE-ID',
        'authorization_reference':'Separate explicit owner approval required',
        'scope_sha256':plan['scope_sha256'],'request':plan['request'],
        'aggregate_ceiling_usd':plan['proposal_ceiling_usd'],'source_permissions_confirmed':False,
        'acknowledge_catalog_not_entitlement':False,'acknowledge_context_reservation_and_cap_assumptions':False,
        'allow_explicit_revisions':True,'allow_one_explicit_writer_retry':True,'bound_run_id':None,'standing_budget':False,'expires_utc':'OWNER-SET-ISO-UTC'}


def validate_authorization(value, *, now=None):
    plan = preflight(); cfg = profile(); expected = set(authorization_template())
    gate(type(value) is dict and set(value) == expected and value['owner_authorized'] is True,
         'Separate explicit live-run authorization required')
    gate(type(value['authorization_id']) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,64}',value['authorization_id']),
         'Unique authorization ID required')
    gate(type(value['authorization_reference']) is str and 0 < len(value['authorization_reference'].strip()) <= 200,
         'Owner authorization reference required')
    gate(value['scope_sha256'] == plan['scope_sha256'] and value['request'] == plan['request'],
         'Authorization task or frozen profile differs')
    gate(value['source_permissions_confirmed'] is True and value['acknowledge_catalog_not_entitlement'] is True
         and value['acknowledge_context_reservation_and_cap_assumptions'] is True
         and type(value['allow_explicit_revisions']) is bool and type(value['allow_one_explicit_writer_retry']) is bool, 'Required source/capability acknowledgments unresolved')
    if value['bound_run_id'] is not None:
        from uuid import UUID
        try:gate(str(UUID(value['bound_run_id']))==value['bound_run_id'],'Invalid bound run identity')
        except (TypeError,ValueError,AttributeError):raise LiveGateError('Invalid bound run identity') from None
    ceiling = money(value['aggregate_ceiling_usd'])
    gate(type(value['standing_budget']) is bool and
         (max(Decimal(r['per_call_reservation_usd']) for r in plan['roles'].values()) if value['standing_budget'] else Decimal(plan['reservation_total_usd'])) <= ceiling <= money(cfg['proposal_ceiling_usd']),
         'Ceiling cannot cover whole-run reservation or exceeds proposed limit')
    try:
        current = datetime.now(timezone.utc) if now is None else now
        expiry = datetime.fromisoformat(value['expires_utc'])
        checked = datetime.fromisoformat(cfg['checked_utc'])
        gate(expiry.tzinfo is not None and current.tzinfo is not None and
             current < expiry and 0 <= (current-checked).total_seconds() <= cfg['qualification_max_age_seconds']
             and (expiry-checked).total_seconds() <= cfg['qualification_max_age_seconds'],
             'Authorization or catalog qualification expired')
    except (TypeError, ValueError):
        raise LiveGateError('Invalid authorization expiry') from None
    return plan


def read_authorization(path=AUTHORIZATION):
    path = Path(path)
    gate(path.is_file() and not path.is_symlink() and not path.stat().st_mode & 0o077,
         'Private owner authorization file unavailable')
    raw = path.read_bytes(); gate(len(raw) <= 8000, 'Authorization exceeds bound')
    result = strict_json(raw); validate_authorization(result)
    return result


def readiness(path=AUTHORIZATION):
    try:
        permission = read_authorization(path)
        gate(profile().get('hosted_schema_qualified') is True or permission.get('standing_budget') is True, 'Hosted schema qualification pending')
        output = ROOT/'data/generated'/('live-package-'+permission['authorization_id'])
        gate(not output.exists(), 'Authorization already consumed; no rerun')
        return {'ready':True,'request':deepcopy(permission['request']),'message':'One separately authorized US run is available.'}
    except Exception:
        return {'ready':False,'request':None,'message':'Live execution awaits separate owner authorization and spending qualification.'}


class StandingBudget:
    """Code-owned private JSON ledger, locked across processes; no credentials."""
    def __init__(self,path=None):self.path=Path(path) if path else BUILD_LEDGER
    def _update(self,operation):
        import fcntl,os
        gate(self.path.is_file() and not self.path.is_symlink() and not self.path.stat().st_mode&0o077,'Standing budget not provisioned privately')
        with self.path.open('r+') as stream:
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX)
            value=strict_json(stream.read());gate(value['ceiling_usd']=='1.00','Standing ceiling differs')
            result=operation(value)
            accounted=Decimal(value['opening_accounted_usd'])+sum(Decimal(e.get('estimated_usd',e['reserved_usd'])) for e in value['claims'])
            gate(accounted<=Decimal(value['ceiling_usd']),'Standing model budget exhausted')
            value['accounted_usd']=str(accounted);value['remaining_usd']=str(Decimal(value['ceiling_usd'])-accounted)
            stream.seek(0);stream.write(json.dumps(value,indent=2)+'\n');stream.truncate();stream.flush();os.fsync(stream.fileno())
            return deepcopy(value) if result is None else result
    def read(self):
        import fcntl
        gate(self.path.is_file() and not self.path.is_symlink() and not self.path.stat().st_mode&0o077,'Standing budget not provisioned privately')
        with self.path.open('r') as stream:
            fcntl.flock(stream.fileno(),fcntl.LOCK_SH)
            return deepcopy(strict_json(stream.read()))
    def claim(self,role,reserved,request_sha):
        from uuid import uuid4
        identity=uuid4().hex
        def update(value):
            value['claims'].append({'id':identity,'role':role,'request_sha256':request_sha,'reserved_usd':reserved,'status':'reserved_unknown_until_usage'})
            return identity
        return self._update(update)
    def reserve_revision(self,amounts,binding_sha):
        """Atomically reserve BOTH future calls before any revision inference."""
        from uuid import uuid4
        ids={r:uuid4().hex for r in amounts}
        def update(value):
            gate(not any(e.get('cycle_binding_sha256')==binding_sha for e in value['claims']),'This version already has a revision reservation')
            for role,amount in amounts.items():
                value['claims'].append({'id':ids[role],'role':role,'request_sha256':'human-cycle:'+binding_sha,
                    'reserved_usd':str(amount),'status':'reserved_unknown_until_usage','reservation_kind':'explicit_human_revision','cycle_binding_sha256':binding_sha})
            return ids
        return self._update(update)

    def bind_revision_call(self,identity,role,request_sha):
        def update(value):
            entry=next(e for e in value['claims'] if e['id']==identity)
            gate(entry['role']==role and entry['status']=='reserved_unknown_until_usage' and entry['request_sha256'].startswith('human-cycle:'),
                'Reserved revision claim is already used or differs')
            entry['request_sha256']=request_sha
        self._update(update)

    def complete(self,identity,cost,usage):
        def update(value):
            entry=next(e for e in value['claims'] if e['id']==identity)
            gate(entry['status']=='reserved_unknown_until_usage' and cost<=Decimal(entry['reserved_usd']),'Invalid standing settlement')
            entry.update(estimated_usd=str(cost),usage=deepcopy(usage),status='usage_accounted')
        return self._update(update)


class RunBudget:
    """Reserve the complete role plan once; claims are atomic and never refunded."""
    def __init__(self, permission, *, store=None, now=None):
        self.plan = validate_authorization(permission,now=now)
        self.permission = deepcopy(permission); self.store = store
        self.stop_at_first_review = profile().get('stop_at_first_review') is True
        self._now = now
        self.lock = Lock(); self.armed = False; self.closed = False; self.active = False
        self.counts = {r:0 for r in ROLES}; self.events = []; self.cost = Decimal(0)
        self.standing=StandingBudget() if permission.get('standing_budget') is True else None
        self.pending_revision_claims={}

    def restore_accounting(self, summary, state, *, review_recovery=False, stopped_display=False):
        gate(not self.armed and not self.events and (summary.get('stopped') is False or review_recovery or stopped_display),
             'Only an idle, known-accounting checkpoint can resume')
        gate(self.permission['bound_run_id'] in {None,state['run_id']},'Authorization belongs to another run')
        counts=summary.get('attempts');events=summary.get('events')
        gate(type(counts) is dict and set(counts)==set(ROLES) and
            all(type(n) is int and n>=0 and (self.plan['roles'][r]['max_attempts'] is None or n<=self.plan['roles'][r]['max_attempts']) for r,n in counts.items()) and
            type(events) is list and len(events)==sum(counts.values()) and sum(n for r,n in counts.items() if r not in {'package_reviewer','package_revision'})<=12 and
            (len(events)==state['turns'] or (review_recovery and state['turns']==len(events)+1 and
                state['events'][-1].get('action')=='model_adapter' and state['events'][-1].get('outcome')=='failed_safely')),
            'Checkpoint counters differ')
        gate(all(e.get('sequence')==i+1 and e.get('role') in ROLES and e.get('status')=='usage_accounted'
            for i,e in enumerate(events)), 'Unknown prior billing cannot resume')
        gate(all(sum(e['role']==r for e in events)==counts[r] for r in ROLES),'Role counters differ')
        total=sum(Decimal(e['estimated_cost_usd']) for e in events)
        gate(total==Decimal(summary['estimated_usage_cost_usd']), 'Prior usage total differs')
        if self.standing:
            ledger={e['id']:e for e in self.standing.read()['claims']}
            gate(all(e.get('standing_claim_id') in ledger and
                ledger[e['standing_claim_id']]['status']=='usage_accounted' and
                ledger[e['standing_claim_id']]['request_sha256']==e['wire_request_sha256'] and
                Decimal(ledger[e['standing_claim_id']]['estimated_usd'])==Decimal(e['estimated_cost_usd'])
                for e in events),'Standing ledger binding differs')
        self.counts=deepcopy(counts);self.events=deepcopy(events);self.cost=total
        self.armed=True;self.closed=stopped_display or summary.get('stopped') is True;self.active=False
        self.pending_revision_claims=deepcopy(summary.get('pending_revision_claims',{}))
        gate(set(self.pending_revision_claims)<={'package_revision','package_reviewer'},'Unknown pending revision claims')
        if self.standing:
            ledger={e['id']:e for e in self.standing.read()['claims']}
            gate(all(v.get('id') in ledger and ledger[v['id']]['role']==r and ledger[v['id']]['status']=='reserved_unknown_until_usage' for r,v in self.pending_revision_claims.items()),'Pending revision reservation differs')

    def arm(self, request):
        with self.lock:
            validate_authorization(self.permission,now=self._now)
            gate(not self.armed and not self.closed and request == self.permission['request'],
                 'Authorization is consumed or request differs')
            self.armed = True

    def claim(self, role, request_hash):
        with self.lock:
            validate_authorization(self.permission,now=self._now)
            gate(type(request_hash) is str and re.fullmatch(r'[0-9a-f]{64}',request_hash), 'Request identity required')
            gate(self.armed and not self.closed and not self.active and role in self.counts,
                 'Live request not armed, overlapping or stopped')
            gate((role in {'package_reviewer','package_revision'} or sum(n for r,n in self.counts.items() if r not in {'package_reviewer','package_revision'}) < 12) and (self.plan['roles'][role]['max_attempts'] is None or self.counts[role] < self.plan['roles'][role]['max_attempts']),
                 'Whole-run or role attempt budget exhausted')
            gate(role != 'package_revision' or self.permission['allow_explicit_revisions'],
                 'Owner did not authorize a revision')
            gate(role != 'package_writer' or self.counts[role]==0 or self.permission['allow_one_explicit_writer_retry'],
                 'Owner did not authorize a Writer retry')
            gate(role!='package_revision' or role in self.pending_revision_claims,'Explicit current-version revision reservation required')
            gate(not self.pending_revision_claims or role in self.pending_revision_claims,'Revision cycle is reserved for its Writer and Reviewer only')
            reservation=self.pending_revision_claims.get(role)
            gate(self.cost+Decimal(self.plan['roles'][role]['per_call_reservation_usd'])+sum(Decimal(v['reserved_usd']) for r,v in self.pending_revision_claims.items() if r!=role)<=money(self.permission['aggregate_ceiling_usd']),'Model spending ceiling exhausted')
            self.counts[role] += 1; self.active = True
            event = {'sequence':len(self.events)+1,'role':role,'wire_request_sha256':request_hash,
                'reserved_usd':self.plan['roles'][role]['per_call_reservation_usd'],'status':'attempted'}
            if self.standing:
                try:
                    if reservation:
                        self.standing.bind_revision_call(reservation['id'],role,request_hash);event['standing_claim_id']=reservation['id']
                    else:event['standing_claim_id']=self.standing.claim(role,event['reserved_usd'],request_hash)
                except Exception:
                    self.closed=True;self.active=False;raise
            self.pending_revision_claims.pop(role,None)
            self.events.append(event); return event

    def complete(self, event, value):
        with self.lock:
            gate(self.active and self.events[-1] is event, 'Invalid completion identity')
            gate(type(value) is dict and value.get('model') == profile()['roles'][event['role']]['model_id'],
                 'Response model identity differs; billing unresolved')
            usage = value.get('usage')
            bounds = self.plan['roles'][event['role']]
            gate(type(usage) is dict and all(type(usage.get(k)) is int and usage[k] >= 0
                for k in ['prompt_tokens','completion_tokens','total_tokens']) and
                usage['total_tokens'] == usage['prompt_tokens']+usage['completion_tokens'] and
                usage['prompt_tokens'] <= bounds['input_token_upper_bound'] and
                usage['completion_tokens'] <= bounds['completion_token_cap'], 'Unknown usage or published bound exceeded')
            details = usage.get('completion_tokens_details')
            if details is not None:
                gate(type(details) is dict and (details.get('reasoning_tokens') is None or
                    type(details['reasoning_tokens']) is int and 0 <= details['reasoning_tokens'] <= usage['completion_tokens']),
                    'Reasoning/output accounting inconsistent')
            m = profile()['roles'][event['role']]
            estimate = (Decimal(usage['prompt_tokens'])*money(m['input_per_million_usd'])+
                Decimal(usage['completion_tokens'])*money(m['output_per_million_usd']))/Decimal(1_000_000)
            gate(estimate <= Decimal(event['reserved_usd']), 'Usage estimate exceeds reservation')
            if self.standing:self.standing.complete(event['standing_claim_id'],estimate,usage)
            self.cost += estimate; self.active = False
            event.update(status='usage_accounted',usage=deepcopy(usage),estimated_cost_usd=str(estimate))

    def stop(self):
        with self.lock:
            self.closed = True; self.active = False

    def reopen_for_saved_writer(self,state):
        """Explicit owner-directed known-billing checkpoint; counters never reset."""
        validate_authorization(self.permission,now=self._now)
        with self.lock:
            gate(self.armed and not self.active and not self.pending_revision_claims and
                self.permission['bound_run_id']==state['run_id'] and
                state['status']=='failed' and not state['drafts'] and state['package'] is None and
                state['writing_attempts']==self.counts['package_writer']==1 and
                state['retry_attempts']==0 and state['review_attempts']==self.counts['package_reviewer']==0 and
                state['turns']==len(self.events)==sum(self.counts.values()) and
                all(e['status']=='usage_accounted' for e in self.events),
                'Saved Writer checkpoint lacks explicit scope or known accounting')
            self.closed=False

    def can_review_saved(self, state):
        try:validate_authorization(self.permission,now=self._now)
        except Exception:return False
        with self.lock:
            count=sum(self.counts.values())
            return (self.armed and not self.active and
                state['mode']=='live_package' and state['status'] in {'failed','stopped'} and
                (state.get('package') or {}).get('version',0)>=2 and state['revision_attempts']>=1 and
                state['pending'] is None and not state['review'] and state['human_accepted'] is False and
                state['review_attempts']==self.counts['package_reviewer'] and
                self.counts['package_revision']>=1 and len(self.events)==count and
                all(e['status']=='usage_accounted' for e in self.events) and
                (state['turns']==count or (state['turns']==count+1 and
                    state['events'][-1].get('action')=='model_adapter' and state['events'][-1].get('outcome')=='failed_safely')))

    def reopen_for_saved_review(self, state):
        gate(self.can_review_saved(state), 'Saved review lacks known accounting or remaining budget')
        with self.lock:self.closed=False  # Reopen only for this explicit required review; never reset counters.

    def _revision_available(self):
        amounts={r:Decimal(self.plan['roles'][r]['per_call_reservation_usd']) for r in ('package_revision','package_reviewer')}
        total=sum(amounts.values())
        available=self.counts['package_revision']<self.plan['roles']['package_revision']['max_attempts'] and self.armed and not self.closed and not self.active and not self.pending_revision_claims and self.permission['allow_explicit_revisions'] and all(e['status']=='usage_accounted' for e in self.events) and self.cost+total<=money(self.permission['aggregate_ceiling_usd'])
        if available and self.standing:available=Decimal(self.standing.read()['remaining_usd'])>=total
        return available,amounts

    def can_revise(self):
        try:
            validate_authorization(self.permission,now=self._now)
            with self.lock:return self._revision_available()[0]
        except Exception:return False

    def reserve_revision(self,binding):
        validate_authorization(self.permission,now=self._now)
        with self.lock:
            available,amounts=self._revision_available()
            gate(available,'Revision requires explicit authorization, known usage and budget for Writer plus review')
            ids=self.standing.reserve_revision(amounts,digest(binding)) if self.standing else {r:None for r in amounts}
            self.pending_revision_claims={r:{'id':ids[r],'reserved_usd':str(amount)} for r,amount in amounts.items()}

    def can_retry_writer(self):
        try:validate_authorization(self.permission,now=self._now)
        except Exception:return False
        with self.lock:
            return (self.armed and not self.closed and not self.active and
                self.permission['allow_one_explicit_writer_retry'] and self.counts['package_writer']==1
                and all(e['status']=='usage_accounted' for e in self.events)
                and sum(n for r,n in self.counts.items() if r not in {'package_reviewer','package_revision'})+2<=12 and self.counts['controller']<self.plan['roles']['controller']['max_attempts'])

    def summary(self):
        return {'reserved_usd':self.plan['reservation_total_usd'],'estimated_usage_cost_usd':str(self.cost),
            'attempts':dict(self.counts),'stopped':self.closed,'events':deepcopy(self.events),
            'pending_revision_claims':deepcopy(self.pending_revision_claims),
            'call_limits':{'research_task_calls':12,'human_revision_calls':3,'required_review_calls':'approved spending'},
            'call_usage':{'research_task_calls':sum(n for r,n in self.counts.items() if r not in {'package_reviewer','package_revision'}),
                          'human_revision_calls':self.counts['package_revision'],'required_review_calls':self.counts['package_reviewer']},
            'unknown_billing_policy':'Retain full reservation and stop; never retry',
            'standing_budget':self.standing.read() if self.standing else None}


class LiveTransport:
    """Role-scoped adapter around existing one-shot HTTP; raw capture before parsing."""
    def __init__(self, role, budget, keys, *, wire_factory=None):
        gate(role in ROLES, 'Unsupported live role')
        self.role,self.guard,self.keys,self.wire_factory = role,budget,dict(keys),wire_factory

    @staticmethod
    def _valid_controller_tools(tools):
        if not isinstance(tools,list) or not tools:return False
        registry={t['function']['name']:t for t in tool_schemas('live_package')}
        names=[t.get('function',{}).get('name') for t in tools if isinstance(t,dict)]
        return (len(names)==len(tools)==len(set(names)) and 'review_package' not in names and
            all(name in registry and tool==registry[name] for name,tool in zip(names,tools)))

    def reset_run(self):
        self.guard.stop()  # Never clear a spent authorization on Reset/Generate again.

    def __call__(self, payload):
        spec = profile()['roles'][self.role]
        gate(type(payload) is dict and payload.get('model') == spec['model_id'] and
            payload.get('temperature') == 0 and payload.get('store') is False and payload.get('stream') is False
            and payload.get('max_tokens') == spec['max_completion_tokens'], 'Unreviewed live role settings')
        common = {'model','messages','temperature','max_tokens','stream','store'}
        if self.role == 'controller':
            gate(set(payload) == common|{'tools','tool_choice','parallel_tool_calls'} and
                self._valid_controller_tools(payload['tools']) and payload['tool_choice'] == 'auto' and
                payload['parallel_tool_calls'] is False, 'Unreviewed live actions')
            stage = 'package_controller'
        else:
            gate(set(payload) == common and len(payload.get('messages',[])) == 2 and
                 payload['messages'][1].get('role') == 'user', 'Unreviewed content envelope')
            stage = self.role
        gate(payload['messages'][0] == {'role':'system','content':load_package_prompt(stage)}, 'Prompt binding differs')
        wire = deepcopy(payload);wire['max_completion_tokens'] = spec['max_completion_tokens']
        if spec.get('reasoning_effort') is not None:wire['reasoning_effort']=spec['reasoning_effort']
        if self.role != 'controller':
            from launchlens.structured_output import response_format
            content = strict_json(wire['messages'][1]['content'])
            wire['response_format'] = response_format(content['output_schema'])
        raw_request = dumps(wire).encode()
        gate(len(raw_request) <= MAX_REQUEST_BYTES and not any(v.encode() in raw_request for v in self.keys.values()),
             'Request exceeds bound or contains credentials')
        event = self.guard.claim(self.role,hashlib.sha256(raw_request).hexdigest())
        prefix = 'call-'+str(event['sequence']).zfill(2)
        store = self.guard.store
        try:
            if store:
                store.write(prefix+'-request.json',wire)
                store.write(prefix+'-claim.json',deepcopy(event))
            model = {'provider':'nebius','model_id':spec['model_id']}
            validator = lambda candidate: candidate == wire
            http = (ProviderHTTP(model,self.keys['NEBIUS_API_KEY'],request_validator=validator,timeout_seconds=180 if self.role!='controller' else 45)
                    if self.wire_factory is None else self.wire_factory(model,validator))
            response = http(wire)
            body = response.body
            redacted = response.credential_redacted
            for secret in self.keys.values():
                if secret.encode() in body:
                    body = body.replace(secret.encode(),b'[REDACTED_CREDENTIAL]');redacted = True
            if store:
                store.write(prefix+'-response.bin',body,raw=True)
                store.write(prefix+'-http.json',{'status':response.status,'headers':redact(response.headers,tuple(self.keys.values())),
                    'credential_redacted':redacted,'truncated':response.truncated,
                    'body_sha256':hashlib.sha256(body).hexdigest()})
            gate(response.status == 200 and not redacted and not response.truncated, 'Provider failure; no retry')
            value = strict_json(body)
            self.guard.complete(event,value)
            if store:store.write(prefix+'-usage.json',deepcopy(event))
            return value
        except Exception:
            self.guard.stop();event['status'] = 'stopped_no_retry'
            if store:
                try:store.write(prefix+'-failure.json',{'code':'transport_response_or_usage_failed','reservation_retained':True})
                except Exception:pass
            raise LiveGateError('Live response or accounting unavailable; stopped without retry') from None


class LivePackageRun:
    """Thin UI/CLI command adapter; all execution stays in FoundationSession."""
    kind = 'live'
    package = True
    scenario = None

    def __init__(self, permission, keys, *, notes='', tools=None, wire_factory=None, store=None, now=None, checkpoint=None, review_recovery=False, stopped_display=False):
        from launchlens.agent_foundation import FoundationSession
        from launchlens.notion_tools import NotionHTTP, NotionReader
        from launchlens.retrieval import PineconeHTTP
        self.guard = RunBudget(permission,store=store,now=now)
        gate(set(keys) == {'NEBIUS_API_KEY','NOTION_API_KEY','PINECONE_API_KEY'} and
             all(type(v) is str and len(v) >= 12 and not any(c.isspace() for c in v) for v in keys.values()),
             'Required private service credentials unavailable')
        self.store = store; self._saved = set(); self._secrets = tuple(keys.values())
        transports = {r:LiveTransport(r,self.guard,keys,wire_factory=wire_factory) for r in ROLES}
        self.controller = ResearchModel(transports['controller'],mode='live_package')
        self.writer,self.reviewer,self.reviser = [ContentCall(transports[r],stage=r,
            model_id=profile()['roles'][r]['model_id'],projector=(project_writer_input if permission['request']['market_id']=='US' else __import__('launchlens.package_content',fromlist=['project_package_context']).project_package_context))
            for r in ['package_writer','package_reviewer','package_revision']]
        self.tools = tools if tools is not None else LiveResearchTools(NotionReader(NotionHTTP(keys['NOTION_API_KEY'])),PineconeHTTP(keys['PINECONE_API_KEY']))
        self.session = FoundationSession(self.controller,self.tools,mode='live_package',writer=self.writer,
            reviewer=self.reviewer,revision_writer=self.reviser,voice_policy_id=BRAND_POLICY_ID,execution_guard=self.guard)
        if checkpoint is None:self.session.start(permission['request'],user_notes=notes)
        else:
            state,capture=checkpoint
            gate(state['request']==permission['request'],'Checkpoint task differs')
            self.guard.restore_accounting(capture['spending'],state,review_recovery=review_recovery,stopped_display=stopped_display)
            for name,adapter in [('controller',self.controller),('writer',self.writer),('review',self.reviewer),('revision',self.reviser)]:
                adapter.calls=deepcopy(capture[name])
            self.session.restore_review_checkpoint(state,review_recovery=review_recovery,stopped_display=stopped_display)
            if self.store:
                for path in self.store.path.glob('state-*.json'):
                    self._saved.add(digest(strict_json(path.read_bytes())))

    def snapshot(self):return self.session.snapshot()
    def execute(self, run_id, *, on_update=None):
        def checkpoint(update,state):
            self._persist(state)
            if on_update is not None:return on_update(update,state)
        state = self.session.run(run_id,on_update=checkpoint)
        if self.guard.permission.get('standing_budget') and state['status']=='draft_incomplete' and (state.get('draft_failure') or {}).get('rule') in {'field_claim_coverage','objective_claim_coverage'} and self.session.can_retry_writer():
            state=self.session.retry_writer(run_id,on_update=checkpoint)
        try:self._save(state)
        except Exception:
            self.guard.stop()
            raise LiveGateError('Protected execution capture unavailable; stopped without retry') from None
        return state
    def can_review_saved(self):return self.session.can_review_saved()
    def review_saved(self, run_id, *, on_update=None):
        try:return self.session.review_saved(run_id,on_update=on_update)
        finally:self._save(self.snapshot())
    def recheck_review(self, run_id):
        # A separate one-shot adapter is permitted for this explicit same-version
        # recheck; ordinary exact-binding replay protection stays unchanged.
        rechecker=ContentCall(self.reviewer._transport,stage='package_reviewer',
            model_id=self.reviewer._model,projector=self.reviewer._projector)
        try:return self.session.recheck_package_review(run_id,rechecker)
        finally:
            self.reviewer.calls.extend(rechecker.calls)
            self._save(self.snapshot())

    def request_revision(self, run_id, feedback, *, draft_version, draft_sha256):
        permission=self.session.check_revision(run_id,feedback,draft_version=draft_version,draft_sha256=draft_sha256)
        self.guard.reserve_revision(permission['binding'])
        result = self.session.request_revision(run_id,feedback,draft_version=draft_version,draft_sha256=draft_sha256)
        self._persist(result)
        return result

    def edit_current_fields(self,run_id,changes,*,draft_version,draft_sha256):
        result=self.session.edit_current_fields(run_id,changes,draft_version=draft_version,draft_sha256=draft_sha256)
        self._persist(result)
        return result

    def revise(self, run_id, feedback, version, sha):
        self.request_revision(run_id,feedback,draft_version=version,draft_sha256=sha)
        return self.execute(run_id)
    def continue_run(self,run_id,*,on_update=None):
        state=self.session.continue_run(run_id,on_update=on_update);self._save(state);return state
    def resume(self,run_id,reply,*,on_update=None):
        state=self.session.resume(run_id,reply,on_update=on_update);self._save(state);return state
    def recover_writer_candidate(self,run_id,*,on_update=None):
        calls=self.writer.calls
        gate(len(calls)==1 and 'candidate' in calls[0],'Saved Writer candidate unavailable')
        try:return self.session.recover_writer_candidate(run_id,deepcopy(calls[0]['candidate']),on_update=on_update)
        finally:self._save(self.snapshot())

    def retry_writer(self,run_id,*,on_update=None):
        state=self.session.retry_writer(run_id,on_update=on_update);self._save(state);return state
    def stop(self,run_id):
        self.session.stop(run_id);self._save(self.snapshot())
    def reset(self):
        self.session.reset();self.guard.stop()
    def capture(self):
        return deepcopy({'controller':self.controller.calls,'writer':self.writer.calls,
            'review':self.reviewer.calls,'revision':self.reviser.calls,'spending':self.guard.summary(),
            'source_events':{'notion':getattr(getattr(getattr(self.tools,'_notion',None),'transport',None),'events',[]),
                             'pinecone':getattr(getattr(self.tools,'_pinecone',None),'events',[])}})
    def _save(self, state):
        if state['status'] == 'failed' and not self.session.can_retry_writer():self.guard.stop()
        self._persist(state)

    def _persist(self,state):
        identity = digest(state)
        if self.store and identity not in self._saved:
            n = str(len(self._saved)+1).zfill(2)
            self.store.write('state-'+n+'.json',redact(state,self._secrets))
            self.store.write('capture-'+n+'.json',redact(self.capture(),self._secrets))
            self._saved.add(identity)
            self._advance_current_pointer(state,self.store.path/('state-'+n+'.json'),self.store.path/('capture-'+n+'.json'))

    def _advance_current_pointer(self,state,state_path,capture_path):
        """Advance this same run only, atomically after both private receipts exist."""
        pointer=ROOT/'data/private/current-live-run.json'
        if not self.store.path.resolve().is_relative_to((ROOT/'data/generated').resolve()) or not pointer.is_file():return
        gate(not pointer.is_symlink() and not pointer.stat().st_mode & 0o077,'Current pointer must remain private')
        spec=strict_json(pointer.read_bytes())
        if (ROOT/spec['store']).resolve()!=self.store.path.resolve():return
        prior=strict_json((ROOT/spec['state']['path']).read_bytes())
        gate(prior['run_id']==state['run_id'],'Current pointer belongs to another run')
        for key,path in [('state',state_path),('capture',capture_path)]:
            spec[key]={'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        import os
        from uuid import uuid4
        temporary=pointer.with_name('.current-live-run-'+uuid4().hex+'.tmp')
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        try:
            with os.fdopen(fd,'w') as stream:stream.write(json.dumps(spec,indent=2)+'\n');stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,pointer)
        finally:
            if temporary.exists():temporary.unlink()


def redact(value, secrets):
    if type(value) is str:
        for secret in secrets:value=value.replace(secret,'[REDACTED_CREDENTIAL]')
        return value
    if type(value) is list:return [redact(v,secrets) for v in value]
    if type(value) is dict:return {redact(k,secrets):redact(v,secrets) for k,v in value.items()}
    return value


def create_live_run(request, notes='', *, authorization_path=AUTHORIZATION):
    request = validate_request(request)
    permission = read_authorization(authorization_path)
    gate(permission['bound_run_id'] is None,'This authorization permits revisions of the saved run only')
    gate(request == permission['request'], 'Only the separately authorized US scenario can execute')
    gate(profile().get('hosted_schema_qualified') is True or permission.get('standing_budget') is True, 'Hosted schema qualification pending')
    plan = validate_authorization(permission)  # Whole-run admission before credentials or source/model clients.
    keys = read_selected_keys({'NEBIUS_API_KEY','NOTION_API_KEY','PINECONE_API_KEY'},ROOT/'.env')
    gate(not any(v in dumps(permission) or v in notes for v in keys.values()), 'Credential present in authorization or notes')
    try:store = ProtectedStore(ROOT/'data/generated'/('live-package-'+permission['authorization_id']))
    except FileExistsError:raise LiveGateError('Authorization already consumed; no rerun') from None
    store.write('authorization.json',permission);store.write('reservation.json',plan)
    return LivePackageRun(permission,keys,notes=notes,store=store)


def current_resume_available():
    import os
    return os.environ.get('LAUNCHLENS_UI_MODE')!='offline' and (ROOT/'data/private/current-live-run.json').is_file()


def load_current_live_run():
    """Explicit UI resume from hash-bound private receipts; zero provider calls."""
    pointer=ROOT/'data/private/current-live-run.json'
    gate(pointer.is_file() and not pointer.is_symlink() and not pointer.stat().st_mode&0o077,
        'Current run receipt unavailable')
    spec=strict_json(pointer.read_bytes());loaded={}
    gate(set(spec)=={'state','capture','authorization','store'},'Invalid current run pointer')
    for name in ['state','capture','authorization']:
        entry=spec[name];relative=Path(entry['path'])
        gate(not relative.is_absolute() and '..' not in relative.parts,'Invalid current receipt path')
        path=ROOT/relative;base=ROOT/('data/private' if name=='authorization' else 'data/generated')
        gate(path.resolve().is_relative_to(base.resolve()) and path.is_file() and not path.is_symlink()
            and not path.stat().st_mode&0o077 and path.stat().st_size<16_000_000,'Invalid private current receipt')
        raw=path.read_bytes();gate(hashlib.sha256(raw).hexdigest()==entry['sha256'],'Current receipt changed')
        loaded[name]=strict_json(raw)
    store_path=ROOT/spec['store'];gate(store_path.resolve().is_relative_to((ROOT/'data/generated').resolve()),'Invalid current store')
    gate((ROOT/spec['state']['path']).parent==store_path and (ROOT/spec['capture']['path']).parent==store_path,
        'Current store differs from receipts')
    gate(max(store_path.glob('state-*.json'),key=lambda p:int(p.stem.rsplit('-',1)[1]))==ROOT/spec['state']['path'] and
        max(store_path.glob('capture-*.json'),key=lambda p:int(p.stem.rsplit('-',1)[1]))==ROOT/spec['capture']['path'],
        'A newer current checkpoint exists; stale counters cannot resume')
    validate_authorization(loaded['authorization'])
    from launchlens.package_content import authoritative_package_binding
    state=loaded['state']
    stopped_display=state['status']=='failed' and state.get('package') is None and not state['drafts']
    if not stopped_display:authoritative_package_binding(state)
    recovery=state['status'] in {'failed','stopped'} and (state.get('package') or {}).get('version',0)>=2 and not state['review']
    gate(recovery or stopped_display or (state['status']=='awaiting_human_review' and bool(state.get('review')) and
        (state['review'].get('review_complete') is True or state['package']['version']>=2)),
        'Current review checkpoint is unavailable')
    # Recheck the grouped raw result independently; do not trust persisted statuses.
    from launchlens.package_content import validate_package_review
    if not recovery and not stopped_display and state['review'].get('assessment_policy')=='human_edit_rescan_v1':
        from launchlens.package_content import verify_human_edit_review
        verify_human_edit_review(state)
    elif not recovery and not stopped_display:gate(validate_package_review(state['review']['raw_response'],state,isolate_findings=state['review'].get('assessment_policy')=='isolated_findings_v1',scan_additions=state['review'].get('scan_additions',False))==state['review'],'Current review changed')
    keys=read_selected_keys({'NEBIUS_API_KEY','NOTION_API_KEY','PINECONE_API_KEY'},ROOT/'.env')
    return LivePackageRun(loaded['authorization'],keys,checkpoint=(state,loaded['capture']),
        store=ProtectedStore.open_existing(store_path),review_recovery=recovery,stopped_display=stopped_display)
