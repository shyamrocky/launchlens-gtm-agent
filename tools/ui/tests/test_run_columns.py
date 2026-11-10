"""Shared run panel remains outside the three tabs; no model/source calls."""
from copy import deepcopy
from pathlib import Path
import os,socket,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from streamlit.testing.v1 import AppTest

class RunColumnTests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  p=patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'offline'});p.start();self.addCleanup(p.stop)
 def app(self):
  a=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
  a.button(key='open-US').click().run();a.button(key='prepare-start').click().run();self.assertFalse(a.exception);return a
 def test_panel_persists_on_all_tabs_without_state_or_execution_changes(self):
  a=self.app();run=a.session_state['offline_run'];state=run.snapshot();calls=deepcopy(run.capture())
  for tab in ['Activity','Review','Package']:
   a.session_state['run-tabs-'+state['run_id']]=tab;a.run();self.assertFalse(a.exception)
   blocks=a.get('flex_container');summary=next(b for b in blocks if b.key=='run-summary')
   self.assertFalse(summary.get('tab'));self.assertFalse(any(b.key=='run-status-card' for b in blocks))
   html=' '.join(x.proto.body for x in summary.get('html'))
   for text in ['Revisions used','Budget left','Campaign brief','LinkedIn','Promotional email','Short blog','Ad']:
    self.assertIn(text,html)
   self.assertEqual(len([b for b in summary.get('button') if b.key=='approve-package']),1)
   self.assertEqual(len([b for b in summary.get('button') if b.key=='create-next-version']),1)
  self.assertEqual(run.snapshot(),state);self.assertEqual(run.capture(),calls)
 def test_full_width_run_uses_65_35_columns_and_responsive_css(self):
  a=self.app();grid=next(b for b in a.get('flex_container') if b.key=='run-columns')
  weights=[b.proto.weight for b in grid.get('column')]
  self.assertIn(.65,weights);self.assertIn(.35,weights)
  self.assertTrue(any(b.key=='run-layout' for b in a.get('flex_container')))
  css=(ROOT/'src/launchlens/inventory_ui.css').read_text()
  self.assertIn('@media(max-width:800px)',css);self.assertIn('flex-direction:column-reverse',css)

if __name__=='__main__':unittest.main()
