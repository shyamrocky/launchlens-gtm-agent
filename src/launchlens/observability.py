"""Opt-in, best-effort LangSmith export. Never exports harness/receipt objects.

The application only enqueues bounded JSON records. All SDK work, sanitization
and network IO happen on one daemon worker; no flush/join occurs during a run.
Native SDK autotracing stays disabled to avoid implicit state/environment capture.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from decimal import Decimal
from functools import wraps
import inspect
import json
import logging
import os
from pathlib import Path
from queue import Queue
import re
from threading import Thread, Lock
import time
from uuid import uuid4, uuid5, NAMESPACE_URL

_CURRENT = ContextVar('launchlens_span', default=None)
_SCANS = ContextVar('launchlens_scan_batch', default=None)
_LOG = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
_EMAIL = re.compile(r"[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
_PRIVATE = re.compile(r'(?:data/(?:private|generated)/[^\s"<>]+|(?:human-(?:decision|internal-approval)|call-\d+-claim|capture-\d+|state-\d+)[^\s"<>]*\.(?:json|bin))')
_EXCLUDE = re.compile(r'(?:api.?key|credential|authorization|password|secret|access.?token|refresh.?token|user.?email|ledger|receipt|spending|budget|headers|runtime|env)', re.I)


def settings(path=None):
    """Read configuration without mutating os.environ or discovering other services."""
    values = {}
    try:
        for line in (Path(path) if path else ROOT/'.env').read_text().splitlines():
            if '=' not in line or line.lstrip().startswith('#'): continue
            key, value = line.split('=', 1)
            values[key.strip().removeprefix('export ').strip()] = value.strip().strip('\"\'')
    except (OSError, UnicodeError): pass
    values.update(os.environ)
    return values


def sanitize(value, secrets=()):
    if isinstance(value, dict):
        return {sanitize(str(k), secrets): sanitize(v, secrets) for k, v in value.items()
                if not _EXCLUDE.search(str(k))}
    if isinstance(value, (list, tuple)): return [sanitize(v, secrets) for v in value]
    if isinstance(value, datetime): return value
    if isinstance(value, str):
        if value[:1] in {'{', '['}:
            try: return json.dumps(sanitize(json.loads(value), secrets), ensure_ascii=False)
            except (ValueError, TypeError, RecursionError): pass
        for secret in secrets:
            if secret: value = value.replace(secret, '[REDACTED]')
        return _PRIVATE.sub('[PRIVATE_FILE]', _EMAIL.sub('[EMAIL]', value))
    if value is None or type(value) in (int, float, bool): return value
    return '[OBJECT]'  # Never repr adapter instances, exceptions or private stores.


def state_view(state):
    """Explicit allowlist; never serialize the full graph/checkpointer state."""
    if not isinstance(state, dict): return {}
    result = {k: state[k] for k in ('run_id', 'request', 'status', 'feedback',
              'clarification', 'pending', 'drafts', 'review', 'evidence') if k in state}
    if isinstance(state.get('launch'), dict): result['gate_decision'] = state['launch'].get('decision')
    return result


def run_metadata(state, models=None):
    request = state.get('request', {})
    # Explicit scope is preferred; legacy requests express scope as *_id.
    scope = request.get('scope') or state.get('metadata', {}).get('scope')
    if isinstance(scope, dict) and 'type' in scope and 'value' in scope:
        kind, value = scope['type'], scope['value']
    else:
        dimensions = [(k[:-3], v) for k, v in request.items() if k.endswith('_id')
                      and k not in {'use_case_id', 'product_id', 'objective_id', 'run_id'}]
        kind, value = dimensions[0] if dimensions else ('all', 'all')
    return {'use_case_id': request.get('use_case_id', 'run'),
            'product_id': request.get('product_id'), 'scope_type': kind, 'scope_value': value,
            'gate_decision': (state.get('launch') or {}).get('decision'),
            'models': models or {}}


def _client(key):
    from langsmith import Client
    from urllib3.util.retry import Retry
    return Client(api_url='https://api.smith.langchain.com', api_key=key,
                  auto_batch_tracing=False, timeout_ms=(2000, 5000),
                  retry_config=Retry(total=0), omit_traced_runtime_info=True,
                  tracing_sampling_rate=1.0)


def _warn_failure(operation, error):
    """Log fixed categories only: no exception text, repr, traceback or payload."""
    try:
        text = str(error).lower()
        if isinstance(error, TimeoutError) or 'timed out' in text or 'timeout' in text: reason = 'timeout'
        elif '401' in text or 'authentication' in text: reason = 'authentication'
        elif '403' in text or 'forbidden' in text or 'workspace' in text: reason = 'permission_or_workspace'
        elif isinstance(error, ConnectionError) or 'connection' in text: reason = 'connection'
        else: reason = 'client_or_delivery_error'
        stage = operation if operation in {'client', 'lookup', 'create', 'update', 'configure', 'context'} else 'delivery'
        _LOG.warning('LangSmith export failed: operation=%s reason=%s; later exports remain enabled', stage, reason)
    except Exception: pass  # Logging must not stop the worker or the application.


class Tracer:
    """Bounded best-effort export; a failed operation never disables future ones."""
    def __init__(self, key, project, *, secrets=(), client_factory=_client, capacity=256):
        self.key, self.project, self.secrets = key, project, tuple(secrets) + (key,)
        self.factory = client_factory
        self.queue = Queue(maxsize=capacity)
        self.roots = {}; self.contexts = {}; self.lock = Lock(); self.failed_operations = 0
        self.worker = Thread(target=self._deliver, name='launchlens-traces', daemon=True)
        self.worker.start()

    def _deliver(self):
        client = None
        while True:
            operation, values = self.queue.get()
            stage = 'client' if client is None else operation
            try:
                if client is None: client = self.factory(self.key)
                clean = sanitize(values, self.secrets)
                # Identity is local/persisted. No read_run or GET /runs lookup.
                stage = operation
                if operation == 'create': client.create_run(**clean)
                else:
                    # The ingestion endpoint accepts a minimal patch without
                    # SDK-added nullable fields. Keep the same one-attempt policy.
                    patch = {k:v for k,v in clean.items() if v is not None}
                    patch['id'] = patch.pop('run_id')
                    body = json.dumps({'patch':[patch]}, ensure_ascii=False,
                        default=lambda v:v.isoformat() if isinstance(v,datetime) else None).encode()
                    client.request_with_retries('POST','/runs/batch',stop_after_attempt=1,
                        request_kwargs={'data':body,'headers':{'Content-Type':'application/json'}})
            except Exception as error:
                self.failed_operations += 1
                _warn_failure(stage, error)
                # Drop this operation only; later records remain enabled.
            finally: self.queue.task_done()

    def emit(self, operation, values):
        try: self.queue.put_nowait((operation, values))
        except Exception: pass  # Tracing is lossy under backpressure, never blocking.

    def _identity(self, run_id):
        identity = str(uuid5(NAMESPACE_URL, 'launchlens/run/' + run_id))
        now = datetime.now(timezone.utc)
        return {'schema': 'launchlens-trace-context-v1', 'run_id': run_id,
                'root_id': identity, 'start_time': now.isoformat(),
                'dotted_order': now.strftime('%Y%m%dT%H%M%S%fZ') + identity}

    def bind_context(self, state, store=None):
        """Private tracing metadata only; never alters graph state or receipts."""
        run_id = state['run_id']
        if store is None: return
        try:
            path = Path(store.path)/'langsmith-trace-context.json'
            with self.lock:
                if run_id in self.contexts: return
                if not path.exists():
                    context = self._identity(run_id)
                    try: store.write(path.name, context)
                    except FileExistsError: pass  # Another local tracer won the race.
                if path.is_symlink() or path.stat().st_mode & 0o077 or path.stat().st_size > 2048:
                    raise ValueError('Invalid tracing context file')
                context = json.loads(path.read_text())
                if not isinstance(context,dict) or set(context) != {'schema','run_id','root_id','start_time','dotted_order'}:
                    raise ValueError('Invalid tracing context shape')
                stamp = datetime.fromisoformat(context['start_time'])
                expected_id = str(uuid5(NAMESPACE_URL, 'launchlens/run/' + run_id))
                if (context['schema'] != 'launchlens-trace-context-v1' or context['run_id'] != run_id or
                    context['root_id'] != expected_id or stamp.utcoffset() != timezone.utc.utcoffset(stamp) or
                    context['dotted_order'] != stamp.strftime('%Y%m%dT%H%M%S%fZ') + expected_id):
                    raise ValueError('Invalid tracing context binding')
                self.contexts[run_id] = context
        except Exception as error:
            _warn_failure('context', error)  # No file/exception contents in logs.

    def root(self, state, models=None):
        run_id = state['run_id']
        metadata = run_metadata(state, models)
        scope = 'all' if metadata['scope_type'] == 'all' else str(metadata['scope_type']) + '=' + str(metadata['scope_value'])
        with self.lock:
            context = self.contexts.setdefault(run_id, self._identity(run_id))
            identity = context['root_id']
            if identity not in self.roots:
                root = {'id': identity, 'trace_id': identity, 'dotted_order': context['dotted_order'],
                        'name': str(metadata['use_case_id']) + ' · ' + scope + ' · ' + run_id,
                        'run_type': 'chain', 'start_time': datetime.fromisoformat(context['start_time']),
                        'inputs': {'request': state.get('request', {})},
                        'project_name': self.project, 'extra': {'metadata': metadata}, 'tags': tags(metadata)}
                self.roots[identity] = root
                # Same-ID POST is safe on reattachment; children keep the exact
                # saved root/order without any server read or receipt upload.
                self.emit('create', dict(root))
            return self.roots[identity]

    def _root_update(self, root, outputs=None):
        # Original start is immutable; every later segment extends the same root.
        with self.lock:
            ended = max(datetime.now(timezone.utc),root.get('_last_end',root['start_time']))
            root['_last_end'] = ended
            value = {'run_id':root['id'], 'trace_id':root['id'],
                'dotted_order':root['dotted_order'], 'start_time':root['start_time'],
                'end_time':ended, 'session_name':self.project,
                'extra':root['extra'], 'tags':root['tags']}
            if outputs is not None: value['outputs'] = outputs
            self.emit('update',value)

    def _merge_root_metadata(self, root, metadata):
        old = root['extra']['metadata']
        merged = {**old, **{k:v for k,v in metadata.items() if v is not None and k!='models'}}
        merged['models'] = {**old.get('models',{}),**metadata.get('models',{})}
        root['extra'] = {'metadata':merged}; root['tags'] = tags(merged)

    def note_gate(self, root_id, decision):
        if decision not in {'Proceed','Clarify','Hold'}: return
        with self.lock:
            root = self.roots.get(root_id)
            if root is None: return
            self._merge_root_metadata(root,{'gate_decision':decision})
        self._root_update(root)

    @contextmanager
    def run(self, state, models=None):
        try:
            root = self.root(state, models)
            token = _CURRENT.set((self, root))
            prior = _SCANS.get(); scan_token = None
            if prior is None or prior['tracer'] is not self or prior['root']['id']!=root['id']:
                batch = {'tracer':self,'root':root,'manager':None,'formats':[],
                         'scan_count':0,'format_scan_count':0,'hit_count':0}
                scan_token = _SCANS.set(batch)
        except Exception:
            yield
            return
        try: yield
        finally:
            if scan_token is not None:
                batch = _SCANS.get()
                if batch['manager'] is not None:
                    batch['record']['outputs'] = {k:batch[k] for k in ('scan_count','format_scan_count','hit_count')}
                    batch['record']['end_time'] = batch['last_end']
                    batch['manager'].__exit__(None,None,None)
                _SCANS.reset(scan_token)
            try: _CURRENT.reset(token)
            finally: self._root_update(root)

    def update(self, state, models=None):
        try:
            root = self.root(state, models)
            metadata = run_metadata(state, models)
            with self.lock: self._merge_root_metadata(root,metadata)
            self._root_update(root,{'status':state.get('status'),
                                   'version':(state.get('package') or {}).get('version')})
        except Exception: pass


def tags(metadata):
    result = [k + '=' + str(v) for k, v in metadata.items() if k != 'models' and v is not None]
    result.extend('model=' + str(v) for v in dict.fromkeys(metadata['models'].values()))
    return result


_EXPORTERS = {}
_EXPORTERS_LOCK = Lock()


def configured(*, path=None, secrets=(), client_factory=_client):
    try:
        values = settings(path)
        if values.get('LANGSMITH_TRACING', '').lower() != 'true' or not values.get('LANGSMITH_API_KEY', '').strip(): return None
        key = values['LANGSMITH_API_KEY']; project = values.get('LANGSMITH_PROJECT') or 'default'
        hidden = tuple(v for k, v in values.items() if v and re.search(r'KEY|TOKEN|SECRET|PASSWORD|EMAIL', k, re.I)) + tuple(secrets)
        cache = (key, project, client_factory)
        with _EXPORTERS_LOCK:
            if cache not in _EXPORTERS: _EXPORTERS[cache] = Tracer(key, project, secrets=hidden, client_factory=client_factory)
            tracer = _EXPORTERS[cache]
            with tracer.lock: tracer.secrets = tuple(dict.fromkeys(tracer.secrets + hidden))
            return tracer
    except Exception as error:
        _warn_failure('configure', error)
        return None


@contextmanager
def span(name, inputs=None, *, kind='tool', metadata=None):
    current = _CURRENT.get()
    record = {}; token = None
    if current:
        try:
            tracer, parent = current; identity = str(uuid4()); now = datetime.now(timezone.utc)
            row = {'id': identity, 'trace_id': parent['trace_id'], 'parent_run_id': parent['id'],
                   'dotted_order': parent['dotted_order'] + '.' + now.strftime('%Y%m%dT%H%M%S%fZ') + identity,
                   'name': name, 'run_type': kind, 'inputs': inputs or {},
                   'start_time': now, 'project_name': tracer.project}
            token = _CURRENT.set((tracer, row)); started = time.monotonic()
        except Exception: current = None
    try: yield record
    except BaseException:
        record['error'] = 'operation_interrupted_or_failed'
        raise
    finally:
        if current and token is not None:
            # Post a completed child in ONE supported create payload, avoiding
            # the failing child PATCH and its nullable identity fields entirely.
            ended = record.get('end_time') or datetime.now(timezone.utc)
            tracer.emit('create', {**row, 'end_time': ended,
                'outputs': record.get('outputs', {'status': 'failed' if record.get('error') else 'completed'}),
                'error': record.get('error'), 'extra': {'metadata': {
                    **(metadata or {}), 'latency_seconds': (ended-row['start_time']).total_seconds(),
                    **record.get('metadata', {})}}})
            try: _CURRENT.reset(token)
            except ValueError:
                # LangGraph callbacks can finish in a different copied context.
                # Completion has already been queued; restore that context's parent.
                _CURRENT.set(current)


def step(name, *, capture=()):
    """Observe function IO, excluding self/state and all non-JSON objects."""
    def decorate(function):
        signature = inspect.signature(function)
        @wraps(function)
        def wrapped(*args, **kwargs):
            if not _CURRENT.get(): return function(*args, **kwargs)
            bound = signature.bind(*args, **kwargs).arguments
            with span(name, {k: bound[k] for k in capture if k in bound}) as record:
                result = function(*args, **kwargs)
                outputs = {'result': result}
                if isinstance(result,dict):
                    if 'decision' in result:
                        outputs['gate_decision'] = result['decision']
                        if name=='launch gate check':
                            tracer,parent = _CURRENT.get()
                            tracer.note_gate(parent['trace_id'],result['decision'])
                    if isinstance(result.get('records'),list): outputs['evidence_hit_count'] = len(result['records'])
                elif isinstance(result,list): outputs['hit_count'] = len(result)
                record['outputs'] = outputs
                return result
        return wrapped
    return decorate


def scan_step(formats):
    """Group the pure format-independent scan calls under one segment parent."""
    def decorate(function):
        @wraps(function)
        def wrapped(package,*args,**kwargs):
            current = _CURRENT.get(); batch = _SCANS.get()
            if not current or batch is None: return function(package,*args,**kwargs)
            if batch['manager'] is None:
                _CURRENT.set((batch['tracer'],batch['root']))
                manager = span('risky-phrase scan',{'formats':batch['formats']})
                record = manager.__enter__(); batch.update(manager=manager,record=record,parent=_CURRENT.get())
                _CURRENT.set(current)
            batch['scan_count'] += 1; hits = []
            try:
                for name in formats:
                    if name not in package: continue
                    if name not in batch['formats']: batch['formats'].append(name)
                    _CURRENT.set(batch['parent'])
                    with span('scan '+name,{'format':name}) as record:
                        # Matches never cross formats: concatenation preserves the
                        # original order, IDs, exclusions and returned scan result.
                        found = function({name:package[name]},*args,**kwargs)
                        record['outputs'] = {'format':name,'hit_count':len(found)}
                        hits.extend(found);batch['format_scan_count'] += 1;batch['hit_count'] += len(found)
                return hits
            finally:
                batch['last_end'] = datetime.now(timezone.utc)
                _CURRENT.set(current)
        return wrapped
    return decorate


def llm(name, payload, operation, *, pricing=None):
    if not _CURRENT.get(): return operation()
    with span(name, {'messages': payload.get('messages'), 'tools': payload.get('tools')},
              kind='llm', metadata={'ls_provider': 'nebius', 'ls_model_name': payload.get('model')}) as record:
        result = operation()
        usage = result.get('usage', {})
        mapped = {target: usage[source] for source,target in (
            ('prompt_tokens','input_tokens'), ('completion_tokens','output_tokens'),
            ('total_tokens','total_tokens')) if type(usage.get(source)) is int and usage[source]>=0}
        # Only the already configured public role rates are used. No ledger read,
        # new price lookup, spending mutation or assumption of unknown usage.
        if pricing and 'input_tokens' in mapped and 'output_tokens' in mapped:
            try:
                inp = Decimal(mapped['input_tokens'])*Decimal(str(pricing['input_per_million_usd']))/Decimal(1_000_000)
                out = Decimal(mapped['output_tokens'])*Decimal(str(pricing['output_per_million_usd']))/Decimal(1_000_000)
                if inp.is_finite() and out.is_finite() and inp>=0 and out>=0:
                    mapped.update(input_cost=float(inp),output_cost=float(out),total_cost=float(inp+out))
            except (ValueError, TypeError, KeyError, ArithmeticError): pass
        record['outputs'] = {'choices': result.get('choices'),
                             'usage': {k:usage[k] for k in ('prompt_tokens','completion_tokens','total_tokens') if k in usage},
                             'usage_metadata': mapped}
        record['metadata'] = {'usage_metadata': mapped}
        if 'total_cost' in mapped:
            record['metadata'].update(cost_source='configured_profile_rates', cost_is_estimate=True)
        return result


def graph_callbacks():
    """LangGraph emits node callbacks automatically; ignore internal runnable IO."""
    if not _CURRENT.get(): return []
    from langchain_core.callbacks import BaseCallbackHandler
    class Nodes(BaseCallbackHandler):
        run_inline = True
        def __init__(self): self.active = {}
        def on_chain_start(self, serialized, inputs, *, run_id, metadata=None, **kwargs):
            name = kwargs.get('name')
            if not metadata or metadata.get('langgraph_node') != name: return
            manager = span('node:' + name, state_view(inputs), kind='chain')
            record = manager.__enter__(); self.active[run_id] = (manager, record)
        def on_chain_end(self, outputs, *, run_id, **kwargs):
            entry = self.active.pop(run_id, None)
            if entry:
                manager, record = entry; record['outputs'] = state_view(outputs); manager.__exit__(None, None, None)
        def on_chain_error(self, error, *, run_id, **kwargs):
            entry = self.active.pop(run_id, None)
            if entry:
                manager, record = entry
                record['outputs'] = {'interrupted_or_failed': True}; manager.__exit__(None, None, None)
    return [Nodes()]


def human_event(state, name, details=None, *, store=None):
    """Receipt-free UI event; no reread of protected approvals/decisions/budgets."""
    try:
        tracer = configured()
        if tracer:
            tracer.bind_context(state,store)
            with tracer.run(state):
                with span(name, details or {}) as record: record['outputs'] = {'version': (state.get('package') or {}).get('version')}
            tracer.update(state)
    except Exception: pass


def download_data(state, text, *, store=None):
    # Streamlit's deferred-data callable runs on download, preserving on_click=
    # ignore (no rerun). Export bytes and the visible controls remain identical.
    if not configured(): return text
    snapshot = {'run_id': state['run_id'], 'request': dict(state['request']),
                'package': {'version': state['package']['version']},
                'launch': {'decision': (state.get('launch') or {}).get('decision')}}
    def deliver():
        human_event(snapshot, 'download', {'format': 'markdown'},store=store)
        return text
    return deliver


@contextmanager
def run_context(tracer, state, models=None):
    from contextlib import nullcontext
    with tracer.run(state, models) if tracer else nullcontext():
        yield
