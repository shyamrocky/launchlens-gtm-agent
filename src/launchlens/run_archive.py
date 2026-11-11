"""Local active/archive references. Protected generated receipts never move or copy.

Archive moves an active descriptor, not evidence. Downloads resolve hash-bound
originals on demand. No model, source, credential or ingestion clients are used.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
from uuid import UUID, uuid4
import zipfile

from launchlens.gtm_registry import HarnessError, validate_request

ROOT = Path(__file__).resolve().parents[2]
LABEL = 'Simulated draft · fictional scenario · not affiliated with The Coca-Cola Company'


def require(ok, message):
    if not ok: raise HarnessError(message)


def private_json(path):
    require(path.is_file() and not path.is_symlink() and not path.stat().st_mode & 0o077,
            'Private run record unavailable')
    require(path.stat().st_size < 32_000_000, 'Run record exceeds bound')
    return json.loads(path.read_bytes())


def write_private(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(not path.is_symlink(), 'Unsafe run record')
    tmp = path.with_name('.'+path.name+'-'+uuid4().hex)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(tmp, path)


def reference(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT.resolve()), 'Unsafe artifact reference')
    return {'path':path.relative_to(ROOT).as_posix(), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def resolve(entry):
    rel = Path(entry['path'])
    require(not rel.is_absolute() and '..' not in rel.parts and rel.parts[:2] in {('data','generated'),('data','private')}, 'Unsafe archive reference')
    path = ROOT/rel
    require(path.resolve().is_relative_to((ROOT/'data').resolve()) and path.is_file() and not path.is_symlink(), 'Archived artifact unavailable')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest()==entry['sha256'], 'Archived artifact changed')
    return path, raw


def _id(value):
    try: require(str(UUID(value))==value, 'Invalid run identity')
    except (ValueError, TypeError, AttributeError): raise HarnessError('Invalid run identity') from None
    return value


def active_path(run_id): return ROOT/'data/private/runs/active'/(_id(run_id)+'.json')
def archive_path(run_id): return ROOT/'data/private/runs/archive'/_id(run_id)/'record.json'
def is_archived(run_id): return archive_path(run_id).is_file()


@contextmanager
def locked():
    import fcntl
    path = ROOT/'data/private/runs/catalog.lock'
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(not path.is_symlink(), 'Unsafe archive lock')
    fd=os.open(path, os.O_RDWR|os.O_CREAT, 0o600)
    with os.fdopen(fd,'r+') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        yield


def record_from_pointer(pointer):
    key='state' if 'state' in pointer else 'source'
    _,raw=resolve(pointer[key]); state=json.loads(raw)
    request=validate_request(state['request']);rid=_id(state['run_id'])
    store=pointer.get('store',str(Path(pointer[key]['path']).parent))
    require((ROOT/store).resolve().is_relative_to((ROOT/'data/generated').resolve()), 'Invalid receipt store')
    version=(state.get('package') or {}).get('version',0)
    approved=state.get('human_accepted') is True
    from types import SimpleNamespace
    from launchlens.package_presentation import effective_approval
    approved=approved or effective_approval(state,store=SimpleNamespace(path=ROOT/store))
    return {'run_id':rid,'request':request,'version':version,'status':'approved' if approved else state['status'],
            'date':datetime.fromtimestamp((ROOT/pointer[key]['path']).stat().st_mtime,timezone.utc).isoformat(),
            'pointer':pointer,'store':store,'simulation_label':LABEL,'state_status':state['status']}


def remember(pointer):
    """Register an updated descriptor only; generated receipts stay in their store."""
    record=record_from_pointer(pointer)
    with locked():
        require(not is_archived(record['run_id']), 'This run was archived; start a new run')
        write_private(active_path(record['run_id']),record)
    return record


def archived_runs():
    base=ROOT/'data/private/runs/archive'
    if not base.exists():return []
    return sorted((private_json(p) for p in base.glob('*/record.json')),key=lambda r:r['archived_at'],reverse=True)


def saved_runs():
    """Current descriptors plus legacy UI pointers; no experimental-store scan."""
    rows={}
    base=ROOT/'data/private/runs/active'
    if base.exists():
        for p in base.glob('*.json'):
            value=private_json(p)
            if not is_archived(value['run_id']): rows[value['run_id']]=value
    for name in ['current-live-run.json','current-review.json']:
        p=ROOT/'data/private'/name
        if p.exists():
            value=record_from_pointer(private_json(p))
            if not is_archived(value['run_id']):rows[value['run_id']]=value
    return sorted(rows.values(),key=lambda r:r['date'],reverse=True)


def market_run(market):
    return next((r for r in saved_runs() if r['request']['market_id']==market),None)


def execution_path(run_id):
    return ROOT/'data/private/runs/execution'/(_id(run_id)+'.lock')


@contextmanager
def execution_lease(run_id):
    """A live worker owns this OS lock, independent of browser session state."""
    import fcntl
    path=execution_path(run_id);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    require(not path.is_symlink(), 'Unsafe execution lock')
    fd=os.open(path,os.O_RDWR|os.O_CREAT,0o600)
    with os.fdopen(fd,'r+') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise HarnessError('A worker is still executing this run') from None
        try:yield
        finally:fcntl.flock(stream,fcntl.LOCK_UN)


def execution_active(run_id):
    import fcntl
    path=execution_path(run_id)
    if not path.exists():return False
    if path.is_symlink():return True
    with path.open('r') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return True
        fcntl.flock(stream,fcntl.LOCK_UN)
    return False


def executing_state(record):
    _,raw=resolve(record['pointer'].get('state',record['pointer'].get('source')))
    state=json.loads(raw)
    return state['status'] in {'created','running'} or state.get('revision_request') is not None


def executing(record):
    return execution_active(record['run_id']) or executing_state(record)


def _artifacts(record):
    refs={}
    store=ROOT/record['store']
    require(store.is_dir() and not store.is_symlink(), 'Receipt store unavailable')
    for p in store.rglob('*'):
        if p.is_file():refs[str(p.relative_to(ROOT))]=reference(p)
    for entry in record['pointer'].values():
        if isinstance(entry,dict) and set(entry)=={'path','sha256'}:
            resolve(entry);refs[entry['path']]=entry
    # Retain the original accounting, never substitute the new demo ledger.
    budget=ROOT/'data/private/build-budget-20261109.json'
    auth=record['pointer'].get('authorization')
    if auth:
        _,raw=resolve(auth);permission=json.loads(raw)
        if permission.get('budget_ledger'):budget=ROOT/permission['budget_ledger']
    budget_summary=None
    if budget.exists():
        ledger=private_json(budget)
        budget_summary={k:ledger[k] for k in ['ceiling_usd','accounted_usd','remaining_usd']}
        budget_summary.update(ledger_path=str(budget.relative_to(ROOT)),ledger_sha256_at_archive=reference(budget)['sha256'])
    return list(refs.values()),budget_summary


def archive_run(record, *, active=False, session_notes=None):
    """MOVE descriptor and matching UI pointers. Never mutate protected originals."""
    with locked(), execution_lease(record['run_id']):
        require(not active and record['state_status'] not in {'created','running'} and not executing_state(record), 'Stop the run first')
        rid=_id(record['run_id']);dest=archive_path(rid)
        require(not dest.exists(),'Package is already archived')
        current=record_from_pointer(record['pointer'])
        require(current['run_id']==rid and current['version']==record['version'], 'Package changed; reopen confirmation')
        artifacts,budget=_artifacts(record)
        current.update(artifacts=artifacts,prior_budget=budget,
            archived_at=datetime.now(timezone.utc).isoformat(),session_notes=session_notes or {})
        # Freeze a descriptor, then rename it into archive. No deletion or copying.
        source=active_path(rid);write_private(source,current)
        dest.parent.mkdir(parents=True,exist_ok=False,mode=0o700)
        os.rename(source,dest)
        for name in ['current-live-run.json','current-review.json']:
            p=ROOT/'data/private'/name
            if not p.exists():continue
            other=record_from_pointer(private_json(p))
            if other['run_id']==rid:os.rename(p,dest.parent/name)
        return current


def download_package(record):
    """All referenced receipts + per-version Markdown, constructed only in memory."""
    refs=record.get('artifacts')
    if refs is None:refs,_=_artifacts(record)
    data=io.BytesIO();versions={}
    with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr('README.txt',LABEL+'\nRead-only archive. Approval never publishes.\n')
        bundle.writestr('archive-record.json',json.dumps(record,ensure_ascii=False,indent=2))
        for entry in refs:
            _,raw=resolve(entry);bundle.writestr('receipts/'+entry['path'],raw)
            if Path(entry['path']).name.startswith('state-'):
                value=json.loads(raw)
                if value.get('package') and value['run_id']==record['run_id']:
                    versions[value['package']['version']]=value
        from launchlens.package_presentation import markdown_package
        for version,state in sorted(versions.items()):
            bundle.writestr('Version-'+str(version)+'.md',markdown_package(state,approved=record['status']=='approved' and version==record['version']))
    return data.getvalue()


def discover_legacy_runs():
    """Explicit one-time owner reset inventory; never run during ordinary Home reads."""
    rows={r['run_id']:r for r in saved_runs()}
    for store in (ROOT/'data/generated').glob('live-package-*'):
        states=list(store.glob('state-*.json'));captures=list(store.glob('capture-*.json'))
        if not states or not captures or not (store/'authorization.json').is_file():continue
        latest=lambda values:max(values,key=lambda p:int(p.stem.rsplit('-',1)[1]))
        pointer={'store':str(store.relative_to(ROOT)),'state':reference(latest(states)),
            'capture':reference(latest(captures)),'authorization':reference(store/'authorization.json')}
        record=record_from_pointer(pointer)
        if not is_archived(record['run_id']):rows.setdefault(record['run_id'],record)
    return sorted(rows.values(),key=lambda r:r['date'])


def demo_session():
    path=ROOT/'data/private/demo-session.json'
    if not path.exists():return None
    value=private_json(path)
    require(value.get('owner_authorized') is True and value.get('ceiling_usd') in {'1.00','2.00'}, 'Demo budget approval unavailable')
    rel=Path(value['budget_ledger'])
    require(rel.parent==Path('data/private') and rel.name.startswith('demo-budget-') and rel.suffix=='.json', 'Invalid demo ledger')
    return value


def demo_budget():
    value=demo_session()
    if not value:return None
    from launchlens.live_package import StandingBudget
    return StandingBudget(ROOT/value['budget_ledger']).read()


def provision_demo_budget():
    """Owner-only provisioning, not called by archive, Refresh, rerender or Start."""
    from launchlens.package_content import CONFIG_SHA256
    from launchlens.live_package import PROFILE_SHA256
    require(demo_session() is None, 'Demo session already exists; budget is never reset implicitly')
    identity=uuid4().hex
    rel='data/private/demo-budget-'+identity+'.json'
    value={'version':1,'ceiling_usd':'1.00','opening_accounted_usd':'0',
           'opening_reference':'Fresh demo allocation; prior spending remains in its original ledger',
           'owner_authorization':'Explicit standing USD1 demo approval, November 10, 2026; dry run and recording',
           'claims':[],'accounted_usd':'0','remaining_usd':'1.00'}
    write_private(ROOT/rel,value)
    write_private(ROOT/'data/private/demo-session.json',{'owner_authorized':True,'session_id':identity,
        'budget_ledger':rel,'ceiling_usd':'1.00','created_at':datetime.now(timezone.utc).isoformat(),
        'scope':'Registered Cherry Float markets; demo dry run and recording only; stop at budget exhaustion',
        'profile_sha256':PROFILE_SHA256,'package_sha256':CONFIG_SHA256})
    return value


def raise_demo_budget():
    """Explicit owner-only USD2 extension of the SAME ledger, never an app action."""
    from launchlens.live_package import StandingBudget
    session=demo_session();require(session is not None,'Demo session unavailable')
    ledger=StandingBudget(ROOT/session['budget_ledger'])
    def extend(value):
        require(value['ceiling_usd'] in {'1.00','2.00'},'Unexpected demo ceiling')
        if value['ceiling_usd']=='2.00':return
        value.setdefault('ceiling_authorizations',[]).append({
            'previous_ceiling_usd':value['ceiling_usd'],'ceiling_usd':'2.00',
            'authorized_at':datetime.now(timezone.utc).isoformat(),
            'reference':'Explicit owner standing USD2 demo cap approval, November 10, 2026; no ledger reset'})
        value['ceiling_usd']='2.00'
    value=ledger._update(extend)
    if session['ceiling_usd']!='2.00':
        session.update(ceiling_usd='2.00',ceiling_authorization='Explicit owner standing USD2 approval, November 10, 2026; original ledger and spending retained')
        write_private(ROOT/'data/private/demo-session.json',session)
    return value
