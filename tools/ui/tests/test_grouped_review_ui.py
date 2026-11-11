"""Grouped PMM review interactions run against real offline harness; zero network."""
from copy import deepcopy
from pathlib import Path
import os,socket,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from streamlit.testing.v1 import AppTest
from launchlens.review_decisions import grouped_findings,decision_book,unresolved_groups,effective_choice
from launchlens.offline_ui_run import OfflineUIRun
from launchlens.offline_fixtures import request
from launchlens.voice_policy import BRAND_POLICY_ID
from ui_review_helpers import finish_stack,show_card

class GroupedReviewUITests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  p=patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'offline'});p.start();self.addCleanup(p.stop)
 def app(self):
  a=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
  a.button(key='open-US').click().run();a.button(key='prepare-start').click().run();a.button(key='run-review').click().run()
  self.assertFalse(a.exception);return a
 def test_replaces_run_page_and_groups_before_highlighted_drafts(self):
  a=self.app();s=a.session_state['offline_run'].snapshot();g=grouped_findings(s)
  self.assertTrue(any('US package' in c.value for c in a.caption));self.assertEqual([t.label for t in a.tabs if t.label in {'Activity','Review','Package'}],['Activity','Review','Package']);self.assertEqual(len(a.tabs),3)
  self.assertTrue(any(str(len(unresolved_groups(g,decision_book(s))))+' must-decide' in c.value or 'must-decide left' in c.value for c in a.caption))
  self.assertIn('What the agent did',[h.value for h in a.subheader])
  self.assertNotIn('Reviewer findings · Independent assessment',[h.value for h in a.subheader])
  self.assertFalse(any('Cleared by Reviewer' in e.label for e in a.expander))
  html=' '.join(x.proto.body for x in a.get('html'));self.assertIn('<mark>',html)
  self.assertTrue(any(e.label=='Technical details' and not e.proto.expanded for e in a.expander))
 def test_group_decision_occurrence_override_and_refresh_do_not_execute(self):
  a=self.app();run=a.session_state['offline_run'];before=run.snapshot();calls=deepcopy(run.capture())
  g=next(x for x in grouped_findings(before) if x['needs_attention']);o=g['occurrences'][0]
  a.button(key='changes-'+g['id']).click().run()
  show_card(a,g)
  if len(g['occurrences'])>1:a.button(key='keep-'+o['id']).click().run()
  else:a.button(key='keep-'+g['id']).click().run()
  book=a.session_state['run-review-decisions-'+before['run_id']]
  self.assertEqual(effective_choice(book,g,o),'keep_wording')
  for other in g['occurrences'][1:]:self.assertEqual(effective_choice(book,g,other),'request_changes')
  a.run();self.assertFalse(a.exception);self.assertEqual(run.snapshot(),before);self.assertEqual(run.capture(),calls)
  self.assertFalse(before['human_accepted']);self.assertFalse(before['package']['publishing_allowed'])
 def test_revision_includes_bound_human_choices_and_gets_fresh_review(self):
  a=self.app();run=a.session_state['offline_run'];before=run.snapshot();g=next(x for x in grouped_findings(before) if x['needs_attention'])
  a.button(key='changes-'+g['id']).click().run()
  finish_stack(a)
  a.text_area[0].input('Retain simulated brand voice.');next(b for b in a.button if b.label=='Create Version 2').click().run()
  self.assertFalse(a.exception);after=run.snapshot()
  self.assertEqual(after['revision_attempts'],1);self.assertEqual(after['review']['binding']['draft_version'],2)
  self.assertIn('Retain simulated brand voice.',after['revision_feedback']);self.assertIn('Human prefers keeping ',after['revision_feedback'])
  self.assertFalse(a.session_state['run-review-decisions-'+before['run_id']]['events'])
  self.assertFalse(after['human_accepted']);self.assertFalse(any(b.label=='Create Version 2' for b in a.button))
 def test_saved_review_navigation_is_explicit_and_never_restores_an_agent(self):
  run=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True);state=run.execute(run.snapshot()['run_id'])
  from launchlens.inventory import load_display
  from launchlens.offline_ui_run import fixture_inventory
  a=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
  with patch('launchlens.inventory_ui.fetch_inventory',return_value=fixture_inventory(load_display())),patch('launchlens.review_decisions.saved_review_available',return_value=True),patch('launchlens.review_decisions.load_saved_review',return_value=state) as load:
   a.selectbox(key='ui-mode').select('Live agent').run();self.assertEqual(load.call_count,0)
   a.button(key='current').click().run();self.assertEqual(load.call_count,1);self.assertFalse(a.exception)
   self.assertTrue(any('Review US package' in c.value for c in a.caption));self.assertNotIn('offline_run',a.session_state)
   self.assertFalse(any(b.label=='Create Version 2' for b in a.button))
   a.button(key='review-back').click().run();self.assertFalse(a.title)
if __name__=='__main__':unittest.main()
