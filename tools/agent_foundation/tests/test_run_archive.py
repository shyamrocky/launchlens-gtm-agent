"""Archive reference integrity, explicit move and isolated demo accounting; no network."""
from copy import deepcopy
import hashlib,io,json,socket,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
import sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from launchlens import run_archive as archive
from launchlens.offline_ui_run import OfflineUIRun
from launchlens.offline_fixtures import request
from launchlens.voice_policy import BRAND_POLICY_ID
from launchlens.gtm_registry import HarnessError

class ArchiveTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  p=patch.object(archive,'ROOT',self.root);p.start();self.addCleanup(p.stop)
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.network=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.network.call_count,0))
 def run_record(self,market='US'):
  run=OfflineUIRun(request(market),voice_policy_id=BRAND_POLICY_ID,package=True)
  state=run.execute(run.snapshot()['run_id']);store=self.root/'data/generated'/('live-package-'+state['run_id'])
  archive.write_private(store/'state-01.json',state);archive.write_private(store/'capture-01.json',{'calls':'safe fixture'})
  archive.write_private(store/'human-decision-01.json',{'safe':'fixture decisions'})
  archive.write_private(store/'authorization.json',{'standing_budget':True})
  pointer={'state':archive.reference(store/'state-01.json'),'capture':archive.reference(store/'capture-01.json'),
   'authorization':archive.reference(store/'authorization.json'),'store':str(store.relative_to(self.root))}
  archive.write_private(self.root/'data/private/current-live-run.json',pointer)
  return archive.remember(pointer),store
 def test_archive_moves_descriptor_and_pointer_original_receipts_never_change(self):
  record,store=self.run_record();before={p.name:p.read_bytes() for p in store.iterdir()}
  source=archive.active_path(record['run_id'])
  with patch.object(archive.os,'rename',wraps=archive.os.rename) as move:
   saved=archive.archive_run(record)
  self.assertTrue(any(Path(c.args[0])==source and Path(c.args[1])==archive.archive_path(record['run_id']) for c in move.call_args_list))
  self.assertFalse(source.exists());self.assertFalse((self.root/'data/private/current-live-run.json').exists())
  self.assertTrue((archive.archive_path(record['run_id']).parent/'current-live-run.json').is_file())
  self.assertEqual(before,{p.name:p.read_bytes() for p in store.iterdir()})
  self.assertEqual(archive.saved_runs(),[]);self.assertEqual(len(archive.archived_runs()),1)
  self.assertEqual(list(archive.archive_path(record['run_id']).parent.glob('state-*.json')),[])
  bundle=zipfile.ZipFile(io.BytesIO(archive.download_package(saved)))
  self.assertIn('Version-1.md',bundle.namelist());self.assertIn(archive.LABEL,bundle.read('Version-1.md').decode())
  self.assertTrue(any('human-decision' in n for n in bundle.namelist()))
 def test_download_first_is_read_only_and_cancel_needs_no_mutation(self):
  record,store=self.run_record();before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
  self.assertTrue(archive.download_package(record).startswith(b'PK'))
  self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
 def test_running_or_explicit_active_blocks_before_any_move(self):
  record,store=self.run_record()
  with self.assertRaisesRegex(HarnessError,'Stop the run first'):archive.archive_run(record,active=True)
  state=json.loads((store/'state-01.json').read_text());state['status']='running'
  archive.write_private(store/'state-01.json',state)
  record['pointer']['state']=archive.reference(store/'state-01.json')
  with self.assertRaisesRegex(HarnessError,'Stop the run first'):archive.archive_run(record)
  self.assertTrue(archive.active_path(record['run_id']).exists());self.assertFalse(archive.archived_runs())
 def test_changed_protected_receipt_fails_closed_and_cannot_restore_archived_run(self):
  record,store=self.run_record();saved=archive.archive_run(record)
  with self.assertRaises(HarnessError):archive.remember(record['pointer'])
  archive.write_private(store/'capture-01.json',{'tampered':True})
  with self.assertRaisesRegex(HarnessError,'changed'):archive.download_package(saved)
 def test_prior_budget_summary_and_new_budget_are_not_reset_by_archiving(self):
  old={'ceiling_usd':'1.00','opening_accounted_usd':'0','claims':[],'accounted_usd':'0.34','remaining_usd':'0.66'}
  archive.write_private(self.root/'data/private/build-budget-20261109.json',old)
  record,_=self.run_record();saved=archive.archive_run(record)
  fresh=archive.provision_demo_budget();self.assertEqual(fresh['remaining_usd'],'1.00')
  self.assertEqual(saved['prior_budget']['accounted_usd'],'0.34')
  self.assertEqual(archive.private_json(self.root/'data/private/build-budget-20261109.json'),old)
  with self.assertRaises(HarnessError):archive.provision_demo_budget()
  self.assertTrue(archive.download_package(saved))
 def test_other_market_survives_archiving_and_no_fake_archives_are_created(self):
  us,_=self.run_record();uk,_=self.run_record('UK')
  archive.archive_run(us)
  self.assertEqual([r['request']['market_id'] for r in archive.saved_runs()],['UK'])
  self.assertEqual([r['request']['market_id'] for r in archive.archived_runs()],['US'])
 def test_archives_keep_all_versions_and_remain_downloadable_as_shared_budget_changes(self):
  record,store=self.run_record();state=json.loads((store/'state-01.json').read_text());state['package']['version']=2
  archive.write_private(store/'state-02.json',state);record['pointer']['state']=archive.reference(store/'state-02.json')
  record=archive.record_from_pointer(record['pointer'])
  ledger=self.root/'data/private/demo-budget-fixture.json'
  archive.write_private(ledger,{'ceiling_usd':'1.00','accounted_usd':'0.20','remaining_usd':'0.80'})
  archive.write_private(store/'authorization.json',{'budget_ledger':'data/private/demo-budget-fixture.json'})
  record['pointer']['authorization']=archive.reference(store/'authorization.json')
  saved=archive.archive_run(record)
  archive.write_private(ledger,{'ceiling_usd':'1.00','accounted_usd':'0.40','remaining_usd':'0.60'})
  z=zipfile.ZipFile(io.BytesIO(archive.download_package(saved)))
  self.assertIn('Version-1.md',z.namelist());self.assertIn('Version-2.md',z.namelist())
  self.assertEqual(saved['prior_budget']['remaining_usd'],'0.80')

if __name__=='__main__':unittest.main()
