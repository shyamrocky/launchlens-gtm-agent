"""Compact Review and full-draft drawer use existing run state, no inference."""
from copy import deepcopy
from pathlib import Path
import os,socket,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from streamlit.testing.v1 import AppTest
from launchlens.review_decisions import grouped_findings
class CompactReviewTests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  p=patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'offline'});p.start();self.addCleanup(p.stop)
 def app(self,case='review'):
  a=AppTest.from_file(str(ROOT/'tools/preview_run_states.py'),default_timeout=20);a.query_params['case']=case;a.run();self.assertFalse(a.exception);return a
 def test_review_only_stack_and_recap_no_full_drafts_or_mock_status(self):
  a=self.app();self.assertEqual(len(a.tabs),3)
  self.assertNotIn('Drafts with highlights',[h.value for h in a.subheader])
  self.assertFalse(any('Mock assessment' in c.value for c in a.caption))
  self.assertFalse(any('Human approval pending' in c.value for c in a.caption))
  html=' '.join(x.proto.body for x in a.get('html'));self.assertNotIn('<article class="draft-copy">',html)
  a.button(key='review-summary').click().run();self.assertIn('You’re through the stack',[h.value for h in a.subheader])
 def test_card_opens_exact_format_drawer_without_state_or_call_change(self):
  a=self.app();run=a.session_state['offline_run'];before=run.snapshot();calls=deepcopy(run.capture())
  with patch('launchlens.agent_run_ui.full_draft_dialog') as modal:
   next(b for b in a.button if (b.key or '').startswith('full-draft-')).click().run()
   self.assertEqual(modal.call_count,1);s,name,focus=modal.call_args.args
   self.assertEqual(s,before);self.assertEqual(name,focus['format'])
   self.assertEqual(focus['context'][focus['start']:focus['end']],focus['quote'])
  self.assertEqual(run.snapshot(),before);self.assertEqual(run.capture(),calls)
 def test_current_v2_wins_over_old_card_position_and_no_v1_quotes(self):
  a=self.app();run=a.session_state['offline_run'];v1=run.snapshot();old=grouped_findings(v1)
  run.revise(v1['run_id'],'Existing fixture feedback',1,v1['package']['package_sha256']);a.run();s=run.snapshot()
  self.assertEqual(s['package']['version'],2);self.assertEqual(s['review']['binding']['draft_version'],2)
  self.assertEqual(a.session_state['run-review-position-'+s['run_id']],0)
  self.assertTrue(any(c.value.startswith('Version 2 ·') for c in a.caption))
  with patch('launchlens.agent_run_ui.full_draft_dialog') as modal:
   next(b for b in a.button if (b.key or '').startswith('full-draft-')).click().run()
   self.assertEqual(modal.call_args.args[0]['package']['version'],2)
  a.button(key='review-summary').click().run()
  self.assertFalse(any(b.label=='Create Version 2' for b in a.button))
  self.assertFalse(any(t.label=='Anything else for Version 2? (optional)' for t in a.text_area))
 def test_current_v2_choices_can_create_v3_and_then_show_new_current_review(self):
  from ui_review_helpers import finish_stack
  a=self.app('review_v2');run=a.session_state['offline_run'];before=run.snapshot()
  finish_stack(a);self.assertEqual(a.button(key='create-next-version').label,'Create Version 3')
  self.assertFalse(a.button(key='create-next-version').disabled)
  a.text_area[0].input('Preserve facts, apply my wording choices.')
  a.button(key='create-next-version').click().run();self.assertFalse(a.exception)
  s=run.snapshot();self.assertEqual(s['package']['version'],3);self.assertEqual(s['review']['binding']['draft_version'],3)
  self.assertEqual(s['draft_history'][:2],before['draft_history']);self.assertEqual(a.session_state['run-tabs-'+s['run_id']],'Review')
  self.assertFalse(s['human_accepted'])
 def test_demo_why_is_user_relevant_and_raw_explanation_stays_technical(self):
  a=self.app();texts=' '.join(m.value for m in a.markdown if m.value.startswith('**Why:**'))
  self.assertTrue(texts);self.assertNotIn('fixture',texts.lower());self.assertNotIn('mock',texts.lower())
  self.assertTrue(any('authored fixture' in c.value for c in a.caption))
  self.assertTrue(any(e.label=='Technical details' and not e.proto.expanded for e in a.expander))
if __name__=='__main__':unittest.main()
