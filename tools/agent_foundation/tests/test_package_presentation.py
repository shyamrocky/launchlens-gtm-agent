"""D032 UI-only decision, comparison and approval/export integrity; no network."""
from pathlib import Path
from copy import deepcopy
import sys,socket,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from launchlens.offline_ui_run import OfflineUIRun
from launchlens.offline_fixtures import request
from launchlens.voice_policy import BRAND_POLICY_ID
from launchlens.review_decisions import decision_book,grouped_findings,record_decision,safe_hints,revision_feedback
from launchlens.package_presentation import *
class PresentationTests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No provider calls'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  self.run=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True)
  self.state=self.run.execute(self.run.snapshot()['run_id']);self.book=decision_book(self.state)
 def keep_all(self):
  for g in grouped_findings(self.state):
   if g['needs_attention']:self.book=record_decision(self.state,self.book,g['id'],'keep_wording')
 def test_selected_hint_is_feedback_only_and_unknown_hint_rejected(self):
  before=deepcopy(self.state);g=next(g for g in grouped_findings(self.state) if g['needs_attention'] and safe_hints(g));hint=safe_hints(g)[0]
  chosen=record_decision(self.state,self.book,g['id'],'request_changes',suggestion=hint)
  self.assertIn(hint,revision_feedback(self.state,chosen));self.assertEqual(self.state,before)
  with self.assertRaises(ValueError):record_decision(self.state,self.book,g['id'],'request_changes',suggestion='Buy now for 20% off')
 def test_must_decide_gate_and_explicit_keep_are_distinct_from_approval(self):
  self.assertGreater(progress(grouped_findings(self.state),self.book)['must_left'],0)
  with self.assertRaises(ValueError):approve_internal(self.state,self.book,True)
  self.keep_all();self.assertFalse(approval_issues(self.state,self.book))
  self.assertFalse(self.state['human_accepted']);self.assertFalse(self.state['package']['publishing_allowed'])
 def test_internal_approval_bound_to_version_and_choices_never_publishes(self):
  self.keep_all();record=approve_internal(self.state,self.book,True)
  self.assertTrue(approval_matches(self.state,self.book,record));self.assertFalse(record['publishing_allowed'])
  with self.assertRaises(ValueError):approve_internal(self.state,self.book,False)
  changed=deepcopy(self.book);changed['events'].append({'test':'changed'})
  self.assertFalse(approval_matches(self.state,changed,record))
  bad=deepcopy(self.state);bad['drafts']['linkedin']['draft']['content']['body']='Changed without validation'
  self.assertFalse(approval_matches(bad,decision_book(bad),record))
 def test_source_tampering_and_requested_changes_block_approval(self):
  self.keep_all();g=next(g for g in grouped_findings(self.state) if g['needs_attention'])
  changed=record_decision(self.state,self.book,g['id'],'request_changes')
  with self.assertRaises(ValueError):approve_internal(self.state,changed,True)
  bad=deepcopy(self.state);bad['evidence'][0]['records'][0]['evidence_payload']['primary_text']='Changed'
  self.assertTrue(any('binding' in i for i in approval_issues(bad,self.book)))
 def test_markdown_includes_every_format_simulation_and_pending_label(self):
  text=markdown_package(self.state)
  self.assertIn(SIMULATION_LABEL,text);self.assertIn('Human approval pending',text)
  for f in FORMATS:self.assertIn('## '+LABELS[f],text)
  self.assertIn('PROD-002',text);self.assertNotIn('NEBIUS_API_KEY',text)
 def test_changes_computed_from_actual_versions_and_diff_escaped(self):
  self.assertFalse(changed_fields(self.state,'linkedin'))
  v2=self.run.revise(self.state['run_id'],'Fixture feedback',1,self.state['package']['package_sha256'])
  self.assertTrue(changed_fields(v2,'linkedin'));self.assertEqual(version_content(v2,1),version_content(self.state,1))
  html=word_diff('<script>old</script>','new & safe');self.assertNotIn('<script>',html);self.assertIn('<del>',html);self.assertIn('<ins>',html)
 def test_drawer_keeps_full_current_text_escaped_and_exact_phrase_anchor(self):
  from launchlens.package_presentation import draft_modal_document,draft_markup
  g=next(g for g in grouped_findings(self.state) if g['occurrences'][0]['quote']);focus=g['occurrences'][0]
  page=draft_modal_document(self.state,focus['format'],focus=focus)
  self.assertEqual(page.count('id="selected-phrase"'),1);self.assertIn('window.scrollTo',page);self.assertNotIn('scrollIntoView',page)
  from html import escape
  for _,text in text_fields(self.state['drafts'][focus['format']]['draft']['content']):
   plain=draft_markup(self.state,focus['format'])
   import re
   self.assertIn(escape(text),re.sub(r'<mark[^>]*>|</mark>','',plain))
  bad=deepcopy(focus);bad['quote']='Not in current draft'
  self.assertNotIn('id="selected-phrase"',draft_modal_document(self.state,focus['format'],focus=bad))
  bad=deepcopy(self.state);bad['drafts'][focus['format']]['draft']['content'][focus['content_field']]='<script>alert(1)</script>'
  self.assertNotIn('<script>alert(1)</script>',draft_markup(bad,focus['format']))
 def test_stale_review_never_supplies_old_version_cards_or_draft_marks(self):
  from launchlens.package_presentation import current_review_matches,card_reason
  self.assertTrue(current_review_matches(self.state));stale=deepcopy(self.state);stale['package']['version']=2
  self.assertFalse(current_review_matches(stale))
  g=next(g for g in grouped_findings(self.state) if g['occurrences'][0]['findings'])
  for o in g['occurrences']:
   for f in o['findings']:f['rationale']='Authored safe fixture disposition: mock judgment'
  self.assertNotIn('fixture',card_reason(g));self.assertNotIn('mock',card_reason(g,demo=True))
 def test_advisory_notes_even_requested_changes_never_block_approval(self):
  group={'id':'advisory','needs_attention':True,'occurrences':[{'id':'advice','needs_attention':True,'human_clearance_required':False,'severity':'advisory'}]}
  with patch('launchlens.package_presentation.grouped_findings',return_value=[group]):
   self.assertEqual(progress([group],self.book)['must_left'],0)
   self.assertEqual(approval_issues(self.state,self.book),[])
   self.book['groups']['advisory']='request_changes'
   self.assertEqual(approval_issues(self.state,self.book),[])
   self.assertTrue(approve_internal(self.state,self.book,True)['internal_approved'])
 def test_mixed_group_requires_only_mandatory_occurrences(self):
  group={'id':'mixed','needs_attention':True,'occurrences':[
   {'id':'must','needs_attention':True,'human_clearance_required':True,'severity':'advisory'},
   {'id':'optional','needs_attention':True,'human_clearance_required':False,'severity':'advisory'}]}
  with patch('launchlens.package_presentation.grouped_findings',return_value=[group]):
   self.assertEqual(progress([group],self.book)['must_left'],1)
   self.book['overrides']['must']='keep_wording'
   self.assertEqual(progress([group],self.book)['must_left'],0)
   self.assertFalse(approval_issues(self.state,self.book))
   self.book['overrides']['optional']='request_changes'
   self.assertFalse(approval_issues(self.state,self.book))
   self.book['overrides']['must']='request_changes'
   self.assertTrue(any('must-decide changes' in i for i in approval_issues(self.state,self.book)))
if __name__=='__main__':unittest.main()
