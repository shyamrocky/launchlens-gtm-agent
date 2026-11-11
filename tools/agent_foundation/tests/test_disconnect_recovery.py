"""Browser loss never replays paid work; stale checkpoints recover or archive."""
from copy import deepcopy
from pathlib import Path
import io,json,socket,sys,tempfile,unittest,zipfile
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/agent_foundation/tests')]
from test_live_package import Wire,permission,KEYS,NOW,project,FrozenDateTime
from launchlens import run_archive as archive
from launchlens.live_package import LivePackageRun,load_current_live_run,ProtectedStore,demo_permission
from launchlens.offline_fixtures import ReviewFixtureTools,request

class BrowserDisconnected(BaseException):pass

class DisconnectRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  for p in [patch('launchlens.live_package.ROOT',self.root),patch('launchlens.run_archive.ROOT',self.root),
   patch('launchlens.live_package.datetime',FrozenDateTime),patch('launchlens.live_package.project_writer_input',side_effect=project),
   patch('launchlens.live_package.read_selected_keys',return_value=KEYS),patch.object(socket.socket,'connect',side_effect=AssertionError('No network'))]:
   obj=p.start();self.addCleanup(p.stop)
 def make_run(self,standing=False):
  grant=permission()
  if standing:
   archive.provision_demo_budget();grant=demo_permission(request());grant['allow_automatic_refinement']=False
  self.wire=Wire();store=ProtectedStore(self.root/'data/generated/live-package-safe-test')
  store.write('authorization.json',grant)
  run=LivePackageRun(grant,KEYS,tools=ReviewFixtureTools(),wire_factory=self.wire,store=store,now=NOW)
  run._persist(run.snapshot());return run
 def test_disconnect_after_completion_reopens_same_review_without_dispatch(self):
  run=self.make_run();rid=run.snapshot()['run_id']
  def drop(_,s):
   if s['status']=='awaiting_human_review':raise BrowserDisconnected()
  with self.assertRaises(BrowserDisconnected):run.execute(rid,on_update=drop)
  calls=len(self.wire.calls);self.assertFalse(archive.execution_active(rid))
  reopened=load_current_live_run();s=reopened.snapshot()
  self.assertEqual(s['run_id'],rid);self.assertEqual(s['package']['version'],1)
  self.assertEqual(s['status'],'awaiting_human_review');self.assertTrue(s['review'])
  self.assertEqual(len(self.wire.calls),calls);self.assertEqual(reopened.capture()['spending']['attempts'],run.capture()['spending']['attempts'])
 def test_disconnect_after_v1_resumes_required_review_without_writer_replay(self):
  run=self.make_run();rid=run.snapshot()['run_id']
  def drop(_,s):
   if s.get('package') and not s.get('review'):raise BrowserDisconnected()
  with self.assertRaises(BrowserDisconnected):run.execute(rid,on_update=drop)
  calls=len(self.wire.calls);before=run.snapshot()['package'];original={p:p.read_bytes() for p in run.store.path.iterdir()}
  with patch('launchlens.live_package.ProviderHTTP',side_effect=lambda model,key,request_validator=None,timeout_seconds=None:self.wire(model,request_validator)):
   reopened=load_current_live_run()
  s=reopened.snapshot()
  self.assertEqual(s['status'],'awaiting_human_review');self.assertEqual(s['package'],before)
  self.assertTrue(s['review']);self.assertEqual(len(self.wire.calls),calls+1)
  self.assertFalse(archive.execution_active(rid))
  self.assertTrue(all(p.read_bytes()==raw for p,raw in original.items()))
  saved=archive.archive_run(archive.market_run('US'))
  self.assertEqual(archive.saved_runs(),[])
  self.assertIsNone(zipfile.ZipFile(io.BytesIO(archive.download_package(saved))).testzip())
 def test_active_worker_attaches_read_only_and_cannot_archive_or_duplicate(self):
  run=self.make_run();rid=run.snapshot()['run_id'];calls=len(self.wire.calls)
  with archive.execution_lease(rid):
   self.assertTrue(archive.execution_active(rid));reopened=load_current_live_run()
   self.assertTrue(reopened.watching_worker);self.assertTrue(reopened.read_only)
   with self.assertRaises(Exception):archive.archive_run(archive.market_run('US'))
   self.assertEqual(len(self.wire.calls),calls)
  self.assertEqual(load_current_live_run().snapshot()['status'],'interrupted')
 def test_reviewed_v1_recovers_abandoned_refinement_without_refunding_reservations(self):
  run=self.make_run(standing=True);s=run.execute(run.snapshot()['run_id']);package=deepcopy(s['package']);review=deepcopy(s['review'])
  from launchlens.package_content import authoritative_package_binding
  binding=authoritative_package_binding(s)[2];run.guard.permission['allow_automatic_refinement']=True;run.guard.reserve_automatic_revision(binding)
  s.update(status='running',revision_request={'origin':'agent','binding':binding},pending=None)
  s['ledger']['harness-auto-refinement']={'status':'scheduled'}
  run._persist(s);budget=archive.demo_budget();calls=len(self.wire.calls)
  reopened=load_current_live_run();restored=reopened.snapshot()
  self.assertEqual(restored['status'],'awaiting_human_review');self.assertEqual(restored['package'],package);self.assertEqual(restored['review'],review)
  self.assertIsNone(restored['revision_request']);self.assertFalse(reopened.guard.pending_revision_claims)
  self.assertEqual(archive.demo_budget(),budget);self.assertEqual(len(self.wire.calls),calls)
  self.assertEqual(restored['revision_attempts'],0);self.assertFalse(restored['human_accepted'])
 def test_unknown_accounting_retains_draft_but_cannot_resume_calls_and_can_archive(self):
  run=self.make_run();s=run.execute(run.snapshot()['run_id']);capture=run.capture()
  capture['spending']['events'][-1]['status']='reserved_unknown_until_usage'
  from launchlens.live_package import _write_recovery,_current_receipts
  loaded,store=_current_receipts();_write_recovery(loaded,store,s,capture)
  reopened=load_current_live_run()
  self.assertTrue(reopened.read_only);self.assertEqual(reopened.snapshot()['status'],'interrupted')
  self.assertEqual(reopened.snapshot()['package'],s['package']);archive.archive_run(archive.market_run('US'))
  self.assertEqual(archive.saved_runs(),[])
 def test_authorization_outside_private_or_exact_run_store_is_still_rejected(self):
  self.make_run();p=self.root/'data/private/current-live-run.json';spec=archive.private_json(p)
  other=self.root/'data/generated/unrelated/authorization.json';archive.write_private(other,permission())
  spec['authorization']=archive.reference(other);archive.write_private(p,spec)
  with self.assertRaises(Exception):load_current_live_run()

if __name__=='__main__':unittest.main()
