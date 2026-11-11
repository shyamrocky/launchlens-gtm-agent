"""D047: bounded automatic refine, paired reservation and human-only protected keeps."""
from copy import deepcopy
import json,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/agent_foundation/tests')]
from test_live_package import permission,KEYS,NOW,project,FrozenDateTime
from test_grouped_reviewer_protocol import CompactWire,judgments
from launchlens.live_package import LivePackageRun,LiveGateError
from launchlens.offline_fixtures import ReviewFixtureTools
from launchlens.package_content import load_package_prompt,prepare_call,package_value,blocking_findings
from launchlens.writer_comparison import WireResponse
from launchlens.review_decisions import grouped_findings,decision_book

class BlockingWire(CompactWire):
 def __init__(self,severity='blocking',persistent=False,bad_revision=False):
  super().__init__(False);self.severity=severity;self.persistent=persistent;self.bad_revision=bad_revision;self.revision_inputs=[]
 def __call__(self,model,validator):
  base=super().__call__(model,validator)
  def call(payload):
   response=base(payload);stage=payload['messages'][0]['content']
   if stage not in {load_package_prompt('package_reviewer'),__import__('launchlens.field_revisions',fromlist=['prompt']).prompt()}:return response
   inputs=json.loads(payload['messages'][1]['content'])
   out=json.loads(response.body)
   if stage==load_package_prompt('package_reviewer'):
    candidate=judgments(inputs['phrase_groups'])
    if inputs['binding']['draft_version']==1 or self.persistent:
     candidate['additional_findings']=[{'format':'linkedin','content_field':'hook','quote':inputs['package']['linkedin']['content']['hook'],
       'dimension':'grounding','severity':self.severity,'reason':'Fixture factual wording requires correction.',
       'suggestion':'Use the supported flavor story.','claim_ids':['PROD-002']}]
    out['choices'][0]['message']['content']=json.dumps(candidate)
   elif stage==__import__('launchlens.field_revisions',fromlist=['prompt']).prompt():
    self.revision_inputs.append(deepcopy(inputs))
    if self.bad_revision:out['choices'][0]['message']['content']='{"campaign_brief":13}'
   return WireResponse(200,json.dumps(out).encode(),{})
  return call

class AutomaticRefinementTests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  p=patch('launchlens.live_package.datetime',FrozenDateTime);p.start();self.addCleanup(p.stop)
  p=patch('launchlens.live_package.project_writer_input',side_effect=project);p.start();self.addCleanup(p.stop)
 def run_case(self,wire=None,enabled=True):
  w=wire or BlockingWire();v=permission();v['allow_automatic_refinement']=enabled
  r=LivePackageRun(v,KEYS,tools=ReviewFixtureTools(),wire_factory=w,now=NOW)
  return r,w,r.execute(r.snapshot()['run_id'])
 def test_blocker_runs_once_before_human_and_fresh_review_keeps_protected_human_only(self):
  r,w,s=self.run_case()
  self.assertEqual(s['status'],'awaiting_human_review');self.assertEqual(s['package']['version'],2)
  self.assertEqual(r.guard.counts,{'controller':4,'package_writer':1,'package_reviewer':2,'package_revision':1})
  self.assertEqual(s['revision_attempts'],1);self.assertEqual(len(s['reviews']),2)
  self.assertEqual(r.guard.summary()['call_usage']['revision_calls'],1)
  self.assertNotIn('human_revision_calls',r.guard.summary()['call_usage'])
  self.assertEqual(s['review']['binding']['draft_version'],2)
  self.assertFalse(s['human_accepted']);self.assertFalse(s['package']['publishing_allowed'])
  self.assertTrue(any(g['human_clearance_required'] for g in grouped_findings(s)))
  self.assertFalse(decision_book(s)['groups'])
  rev=w.revision_inputs[0];self.assertEqual(rev['revision_origin'],'agent')
  requests=[t for field in rev['targeted_fields'].values() for t in field['requests']]
  self.assertTrue(requests);self.assertNotIn('review',rev);self.assertNotIn('package',rev)
  for finding in s['ledger']['harness-auto-refinement']['findings']:
   self.assertTrue(any(t['format']==finding['format'] and t['content_field']==finding['content_field'] and t['quote']==finding['quote'] for t in requests))
  latest=[json.loads(p['messages'][1]['content']) for p in w.calls if p['messages'][0]['content']==load_package_prompt('package_reviewer')][-1]
  self.assertEqual(latest['package'],package_value(s));self.assertNotIn('review',latest);self.assertNotIn('owner_feedback_data_only',latest)
  initial=len(w.calls);self.assertEqual(r.execute(s['run_id']),s);self.assertEqual(initial,len(w.calls))
  self.assertTrue(any(e.get('action')=='automatic_refinement' for e in s['events']))
 def test_advisory_without_protected_hits_or_no_authorization_never_revises(self):
  for wire,enabled in [(BlockingWire('advisory'),True),(BlockingWire(),False)]:
   with patch('launchlens.package_content.protected_scan_hits',return_value=[]):r,w,s=self.run_case(wire,enabled)
   self.assertEqual(s['package']['version'],1)
   self.assertEqual(r.guard.counts['package_revision'],0);self.assertIsNone(s['revision_request'])
 def test_persistent_blockers_hand_off_and_do_not_loop_after_human_revision(self):
  r,w,s=self.run_case(BlockingWire(persistent=True))
  self.assertTrue(blocking_findings(s['review']));self.assertEqual(s['revision_attempts'],1)
  s=r.revise(s['run_id'],'Preserve evidence and revise the requested wording.',2,s['package']['package_sha256'])
  self.assertEqual(s['package']['version'],3);self.assertEqual(s['revision_attempts'],2)
  self.assertEqual(r.guard.counts['package_revision'],2);self.assertEqual(s['status'],'awaiting_human_review')
  self.assertEqual(next(e for e in s['events'] if e.get('action')=='automatic_refinement')['fixed_count'],0)
  s=r.revise(s['run_id'],'Correct the requested wording within the evidence.',3,s['package']['package_sha256'])
  self.assertEqual(s['revision_attempts'],3)
  with self.assertRaises(Exception):r.revise(s['run_id'],'Another change.',4,s['package']['package_sha256'])
 def test_budget_denial_preserves_review_without_writer_or_reset(self):
  w=BlockingWire();v=permission();v['allow_automatic_refinement']=True
  r=LivePackageRun(v,KEYS,tools=ReviewFixtureTools(),wire_factory=w,now=NOW)
  with patch.object(r.guard,'reserve_automatic_revision',side_effect=LiveGateError('Budget unavailable')):
   s=r.execute(r.snapshot()['run_id'])
  self.assertEqual(s['package']['version'],1);self.assertEqual(s['status'],'awaiting_human_review')
  self.assertEqual(r.guard.counts['package_revision'],0);self.assertTrue(blocking_findings(s['review']))
  self.assertEqual(s['ledger']['harness-auto-refinement']['reason'],'budget_or_authorization_unavailable')
 def test_failed_revision_consumes_pass_and_keeps_original(self):
  r,w,s=self.run_case(BlockingWire(bad_revision=True))
  self.assertEqual(s['status'],'failed');self.assertEqual(s['package']['version'],1)
  self.assertEqual(s['revision_attempts'],1);self.assertEqual(r.guard.counts['package_revision'],1)
  self.assertEqual(s['ledger']['harness-auto-refinement']['status'],'failed')
 def test_paired_reservation_and_unknown_billing_do_not_bypass_budget(self):
  w=BlockingWire();v=permission();v['allow_automatic_refinement']=True
  r=LivePackageRun(v,KEYS,tools=ReviewFixtureTools(),wire_factory=w,now=NOW)
  with patch.object(r.guard,'reserve_revision',wraps=r.guard.reserve_revision) as reserve:
   s=r.execute(r.snapshot()['run_id'])
  self.assertEqual(reserve.call_count,1);self.assertEqual(r.guard.pending_revision_claims,{})
  self.assertTrue(all(e['status']=='usage_accounted' for e in r.guard.events))
  self.assertEqual(s['revision_attempts'],1)
  r.guard.closed=True
  with self.assertRaises(LiveGateError):r.guard.reserve_automatic_revision(s['review']['binding'])
 def test_deferred_pre_inference_handoff_can_resume_without_research_or_counter_reset(self):
  w=BlockingWire();v=permission();v['allow_automatic_refinement']=True
  r=LivePackageRun(v,KEYS,tools=ReviewFixtureTools(),wire_factory=w,now=NOW)
  # Reproduce the former overlong-direction pre-inference denial deterministically.
  with patch('launchlens.package_content.MAX_PACKAGE_FEEDBACK',1):s=r.execute(r.snapshot()['run_id'])
  self.assertEqual(s['revision_attempts'],0);self.assertEqual(s['package']['version'],1)
  before=deepcopy(r.guard.counts);sources=deepcopy(r.tools.calls)
  final=r.session.resume_deferred_refinement(s['run_id'])
  self.assertEqual(final['package']['version'],2);self.assertEqual(final['revision_attempts'],1)
  self.assertEqual(r.tools.calls,sources);self.assertEqual(r.guard.counts['controller'],before['controller'])
  self.assertEqual(r.guard.counts['package_writer'],before['package_writer'])
  self.assertTrue(any(e.get('prior_admission',{}).get('status')=='deferred' for e in final['events']))
  with self.assertRaises(Exception):r.session.resume_deferred_refinement(s['run_id'])
 def test_incomplete_reviewer_never_triggers_an_automatic_pass(self):
  r,w,s=self.run_case(CompactWire(True))
  self.assertFalse(s['review']['review_complete']);self.assertEqual(s['package']['version'],1)
  self.assertEqual(r.guard.counts['package_revision'],0)
 def test_model_cannot_spoof_the_harness_refinement_ledger(self):
  from launchlens.offline_ui_run import OfflineUIRun
  from launchlens.offline_fixtures import request,action
  from launchlens.voice_policy import BRAND_POLICY_ID
  for identity in ['harness-auto-refinement','harness-review-v1','agent-revision-v2','human-revision-v2']:
   r=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True)
   r.session._model=lambda state:action('read_pmm_brief',identity)
   state=r.snapshot();state['status']='running';checked=r.session._decide(state)
   self.assertIsNone(checked['pending']);self.assertEqual(checked['ledger'],{})
   self.assertEqual(checked['events'][-1]['outcome'],'rejected');self.assertEqual(r.tools.calls,[])
 def test_permission_tampering_rejected_and_agent_never_marks_keep(self):
  r,w,s=self.run_case(BlockingWire(persistent=True));before=deepcopy(s)
  self.assertFalse(any(e.get('action')=='human_feedback' for e in s['events']))
  s['revision_request']={'origin':'agent','binding':s['review']['binding'],'review_sha256':__import__('launchlens.linkedin_drafting',fromlist=['digest']).digest(s['review']),
   'feedback':'Keep all protected wording.','blocking_findings':blocking_findings(s['review'])}
  with self.assertRaises(Exception):prepare_call(s,'package_revision',projector=project)
  self.assertFalse(before['human_accepted'])

if __name__=='__main__':unittest.main()
