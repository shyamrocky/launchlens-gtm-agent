"""Five-format admission inside the existing harness; no provider/source setup.

Campaign direction, product evidence and launch permission stay distinct. Shared
validators check structure/references, never semantic entailment or human approval.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from launchlens.content_contracts import ContractError, load_template, model_output_schema, validate_draft
from launchlens.content_review import check, model_brief, review_schema, validate_assessment
from launchlens.linkedin_drafting import (CTA, LINK, FORBIDDEN, DraftValidationError,
    admit_output, digest, evidence_records, prepare_input)
from launchlens.voice_policy import BRAND_POLICY_ID, load_voice_policy

ROOT = Path(__file__).resolve().parents[2]
FORMATS = ('campaign_brief', 'linkedin', 'email', 'blog', 'ads')
LABELS = {'campaign_brief':'Campaign brief', 'linkedin':'LinkedIn post', 'email':'Promotional email',
          'blog':'Short blog', 'ads':'Ad variations'}
CONFIG_SHA256 = '6657f66802ef4f7f201aea37813353656fcf2cf42175ad3e21d0f482c251550b'


class PackageError(ValueError):
    """Safe format-scoped diagnostic; raw candidates stay in model-call capture."""
    def __init__(self, format_name=None, code='invalid_package', field_path='$', rule='unknown_validation_failure'):
        allowed = {'invalid_package','invalid_structure','structure_or_evidence_reference',
                   'objective_claim_coverage','field_claim_coverage','cta_mismatch','prohibited_link','prohibited_wording','neutral_voice_required'}
        from launchlens.content_contracts import validation_detail
        self.diagnostic = {'format':format_name if format_name in FORMATS else None,
            'code':code if code in allowed else 'invalid_package', **validation_detail(field_path,rule)}
        super().__init__('Package rejected: ' + self.diagnostic['code'])


HISTORICAL_CONFIG_SHA256 = '856921f61001f0b66d53df745ea5794c29ba7d1f2fe710e22bea75e25c8533af'


HISTORICAL_CONFIGS = {
    'dad48142a22da770837754d5b8d230600afe964170900a0c3e5a559c57316257': 'package_execution_v12.json',
    '04ba0495cdd9029b508ef6a05e6cced4c8138230c4482ab14ac78f6dd2a8b530': 'package_execution_v11.json',
    'a6e796afa2949c064042d7e14604e6a2ce72bdfa08ac2612ef18661508dab6e6': 'package_execution_v10.json',
    'cd407d68252a5bcea6f3872049238dace8370551ce2b26d659f4a2f0c6e22a56': 'package_execution_v9.json',
    '96f9292431f661fc233f2eea40f2054974b8788459dead1f2b84cd104488d1f8': 'package_execution_v8.json',
    '6f7d4640e846bdf71dee06eaf9862b62291062d06eeb38f8991cc9aa64c91358': 'package_execution_v7.json',
    '3204c24116c5924bf49bae687f1b83327913a16dfca95fc2959fe511ac0453b4': 'package_execution_v6.json',
    HISTORICAL_CONFIG_SHA256: 'package_execution_v4.json',
    '39fa5cc7729fccc4409613140f32565d41d47e37ac2887d3ed19fb67c6084900': 'package_execution_v5.json',
}
MAX_PACKAGE_FEEDBACK = 12000


def configuration(expected_hash=None):
    expected_hash = expected_hash or CONFIG_SHA256
    check(expected_hash == CONFIG_SHA256 or expected_hash in HISTORICAL_CONFIGS, 'stale_binding')
    filename = 'package_execution_v13.json' if expected_hash == CONFIG_SHA256 else HISTORICAL_CONFIGS[expected_hash]
    raw = (ROOT/'data/templates/gtm'/filename).read_bytes()
    check(hashlib.sha256(raw).hexdigest() == expected_hash, 'stale_binding')
    spec = json.loads(raw)
    check(spec['formats'] == list(FORMATS) and spec['voice_policy_id'] == BRAND_POLICY_ID, 'stale_binding')
    for name, expected in spec['template_sha256'].items():
        from launchlens.content_contracts import TEMPLATE_DIR, TEMPLATES
        check(hashlib.sha256((TEMPLATE_DIR/TEMPLATES[name]).read_bytes()).hexdigest() == expected, 'stale_binding')
    if spec.get('tone_policy_sha256'):
        from launchlens.voice_policy import load_tone_policy
        load_tone_policy(spec['tone_policy_sha256'])
    return spec


def load_package_prompt(stage, expected_hash=None):
    spec = configuration(expected_hash)['prompts'].get(stage)
    check(type(spec) is dict, 'permission_denied')
    raw = (ROOT/'src/launchlens/prompts'/spec['file']).read_bytes()
    check(hashlib.sha256(raw).hexdigest() == spec['sha256'], 'stale_binding')
    return raw.decode()


def package_schema(review=False):
    return {'type':'object','required':list(FORMATS),'additionalProperties':False,
            'properties':{f:package_review_schema() if review else model_output_schema(f) for f in FORMATS}}


def prepare_package_input(state):
    check(state.get('mode') in {'offline_package','live_package'} and state.get('voice_policy_id') == BRAND_POLICY_ID,
          'permission_denied')
    # Reuse the full original research, market/date/permission and two-claim checks.
    inputs = prepare_input(state)
    base=deepcopy(inputs)
    def configured(expected_hash):
        result=deepcopy(base);spec=configuration(expected_hash);policy=load_voice_policy(BRAND_POLICY_ID)
        result['template']={'format':'package','templates':{f:load_template(f) for f in FORMATS}}
        result['output_schema']=package_schema()
        result['voice_policy']={k:v for k,v in result['voice_policy'].items() if k not in {'format','voice_mode'}}
        result['voice_policy']['format_voices']={f:policy['format_voices']['ad_variations' if f=='ads' else f] for f in FORMATS}
        result['package_contract']={'id':spec['contract_id'],'sha256':expected_hash,'formats':list(FORMATS),
            'campaign_brief_role':'Shared creative direction only; never evidence or launch permission'}
        result['user_notes_data_only']=state.get('user_notes','')
        if spec.get('tone_policy_sha256'):
            from launchlens.voice_policy import load_tone_policy,tone_schema
            result['tone_policy']=load_tone_policy(spec['tone_policy_sha256'])
            result['voice_policy']={k:deepcopy(result['tone_policy'][k]) for k in ['policy_id','version','format_voices','meaning']}
            result['voice_policy']['policy_sha256']=spec['tone_policy_sha256']
            result['output_schema']=tone_schema(result['output_schema'],result['tone_policy'])
            # Earlier raw templates remain immutable. Current derived guidance comes
            # exclusively from the bound tone policy, not duplicate legacy targets.
            for name,template in result['template']['templates'].items():
                rules=result['tone_policy']['format_specs'][name]
                template['content_schema']=deepcopy(result['output_schema']['properties'][name]['properties']['content'])
                template['editorial_guidelines']['tone']=rules['tone']
                template['editorial_guidelines']['length_targets']=deepcopy(rules['advisory'])
        return result
    inputs=configured(CONFIG_SHA256)
    expected=(state.get('package') or {}).get('input_sha256')
    if expected and digest(inputs)!=expected:
        for predecessor in HISTORICAL_CONFIGS:
            historical=configured(predecessor)
            if digest(historical)==expected:
                inputs=historical
                break
    return inputs


def text_fields(content, prefix=''):
    if type(content) is str:
        yield prefix, content
    elif type(content) is dict:
        for key, value in content.items():
            yield from text_fields(value, (prefix+'.' if prefix else '')+key)
    elif type(content) is list:
        for i, value in enumerate(content):
            yield from text_fields(value, (prefix+'.' if prefix else '')+str(i))


def resolve_field(content, path):
    # Only exact schema-validated text leaves, including blog/ad/brief array fields.
    check(type(path) is str and len(path) <= 140, 'invalid_reference', 'findings')
    fields = dict(text_fields(content))
    check(path in fields, 'invalid_reference', 'findings')
    return fields[path]


def admit_package(value, inputs, *, version=1, revision_execution=None):
    if type(value) is not dict or set(value) != set(FORMATS):
        raise PackageError()
    records = evidence_records(inputs); drafts = {}
    spec=configuration(inputs['package_contract']['sha256'])
    if inputs.get('tone_policy'):
        from launchlens.voice_policy import load_tone_policy
        check(bool(spec.get('tone_policy_sha256')) and inputs['tone_policy']==load_tone_policy(spec['tone_policy_sha256']),'stale_binding')
    else:check(not spec.get('tone_policy_sha256'),'stale_binding')
    anchor = digest(value['campaign_brief'])
    for name in FORMATS:
        try:
            if inputs.get('tone_policy'):
                from launchlens.voice_policy import validate_tone_structure
                # Existing shape/reference validation still precedes typed access.
                validate_draft(value[name],format_name=name,evidence_records=records)
                validate_tone_structure(value[name],name,inputs['tone_policy'],inputs['draft_constraints']['exact_cta'])
            # Existing LinkedIn admission is retained, including its exact CTA.
            if name == 'linkedin':
                record = admit_output(value[name], inputs)
            else:
                validation = validate_draft(value[name], format_name=name, evidence_records=records)
                referenced = {c for ref in value[name]['claim_references'] for c in ref['claim_ids']}
                if referenced != set(inputs['draft_constraints']['allowed_claim_ids']):
                    raise DraftValidationError('objective_claim_coverage', field_path='claim_references', rule='objective_claim_coverage')
                for path, text in text_fields(value[name]['content']):
                    if LINK.search(text):
                        raise DraftValidationError('prohibited_link', field_path='content.'+path, rule='prohibited_link')
                    # Internal restrictions may quote a prohibited phrase to forbid it.
                    if not (name == 'campaign_brief' and path.startswith('restrictions_and_unknowns.')) and FORBIDDEN.search(text):
                        raise DraftValidationError('prohibited_wording', field_path='content.'+path, rule='prohibited_wording')
                record = {'draft':deepcopy(value[name]),'validation':validation,
                    'evidence_bindings':[{'unit_id':r['unit_id'],'chunk_id':r['chunk_id'],
                        'evidence_sha256':r['evidence_sha256']} for r in records]}
        except (ContractError, DraftValidationError) as error:
            raise PackageError(name, getattr(error,'code','structure_or_evidence_reference'),
                **error.diagnostic) from None
        check_field_claims(value[name], name)
        if inputs.get('tone_policy'):
            from launchlens.voice_policy import tone_measurements
            record['validation']['editorial_warnings']=[{k:v for k,v in m.items() if k!='meets_target'} | {'severity':'advisory'}
                for m in tone_measurements(value[name]['content'],name,inputs['tone_policy']) if not m['meets_target']]
        record.update(version=version, review_status='unreviewed', human_accepted=False,
            publishing_allowed=False, input_sha256=digest(inputs), creative_anchor_sha256=anchor,
            writer_prompt_sha256=configuration(inputs['package_contract']['sha256'])['prompts']['package_writer' if version == 1 else 'package_revision']['sha256'])
        drafts[name] = record
    metadata = {'version':version,'input_sha256':digest(inputs),'package_sha256':digest(value),
        'creative_anchor_sha256':anchor,'human_accepted':False,'publishing_allowed':False}
    if inputs.get('tone_policy'):
        metadata['tone_policy_sha256']=configuration(inputs['package_contract']['sha256'])['tone_policy_sha256']
    if revision_execution is not None:
        from launchlens.field_revisions import PROTOCOL,PROMPT_SHA
        check(revision_execution in (
            {'protocol':PROTOCOL,'method':'field_writer','prompt_sha256':PROMPT_SHA},
            {'protocol':PROTOCOL,'method':'exact_replacement','prompt_sha256':None}), 'stale_binding')
        metadata['revision_execution']=deepcopy(revision_execution)
        for record in drafts.values():record['writer_prompt_sha256']=revision_execution['prompt_sha256']
    return drafts, metadata


def package_value(state):
    return {f:deepcopy(state['drafts'][f]['draft']) for f in FORMATS}


def authoritative_package_binding(state):
    inputs = prepare_package_input(state); metadata = state.get('package')
    check(type(metadata) is dict and set(state['drafts']) == set(FORMATS), 'stale_binding', 'binding')
    version = metadata.get('version')
    check(type(version) is int and version >= 1, 'stale_binding', 'binding')
    expected, expected_meta = admit_package(package_value(state), inputs, version=version, revision_execution=metadata.get('revision_execution'))
    check(metadata == expected_meta, 'stale_binding', 'binding')
    for name in FORMATS:
        actual = deepcopy(state['drafts'][name]); actual['review_status'] = 'unreviewed'
        check(actual == expected[name], 'stale_binding', 'binding')
    binding = {'run_id':state['run_id'],'draft_version':version,
        'draft_sha256':metadata['package_sha256'],'authoritative_input_sha256':digest(inputs),
        'creative_anchor_sha256':metadata['creative_anchor_sha256']}
    return inputs, metadata, binding


def package_measurements(package, inputs):
    from launchlens.voice_policy import tone_measurements
    from launchlens.content_contracts import measured_lengths
    policy=inputs.get('tone_policy')
    return {f:tone_measurements(package[f]['content'],f,policy) if policy else measured_lengths(package[f]['content'],f) for f in FORMATS}


def validate_package_review(value, state, *, isolate_findings=True, scan_additions=True):
    inputs, _, binding = authoritative_package_binding(state)
    return assess_package_review(value, package_value(state), inputs, binding, isolate_findings=isolate_findings,scan_additions='tone_v2' if inputs.get('tone_policy') and scan_additions else scan_additions)


def prepare_call(state, stage, *, projector=None):
    check(stage in {'package_writer','package_reviewer','package_revision'}, 'permission_denied')
    inputs = prepare_package_input(state)
    brief, manifest = model_brief(inputs, projector)
    if stage == 'package_writer':
        check(not state['drafts'], 'permission_denied')
        binding = {'run_id':state['run_id'],'draft_version':0,
                   'draft_sha256':None,'authoritative_input_sha256':digest(inputs)}
    else:
        _, _, binding = authoritative_package_binding(state)
    result = {'binding':binding,'writer_brief':brief, 'projection_manifest':manifest,
              'output_schema':package_schema(True) if stage == 'package_reviewer' else deepcopy(inputs['output_schema'])}
    if stage != 'package_writer':
        result['package'] = package_value(state)
    if stage == 'package_reviewer':
        result['writing_instructions'] = load_package_prompt('package_writer',inputs['package_contract']['sha256'])
        from launchlens.reviewer_groups import phrase_groups,group_schema,PROTOCOL
        result['review_protocol']=PROTOCOL
        result['phrase_groups']=phrase_groups(result['package'],scan_additions='tone_v2' if inputs.get('tone_policy') else True)
        result['output_schema']=group_schema(result['phrase_groups'])
        from launchlens.content_contracts import measured_lengths
        result['computed_lengths'] = package_measurements(result['package'],inputs)
        result['review_criteria'] = inputs['common_review_criteria']
        # Judge only the bound CURRENT package. Prior findings and human feedback
        # contain obsolete quoted prose; they never cross this review boundary.
        result['review_scope'] = 'Current package version only; no inherited findings or clearance.'
        marker=state['ledger'].get('harness-auto-refinement',{})
        if marker.get('status')=='revised' and 'protected_scan_hits' in marker:
            current=protected_scan_hits(state)
            result['post_refinement_scan']={'current_version':binding['draft_version'],
                'protected_scan_hits':current,'new_protected_scan_hits':new_protected_hits(marker['protected_scan_hits'],current),
                'instruction':'Judge current V2 wording in context. Every surviving/new protected phrase still requires human clearance. No further automatic Writer call.'}
    if stage == 'package_revision':
        permission = state.get('revision_request'); review = state.get('review')
        check(type(permission) is dict and type(review) is dict and review.get('binding') == binding
              and permission.get('binding') == binding and permission.get('review_sha256') == digest(review),
              'permission_denied', 'binding')
        check(type(permission.get('feedback')) is str and 0 < len(permission['feedback'].strip()) <= MAX_PACKAGE_FEEDBACK,
              'permission_denied')
        result['full_avoid_list']=refinement_avoid_list(inputs)
        result['current_flagged_locations']=revision_flagged_locations(state)
        result['requested_phrase_changes']=revision_phrase_targets(state)
        result['revision_self_check']='For either revision origin, check all returned copy against full_avoid_list. Apply requested_phrase_changes at their exact fields; inspect for new risky phrases before returning once. Kept wording remains a human preference subject to evidence and launch restrictions.'
        if permission.get('origin')=='agent':
            marker=state['ledger'].get('harness-auto-refinement',{})
            targets=refinement_targets(state)
            check(marker.get('permission_sha256')==digest(permission) and marker.get('source_binding')==binding
                  and permission.get('blocking_findings')==targets['blocking_findings']
                  and permission.get('protected_scan_hits',[])==targets['protected_scan_hits']
                  and bool(targets['blocking_findings'] or targets['protected_scan_hits']),
                  'permission_denied','binding')
            if targets['protected_scan_hits'] or configuration(inputs['package_contract']['sha256']).get('automatic_refinement',{}).get('trigger')=='reviewer_blocking_or_protected_scan_hits':
                result['protected_scan_hits_to_rewrite']=deepcopy(targets['protected_scan_hits'])
                result['full_avoid_list']=refinement_avoid_list(inputs)
            result['revision_origin']='agent'
            result['blocking_findings_to_fix']=deepcopy(permission['blocking_findings'])
            result['protected_phrase_rule']='Rewrite if needed; never grant keep clearance. Remaining protected phrases require a human.'
        result.update(review=({name:{**deepcopy(item),'findings':[f for f in deepcopy(item['findings']) if f.get('severity')=='blocking' and f.get('origin')!='deterministic_scan']} for name,item in review['assessment'].items()} if permission.get('origin')=='agent' else deepcopy(review['assessment'])),owner_feedback_data_only=permission['feedback'],
                      writing_instructions=load_package_prompt('package_writer',inputs['package_contract']['sha256']))
        if permission.get('field_plan'):
            from launchlens.field_revisions import prepare,plan
            check(permission['field_plan']==plan(state,permission),'permission_denied','binding')
            return prepare(state,inputs,binding,projector)
    return result


def field_claim_gaps(draft, format_name):
    """Narrow deterministic coverage, not entailment or general factuality detection."""
    refs={v['content_field']:set(v['claim_ids']) for v in draft['claim_references']}
    for path,text in text_fields(draft['content']):
        if format_name=='campaign_brief' and path.startswith('restrictions_and_unknowns.'):
            continue
        lower=text.lower()
        historical_hook=(path=='hook' and 'bringing' in lower and 'cherry experience' in lower)
        clear_flavor=bool(re.search(r"(?:cherry float|this (?:product|flavor)) (?:combines|contains|is made with|has)\b",lower))
        clear_inspiration=bool(re.search(r"(?:is |takes |draws )?inspir(?:ed|ation) (?:by|from) (?:classic )?soda[ -]floats?",lower))
        # Only a blog section heading can inherit its OWN section body's refs.
        # Titles, introductions, CTAs and other sections remain independent.
        body_path=path[:-7]+'body' if format_name=='blog' and re.fullmatch(r'sections\.[0-9]+\.heading',path) else None
        if (historical_hook or clear_flavor or clear_inspiration) and not (refs.get(path) or (body_path and refs.get(body_path))):
            yield PackageError(format_name,'field_claim_coverage','content.'+path,'field_claim_coverage').diagnostic


def check_field_claims(draft, format_name):
    for gap in field_claim_gaps(draft,format_name):
        raise PackageError(format_name,**{k:v for k,v in gap.items() if k!='format'})


def citation_only_failures(value, inputs):
    """Return citation diagnostics ONLY after all other checks pass.

    Inspection never changes text/references or admits a candidate. This full pass
    prevents an early citation error from masking a later policy/structure error.
    """
    try:
        if type(value) is not dict or set(value)!=set(FORMATS):return []
        records=evidence_records(inputs);gaps=[]
        for name in FORMATS:
            draft=value[name]
            if type(draft) is not dict:return []
            citation_free=deepcopy(draft);citation_free['claim_references']=[]
            # Validate every non-citation rule independently. A bad link, CTA,
            # field type or tone structure must never become a citation retry.
            validate_draft(citation_free,format_name=name,evidence_records=records)
            if inputs.get('tone_policy'):
                from launchlens.voice_policy import validate_tone_structure
                validate_tone_structure(citation_free,name,inputs['tone_policy'],inputs['draft_constraints']['exact_cta'])
            if name=='linkedin' and citation_free['content']['cta']!=CTA:return []
            for path,text in text_fields(citation_free['content']):
                if LINK.search(text):return []
                if not (name=='campaign_brief' and path.startswith('restrictions_and_unknowns.')) and FORBIDDEN.search(text):return []
            # Inspect every reference separately so one invalid entry cannot hide
            # uncited fields or another citation error in the same format.
            valid=[];seen=set()
            if type(draft['claim_references']) is not list:return []
            for index,reference in enumerate(draft['claim_references']):
                trial=deepcopy(draft);trial['claim_references']=[reference]
                try:validate_draft(trial,format_name=name,evidence_records=records)
                except ContractError as error:
                    path=error.diagnostic.get('field_path','')
                    if not (path.startswith('claim_references') or path.startswith('draft.claim_references')):return []
                    diagnostic=deepcopy(error.diagnostic)
                    diagnostic['field_path']=path.replace('claim_references.0','claim_references.'+str(index),1)
                    if diagnostic.get('rule')=='invalid_claim_reference':
                        for claim_index,claim in enumerate(reference['claim_ids']):
                            if claim not in inputs['draft_constraints']['allowed_claim_ids']:
                                item={**diagnostic,'field_path':'claim_references.'+str(index)+'.claim_ids.'+str(claim_index)}
                                gaps.append(PackageError(name,'structure_or_evidence_reference',**item).diagnostic)
                    else:gaps.append(PackageError(name,'structure_or_evidence_reference',**diagnostic).diagnostic)
                    continue
                if reference['content_field'] in seen:
                    gaps.append(PackageError(name,'structure_or_evidence_reference','claim_references.'+str(index)+'.content_field','duplicate_field_reference').diagnostic)
                    continue
                seen.add(reference['content_field']);valid.append(reference)
            checked=deepcopy(draft);checked['claim_references']=valid
            referenced={c for ref in valid for c in ref['claim_ids']}
            if referenced!=set(inputs['draft_constraints']['allowed_claim_ids']):
                gaps.append(PackageError(name,'objective_claim_coverage','claim_references','objective_claim_coverage').diagnostic)
            gaps.extend(field_claim_gaps(checked,name))
        return gaps
    except (ContractError,DraftValidationError,PackageError,KeyError,TypeError):return []


def project_package_context(inputs):
    """One Writer input builder for Proceed and answered Clarify paths."""
    from launchlens.writer_context import project_writer_input
    return project_writer_input(inputs,allow_restricted_clarify=True)


def normalize_package(value):
    """Only shape-preserving decoding/path fixes; never manufacture evidence/prose."""
    from launchlens.live_research import strict_json
    log=[]
    def shape(v,schema,path):
        kind=schema.get('type')
        if kind in ('object','array') and type(v) is str:
            for _ in range(2):
                try:parsed=strict_json(v)
                except Exception:break
                if type(parsed) not in (str,dict,list):break
                log.append({'rule':'quoted_json_decoded','path':path});v=parsed
                if type(v) is not str:break
        if kind=='object' and type(v) is dict:
            v=deepcopy(v)
            for k,child in schema['properties'].items():
                if k in v:v[k]=shape(v[k],child,path+'.'+k)
        elif kind=='array' and type(v) is list:
            v=[shape(x,schema['items'],path+'.'+str(i)) for i,x in enumerate(v)]
        return v
    result=shape(value,package_schema(),'$')
    if type(result) is dict:
        for name in FORMATS:
            item=result.get(name)
            if type(item) is not dict or type(item.get('claim_references')) is not list:continue
            refs=[]
            for i,ref in enumerate(item['claim_references']):
                ref=deepcopy(ref);path=name+'.claim_references.'+str(i)
                if type(ref) is dict and set(ref)=={'content_field','claim_ids'} and ref['claim_ids']==[]:
                    log.append({'rule':'empty_citation_removed','path':path,'content_field':ref['content_field']});continue
                if type(ref) is dict and type(ref.get('content_field')) is str and ref['content_field'].startswith('content.'):
                    ref['content_field']=ref['content_field'][8:]
                    log.append({'rule':'content_prefix_removed','path':path+'.content_field'})
                refs.append(ref)
            item['claim_references']=refs
    return result,log


RISK_PATTERNS = {
 'availability_urgency':r"\b(?:announce the launch|stay tuned|stay informed|where you can find|is here|try it(?: today)?|available(?: now| today)?|now|buy now|shop now|in stores|limited[ -]time|hurry|today only|can['’]t wait)\b",
 'novelty':r"\b(?:announce|launch|latest|introducing|new (?:flavou?r|way|twist|experience)|innovative|innovation|first[ -]ever)\b",
 'preference_prediction':r"\b(?:fondly remember|sure to|will (?:love|become)|new favou?rite|favou?rite|consumers prefer|everyone loves)\b",
 'differentiation':r"\b(?:stands out|the difference|unique(?: twist| taste| combination)?|sets? [^.]*?apart|better than|unlike|one[ -]of[ -]a[ -]kind|superior)\b",
 'ingredient_intensity':r"\b(?:real (?:vanilla|ice cream)|made with|contains|dairy|ice cream|intense|intensity|bold|rich|creamy|strong|burst)\b",
 'invented_product_facts':r"\b(?:ready[ -]to[ -]drink|formats?|quench|born from|family|lineup|real (?:vanilla|ice cream)|made with|contains|dairy|ice cream)\b",
}
HUMAN_CLEARANCE_CATEGORIES=frozenset({'availability_urgency','invented_product_facts','preference_prediction'})
LENGTH_COMPLIANCE=re.compile(r"(?:meet\w*|satisf\w*|within|complian\w*).{0,80}(?:length|word.count|character.count|length.targets)|(?:length|word.count|character.count|length.targets).{0,80}(?:met|satisfied|within|compliant)",re.I)


def claims_length_compliance(text):
    for match in LENGTH_COMPLIANCE.finditer(text):
        local=text[max(0,match.start()-24):match.end()]
        if not re.search(r"\b(?:not|below|outside|short|exceed\w*|insufficient)\b|doesn['’]t|don['’]t",local,re.I):return True
    return False


def risk_patterns(*,scan_additions=True,suggestion=False):
    patterns=dict(RISK_PATTERNS)
    if scan_additions:
        patterns['novelty'] += r'|\bpresenting\b'
        patterns['invented_product_facts'] += r'|\b(?:guided the development|designed to)\b'
    if scan_additions=='tone_v2':
        from launchlens.voice_policy import load_tone_policy
        for category,phrases in load_tone_policy()['all_formats']['scan_phrases'].items():
            patterns[category] += '|'+ '|'.join(r'\b'+re.escape(term)+r'\b' for term in phrases)
    if suggestion:
        patterns['novelty'] += r'|\b(?:new|introduce)\b'
        patterns['preference_prediction'] += r'|\b(?:may recall|remember|recall)\b'
        patterns['ingredient_intensity'] += r'|\b(?:smooth|velvety)\b'
    return patterns


def risky_phrase_scan(package, *, suggestion=False, scan_additions=True):
    hits=[]
    for name in FORMATS:
        if name not in package:continue
        for path,text in text_fields(package[name]['content']):
            if name=='campaign_brief' and path.startswith('restrictions_and_unknowns.'):
                continue  # Policy warnings are not promotional copy; retained in context.
            patterns=risk_patterns(scan_additions=scan_additions,suggestion=suggestion)
            for category,pattern in patterns.items():
                for match in re.finditer(pattern,text,re.I):
                    hit={'format':name,'content_field':path,'category':category,'quote':match.group(),
                         'context':text,'start':match.start(),'end':match.end(),
                         'human_clearance_required':category in HUMAN_CLEARANCE_CATEGORIES}
                    hit['hit_id']='risk-'+digest(hit)[:12];hits.append(hit)
    # A protected multiword availability match is one occurrence, not separate
    # novelty decisions for its contained announce/launch tokens.
    return [h for h in hits if not (h['category']=='novelty' and any(
        a['format']==h['format'] and a['content_field']==h['content_field'] and
        a['category']=='availability_urgency' and a['start']<=h['start'] and a['end']>=h['end']
        for a in hits))]


def reviewer_hint(finding, *, scan_additions='tone_v2'):
    """Filter advisory replacements; absence of a scan hit is NOT semantic proof."""
    value=finding.get('suggested_change');original=finding.get('quote')
    if not isinstance(value,str) or not isinstance(original,str):return None,'not_wording_hint'
    value=value.strip().strip('"“”')
    norm=lambda x:' '.join(re.findall(r"[\w']+",x.casefold()))
    if not value or len(value)>250 or len(value.split())>30:return None,'not_short_replacement'
    if norm(original) and norm(original) in norm(value):return None,'repeats_original'
    if re.match(r"(?:no replacement|no changes?|replace|remove|revise|avoid|keep|use |drop |otherwise|consider|rewrite|describe|retain|do not|delete)\b",value,re.I):
        return None,'editing_instruction_or_no_hint'
    if risky_phrase_scan({'linkedin':{'content':{'body':value}}},suggestion=True,scan_additions=scan_additions):return None,'risky_replacement'
    return value,None


def package_review_schema():
    def obj(properties):return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
    text={'type':'string','minLength':1}
    finding=obj({'dimension':{'type':'string','enum':['grounding','qualifications','voice','tone','consistency','completeness']},
        'content_field':text,'quote':{'type':['string','null']},
        'severity':{'type':'string','enum':['blocking','advisory','cleared']},
        'rationale':text,'suggested_change':text,
        'claim_ids':{'type':'array','maxItems':2,'items':{'type':'string','enum':['PROD-002','PROD-003']}},
        'scan_hit_ids':{'type':'array','items':text}})
    return obj({'findings':{'type':'array','maxItems':80,'items':finding}})


def assess_package_review(value, package, inputs, binding, *, isolate_findings=True, scan_additions=True):
    """Findings-only review; malformed output stays visible and never marks reviewed."""
    from launchlens.content_review import DIMENSIONS
    from launchlens.live_research import strict_json
    original=deepcopy(value);log=[];group_errors=[];dropped=[];coverage_errors=[]
    if type(value) is str:
        try:value=strict_json(value);log.append({'rule':'quoted_json_decoded','path':'review'})
        except Exception:pass
    if isinstance(value,dict) and 'group_judgments' in value:
        from launchlens.reviewer_groups import expand_judgments
        group_count=len(value['group_judgments']) if isinstance(value['group_judgments'],list) else 0
        if isolate_findings:
            from launchlens.reviewer_groups import isolate_judgments
            value,dropped,coverage_errors=isolate_judgments(value,package,scan_additions=scan_additions)
        else:value,group_errors=expand_judgments(value,package,scan_additions=scan_additions)
        log.append({'rule':'group_judgments_expanded','group_count':group_count})
    from launchlens.content_contracts import measured_lengths
    lengths=package_measurements(package,inputs)
    hits=risky_phrase_scan(package,scan_additions=scan_additions);by_id={h['hit_id']:h for h in hits};formats={};all_findings={};issues=[]
    for name in FORMATS:
        raw=value.get(name) if type(value) is dict else None
        if type(raw) is str:
            try:raw=strict_json(raw);log.append({'rule':'quoted_json_decoded','path':name})
            except Exception:pass
        findings=[];errors=list(group_errors);seen=set();judged={}
        if type(raw) is not dict or type(raw.get('findings')) is not list:
            errors.append('malformed_findings');rows=[]
        else:rows=raw['findings']
        if type(raw) is dict and 'assessments' in raw:log.append({'rule':'model_statuses_ignored','path':name})
        for row in rows[:80]:
            if type(row) is not dict:errors.append('malformed_finding');continue
            f=deepcopy(row);field=f.get('content_field')
            ids=f.get('claim_ids')
            if type(ids) is list and any(type(c) is not str or c not in inputs['draft_constraints']['allowed_claim_ids'] for c in ids):
                if isolate_findings:errors.append('invalid_claim_reference');continue
                raise PackageError(name,'structure_or_evidence_reference','claim_references','invalid_claim_reference')
            if type(field) is str and field.startswith('content.'):
                f['content_field']=field=field[8:];log.append({'rule':'content_prefix_removed','path':name+'.finding'})
            if f.get('quote') is None and field in (None,'content','$format'):
                f['content_field']=field='$format'
            if type(f.get('dimension')) is not str or f.get('dimension') not in DIMENSIONS or type(f.get('severity')) is not str or f.get('severity') not in {'blocking','advisory','cleared'} or not all(type(f.get(k)) is str and f[k].strip() for k in ['rationale','suggested_change']):
                errors.append('malformed_finding');continue
            if type(ids) is not list or len(ids)>2 or len(set(ids))!=len(ids):errors.append('invalid_reference');continue
            if f.get('quote') is None:
                if field!='$format':errors.append('format_scope_required');continue
            else:
                target=dict(text_fields(package[name]['content'])).get(field) if isinstance(field,str) else None
                if type(target) is not str or type(f.get('quote')) is not str or not f['quote'] or f['quote'] not in target:
                    errors.append('exact_quote_or_path_invalid');continue
            if any(not m['meets_target'] for m in lengths[name]) and claims_length_compliance(f['rationale']+' '+f['suggested_change']):
                errors.append('contradicts_computed_length');continue
            linked=f.get('scan_hit_ids',[])
            if type(linked) is not list or any(type(i) is not str or i not in by_id or by_id[i]['format']!=name or by_id[i]['content_field']!=field or type(f.get('quote')) is not str or by_id[i]['quote'] not in f['quote'] for i in linked):
                errors.append('scan_judgment_invalid');continue
            f['scan_hit_ids']=linked
            identity=digest(f)
            if identity in seen:log.append({'rule':'duplicate_finding_ignored','path':name});continue
            seen.add(identity)
            f['reviewer_hint'],f['hint_hidden_reason']=reviewer_hint(f,scan_additions=scan_additions)
            findings.append(f)
            for i in linked:judged[i]=f['severity']
        # High-risk matches always require a human, even if omitted or cleared by the model.
        mandatory=[h for h in hits if h['format']==name and h['human_clearance_required']]
        for hit in mandatory:
            matching=[f for f in findings if hit['hit_id'] in f['scan_hit_ids']]
            for finding in matching:
                finding['human_clearance_required']=True
                if finding['severity']=='cleared':
                    finding['model_severity']='cleared';finding['severity']='advisory'
                    log.append({'rule':'reviewer_clearance_requires_human','hit_id':hit['hit_id']})
            if not matching:
                findings.append({'dimension':'grounding','content_field':hit['content_field'],
                    'quote':hit['quote'],'severity':'advisory','rationale':'This '+hit['category'].replace('_',' ')+' scan match requires human clearance; model approval cannot clear it.',
                    'suggested_change':'Remove or reword the phrase, or have a human verify its support before accepting it.',
                    'claim_ids':[],'scan_hit_ids':[hit['hit_id']],'origin':'deterministic_scan','human_clearance_required':True})
            judged[hit['hit_id']]='human_clearance_required'
        missing=[h['hit_id'] for h in hits if h['format']==name and h['hit_id'] not in judged]
        if isolate_findings:
            malformed='malformed_findings' in errors
            dropped.extend({'format':name,'rule':e} for e in errors if e!='malformed_findings')
            complete=not malformed and not coverage_errors
        else:complete=not errors and not missing
        assessments=[{'dimension':d,'status':'needs_changes' if any(f['dimension']==d and f['severity']=='blocking' for f in findings) else 'uncertain' if (mandatory or missing) and d=='grounding' else 'pass' if complete else 'uncertain'} for d in DIMENSIONS]
        status='changes_requested' if any(f['severity']=='blocking' for f in findings) else 'review_incomplete' if not complete else 'human_clearance_required' if mandatory else 'reviewed_for_human'
        formats[name]={'binding':binding,'assessment':{'assessments':assessments,'findings':findings},
            'review_status':status,'review_complete':complete,'human_clearance_required':bool(mandatory),'raw_findings':deepcopy(raw),
            'validation_issues':errors,'unassessed_scan_hit_ids':missing,'human_accepted':False,'publishing_allowed':False}
        all_findings[name]={'assessments':assessments,'findings':findings}
        for h in hits:
            if h['format']==name:h['reviewer_disposition']=judged.get(h['hit_id'],'unassessed')
    complete=all(f['review_complete'] for f in formats.values())
    status='changes_requested' if any(f['review_status']=='changes_requested' for f in formats.values()) else 'review_incomplete' if not complete else 'human_clearance_required' if any(f['human_clearance_required'] for f in formats.values()) else 'reviewed_for_human'
    result = {'binding':binding,'assessment':all_findings,'format_reviews':formats,'review_status':status,
        'review_complete':complete,'computed_lengths':lengths,'human_clearance_required':any(f['human_clearance_required'] for f in formats.values()),'raw_response':original,'risk_scan':hits,'normalizations':log,
        'human_accepted':False,'publishing_allowed':False}
    if scan_additions:result['scan_additions']=scan_additions
    if isolate_findings:
        result.update(assessment_policy='isolated_findings_v1',unverified_finding_count=len(dropped),
            dropped_findings=dropped,coverage_issues=coverage_errors)
    return result


def human_edit_review(state, source_review, edited_fields, *, scan_additions=True):
    """Deterministic rescan after a human edit; never represents a new AI review."""
    inputs,_,binding=authoritative_package_binding(state)
    check(source_review.get('review_complete') is True and source_review.get('binding',{}).get('run_id')==binding['run_id'] and source_review['binding'].get('draft_version')==binding['draft_version'],'permission_denied')
    package=package_value(state);changed={(e['format'],e['content_field']) for e in edited_fields}
    check(changed and all(name in FORMATS and path in dict(text_fields(package[name]['content'])) for name,path in changed),'permission_denied')
    raw={name:{'findings':[]} for name in FORMATS}
    for name in FORMATS:
        for finding in source_review['format_reviews'][name]['assessment']['findings']:
            path=finding['content_field']
            if (name,path) in changed or (path=='$format' and any(n==name for n,_ in changed)):continue
            # Unchanged fields retain their prior independent findings. Changed
            # fields get fresh scan hits, never stale AI quotations or clearances.
            raw[name]['findings'].append(deepcopy(finding))
    result=assess_package_review(raw,package,inputs,binding,isolate_findings=True,scan_additions='tone_v2' if inputs.get('tone_policy') and scan_additions else scan_additions)
    result.update(assessment_policy='human_edit_rescan_v1',source_review_sha256=digest(source_review),
        human_edited_fields=deepcopy(edited_fields),no_new_model_review=True)
    return result


def verify_human_edit_review(state):
    review=state.get('review') or {}
    check(review.get('assessment_policy')=='human_edit_rescan_v1','stale_binding')
    source=next((r for r in state['reviews'] if digest(r)==review.get('source_review_sha256')),None)
    check(source is not None,'stale_binding')
    check(human_edit_review(state,source,review.get('human_edited_fields',[]),scan_additions=review.get('scan_additions',False))==review,'stale_binding')
    return review


def blocking_findings(review):
    """Validated Reviewer blockers only. Scan/advisory hits never schedule inference."""
    return [dict(f,format=name) for name,item in review.get('format_reviews',{}).items()
            for f in item['assessment']['findings']
            if f.get('severity')=='blocking' and f.get('origin')!='deterministic_scan']


def protected_scan_hits(state):
    inputs,_,_=authoritative_package_binding(state)
    return [h for h in risky_phrase_scan(package_value(state),scan_additions='tone_v2' if inputs.get('tone_policy') else True)
            if h['human_clearance_required']]


def refinement_targets(state):
    inputs,_,_=authoritative_package_binding(state)
    spec=configuration(inputs['package_contract']['sha256']).get('automatic_refinement',{})
    expanded=spec.get('trigger')=='reviewer_blocking_or_protected_scan_hits'
    return {'blocking_findings':blocking_findings(state['review']),
            'protected_scan_hits':protected_scan_hits(state) if expanded else []}


def refinement_avoid_list(inputs):
    policy=inputs.get('tone_policy')
    if policy is None:
        return {'scan_patterns':risk_patterns(),'no_links':True}
    return {'per_format':{f:deepcopy(policy['format_specs'][f]['avoid']) for f in FORMATS},
            'all_formats_never':deepcopy(policy['all_formats']['never']),
            'no_links':policy['all_formats']['no_links'],
            'scan_patterns':risk_patterns(scan_additions='tone_v2')}


def new_protected_hits(before,after):
    from collections import Counter
    key=lambda h:(h['format'],h['content_field'],h['category'],' '.join(h['quote'].casefold().split()))
    remaining=Counter(key(h) for h in before);new=[]
    for hit in after:
        identity=key(hit)
        if remaining[identity]:remaining[identity]-=1
        else:new.append(deepcopy(hit))
    return new


def revision_flagged_locations(state):
    """Current scan and semantic findings, including unresolved prior requests."""
    from launchlens.review_decisions import grouped_findings
    return [dict(format=o['format'],content_field=o['content_field'],quote=o['quote'],
                 start=o['start'],end=o['end'],severity=o['severity'],
                 human_clearance_required=o['human_clearance_required'],needs_attention=o['needs_attention'])
            for g in grouped_findings(state) for o in g['occurrences']]


def revision_phrase_targets(state):
    """Resolve generated human feedback or bound agent findings to exact text spans.

    Freeform notes are still delivered, but never claimed as mechanically verified.
    Only source-verified paths/offsets enter the deterministic comparison.
    """
    permission=state.get('revision_request') or {};package=package_value(state);targets=[]
    def add(name,path,quote,start,end):
        text=dict(text_fields(package.get(name,{}).get('content',{}))).get(path,'')
        if (isinstance(start,int) and isinstance(end,int) and 0<=start<end<=len(text)
                and quote.casefold()==text[start:end].casefold()):
            row=dict(format=name,content_field=path,quote=text[start:end],start=start,end=end)
            if row not in targets:targets.append(row)
    if permission.get('origin')=='agent':
        for finding in permission.get('blocking_findings',[])+permission.get('protected_scan_hits',[]):
            name,path,quote=finding['format'],finding['content_field'],finding.get('quote')
            if not quote:continue
            text=dict(text_fields(package.get(name,{}).get('content',{}))).get(path,'')
            for match in re.finditer(re.escape(quote),text):add(name,path,match.group(),match.start(),match.end())
    else:
        for line in permission.get('feedback','').splitlines():
            match=re.fullmatch(r'Change “(.+)” at (.+)',line)
            if not match:continue
            quote,locations=match.groups()
            for location in locations.split(', '):
                found=re.fullmatch(r'(\w+)\.([\w.]+)\[(\d+):(\d+)\]',location)
                if found:
                    name,path,start,end=found.groups();add(name,path,quote,int(start),int(end))
    return targets


def compare_revision_phrases(before,after,targets):
    """Track each requested occurrence across edits, without judging meaning.

    Align all equal phrases in a field, including unrequested repeats, so deleting
    one occurrence cannot count as deleting its surviving sibling. Ambiguous
    surviving matches are conservatively assigned to remaining source occurrences.
    """
    from difflib import SequenceMatcher
    results=[];alignments={}
    for target in targets:
        name,path,quote=target['format'],target['content_field'],target['quote']
        key=(name,path,quote.casefold())
        old=dict(text_fields(before[name]['content'])).get(path,'')
        new=dict(text_fields(after[name]['content'])).get(path,'')
        if key not in alignments:
            sources=list(re.finditer(re.escape(quote),old,re.I));destinations=list(re.finditer(re.escape(quote),new,re.I))
            pairs={};used=set()
            blocks=SequenceMatcher(None,old,new,autojunk=False).get_matching_blocks()
            for source in sources:
                for block in blocks:
                    if block.a<=source.start() and source.end()<=block.a+block.size:
                        offset=block.b+source.start()-block.a
                        dest=next((i for i,m in enumerate(destinations) if m.start()==offset),None)
                        if dest is not None and dest not in used:pairs[source.span()]=dest;used.add(dest)
                        break
            remaining=[m for m in sources if m.span() not in pairs]
            for i,dest in enumerate(destinations):
                if i in used or not remaining:continue
                source=min(remaining,key=lambda m:abs(m.start()/max(len(old),1)-dest.start()/max(len(new),1)))
                pairs[source.span()]=i;remaining.remove(source)
            alignments[key]=(pairs,destinations)
        pairs,destinations=alignments[key];index=pairs.get((target['start'],target['end']))
        row=deepcopy(target);row['status']='unresolved' if index is not None else 'wording_changed'
        if index is not None:row.update(current_start=destinations[index].start(),current_end=destinations[index].end())
        results.append(row)
    return results


def current_revision_resolution(state):
    """Only a report bound to the exact current text may affect its review UI."""
    package=state.get('package') or {}
    ledger=state.get('ledger',{})
    report=ledger.get('last-revision-result') or ledger.get('revision-resolution-v'+str(package.get('version')), {})
    return report if report.get('draft_sha256')==package.get('package_sha256') else {}
