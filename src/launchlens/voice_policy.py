"""Small application-owned writing-policy binding; no provider or semantic validator."""
import hashlib
import json
from pathlib import Path

BRAND_POLICY_ID = 'simulated_brand_v1'
ROOT = Path(__file__).resolve().parents[2]
POLICY_SHA256 = '532a7940770f7462b6507d95cbfa8bacd26f745ce821ae920fc633e02415f583'


def load_voice_policy(policy_id):
    if policy_id != BRAND_POLICY_ID:
        raise ValueError('Unsupported writing policy')
    raw = (ROOT / 'data/templates/gtm/voice_policy_v1.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != POLICY_SHA256:
        raise ValueError('Writing policy identity differs')
    return json.loads(raw)


def voice_brief(policy_id):
    policy = load_voice_policy(policy_id)
    return {'policy_id':policy['policy_id'], 'version':policy['version'],
            'policy_sha256':POLICY_SHA256, 'format':'linkedin',
            'voice_mode':policy['format_voices']['linkedin'], 'meaning':policy['meaning']}


def voice_prompt(stage, policy_id):
    policy = load_voice_policy(policy_id)
    if stage not in policy['prompts']:
        raise ValueError('Unsupported writing-policy prompt')
    spec = policy['prompts'][stage]
    raw = (ROOT / 'src/launchlens/prompts' / spec['file']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != spec['sha256']:
        raise ValueError('Writing-policy prompt identity differs')
    return raw.decode()


# Active package tone policy. v1 above remains immutable for historical bindings
# and the earlier LinkedIn-only checkpoint; new package inputs bind this v2 hash.
TONE_POLICY_SHA256 = '182225f865f6aaa7e7a6085f8b8b8a56bb3850a6fcd848a909351aba47dc8805'


def load_tone_policy(expected_hash=None):
    expected_hash = expected_hash or TONE_POLICY_SHA256
    if expected_hash != TONE_POLICY_SHA256:
        raise ValueError('Unsupported package tone policy')
    raw = (ROOT / 'data/templates/gtm/voice_policy_v2.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError('Package tone policy identity differs')
    return json.loads(raw)


def tone_measurements(content, format_name, policy):
    """Measure copy only, excluding citations and app-owned metadata. Advisory."""
    from launchlens.content_contracts import _field, _texts
    result = []
    for target in policy['format_specs'][format_name]['advisory']:
        values = [content if field == '$content' else _field(content, field) for field in target['fields']]
        text = ' '.join(s for value in values for s in _texts(value))
        metric = target['metric']
        actual = len(text.split()) if metric == 'words' else text.count('!') if metric == 'exclamation_marks' else len(text)
        result.append({'fields':target['fields'], 'metric':metric, 'actual':actual,
            'target':{k:v for k,v in target.items() if k in {'min','max'}},
            'meets_target':target.get('min',0) <= actual <= target.get('max',float('inf'))})
    return result


def validate_tone_structure(draft, format_name, policy, exact_cta):
    """Explicit structural rules only. Tone/claim semantics stay with review."""
    import re
    from launchlens.content_contracts import require, _texts
    from launchlens.linkedin_drafting import LINK
    content = draft['content']; rules = policy['format_specs'][format_name]['blocking']
    if rules.get('exact_supplied_cta'):
        require(content['cta'] == exact_cta, 'Supplied CTA required',field_path='content.cta',rule='cta_mismatch')
    for field,bounds in rules.get('arrays',{}).items():
        require(bounds['min'] <= len(content[field]) <= bounds['max'], 'Required array count differs',
                field_path='content.'+field,rule='array_length_invalid')
    from launchlens.package_content import text_fields
    for path,text in text_fields(content):
        if policy['all_formats']['no_links']:
            require(not LINK.search(text),'Draft links prohibited',field_path='content.'+path,rule='prohibited_link')
        pronouns=rules.get('neutral_pronouns',[])
        if pronouns:
            require(not re.search(r"\b(?:"+'|'.join(re.escape(x) for x in pronouns)+r")\b",text,re.I),
                    'Neutral third-person brief required',field_path='content.'+path,rule='neutral_voice_required')


def tone_schema(schema, policy):
    """Project configured structural array bounds into the model-facing schema."""
    from copy import deepcopy
    result=deepcopy(schema)
    for name,spec in policy['format_specs'].items():
        props=result['properties'][name]['properties']['content']['properties']
        for field,bounds in spec['blocking'].get('arrays',{}).items():
            props[field].update(minItems=bounds['min'],maxItems=bounds['max'])
    return result
