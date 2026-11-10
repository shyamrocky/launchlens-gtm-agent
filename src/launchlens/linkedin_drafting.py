"""One bounded LinkedIn writing call; no retrieval, credentials or file provisioning.

The harness owns admission and draft metadata. Shape/reference/CTA checks do not
establish prose entailment; admitted output remains unreviewed until a later stage.
"""
from copy import deepcopy
import hashlib
import re

from launchlens.content_contracts import (COMMON_REVIEW_CRITERIA, ContractError, load_template,
                                        model_output_schema, validate_draft, validation_detail)
from launchlens.evidence_payload import storage_fields
from launchlens.gtm_registry import objective_claims, supported_use_cases, validate_request
from launchlens.live_research import (MODEL, MAX_REQUEST_BYTES, MAX_WRITER_OUTPUT_TOKENS,
    PROMPTS, ResearchError, dumps, load_prompt, require, strict_json)
from launchlens.model_context import build_context, canonical, expand_packet
from launchlens.notion_tools import PMM_PAGE
from launchlens.retrieval import checked_packet
from launchlens.voice_policy import voice_brief, voice_prompt

CTA = "What would you like to know about Cherry Float's flavor inspiration?"
# Deliberately limited detection of explicit links; not a semantic marketing classifier.
LINK = re.compile(r"[a-z][a-z0-9+.-]*://|www\.|\b[a-z0-9][a-z0-9.-]*\.[a-z]{2,63}\b|\[[^\]]*\]\([^)]*\)", re.I)

FORBIDDEN = re.compile(r"\b(?:buy|shop|order)\s+now\b|\bavailable\s+(?:now|today)\b|"
    r"\bin\s+stores?\s+(?:now|today)\b|[$£€₹]\s*\d|\b\d+(?:\.\d+)?\s*%|"
    r"\b(?:discount|promo\s+code|limited[- ]time\s+offer)\b", re.I)


class DraftValidationError(ResearchError):
    """Application-owned diagnostic code; never echoes model/provider text."""
    def __init__(self, code, *, field_path=None, rule="unknown_validation_failure"):
        allowed = {"structure_or_evidence_reference", "objective_claim_coverage", "cta_mismatch",
                   "prohibited_link", "prohibited_wording"}
        self.code = code if type(code) is str and code in allowed else "unknown_validation_failure"
        self.diagnostic = validation_detail(field_path, rule)
        super().__init__('Draft rejected: ' + self.code)


def draft_require(condition, code, field_path):
    if not condition:
        raise DraftValidationError(code, field_path=field_path, rule=code)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def prepare_input(state):
    """Fail before inference unless current protected state admits this draft."""
    request = validate_request(state['request'])
    require(state['mode'] in {'live_linkedin', 'offline_review', 'offline_package', 'live_package'} and (request['market_id'] == 'US' or (request['market_id']=='UK' and state['mode'] in {'offline_package','live_package'})),
            'This checkpoint supports US LinkedIn drafting only')
    launch, pmm = state['launch'], state['pmm']
    from launchlens.launch_checks import availability_only_gap
    restricted = (availability_only_gap(launch) and state.get('restricted_drafting') == {
        'request_sha256':digest(request),'launch_sha256':digest(launch),'availability_wording_allowed':False})
    require(type(launch) is dict and launch.get('authority') == 'synthetic_launch_decision'
            and launch.get('product_id') == request['product_id']
            and launch.get('market_id') == request['market_id']
            and launch.get('evaluation_date') == request['evaluation_date']
            and ((launch.get('decision') == 'Proceed' and launch.get('conditions') == []
            and launch.get('promotional_draft_allowed') is True) or restricted)
            and launch.get('publishing_allowed') is False, 'Drafting permission is absent')
    require(type(pmm) is dict and pmm.get('status') == 'ok' and pmm.get('page_id') == PMM_PAGE
            and pmm.get('authority') == 'synthetic_pmm_guidance'
            and type(pmm.get('blocks')) is list and pmm['blocks'], 'Complete PMM guidance required')
    required = set(objective_claims(request))
    rows, identities = {}, {}
    for result in state['evidence']:
        for row in result['records']:
            unit = row.get('unit_id')
            if unit not in required:
                continue
            p = row['evidence_payload'];fields = storage_fields(p)
            require(row.get('authority') == 'public_product_facts' and unit == p['unit_id']
                    and row['chunk_id'] == p['chunk_id'] and row['evidence_sha256'] == fields['evidence_sha256']
                    and p.get('chunk_kind') == 'product_claim' and p.get('claim_source_mappings'),
                    'Required public evidence is invalid')
            checked_packet({'id':row['chunk_id'], 'metadata':fields}, 'public_product_facts')
            identity = (row['chunk_id'], fields['evidence_sha256'])
            require(unit not in identities or identities[unit] == identity, 'Conflicting objective evidence')
            identities[unit] = identity
            if row.get('usable_as_complete_evidence') is True and row.get('reference_status') in {'resolved','not_expanded'}:
                rows[unit] = deepcopy(row)
    require(set(rows) == required, 'Complete objective evidence is missing')
    selected = [rows[k] for k in sorted(required)]
    context = build_context({'pmm':pmm, 'launch':launch, 'evidence':[{
        'status':'evidence_found', 'requested_authority':'public_product_facts',
        'product_id':request['product_id'], 'records':selected, 'issues':[],
        'selection':'Two complete objective claims only; other research stays in harness state'}]})
    result = {'validated_request':request,
        'objective_label':supported_use_cases()[0]['objectives'][0]['label'],
        'template':load_template('linkedin'), 'output_schema':model_output_schema('linkedin'),
        'common_review_criteria':list(COMMON_REVIEW_CRITERIA), 'research_context':context,
        'draft_constraints':{'internal_draft_only':True, 'exact_cta':CTA,
            'allowed_claim_ids':sorted(required), 'urls_allowed':False,
            'availability_wording_allowed':False, 'offers_allowed':False}}
    policy_id = state.get('voice_policy_id')
    if policy_id is not None:
        require(state['mode'] in {'offline_review', 'offline_package', 'live_package'}, 'New writing policy is offline-only')
        result['voice_policy'] = voice_brief(policy_id)
    return result


def writer_instructions(inputs):
    policy = inputs.get('voice_policy')
    if policy is None:
        return load_prompt('linkedin_writer')
    require(type(policy) is dict and policy == voice_brief(policy.get('policy_id')),
            'Writing policy binding differs')
    return voice_prompt('linkedin_writer', policy['policy_id'])


def evidence_records(inputs):
    context = inputs['research_context']
    return [{**row, 'evidence_payload':expand_packet(context,row['packet_ref'])}
            for result in context['retrieval_results'] for row in result['records']]


def admit_output(value, inputs):
    """Return app-owned metadata only after hard checks; no semantic approval."""
    records = evidence_records(inputs)
    try:
        validation = validate_draft(value, format_name='linkedin', evidence_records=records)
    except ContractError as error:
        detail = error.diagnostic
        raise DraftValidationError('structure_or_evidence_reference', **detail) from None
    referenced = {claim for ref in value['claim_references'] for claim in ref['claim_ids']}
    draft_require(referenced == set(inputs['draft_constraints']['allowed_claim_ids']), 'objective_claim_coverage', 'claim_references')
    draft_require(value['content']['cta'] == CTA, 'cta_mismatch', 'content.cta')
    strings = [("content." + k, value['content'][k]) for k in ('hook','body','cta')]
    strings += [("content.hashtags." + str(i), text) for i, text in enumerate(value['content']['hashtags'])]
    for path, text in strings:
        draft_require(not LINK.search(text), 'prohibited_link', path)
    for path, text in strings:
        draft_require(not FORBIDDEN.search(text), 'prohibited_wording', path)
    return {'version':1, 'review_status':'unreviewed', 'human_accepted':False,
        'publishing_allowed':False, 'draft':deepcopy(value), 'validation':validation,
        'input_sha256':digest(inputs), 'writer_prompt_sha256':PROMPTS['linkedin_writer'],
        'evidence_bindings':[{'unit_id':r['unit_id'], 'chunk_id':r['chunk_id'],
                              'evidence_sha256':r['evidence_sha256']} for r in records]}


def writer_request(inputs, prompt=None):
    """Exact existing provider-request serialization contract; no network call."""
    return {'model':MODEL, 'messages':[{'role':'system','content':writer_instructions(inputs) if prompt is None else prompt},
                {'role':'user','content':dumps(inputs)}],
        'temperature':0, 'max_tokens':MAX_WRITER_OUTPUT_TOKENS, 'stream':False, 'store':False}


class LinkedInWriter:
    """One attempt/run; same inference client/budget as the action controller."""
    def __init__(self, transport, *, context_projector=None):
        require(context_projector is None or callable(context_projector), 'Invalid context projector')
        self._context_projector = context_projector  # Harness-owned, never model-selected.
        self._transport = transport
        self._prompt = load_prompt('linkedin_writer')
        self.calls = []

    def reset_run(self):
        self.calls.clear()  # Shared HTTP budget is cleared by the controller reset.

    def __call__(self, inputs):
        require('voice_policy' not in inputs, 'This live adapter remains on the historical writing policy')
        require(not self.calls, 'Writing already attempted; no retry')
        model_input = deepcopy(inputs)
        projection = None
        if self._context_projector is not None:
            projection = self._context_projector(deepcopy(inputs))
            model_input = deepcopy(projection['model_input'])
            require(set(model_input) == set(inputs) and all(model_input[k] == inputs[k]
                    for k in inputs if k != 'research_context'), 'Projection changed non-context contract')
            require(projection['manifest']['authoritative_input_sha256'] == digest(inputs)
                    and projection['manifest']['model_input_sha256'] == digest(model_input),
                    'Projection identity differs')
        payload = writer_request(model_input, self._prompt)
        require(len(dumps(payload).encode('utf-8')) <= MAX_REQUEST_BYTES,
                'Writing input exceeds byte bound; no trimming')
        event = {'outcome':'attempted', 'input_sha256':digest(inputs), 'input':deepcopy(inputs)}
        if projection is not None:
            event.update(model_input=deepcopy(model_input), model_input_sha256=digest(model_input),
                         projection_manifest=deepcopy(projection['manifest']),
                         request_sha256=hashlib.sha256(dumps(payload).encode()).hexdigest())
        self.calls.append(event)
        try:
            response = self._transport(payload)
            require(response.get('model') == MODEL and type(response.get('choices')) is list
                    and len(response['choices']) == 1, 'Invalid writing response')
            choice = response['choices'][0];message = choice.get('message', {})
            require(choice.get('finish_reason') == 'stop' and message.get('role') == 'assistant'
                    and not message.get('tool_calls') and type(message.get('content')) is str,
                    'Writing response is incomplete or not plain JSON content')
            event['response_content'] = message['content']  # Untrusted final candidate, protected audit only.
            result = strict_json(message['content'])
            event['candidate'] = deepcopy(result)
            event['outcome'] = 'returned_for_validation'
            return result
        except Exception:
            event['outcome'] = 'failed'
            raise ResearchError('Writing unavailable or invalid; no retry') from None
