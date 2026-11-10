"""Approve as-is in the existing app; no inference or draft rewriting."""
from copy import deepcopy
from pathlib import Path
import os,socket,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from streamlit.testing.v1 import AppTest
from launchlens.review_decisions import grouped_findings,record_decision,decision_book

class ApproveAsIsUITests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  p=patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'offline'});p.start();self.addCleanup(p.stop)
 def app(self):
  a=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
  a.button(key='open-US').click().run();a.button(key='prepare-start').click().run();self.assertFalse(a.exception);return a
 def test_approve_directly_without_card_choices_and_no_change_until_button_clicked(self):
  a=self.app();run=a.session_state['offline_run'];s=run.snapshot();before=deepcopy(run.capture())
  key='run-review-decisions-'+s['run_id'];book=deepcopy(a.session_state[key])
  a.session_state['run-tabs-'+s['run_id']]='Package';a.run()
  self.assertTrue(a.button(key='approve-package').disabled)
  next(c for c in a.checkbox if (c.key or '').startswith('run-approval-as-is-')).check().run()
  self.assertFalse(a.button(key='approve-package').disabled);self.assertEqual(a.session_state[key],book)
  a.button(key='approve-package').click().run();self.assertFalse(a.exception)
  self.assertTrue(any('Package approved for internal use' in x.proto.body for x in a.get('html')))
  self.assertEqual(run.snapshot(),s);self.assertEqual(run.capture(),before)
  self.assertEqual(a.session_state['run-internal-approval-'+s['run_id']]['version'],1)
  self.assertTrue(any('Package approved for internal use' in x.proto.body for x in a.get('html')))
 def test_prior_requested_rewrite_does_not_force_another_version_and_later_revision_still_works(self):
  a=self.app();run=a.session_state['offline_run'];s=run.snapshot()
  s=run.revise(s['run_id'],'Explicit first revision',1,s['package']['package_sha256']);a.run()
  key='run-review-decisions-'+s['run_id'];book=decision_book(s)
  for g in grouped_findings(s):
   if g['needs_attention']:book=record_decision(s,book,g['id'],'request_changes')
  a.session_state[key]=book;a.session_state['run-tabs-'+s['run_id']]='Package';a.run();calls=deepcopy(run.capture())
  next(c for c in a.checkbox if (c.key or '').startswith('run-approval-as-is-')).check().run()
  self.assertFalse(a.button(key='approve-package').disabled)
  a.button(key='approve-package').click().run();self.assertEqual(run.snapshot(),s);self.assertEqual(run.capture(),calls)
  receipt=deepcopy(a.session_state['run-internal-approval-'+s['run_id']]);self.assertEqual(receipt['version'],2)
  run.revise(s['run_id'],'Owner explicitly asks for a later version',2,s['package']['package_sha256']);a.run()
  self.assertFalse(a.exception);self.assertEqual(run.snapshot()['package']['version'],3)
  self.assertTrue(a.button(key='approve-package').disabled)
  self.assertFalse(next(c for c in a.checkbox if (c.key or '').startswith('run-approval-as-is-')).value)
  self.assertEqual(a.session_state['run-internal-approval-'+s['run_id']],receipt)

if __name__=='__main__':unittest.main()
