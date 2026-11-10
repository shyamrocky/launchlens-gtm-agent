"""One shared, explicitly provisioned demo ledger across fresh registered runs."""
import json,socket,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/agent_foundation/tests')]
from test_live_package import KEYS,NOW,FrozenDateTime
from launchlens import run_archive as archive
from launchlens.live_package import demo_permission,RunBudget,create_live_run,LiveGateError,StandingBudget
from launchlens.offline_fixtures import request

class DemoBudgetTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  for p in [patch('launchlens.run_archive.ROOT',self.root),patch('launchlens.live_package.ROOT',self.root),
            patch('launchlens.live_package.datetime',FrozenDateTime),patch.object(socket.socket,'connect',side_effect=AssertionError('No network'))]:
   p.start();self.addCleanup(p.stop)
  archive.provision_demo_budget()
 def test_registered_market_permissions_have_same_budget_and_original_models(self):
  values=[demo_permission(request(m)) for m in ['US','UK','IN']]
  self.assertEqual(len({v['budget_ledger'] for v in values}),1)
  self.assertEqual([v['request']['market_id'] for v in values],['US','UK','IN'])
  self.assertEqual(len({v['authorization_id'] for v in values}),3)
  with self.assertRaises(LiveGateError):demo_permission({**request(),'product_id':'NIKE'})
  a=RunBudget(values[0],now=NOW);a.arm(request());event=a.claim('controller','a'*64)
  a.complete(event,{'model':a.plan['roles']['controller']['model_id'],'usage':{'prompt_tokens':100,'completion_tokens':50,'total_tokens':150}})
  b=RunBudget(demo_permission(request()),now=NOW)
  self.assertEqual(b.standing.path,a.standing.path);self.assertLess(Decimal(b.standing.read()['remaining_usd']),Decimal('1'))
  self.assertEqual(len(b.standing.read()['claims']),1)
 def test_archive_then_fresh_start_never_refills_budget_and_stale_guard_cannot_call(self):
  with patch('launchlens.live_package.read_selected_keys',return_value=KEYS):
   run=create_live_run(request());rid=run.snapshot()['run_id'];self.assertFalse(run.capture()['writer'])
   with self.assertRaises(LiveGateError):create_live_run(request())
   run.stop(rid)
   before=archive.demo_budget();record=archive.market_run('US');archive.archive_run(record)
   new=create_live_run(request())
  self.assertNotEqual(new.snapshot()['run_id'],rid);self.assertEqual(archive.demo_budget(),before)
  with self.assertRaisesRegex(LiveGateError,'Archived'):run.guard.claim('controller','b'*64)
  with self.assertRaisesRegex(LiveGateError,'Archived'):run._persist(run.snapshot())
  with self.assertRaisesRegex(LiveGateError,'Archived'):run.guard.reserve_revision({'draft_version':1})
  self.assertTrue(archive.download_package(archive.archived_runs()[0]))
 def test_exhausted_shared_ledger_prevents_start_before_reading_keys(self):
  session=archive.demo_session();ledger=self.root/session['budget_ledger']
  value=archive.private_json(ledger);value.update(opening_accounted_usd='1.00',accounted_usd='1.00',remaining_usd='0.00')
  archive.write_private(ledger,value)
  with patch('launchlens.live_package.read_selected_keys',side_effect=AssertionError('No credentials read')):
   with self.assertRaises(LiveGateError):create_live_run(request())
  self.assertFalse((self.root/'data/generated').exists())

if __name__=='__main__':unittest.main()
