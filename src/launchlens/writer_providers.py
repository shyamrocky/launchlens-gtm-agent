"""Nebius-only stdlib one-attempt transport for explicit Writer comparisons.

No credential discovery or network calls at import. Endpoint allowlist is code-owned.
Never logs request headers or exception strings; preserves response bytes pre-parse.
"""
from pathlib import Path
from threading import Lock
import os
import ssl
import urllib.error
import urllib.request

from launchlens.live_research import NoRedirect, dumps, ENDPOINT
from launchlens.writer_comparison import REGISTERED_MODELS, WireResponse, require


def read_provider_keys(models, env_file=None):
    """Future live provisioning only. Read selected keys; never return/log others."""
    require(models and all(m['provider']=='nebius' and m['model_id'] in REGISTERED_MODELS.values() for m in models),
        'Only registered Nebius profiles can load credentials')
    return read_selected_keys({'NEBIUS_API_KEY'}, env_file)


def read_selected_keys(names, env_file=None):
    require(type(names) is set and names and names <= {'NEBIUS_API_KEY','NOTION_API_KEY','PINECONE_API_KEY'}, 'Unregistered credential scope')
    values={}
    for name in names:
        value=os.environ.get(name)
        if value:values[name]=value
    if env_file is not None and Path(env_file).exists():
        path=Path(env_file)
        require(path.is_file() and not path.stat().st_mode&0o077,'Credential file must be private')
        seen=set()
        for line in path.read_text().splitlines():
            if '=' not in line or line.lstrip().startswith('#'):continue
            name,value=line.split('=',1);name=name.strip().removeprefix('export ').strip()
            if name not in names:continue
            require(name not in seen,'Duplicate selected credential');seen.add(name)
            value=value.strip().strip("\"'")
            if name not in values:values[name]=value
    require(set(values)==names and all(type(v) is str and len(v)>=12 and not any(c.isspace() for c in v) for v in values.values()),
        'Selected provider credentials unresolved')
    return values


class ProviderHTTP:
    """One HTTPS request; default 45s timeout (bounded override), 2MB bound, no retries."""
    def __init__(self,model,key, *, request_validator=None, timeout_seconds=45):
        require(model['provider']=='nebius' and (model['model_id'] in REGISTERED_MODELS.values() or (model['model_id']=='openai/gpt-oss-120b' and request_validator is not None)),'Unknown Nebius profile')
        require(type(key) is str and len(key)>=12 and not any(c.isspace() for c in key),'Invalid credential')
        require(request_validator is None or callable(request_validator),'Invalid application request validator')
        require(type(timeout_seconds) in {int,float} and 0 < timeout_seconds <= 180,'Invalid provider timeout')
        self.timeout_seconds=timeout_seconds
        self.request_validator=request_validator
        self.model=dict(model);self.key=key;self.lock=Lock();self.used=False
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()))

    def __call__(self,payload):
        with self.lock:
            require(not self.used,'Provider attempt already consumed');self.used=True
        require(payload.get('model')==self.model['model_id'],'Model differs')
        if self.request_validator is not None:
            require(self.request_validator(payload) is True,'Unreviewed prepared request')
        else:
            require(set(payload)=={'model','messages','temperature','max_tokens','stream','store'} and
                payload['stream'] is False and payload['store'] is False and payload['temperature']==0 and
                payload['max_tokens']==2048 and type(payload['messages']) is list and len(payload['messages'])==2 and
                payload['messages'][0].get('role')=='system' and payload['messages'][1].get('role')=='user' and
                all(type(v.get('content')) is str for v in payload['messages']),'Unreviewed Nebius Writer request')
        headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json','Accept':'application/json'}
        request=urllib.request.Request(ENDPOINT,data=dumps(payload).encode(),headers=headers,method='POST')
        try:
            response=self.opener.open(request,timeout=self.timeout_seconds)
        except urllib.error.HTTPError as error:
            response=error  # Preserve the provider error body as well; never retry.
        with response:
            body=response.read(2_000_001)
            status=response.status
            truncated=len(body)>2_000_000
            telemetry={k:response.headers[k] for k in ['x-request-id','request-id','retry-after'] if k in response.headers}
        redacted=self.key.encode() in body or any(self.key in v for v in telemetry.values())
        if redacted:
            body=body.replace(self.key.encode(),b'[REDACTED_CREDENTIAL]')
            telemetry={k:v.replace(self.key,'[REDACTED_CREDENTIAL]') for k,v in telemetry.items()}
        return WireResponse(status,body,telemetry,redacted,truncated)
