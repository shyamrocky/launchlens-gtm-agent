"""Shared header placement/persistence through real Streamlit reruns; offline only."""
from copy import deepcopy
from pathlib import Path
import os,socket,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from streamlit.testing.v1 import AppTest
from launchlens.offline_ui_run import fixture_inventory

class CompactHeaderTests(unittest.TestCase):
 def setUp(self):
  self.net=self.enterContext(patch.object(socket.socket,'connect',side_effect=AssertionError('No network')))
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  self.enterContext(patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'offline','LANGSMITH_TRACING':'false'}))
  self.enterContext(patch('launchlens.inventory_ui.fetch_inventory',side_effect=lambda display,**kwargs:fixture_inventory(display)))
  self.enterContext(patch('launchlens.live_package.current_resume_available',return_value=False))
  self.enterContext(patch('launchlens.review_decisions.saved_review_available',return_value=False))
  self.budget={'remaining_usd':'0.9775988'}
  self.enterContext(patch('launchlens.run_archive.demo_budget',side_effect=lambda:self.budget))
 def app(self):
  a=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
  self.assertFalse(a.exception);return a
 def header(self,a):
  header=next(b for b in a.get('flex_container') if b.key=='page-header')
  self.assertEqual(len(header.get('selectbox')),1)
  self.assertEqual(header.get('selectbox')[0].key,'ui-mode')
  self.assertEqual({b.key for b in header.get('button')},{'home','current'})
  self.assertFalse(a.title);self.assertFalse(a.exception)
 def test_same_mode_widget_is_in_header_on_home_and_empty_current(self):
  a=self.app();self.header(a)
  a.button(key='current').click().run();self.header(a)
  self.assertTrue(any('No current package' in x.value for x in a.info))
  a.button(key='home').click().run();self.header(a)
 def test_both_mode_values_survive_tab_switching_and_reruns(self):
  a=self.app()
  for mode in ['Live agent','Demo simulation','Live agent']:
   a.selectbox(key='ui-mode').select(mode).run()
   for key in ['current','home','current','home']:
    a.button(key=key).click().run();self.header(a)
    self.assertEqual(a.selectbox(key='ui-mode').value,mode)
    self.assertEqual(a.session_state['ui-mode'],mode)
    self.assertEqual(a.session_state['_data_mode'],mode)
 def test_single_live_budget_caption_on_each_tab_tracks_latest_amount(self):
  a=self.app();a.selectbox(key='ui-mode').select('Live agent').run()
  for key,amount,display in [('current','0.9775988','$0.98'),('home','0.734','$0.73')]:
   self.budget['remaining_usd']=amount;a.button(key=key).click().run()
   captions=[x.value for x in a.caption if x.value.startswith('Budget left:')]
   self.assertEqual(captions,['Budget left: '+display])
   header=next(b for b in a.get('flex_container') if b.key=='page-header')
   self.assertEqual(len([x for x in header.get('caption') if x.value.startswith('Budget left:')]),1)
 def test_simulation_keeps_existing_no_live_budget_caption(self):
  a=self.app()
  for key in ['current','home']:
   a.button(key=key).click().run()
   self.assertFalse(any(x.value.startswith('Budget left:') for x in a.caption))
 def test_uk_pause_tab_navigation_and_real_resume_preserve_same_run(self):
  a=self.app();a.button(key='open-UK').click().run();a.button(key='prepare-start').click().run()
  self.header(a);run=a.session_state['offline_run'];before=deepcopy(run.snapshot());calls=deepcopy(run.capture())
  self.assertEqual(before['status'],'needs_clarification')
  self.assertTrue(a.selectbox(key='ui-mode').disabled)
  for key in ['home','current','home','current']:
   a.button(key=key).click().run();self.header(a)
   self.assertIs(a.session_state['offline_run'],run);self.assertEqual(run.snapshot(),before)
   self.assertEqual(run.capture(),calls);self.assertEqual(a.selectbox(key='ui-mode').value,'Demo simulation')
   self.assertTrue(a.selectbox(key='ui-mode').disabled)
  a.radio(key='run-choice').set_value('Draft without availability wording').run()
  next(x for x in a.button if x.label=='Continue').click().run()
  self.assertFalse(a.exception);self.assertIs(a.session_state['offline_run'],run)
  after=run.snapshot();self.assertEqual(after['run_id'],before['run_id'])
  self.assertEqual(after['status'],'awaiting_human_review');self.assertEqual(after['request'],before['request'])
  self.assertTrue(any('UK package' in x.value for x in a.caption))

if __name__=='__main__':unittest.main()
