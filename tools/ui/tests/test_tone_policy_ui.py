"""Read-only tone guidance and visible advisory measurements; no provider calls."""
from pathlib import Path
from copy import deepcopy
import os,socket,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from streamlit.testing.v1 import AppTest
from launchlens.voice_policy import load_tone_policy
class ToneUITests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  p=patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'offline'});p.start();self.addCleanup(p.stop)
 def app(self):
  a=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=25).run();a.button(key='open-US').click().run();return a
 def test_prepare_core_tone_and_five_lines_read_only_notes_do_not_change_policy(self):
  a=self.app();self.assertFalse(a.exception);p=load_tone_policy()
  self.assertTrue(any(p['core_tone'] in x.proto.body for x in a.get('html')))
  self.assertIn('per format ›',[e.label for e in a.expander])
  text=' '.join(m.value for m in a.markdown)
  for spec in p['format_specs'].values():self.assertIn(spec['tone'],text)
  self.assertFalse(any('Tone' in x.label for x in a.selectbox));self.assertFalse(any('Tone' in x.label for x in a.text_input))
  a.text_area(key='prepare-notes-US').input('Make LinkedIn more playful').run();self.assertEqual(load_tone_policy(),p)
 def test_package_labels_and_computed_advisories_visible_without_more_calls(self):
  a=self.app();a.button(key='prepare-start').click().run();self.assertFalse(a.exception)
  run=a.session_state['offline_run'];state=run.snapshot();before=deepcopy(run.capture())
  a.session_state['run-tabs-'+state['run_id']]='Package';a.run();self.assertFalse(a.exception)
  captions=' '.join(c.value for c in a.caption)
  for spec in load_tone_policy()['format_specs'].values():self.assertIn(spec['label'],captions)
  self.assertIn('Advisory ·',captions);self.assertIn('Does not block approval',captions)
  self.assertEqual(run.capture(),before);self.assertEqual(run.snapshot(),state)

if __name__=='__main__':unittest.main()
