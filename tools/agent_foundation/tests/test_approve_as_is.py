"""Explicit human acceptance supersedes edit intentions, never product/launch controls."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import json,os,socket,unittest
from unittest.mock import patch
from launchlens.offline_ui_run import OfflineUIRun
from launchlens.offline_fixtures import request
from launchlens.voice_policy import BRAND_POLICY_ID
from launchlens.review_decisions import decision_book,record_decision,grouped_findings,effective_choice
from launchlens.package_presentation import (current_wording_book,approve_current_version,
 approval_matches,approval_issues,restored_decisions,restored_approval)

class ApproveAsIsTests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('Offline only'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  self.run=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True)
  self.state=self.run.execute(self.run.snapshot()['run_id']);self.book=decision_book(self.state)
 def test_accepts_undecided_current_text_without_any_rewrite_or_model_call(self):
  before=deepcopy(self.state);calls=deepcopy(self.run.capture());original=deepcopy(self.book)
  accepted,receipt=approve_current_version(self.state,self.book,True)
  self.assertTrue(approval_matches(self.state,accepted,receipt));self.assertFalse(receipt['publishing_allowed'])
  self.assertEqual(receipt['wording_disposition'],'accepted_as_is');self.assertIn('approved_at',receipt)
  invalid=dict(receipt,publishing_allowed=True);self.assertFalse(approval_matches(self.state,accepted,invalid))
  self.assertEqual(self.state,before);self.assertEqual(self.book,original);self.assertEqual(self.run.capture(),calls)
 def test_supersedes_phrase_and_occurrence_rewrites_and_keeps_prior_history(self):
  g=next(g for g in grouped_findings(self.state) if g['needs_attention']);o=g['occurrences'][0]
  book=record_decision(self.state,self.book,g['id'],'request_changes')
  book=record_decision(self.state,book,o['id'],'request_changes',occurrence=True)
  accepted,receipt=approve_current_version(self.state,book,True)
  self.assertEqual(accepted['events'][:len(book['events'])],book['events'])
  self.assertEqual(effective_choice(accepted,g,o),'keep_wording');self.assertFalse(approval_issues(self.state,accepted))
  self.assertTrue(approval_matches(self.state,accepted,receipt));self.assertEqual(book['overrides'][o['id']],'request_changes')
  later=record_decision(self.state,accepted,g['id'],'request_changes')
  self.assertTrue(approval_matches(self.state,later,receipt))
 def test_requires_explicit_acknowledgment_and_current_review_identity(self):
  for ack in [False,None,1,'yes']:
   with self.subTest(ack=ack),self.assertRaises(ValueError):approve_current_version(self.state,self.book,ack)
  stale=deepcopy(self.book);stale['binding']={}
  with self.assertRaises(ValueError):current_wording_book(self.state,stale)
 def test_binding_launch_and_complete_review_controls_still_block_acceptance(self):
  def body(s):s['drafts']['linkedin']['draft']['content']['body']='Unvalidated changed content'
  def evidence(s):s['evidence'][0]['records'][0]['evidence_payload']['primary_text']='Tampered'
  def hold(s):s['launch']['decision']='Hold'
  def incomplete(s):s['review']['review_complete']=False
  def stale(s):s['review']['binding']['draft_sha256']='wrong'
  for mutate in [body,evidence,hold,incomplete,stale]:
   state=deepcopy(self.state);mutate(state)
   with self.subTest(mutate=mutate.__name__),self.assertRaises(ValueError):approve_current_version(state,decision_book(state),True)
 def test_every_current_version_is_approvable_and_next_version_does_not_inherit_approval(self):
  for version in range(1,5):
   if version>1:self.state=self.run.revise(self.state['run_id'],'Explicit later revision',version-1,self.state['package']['package_sha256'])
   book=decision_book(self.state);accepted,receipt=approve_current_version(self.state,book,True)
   self.assertEqual(receipt['version'],version);self.assertTrue(approval_matches(self.state,accepted,receipt))
   if version>1:self.assertFalse(approval_matches(self.state,accepted,previous))
   previous=receipt
 def test_receipts_restore_acceptance_without_rewriting_draft_and_reject_stale_or_public_files(self):
  accepted,receipt=approve_current_version(self.state,self.book,True)
  with TemporaryDirectory() as folder:
   store=SimpleNamespace(path=Path(folder))
   def save(name,value):
    p=store.path/name;p.write_text(json.dumps(value));p.chmod(0o600);return p
   save('human-decision-1.json',accepted);path=save('human-internal-approval-1.json',receipt)
   self.assertEqual(restored_decisions(self.state,store),accepted)
   self.assertEqual(restored_approval(self.state,accepted,store),receipt)
   self.assertEqual(restored_approval(self.state,self.book,store),receipt)
   stale=deepcopy(self.book);stale['binding']='other-review';self.assertIsNone(restored_approval(self.state,stale,store))
   path.chmod(0o644);self.assertIsNone(restored_approval(self.state,accepted,store))
   self.assertEqual(restored_approval(self.state,accepted,None),None)

if __name__=='__main__':unittest.main()
