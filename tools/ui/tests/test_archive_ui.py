"""Archive dialog/list and empty Current run; offline UI with no provider calls."""
import io,os,socket,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from streamlit.testing.v1 import AppTest
from launchlens import run_archive as archive

class ArchiveUITests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  for p in [patch.object(archive,'ROOT',Path(self.tmp.name)),patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'offline'}),
            patch.object(socket.socket,'connect',side_effect=AssertionError('No network'))]:
   p.start();self.addCleanup(p.stop)
 def app(self):return AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=25).run()
 def start(self):
  a=self.app();a.button(key='open-US').click().run();a.button(key='prepare-start').click().run();self.assertFalse(a.exception);return a
 def test_download_first_cancel_and_confirm_move_to_prepare_without_execution(self):
  a=self.start();run=a.session_state['offline_run'];before=run.snapshot();count=len(run.capture()['writer'])
  a.button(key='run-archive').click().run();self.assertFalse(a.exception)
  self.assertTrue(any(x.label=='Download first' for x in a.get('download_button')))
  a.button(key='archive-cancel').click().run();self.assertEqual(run.snapshot(),before)
  a.button(key='run-archive').click().run();a.button(key='archive-confirm').click().run();self.assertFalse(a.exception)
  self.assertEqual(a.title[0].value,'Prepare US package');self.assertNotIn('offline_run',a.session_state)
  self.assertEqual(run.snapshot(),before);self.assertEqual(len(run.capture()['writer']),count)
  a.button(key='home').click().run();self.assertEqual(a.button(key='archives').label,'Archived packages (1) ›')
  self.assertFalse(any(b.key=='fresh-US' for b in a.button))
  a.button(key='current').click().run();self.assertEqual(a.title[0].value,'Current run')
  self.assertTrue(any('No current package' in n.value for n in a.info))
  a.button(key='home').click().run();a.button(key='archives').click().run()
  self.assertEqual(a.title[0].value,'Archived packages');self.assertEqual(len(a.get('download_button')),1)
  self.assertFalse(any('Restore' in b.label for b in a.button))
 def test_home_per_market_archive_and_active_run_guard(self):
  a=self.start();run=a.session_state['offline_run'];before=run.snapshot()
  a.button(key='home').click().run();self.assertTrue(a.button(key='fresh-US'))
  a.button(key='fresh-US').click().run();a.button(key='archive-cancel').click().run()
  self.assertEqual(run.snapshot(),before)
  from launchlens.offline_ui_run import OfflineUIRun
  from launchlens.offline_fixtures import request
  from launchlens.voice_policy import BRAND_POLICY_ID
  fresh=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True)
  a.session_state['offline_run']=fresh;a.session_state['screen']='run';a.run()
  self.assertTrue(a.button(key='run-archive').disabled)
  a.button(key='home').click().run();a.button(key='fresh-US').click().run()
  self.assertTrue(a.button(key='archive-confirm').disabled)
  self.assertTrue(any('Stop the run first' in x.value for x in a.warning))
 def test_saved_market_opens_run_and_keeps_secondary_start_fresh(self):
  a=self.start();run=a.session_state['offline_run'];before=run.snapshot()
  a.button(key='home').click().run()
  self.assertEqual(a.button(key='view-US').label,'View run ›')
  self.assertTrue(a.button(key='fresh-US'))
  self.assertFalse(any(b.key=='open-US' for b in a.button))
  self.assertTrue(all(a.button(key=f'open-{market}') for market in ('UK','IN')))
  a.button(key='view-US').click().run()
  self.assertFalse(a.exception)
  self.assertEqual(a.title[0].value,'US package')
  self.assertEqual(run.snapshot(),before)
 def test_approved_market_uses_view_package_label(self):
  a=self.start();run=a.session_state['offline_run'];a.button(key='home').click().run()
  from launchlens import inventory_ui
  record=inventory_ui.simulation_record(run)
  record['status']='approved'
  with patch('launchlens.inventory_ui.ui_saved_runs',return_value=[record]):
   a.run()
  self.assertEqual(a.button(key='view-US').label,'View package ›')
  self.assertTrue(a.button(key='fresh-US'))
 def test_source_refresh_not_in_nav_and_rebuild_notice_only_on_mismatch(self):
  a=self.app();self.assertEqual([b.label for b in a.button[:2]],['GTM launches','Current run'])
  self.assertEqual(a.button(key='refresh').label,'↻ Refresh')
  self.assertFalse(any(b.key=='rebuild' for b in a.button));self.assertFalse(any('Rebuild evidence' in x.value for x in a.info))
  snap=a.session_state['inventory'];snap['source_access']={'Product Brief':{'status':'changed'}}
  a.session_state['inventory']=snap;a.run()
  self.assertIn('Product brief changed · evidence not re-indexed',' '.join(x.proto.body for x in a.get('html')));self.assertTrue(a.button(key='source-rebuild'))

if __name__=='__main__':unittest.main()
