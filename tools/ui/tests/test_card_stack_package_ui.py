"""D032 card navigation, human handoff and export controls, zero live calls."""
from copy import deepcopy
from pathlib import Path
import os,socket,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from streamlit.testing.v1 import AppTest
from ui_review_helpers import finish_stack,show_card
from launchlens.review_decisions import grouped_findings,safe_hints
class CardStackTests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  p=patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'offline'});p.start();self.addCleanup(p.stop)
 def app(self):
  a=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
  a.button(key='open-US').click().run();a.button(key='prepare-start').click().run();self.assertFalse(a.exception);return a
 def test_one_card_choice_advances_and_drafts_stay_visible_without_calls(self):
  a=self.app();run=a.session_state['offline_run'];before=run.snapshot();calls=deepcopy(run.capture())
  self.assertEqual(len([b for b in a.button if (b.key or '').startswith('changes-phrase-')]),1)
  next(b for b in a.button if (b.key or '').startswith('keep-phrase-')).click().run()
  self.assertEqual(a.session_state['run-review-position-'+before['run_id']],1)
  a.button(key='review-previous').click().run();self.assertEqual(a.session_state['run-review-position-'+before['run_id']],0)
  self.assertNotIn('Drafts with highlights',[s.value for s in a.subheader]);self.assertEqual(run.capture(),calls);self.assertEqual(run.snapshot(),before)
 def test_summary_locks_until_must_decide_and_recap_reopens_card(self):
  a=self.app();a.button(key='review-summary').click().run();self.assertTrue(a.button(key='create-next-version').disabled)
  a.button(key='review-back-cards').click().run();finish_stack(a);self.assertFalse(a.button(key='create-next-version').disabled)
  next(b for b in a.button if (b.key or '').startswith('recap-')).click().run()
  self.assertTrue(any((b.key or '').startswith('changes-phrase-') for b in a.button))
 def test_suggestion_selection_is_saved_not_applied_to_draft(self):
  a=self.app();run=a.session_state['offline_run'];s=run.snapshot();g=next(g for g in grouped_findings(s) if g['needs_attention'] and safe_hints(g))
  show_card(a,g);a.button(key='use-'+g['id']).click().run()
  book=a.session_state['run-review-decisions-'+s['run_id']]
  self.assertEqual(book['replacements'][g['id']],safe_hints(g)[0]);self.assertEqual(run.snapshot(),s)
 def test_package_view_changes_compare_export_and_bound_approval(self):
  a=self.app();run=a.session_state['offline_run'];s=run.snapshot();finish_stack(a)
  before=run.capture()
  self.assertTrue(a.button(key='approve-package').disabled)
  next(c for c in a.checkbox if (c.key or '').startswith('run-approval-as-is-')).check().run();self.assertFalse(a.button(key='approve-package').disabled)
  a.button(key='approve-package').click().run();self.assertTrue(any('Package approved for internal use' in x.proto.body for x in a.get('html')))
  self.assertFalse(run.snapshot()['human_accepted']);self.assertEqual(run.capture(),before)
  self.assertTrue(any('Download Markdown'==d.label for d in a.get('download_button')))
  a.button(key='package-view-linkedin').click().run();self.assertIn('LinkedIn post · Version 1',[h.value for h in a.subheader])
  self.assertFalse(any((x.key or '').startswith('run-compare-') for x in a.toggle));self.assertNotIn('Versions',[h.value for h in a.subheader])
 def test_v2_shows_only_current_version_and_retains_activity_and_internal_history(self):
  a=self.app();run=a.session_state['offline_run'];s=run.snapshot()
  run.revise(s['run_id'],'Authored preview feedback.',1,s['package']['package_sha256']);a.run();self.assertFalse(a.exception)
  self.assertFalse(any((x.key or '').startswith('run-compare-') for x in a.toggle));self.assertNotIn('Versions',[h.value for h in a.subheader])
  html=' '.join(x.proto.body for x in a.get('html'))
  for title in ['You reviewed and asked for changes','Wrote Version 2','Reviewer checked Version 2']:self.assertIn(title,html)
  self.assertNotIn('version-row',html);self.assertEqual(len(run.snapshot()['draft_history']),2);self.assertIn('Deliverables · Version 2',[h.value for h in a.subheader])
 def test_four_fixture_previews_render_truthfully_without_source_access(self):
  for case,tab in [('activity','Activity'),('review','Review'),('summary','Review'),('package','Package')]:
   a=AppTest.from_file(str(ROOT/'tools/preview_run_states.py'),default_timeout=20);a.query_params['case']=case;a.run();self.assertFalse(a.exception)
   s=a.session_state['offline_run'].snapshot();self.assertEqual(a.session_state['run-tabs-'+s['run_id']],tab)
   self.assertEqual(s['mode'],'offline_package');self.assertFalse(s['human_accepted'])
 def test_three_revision_cap_disables_next_creation_without_losing_current_approval(self):
  a=self.app();run=a.session_state['offline_run'];s=run.snapshot()
  for v in (2,3,4):s=run.revise(s['run_id'],'Explicit human feedback',v-1,s['package']['package_sha256'])
  a.run();finish_stack(a)
  self.assertTrue(a.button(key='create-next-version').disabled)
  self.assertEqual(a.button(key='create-next-version').label,'Revision limit reached')
  self.assertFalse(any('Version 5' in x.label for x in a.text_area))
  self.assertTrue(any('All 3 revisions' in x.value for x in a.info))
  next(c for c in a.checkbox if (c.key or '').startswith('run-approval-as-is-')).check().run()
  self.assertFalse(a.button(key='approve-package').disabled)
  self.assertEqual(run.snapshot()['package']['version'],4);self.assertEqual(len(run.snapshot()['draft_history']),4)
 def test_final_cards_offer_inline_edit_and_keep_no_rewrite_actions(self):
  a=self.app();run=a.session_state['offline_run'];s=run.snapshot()
  for v in (2,3,4):s=run.revise(s['run_id'],'Apply choices',v-1,s['package']['package_sha256'])
  a.run();before=deepcopy(run.capture());g=next(g for g in grouped_findings(s) if g['needs_attention'])
  show_card(a,g)
  self.assertFalse(any(b.label=='Let the Writer rephrase' or (b.key or '').startswith('use-') for b in a.button))
  a.button(key='manual-edit-'+g['id']).click().run();self.assertFalse(a.exception)
  text=next(x for x in a.text_area if (x.key or '').startswith('human-edit-text-'))
  text.input(text.value+' Explore the flavor story.').run()
  a.button(key='save-'+g['id']).click().run();self.assertFalse(a.exception)
  after=run.snapshot();self.assertTrue(after['review']['no_new_model_review']);self.assertEqual(after['package']['version'],4)
  self.assertNotEqual(after['package']['package_sha256'],s['package']['package_sha256']);self.assertEqual(run.capture(),before)
  self.assertTrue(any('Human edits saved' in c.value for c in a.caption))
if __name__=='__main__':unittest.main()
