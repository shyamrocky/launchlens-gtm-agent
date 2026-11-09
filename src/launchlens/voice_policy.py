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
