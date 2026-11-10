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
CONFIG_SHA256 = '96f9292431f661fc233f2eea40f2054974b8788459dead1f2b84cd104488d1f8'


class PackageError(ValueError):
    """Safe format-scoped diagnostic; raw candidates stay in model-call capture."""
    def __init__(self, format_name=None, code='invalid_package', field_path='$', rule='unknown_validation_failure'):
        allowed = {'invalid_package','invalid_structure','structure_or_evidence_reference',
                   'objective_claim_coverage','field_claim_coverage','cta_mismatch','prohibited_link','prohibited_wording'}
        from launchlens.content_contracts import validation_detail
        self.diagnostic = {'format':format_name if format_name in FORMATS else None,
            'code':code if code in allowed else 'invalid_package', **validation_detail(field_path,rule)}
        super().__init__('Package rejected: ' + self.diagnostic['code'])


HISTORICAL_CONFIG_SHA256 = '856921f61001f0b66d53df745ea5794c29ba7d1f2fe710e22bea75e25c8533af'


HISTORICAL_CONFIGS = {
    '6f7d4640e846bdf71dee06eaf9862b62291062d06eeb38f8991cc9aa64c91358': 'package_execution_v7.json',
    '3204c24116c5924bf49bae687f1b83327913a16dfca95fc2959fe511ac0453b4': 'package_execution_v6.json',
    HISTORICAL_CONFIG_SHA256: 'package_execution_v4.json',
    '39fa5cc7729fccc4409613140f32565d41d47e37ac2887d3ed19fb67c6084900': 'package_execution_v5.json',
}
MAX_PACKAGE_FEEDBACK = 12000


def configuration(expected_hash=None):
    expected_hash = expected_hash or CONFIG_SHA256
    check(expected_hash == CONFIG_SHA256 or expected_hash in HISTORICAL_CONFIGS, 'stale_binding')
    filename = 'package_execution_v8.json' if expected_hash == CONFIG_SHA256 else HISTORICAL_CONFIGS[expected_hash]
    raw = (ROOT/'data/templates/gtm'/filename).read_bytes()
    check(hashlib.sha256(raw).hexdigest() == expected_hash, 'stale_binding')
    spec = json.loads(raw)
    check(spec['formats'] == list(FORMATS) and spec['voice_policy_id'] == BRAND_POLICY_ID, 'stale_binding')
    for name, expected in spec['template_sha256'].items():
        from launchlens.content_contracts import TEMPLATE_DIR, TEMPLATES
        check(hashlib.sha256((TEMPLATE_DIR/TEMPLATES[name]).read_bytes()).hexdigest() == expected, 'stale_binding')
    return spec


def load_package_prompt(stage):
    spec = configuration()['prompts'].get(stage)
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
    spec = configuration(); policy = load_voice_policy(BRAND_POLICY_ID)
    inputs['template'] = {'format':'package', 'templates':{f:load_template(f) for f in FORMATS}}
    inputs['output_schema'] = package_schema()
    inputs['voice_policy'] = {k:v for k,v in inputs['voice_policy'].items() if k not in {'format','voice_mode'}}
    inputs['voice_policy']['format_voices'] = {f:policy['format_voices']['ad_variations' if f == 'ads' else f] for f in FORMATS}
    inputs['package_contract'] = {'id':spec['contract_id'],'sha256':CONFIG_SHA256,
        'formats':list(FORMATS),'campaign_brief_role':'Shared creative direction only; never evidence or launch permission'}
    inputs['user_notes_data_only'] = state.get('user_notes','')
    # Re-review preserved admitted packages against their ORIGINAL input contract.
    # Only the pinned, approved predecessor is allowed; changed evidence still fails binding.
    expected = (state.get('package') or {}).get('input_sha256')
    if expected and digest(inputs) != expected:
        for predecessor in HISTORICAL_CONFIGS:
            historical = deepcopy(inputs)
            historical['package_contract']['sha256'] = predecessor
            if digest(historical) == expected:
                configuration(predecessor)
                inputs = historical
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


def admit_package(value, inputs, *, version=1):
    if type(value) is not dict or set(value) != set(FORMATS):
        raise PackageError()
    records = evidence_records(inputs); drafts = {}
    anchor = digest(value['campaign_brief'])
    for name in FORMATS:
        try:
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
        record.update(version=version, review_status='unreviewed', human_accepted=False,
            publishing_allowed=False, input_sha256=digest(inputs), creative_anchor_sha256=anchor,
            writer_prompt_sha256=configuration(inputs['package_contract']['sha256'])['prompts']['package_writer' if version == 1 else 'package_revision']['sha256'])
        drafts[name] = record
    metadata = {'version':version,'input_sha256':digest(inputs),'package_sha256':digest(value),
        'creative_anchor_sha256':anchor,'human_accepted':False,'publishing_allowed':False}
    return drafts, metadata


def package_value(state):
    return {f:deepcopy(state['drafts'][f]['draft']) for f in FORMATS}


def authoritative_package_binding(state):
    inputs = prepare_package_input(state); metadata = state.get('package')
    check(type(metadata) is dict and set(state['drafts']) == set(FORMATS), 'stale_binding', 'binding')
    version = metadata.get('version')
    check(type(version) is int and version in {1,2}, 'stale_binding', 'binding')
    expected, expected_meta = admit_package(package_value(state), inputs, version=version)
    check(metadata == expected_meta, 'stale_binding', 'binding')
    for name in FORMATS:
        actual = deepcopy(state['drafts'][name]); actual['review_status'] = 'unreviewed'
        check(actual == expected[name], 'stale_binding', 'binding')
    binding = {'run_id':state['run_id'],'draft_version':version,
        'draft_sha256':metadata['package_sha256'],'authoritative_input_sha256':digest(inputs),
        'creative_anchor_sha256':metadata['creative_anchor_sha256']}
    return inputs, metadata, binding


def validate_package_review(value, state, *, isolate_findings=True):
    inputs, _, binding = authoritative_package_binding(state)
    return assess_package_review(value, package_value(state), inputs, binding, isolate_findings=isolate_findings)


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
              'output_schema':package_schema(stage == 'package_reviewer')}
    if stage != 'package_writer':
        result['package'] = package_value(state)
    if stage == 'package_reviewer':
        result['writing_instructions'] = load_package_prompt('package_writer')
        from launchlens.reviewer_groups import phrase_groups,group_schema,PROTOCOL
        result['review_protocol']=PROTOCOL
        result['phrase_groups']=phrase_groups(result['package'])
        result['output_schema']=group_schema(result['phrase_groups'])
        from launchlens.content_contracts import measured_lengths
        result['computed_lengths'] = {f:measured_lengths(result['package'][f]['content'],f) for f in FORMATS}
        result['review_criteria'] = inputs['common_review_criteria']
        # Judge only the bound CURRENT package. Prior findings and human feedback
        # contain obsolete quoted prose; they never cross this review boundary.
        result['review_scope'] = 'Current package version only; no inherited findings or clearance.'
    if stage == 'package_revision':
        permission = state.get('revision_request'); review = state.get('review')
        check(type(permission) is dict and type(review) is dict and review.get('binding') == binding
              and permission.get('binding') == binding and permission.get('review_sha256') == digest(review),
              'permission_denied', 'binding')
        check(type(permission.get('feedback')) is str and 0 < len(permission['feedback'].strip()) <= MAX_PACKAGE_FEEDBACK,
              'permission_denied')
        result.update(review=deepcopy(review['assessment']),owner_feedback_data_only=permission['feedback'],
                      writing_instructions=load_package_prompt('package_writer'))
    return result


def check_field_claims(draft, format_name):
    """Narrow deterministic coverage, not entailment or general factuality detection."""
    refs={v['content_field']:set(v['claim_ids']) for v in draft['claim_references']}
    for path,text in text_fields(draft['content']):
        if format_name=='campaign_brief' and path.startswith('restrictions_and_unknowns.'):
            continue
        lower=text.lower()
        historical_hook=(path=='hook' and 'bringing' in lower and 'cherry experience' in lower)
        clear_flavor=bool(re.search(r"(?:cherry float|this (?:product|flavor)) (?:combines|contains|is made with|has)\b",lower))
        clear_inspiration=bool(re.search(r"(?:is |takes |draws )?inspir(?:ed|ation) (?:by|from) (?:classic )?soda[ -]floats?",lower))
        if (historical_hook or clear_flavor or clear_inspiration) and not refs.get(path):
            raise PackageError(format_name,'field_claim_coverage','content.'+path,'field_claim_coverage')


def project_package_context(inputs):
    """US uses accepted projection unchanged. UK preserves complete scoped context.

    The frozen US projection pins its launch hash: never counterfeit it for UK.
    UK's explicit restricted view therefore retains all original caveats/conflicts.
    """
    from launchlens.writer_context import project_writer_input
    if inputs['validated_request']['market_id']=='US':return project_writer_input(inputs)
    check(inputs['validated_request']['market_id']=='UK','permission_denied')
    view=deepcopy(inputs)
    return {'model_input':view,'manifest':{'authoritative_input_sha256':digest(inputs),
        'model_input_sha256':digest(view),'policy_id':'uk_complete_authority_v1',
        'note':'Complete scoped input retained; US-only frozen projection not reused'}}


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
 'availability_urgency':r"\b(?:announce the launch|stay tuned|where you can find|is here|try it(?: today)?|available(?: now| today)?|now|buy now|shop now|in stores|limited[ -]time|hurry|today only|can['’]t wait)\b",
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


def risky_phrase_scan(package, *, suggestion=False):
    hits=[]
    for name in FORMATS:
        if name not in package:continue
        for path,text in text_fields(package[name]['content']):
            if name=='campaign_brief' and path.startswith('restrictions_and_unknowns.'):
                continue  # Policy warnings are not promotional copy; retained in context.
            patterns=dict(RISK_PATTERNS)
            if suggestion:
                # Hints have no surrounding sentence: screen bare novelty, inferred
                # consumer memory and replacement texture assertions conservatively.
                patterns['novelty'] += r'|\b(?:new|introduce)\b'
                patterns['preference_prediction'] += r'|\b(?:may recall|remember|recall)\b'
                patterns['ingredient_intensity'] += r'|\b(?:smooth|velvety)\b'
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


def reviewer_hint(finding):
    """Filter advisory replacements; absence of a scan hit is NOT semantic proof."""
    value=finding.get('suggested_change');original=finding.get('quote')
    if not isinstance(value,str) or not isinstance(original,str):return None,'not_wording_hint'
    value=value.strip().strip('"“”')
    norm=lambda x:' '.join(re.findall(r"[\w']+",x.casefold()))
    if not value or len(value)>250 or len(value.split())>30:return None,'not_short_replacement'
    if norm(original) and norm(original) in norm(value):return None,'repeats_original'
    if re.match(r"(?:no replacement|no changes?|replace|remove|revise|avoid|keep|use |drop |otherwise|consider|rewrite|describe|retain|do not|delete)\b",value,re.I):
        return None,'editing_instruction_or_no_hint'
    if risky_phrase_scan({'linkedin':{'content':{'body':value}}},suggestion=True):return None,'risky_replacement'
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


def assess_package_review(value, package, inputs, binding, *, isolate_findings=True):
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
            value,dropped,coverage_errors=isolate_judgments(value,package)
        else:value,group_errors=expand_judgments(value,package)
        log.append({'rule':'group_judgments_expanded','group_count':group_count})
    from launchlens.content_contracts import measured_lengths
    lengths={f:measured_lengths(package[f]['content'],f) for f in FORMATS}
    hits=risky_phrase_scan(package);by_id={h['hit_id']:h for h in hits};formats={};all_findings={};issues=[]
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
            f['reviewer_hint'],f['hint_hidden_reason']=reviewer_hint(f)
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
    if isolate_findings:
        result.update(assessment_policy='isolated_findings_v1',unverified_finding_count=len(dropped),
            dropped_findings=dropped,coverage_issues=coverage_errors)
    return result
