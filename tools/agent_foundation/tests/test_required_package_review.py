"""D030: mandatory review, spent actions and exact saved-V2 recovery; no network."""
from copy import deepcopy
import json,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/agent_foundation/tests')]
from test_live_package import Wire,permission,KEYS,NOW,project,FrozenDateTime
from test_grouped_reviewer_protocol import CompactWire
from launchlens.live_package import LivePackageRun,RunBudget,LiveGateError
from launchlens.offline_fixtures import ReviewFixtureTools,request
from launchlens.package_content import package_value,risky_phrase_scan,authoritative_package_binding
from launchlens.gtm_registry import eligible_actions,HarnessError
from launchlens.review_decisions import grouped_findings,safe_hints

class RequiredReviewTests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  p=patch('launchlens.live_package.datetime',FrozenDateTime);p.start();self.addCleanup(p.stop)
  p=patch('launchlens.live_package.project_writer_input',side_effect=project);p.start();self.addCleanup(p.stop)
 def run_case(self):
  wire=CompactWire(False);r=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW)
  return r,wire,r.execute(r.snapshot()['run_id'])
 def legacy_stopped(self):
  wire=CompactWire();r=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW)
  first=r.execute(r.snapshot()['run_id']);first=r.recheck_review(first['run_id'])
  s=r.revise(first['run_id'],'Remove unsupported wording; retain brand voice.',1,first['package']['package_sha256'])
  capture=r.capture();s=deepcopy(s);s.update(status='failed',review={},review_attempts=2,pending=None,turns=12)
  s['reviews']=s['reviews'][:-1]
  s['ledger'].pop('harness-review-v2',None)
  for record in s['drafts'].values():record['review_status']='unreviewed'
  s['events']=s['events'][:-1]+[{'action':'revise_package','outcome':'duplicate_suppressed'}, {'action':'model_adapter','outcome':'failed_safely'}]
  capture['review']=capture['review'][:-1]
  budget=RunBudget(permission(),now=NOW);budget.arm(request())
  roles=['controller']*4+['package_writer','package_reviewer','package_reviewer','controller','package_revision','controller','controller']
  for role in roles:
   event=budget.claim(role,'0'*64)
   budget.complete(event,{'model':budget.plan['roles'][role]['model_id'],'usage':{'prompt_tokens':100,'completion_tokens':50,'total_tokens':150}})
  budget.stop();capture['spending']=budget.summary()
  return wire,s,capture
 def test_required_review_is_not_a_controller_choice_after_either_writer(self):
  r,w,s=self.run_case();self.assertEqual(len(r.controller.calls),4)
  self.assertEqual(s['events'][-1]['origin'],'harness_required')
  initial=len(w.calls);s=r.revise(s['run_id'],'Keep supported facts.',1,s['package']['package_sha256'])
  self.assertEqual(len(w.calls),initial+3) # controller -> revision -> required Reviewer
  self.assertEqual(len(r.controller.calls),5);self.assertEqual(s['review']['binding']['draft_version'],2)
  self.assertEqual(s['status'],'awaiting_human_review');self.assertEqual(s['events'][-1]['origin'],'harness_required')
  self.assertNotIn('revise_package',eligible_actions(s));self.assertNotIn('review_package',eligible_actions(s))
  self.assertNotIn('generate_package',eligible_actions(s));self.assertFalse(s['human_accepted'])
  for call in r.controller.calls:self.assertNotEqual(call.get('action',{}).get('name'),'review_package')
  for payload in w.calls:
   if 'tools' in payload:self.assertNotIn('review_package',[t['function']['name'] for t in payload['tools']])
 def test_recover_legacy_stopped_version_two_uses_only_last_reviewer_slot(self):
  wire,s,c=self.legacy_stopped();old=deepcopy(c['spending']);drafts=deepcopy(package_value(s));history=deepcopy(s['events'])
  r=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW,checkpoint=(s,c),review_recovery=True)
  self.assertTrue(r.can_review_saved());before=len(wire.calls);sources=deepcopy(r.tools.calls)
  result=r.review_saved(s['run_id'])
  self.assertEqual(len(wire.calls),before+1);self.assertEqual(package_value(result),drafts)
  self.assertEqual(r.tools.calls,sources);self.assertEqual(result['run_id'],s['run_id'])
  self.assertEqual(result['turns'],12);self.assertEqual(sum(r.guard.counts.values()),12)
  self.assertEqual(r.guard.counts,{'controller':7,'package_writer':1,'package_reviewer':3,'package_revision':1})
  self.assertEqual(r.guard.events[:11],old['events']);self.assertEqual(result['events'][:len(history)],history)
  self.assertEqual(result['status'],'awaiting_human_review');self.assertTrue(result['review']['review_complete'])
  self.assertEqual(result['review']['binding']['draft_version'],2);self.assertFalse(result['human_accepted'])
  self.assertTrue(any(n['rule']=='pre_http_attempt_separated_from_paid_calls' for n in result['normalizations']))
  self.assertFalse(r.can_review_saved())
  with self.assertRaises(HarnessError):r.review_saved(s['run_id'])
  self.assertEqual(len(wire.calls),before+1)
 def test_recovery_cannot_refund_unknown_billing_or_bypass_source_integrity(self):
  wire,s,c=self.legacy_stopped()
  for kind in ['unknown','count','source','version']:
   state,capture=deepcopy(s),deepcopy(c)
   if kind=='unknown':capture['spending']['events'][-1]['status']='unknown'
   elif kind=='count':capture['spending']['attempts']['controller']=6
   elif kind=='source':state['evidence'][0]['records'][0]['evidence_payload']['primary_text']='Altered'
   else:state['package']['version']=1
   with self.assertRaises(Exception):LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW,checkpoint=(state,capture),review_recovery=True)
 def test_incomplete_v2_review_can_reopen_without_inference_or_false_clearance(self):
  wire,old,capture=self.legacy_stopped()
  r=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW,checkpoint=(old,capture),review_recovery=True)
  # A malformed review is retained and is not an instruction to call another model.
  from launchlens.content_review import ContentCall
  stage=r.reviewer._transport
  def malformed(payload):
   response=stage(payload);response['choices'][0]['message']['content']='{"not_a_review":true}';return response
  r.reviewer=ContentCall(malformed,stage='package_reviewer',model_id=r.reviewer._model,projector=r.reviewer._projector)
  r.session._reviewer=r.reviewer
  result=r.review_saved(old['run_id']);self.assertFalse(result['review']['review_complete'])
  before=len(wire.calls);saved=r.capture()
  restored=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW,checkpoint=(result,saved))
  self.assertEqual(restored.snapshot(),result);self.assertEqual(len(wire.calls),before)
  self.assertFalse(restored.can_review_saved());self.assertFalse(restored.snapshot()['human_accepted'])
 def test_overlap_merges_categories_protection_and_keeps_raw_findings(self):
  r,w,s=self.run_case();before=deepcopy(s['review']);groups=grouped_findings(s)
  locations=[o for g in groups for o in g['occurrences'] if o['quote']]
  for i,a in enumerate(locations):
   for b in locations[i+1:]:
    if (a['format'],a['content_field'])==(b['format'],b['content_field']):self.assertFalse(a['start']<b['end'] and b['start']<a['end'])
  self.assertTrue(any(len(g['categories'])>1 for g in groups))
  for g in groups:
   if any(o['human_clearance_required'] for o in g['occurrences']):self.assertTrue(g['human_clearance_required'])
  self.assertEqual(s['review'],before)
 def test_new_scan_matches_and_every_advisory_alternative_is_bounded_and_screened(self):
  hits=risky_phrase_scan({'linkedin':{'content':{'body':'Stay tuned to learn where you can find it.'}}})
  self.assertEqual({h['quote'].lower() for h in hits},{'stay tuned','where you can find'})
  self.assertTrue(all(h['human_clearance_required'] for h in hits))
  r,w,s=self.run_case()
  for group in grouped_findings(s):
   hints=safe_hints(group);self.assertLessEqual(len(hints),2)
   for hint in hints:
    self.assertFalse(risky_phrase_scan({'linkedin':{'content':{'body':hint}}},suggestion=True))
    self.assertTrue(hint.strip())

if __name__=='__main__':unittest.main()
