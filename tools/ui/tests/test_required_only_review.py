"""D048: required cards only; optional notes expand without mandatory choices."""
import os,socket,sys,unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from streamlit.testing.v1 import AppTest
from launchlens.package_presentation import must_decide
from launchlens.review_decisions import grouped_findings
class RequiredOnlyReviewTests(unittest.TestCase):
 def test_stack_and_summary_exclude_optional_findings_without_changing_state(self):
  with patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'offline'}),patch.object(socket.socket,'connect',side_effect=AssertionError('No network')) as net:
   a=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
   a.button(key='open-US').click().run();a.button(key='prepare-start').click().run();self.assertFalse(a.exception)
   r=a.session_state['offline_run'];state=r.snapshot();calls=deepcopy(r.capture())
   groups=grouped_findings(state);required=[g for g in groups if must_decide(g)];optional=[g for g in groups if g['needs_attention'] and not must_decide(g)]
   self.assertTrue(optional);self.assertTrue(required)
   self.assertIn(str(len(optional))+' optional suggestions ›',[x.label for x in a.expander])
   opt=next(x for x in a.expander if x.label.endswith('optional suggestions ›'));self.assertFalse(opt.proto.expanded)
   self.assertTrue(any('of '+str(len(required))+' decided' in x.value for x in a.caption))
   for _ in required:
    next(b for b in a.button if (b.key or '').startswith('keep-phrase-')).click().run()
   self.assertIn('You’re through the stack',[x.value for x in a.subheader])
   self.assertFalse(a.button(key='create-next-version').disabled)
   self.assertEqual(len([b for b in a.button if (b.key or '').startswith('recap-')]),len(required))
   self.assertEqual(r.snapshot(),state);self.assertEqual(r.capture(),calls);self.assertEqual(net.call_count,0)
if __name__=='__main__':unittest.main()
