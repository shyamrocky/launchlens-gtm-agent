"""Independent review and revision contracts; injected transports, no credentials/IO.

Offline harness integration only in M2.3c. A valid review is a model assessment,
not factual proof, human acceptance or launch permission. Full original evidence
continues to govern backend admission independently of the model-facing projection.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import re
import time

from launchlens.linkedin_drafting import admit_output, digest, prepare_input, writer_instructions
from launchlens.live_research import dumps, load_prompt, strict_json, MAX_REQUEST_BYTES
from launchlens.voice_policy import voice_prompt

DIMENSIONS = ('grounding', 'qualifications', 'voice', 'tone', 'consistency', 'completeness')
STATUSES = {'pass', 'needs_changes', 'uncertain'}
PROMPTS = {'linkedin_reviewer': 'eb768eda3ca371e929e90d42ca742264377a3067857918f30b5e816758172fdb', 'linkedin_revision': 'eadeeea3f02dff5ee414ba2aa2932057725c3f568b5549d9b5788e878e14cf7c'}


class ReviewError(ValueError):
    """Bounded diagnostics only; candidate and raw response stay in protected state."""
    def __init__(self, code, field_path='$'):
        codes = {'invalid_structure', 'invalid_reference', 'invalid_quote', 'inconsistent_assessment',
                 'stale_binding', 'permission_denied', 'invalid_projection', 'attempt_limit',
                 'invalid_response', 'invalid_json', 'request_too_large', 'operation_failed'}
        fields = {'assessments', 'findings', 'dimension', 'status', 'content_field', 'quote',
                  'severity', 'rationale', 'suggested_change', 'claim_ids', 'binding'}
        safe = field_path == '$' or (type(field_path) is str and len(field_path) < 160 and
            all(x in fields or re.fullmatch(r'0|[1-9][0-9]{0,2}', x) for x in field_path.split('.')))
        self.diagnostic = {'code': code if code in codes else 'operation_failed',
                           'field_path': field_path if safe else '$'}
        super().__init__('Content review/revision rejected: ' + self.diagnostic['code'])


def check(condition, code='invalid_structure', path='$'):
    if not condition:
        raise ReviewError(code, path)


def load_review_prompt(stage):
    check(stage in PROMPTS)
    raw = Path(__file__).with_name('prompts').joinpath(stage + '.txt').read_bytes()
    check(hashlib.sha256(raw).hexdigest() == PROMPTS[stage])
    return raw.decode()


def review_schema():
    text = {'type':'string', 'minLength':1}
    def obj(properties):
        return {'type':'object', 'properties':properties, 'required':list(properties), 'additionalProperties':False}
    return obj({
        'assessments':{'type':'array','minItems':6,'maxItems':6,'items':obj({
            'dimension':{'type':'string','enum':list(DIMENSIONS)},
            'status':{'type':'string','enum':sorted(STATUSES)}})},
        'findings':{'type':'array','maxItems':20,'items':obj({
            'dimension':{'type':'string','enum':list(DIMENSIONS)},
            'content_field':text, 'quote':text,
            'severity':{'type':'string','enum':['blocking','advisory']},
            'rationale':text, 'suggested_change':text,
            'claim_ids':{'type':'array','maxItems':2,'uniqueItems':True,
                         'items':{'type':'string','enum':['PROD-002','PROD-003']}}})}})


def authoritative_binding(state):
    """Revalidate original authority, not the smaller model view or a model verdict."""
    inputs = prepare_input(state)
    record = state['drafts'].get('linkedin')
    check(type(record) is dict, 'stale_binding', 'binding')
    original = admit_output(record['draft'], inputs)
    check(record['input_sha256'] == digest(inputs) and
          record['evidence_bindings'] == original['evidence_bindings'] and
          type(record['version']) is int and record['version'] in {1, 2}, 'stale_binding', 'binding')
    binding = {'run_id':state['run_id'], 'draft_version':record['version'],
               'draft_sha256':digest(record['draft']), 'authoritative_input_sha256':digest(inputs)}
    return inputs, record, binding


def model_brief(inputs, projector=None):
    if projector is None:
        return deepcopy(inputs), None
    projection = projector(deepcopy(inputs))
    model = projection['model_input']; manifest = projection['manifest']
    check(set(model) == set(inputs) and all(model[k] == inputs[k] for k in inputs if k != 'research_context')
          and manifest['authoritative_input_sha256'] == digest(inputs)
          and manifest['model_input_sha256'] == digest(model), 'invalid_projection')
    # The only allowed projector is application-owned; accepted span rules preserve
    # material caveats/conflicts/qualifications. The model cannot select a projector.
    return deepcopy(model), deepcopy(manifest)


def prepare_review(state, *, projector=None):
    inputs, record, binding = authoritative_binding(state)
    brief, manifest = model_brief(inputs, projector)
    revision_context = None
    if binding['draft_version'] == 2:
        previous = [r for r in state['reviews'] if r['binding']['draft_version'] == 1]
        check(len(previous) == 1 and state.get('revision_feedback'), 'stale_binding', 'binding')
        revision_context = {'owner_feedback':state['revision_feedback'],
                            'previous_review':deepcopy(previous[0]['assessment'])}
    return {'binding':binding, 'writer_brief':brief, 'draft':deepcopy(record['draft']),
            'revision_context':revision_context,
            'writing_instructions':writer_instructions(inputs),
            'review_criteria':list(inputs['common_review_criteria']),
            'editorial_warnings':deepcopy(record['validation']['editorial_warnings']),
            'output_schema':review_schema(), 'projection_manifest':manifest}


def validate_review(value, state):
    """Validate coverage, exact quotations and eligible IDs; NOT semantic entailment."""
    inputs, record, binding = authoritative_binding(state)
    return validate_assessment(value, inputs, record, binding)


def validate_assessment(value, inputs, record, binding, *, resolve_field=None):
    """Shared exact-quote/coverage validator; caller independently binds authority."""
    def keys(item, expected, path):
        check(type(item) is dict and set(item) == set(expected), path=path)
    keys(value, ['assessments','findings'], '$')
    check(type(value['assessments']) is list and len(value['assessments']) == 6, path='assessments')
    assessments = {}
    for i, item in enumerate(value['assessments']):
        path = f'assessments.{i}'
        keys(item, ['dimension','status'], path)
        check(type(item['dimension']) is str and item['dimension'] in DIMENSIONS and
              item['dimension'] not in assessments, path=path + '.dimension')
        check(type(item['status']) is str and item['status'] in STATUSES, path=path + '.status')
        assessments[item['dimension']] = item['status']
    check(type(value['findings']) is list and len(value['findings']) <= 20, path='findings')
    seen = set(); findings = []
    for i, finding in enumerate(value['findings']):
        path = f'findings.{i}'
        keys(finding, ['dimension','content_field','quote','severity','rationale','suggested_change','claim_ids'], path)
        for field in ['dimension','content_field','quote','severity','rationale','suggested_change']:
            check(type(finding[field]) is str and finding[field].strip() and len(finding[field]) <= 1200,
                  path=path + '.' + field)
        check(finding['dimension'] in DIMENSIONS and finding['severity'] in {'blocking','advisory'}, path=path)
        field = finding['content_field']; content = record['draft']['content']
        if resolve_field is not None:
            target = resolve_field(content, field)
        elif field in {'hook','body','cta'}:
            target = content[field]
        elif re.fullmatch(r'hashtags\.(0|[1-9][0-9]{0,2})', field):
            index = int(field.split('.')[1])
            check(index < len(content['hashtags']), 'invalid_reference', path + '.content_field')
            target = content['hashtags'][index]
        else:
            raise ReviewError('invalid_reference', path + '.content_field')
        check(finding['quote'] in target, 'invalid_quote', path + '.quote')
        ids = finding['claim_ids']
        check(type(ids) is list and len(ids) <= 2 and all(type(c) is str for c in ids)
              and len(set(ids)) == len(ids) and set(ids) <= set(inputs['draft_constraints']['allowed_claim_ids']),
              'invalid_reference', path + '.claim_ids')
        identity = digest(finding)
        check(identity not in seen, path=path); seen.add(identity)
        findings.append(deepcopy(finding))
    for dimension, status in assessments.items():
        blocking = any(f['dimension'] == dimension and f['severity'] == 'blocking' for f in findings)
        check((status != 'pass') == blocking, 'inconsistent_assessment', 'assessments')
    return {'binding':binding, 'assessment':deepcopy(value),
            'review_status':'changes_requested' if any(s != 'pass' for s in assessments.values()) else 'reviewed_for_human',
            'human_accepted':False, 'publishing_allowed':False}


def prepare_revision(state, *, projector=None):
    inputs, record, binding = authoritative_binding(state)
    permission = state.get('revision_request'); review = state.get('review')
    check(type(permission) is dict and type(review) is dict and review.get('binding') == binding
          and permission.get('binding') == binding and permission.get('review_sha256') == digest(review),
          'permission_denied', 'binding')
    check(type(permission.get('feedback')) is str and 0 < len(permission['feedback'].strip()) <= 2000,
          'permission_denied')
    brief, manifest = model_brief(inputs, projector)
    return {'binding':binding, 'writer_brief':brief, 'previous_draft':deepcopy(record['draft']),
            'review':deepcopy(review['assessment']), 'owner_feedback':permission['feedback'],
            'writing_instructions':writer_instructions(inputs), 'projection_manifest':manifest}


class ContentCall:
    """Independent injected model call; no default model/provider or network setup.

    Only offline mock transports are wired by this checkpoint. Future hosted wiring
    requires explicit model/configuration/cost approval; no live CLI is supplied.
    Complete returned response is captured before parsing. No retries or repairs.
    """
    def __init__(self, transport, *, stage, model_id, projector=None):
        check(callable(transport) and stage in {'linkedin_reviewer','linkedin_revision','package_writer','package_reviewer','package_revision'})
        check(type(model_id) is str and model_id.strip() and len(model_id) <= 120)
        self._transport, self._stage, self._model = transport, stage, model_id
        self._projector = projector
        self.calls = []

    def reset_run(self):
        self.calls.clear()

    def __call__(self, state):
        package_stage = self._stage.startswith('package_')
        maximum = __import__('launchlens.package_content',fromlist=['configuration']).configuration()['limits']['review_attempts'] if self._stage == 'package_reviewer' else 2 if self._stage in {'linkedin_reviewer','package_writer'} else 1
        check(len(self.calls) < maximum, 'attempt_limit')
        if package_stage:
            from launchlens.package_content import prepare_call, load_package_prompt
            inputs = prepare_call(state, self._stage, projector=self._projector)
        else:
            inputs = (prepare_review(state, projector=self._projector) if maximum == 2 else
                      prepare_revision(state, projector=self._projector))
        retry = self._stage == 'package_writer' and state.get('writer_retry') is True and len(self.calls)==1
        if self._stage == 'package_writer' and self.calls:check(retry,'attempt_limit','binding')
        check(retry or not any(c['binding'] == inputs['binding'] for c in self.calls), 'attempt_limit', 'binding')
        policy_id = state.get('voice_policy_id')
        instructions = (load_package_prompt(self._stage) if package_stage else
            voice_prompt(self._stage, policy_id) if policy_id is not None else load_review_prompt(self._stage))
        model_inputs = deepcopy(inputs)
        if retry:
            model_inputs['previous_validation_diagnostic_data_only'] = deepcopy(state['draft_failure'])
        if package_stage:
            model_inputs.pop('projection_manifest', None)  # Audit ledger stays outside model context.
        payload = {'model':self._model, 'messages':[
            {'role':'system','content':instructions},
            {'role':'user','content':dumps(model_inputs)}],
            'temperature':0, 'max_tokens':(__import__('launchlens.package_content',fromlist=['configuration']).configuration()['limits']['review_output_tokens'] if self._stage == 'package_reviewer' else 8192) if package_stage else 2048, 'stream':False, 'store':False}
        check(len(dumps(payload).encode()) <= MAX_REQUEST_BYTES, 'request_too_large')
        event = {'binding':deepcopy(inputs['binding']), 'input_sha256':digest(inputs),
                 'request_sha256':digest(payload), 'input':deepcopy(inputs), 'outcome':'attempted'}
        if package_stage:
            event.update(model_input=deepcopy(model_inputs), model_input_sha256=digest(model_inputs))
        self.calls.append(event); started = time.monotonic()
        try:
            response = self._transport(deepcopy(payload))
            event['response'] = deepcopy(response)
            check(type(response) is dict and response.get('model') == self._model and
                  type(response.get('choices')) is list and len(response['choices']) == 1, 'invalid_response')
            choice = response['choices'][0]; message = choice.get('message', {})
            if type(message) is dict and type(message.get('content')) is str:
                event['response_content'] = message['content']
            check(choice.get('finish_reason') == 'stop' and message.get('role') == 'assistant' and
                  type(message.get('content')) is str and not message.get('tool_calls'), 'invalid_response')
            try:
                candidate = strict_json(message['content'])
            except Exception:
                raise ReviewError('invalid_json') from None
            event['raw_candidate'] = deepcopy(candidate)
            if self._stage in {'package_writer','package_revision'}:
                from launchlens.package_content import normalize_package
                candidate,journal=normalize_package(candidate);event['normalizations']=journal
            event['candidate'] = deepcopy(candidate); event['outcome'] = 'returned_for_validation'
            return candidate
        except Exception as error:
            event['outcome'] = 'failed'
            detail = error.diagnostic if isinstance(error, ReviewError) else {'code':'operation_failed','field_path':'$'}
            event['diagnostic'] = deepcopy(detail)
            raise ReviewError(**detail) from None
        finally:
            event['elapsed_seconds'] = round(time.monotonic() - started, 6)
