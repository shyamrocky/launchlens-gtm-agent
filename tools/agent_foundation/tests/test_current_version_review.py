"""D031: current-version boundary, individually isolated findings and review budget."""
from copy import deepcopy
import json,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/agent_foundation/tests')]
from test_live_package import permission,KEYS,NOW,project,FrozenDateTime
from test_grouped_reviewer_protocol import CompactWire,judgments
from launchlens.live_package import RunBudget,LiveGateError,LivePackageRun,profile
from launchlens.package_content import prepare_call,package_value,validate_package_review,authoritative_package_binding
from launchlens.reviewer_groups import phrase_groups
from launchlens.offline_fixtures import ReviewFixtureTools,request

class CurrentVersionReviewTests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  p=patch('launchlens.live_package.datetime',FrozenDateTime);p.start();self.addCleanup(p.stop)
  p=patch('launchlens.live_package.project_writer_input',side_effect=project);p.start();self.addCleanup(p.stop)
 def revised(self):
  w=CompactWire(False);r=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=w,now=NOW)
  s=r.execute(r.snapshot()['run_id']);s=r.revise(s['run_id'],'OLD_FEEDBACK_SENTINEL',1,s['package']['package_sha256'])
  return r,w,s
 def test_current_v2_has_no_prior_quotes_findings_or_feedback(self):
  r,w,s=self.revised();s['reviews'][0]['assessment']={'old':'V1_ONLY_SENTINEL'}
  p=prepare_call(s,'package_reviewer',projector=project)
  self.assertEqual(p['package'],package_value(s));self.assertEqual(p['phrase_groups'],prepare_call(s,'package_reviewer')['phrase_groups'])
  self.assertNotIn('previous_review',p);self.assertNotIn('owner_feedback_data_only',p)
  self.assertNotIn('V1_ONLY_SENTINEL',json.dumps(p));self.assertNotIn('OLD_FEEDBACK_SENTINEL',json.dumps(p))
  self.assertEqual(p['binding']['draft_version'],2)
 def test_bad_quote_drops_one_finding_keeps_current_valid_findings(self):
  r,w,s=self.revised();raw=judgments(prepare_call(s,'package_reviewer')['phrase_groups'])
  text=s['drafts']['linkedin']['draft']['content']['body']
  valid={'format':'linkedin','content_field':'body','quote':text,'dimension':'tone','severity':'advisory',
   'reason':'Inspect the current draft tone.','suggestion':'No replacement','claim_ids':[]}
  raw['additional_findings']=[valid,{**valid,'quote':'V1_ONLY_SENTINEL'}]
  checked=validate_package_review(raw,s)
  self.assertTrue(checked['review_complete']);self.assertEqual(checked['unverified_finding_count'],1)
  self.assertTrue(any(f['quote']==text for f in checked['assessment']['linkedin']['findings']))
  self.assertFalse(any(f['quote']=='V1_ONLY_SENTINEL' for v in checked['assessment'].values() for f in v['findings']))
  self.assertEqual(checked['raw_response'],raw);self.assertFalse(checked['human_accepted'])
 def test_invalid_occurrence_does_not_erase_valid_group_default(self):
  r,w,s=self.revised();raw=judgments(prepare_call(s,'package_reviewer')['phrase_groups']);g=raw['group_judgments'][0]
  hit=prepare_call(s,'package_reviewer')['phrase_groups'][0]['locations'][0]['location_id']
  g['occurrence_judgments']=[{'location_id':hit,'meaning_differs':False,**{k:g[k] for k in ['dimension','severity','reason','suggestion','claim_ids']}}]
  checked=validate_package_review(raw,s);self.assertEqual(checked['unverified_finding_count'],1)
  self.assertTrue(checked['review_complete']);self.assertTrue(any(hit in f['scan_hit_ids'] for v in checked['assessment'].values() for f in v['findings']))
 def test_unknown_reviewer_claim_never_enters_accepted_findings(self):
  r,w,s=self.revised();raw=judgments(prepare_call(s,'package_reviewer')['phrase_groups']);raw['group_judgments'][0]['claim_ids']=['PROD-999']
  checked=validate_package_review(raw,s);self.assertGreater(checked['unverified_finding_count'],0)
  self.assertFalse(any('PROD-999' in f['claim_ids'] for v in checked['assessment'].values() for f in v['findings']))
  bad=deepcopy(s);bad['evidence'][0]['records'][0]['evidence_payload']['primary_text']='Changed'
  with self.assertRaises(Exception):validate_package_review(raw,bad)
 def test_required_reviews_have_four_slots_separate_from_12_task_calls(self):
  b=RunBudget(permission(),now=NOW);b.arm(request())
  def call(role):
   e=b.claim(role,'0'*64);b.complete(e,{'model':profile()['roles'][role]['model_id'],
    'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}})
  for _ in range(12):call('controller')
  with self.assertRaises(LiveGateError):b.claim('controller','1'*64)
  for _ in range(4):call('package_reviewer')
  call('package_reviewer') # No arbitrary per-run review ceiling; spending still checked.
  self.assertEqual(b.summary()['call_usage'],{'research_task_calls':12,'human_revision_calls':0,'no_op_writer_calls':0,'required_review_calls':5})
  self.assertEqual(len(b.events),17);self.assertGreater(b.cost,0)
 def test_explicit_v2_recheck_calls_only_reviewer_and_cannot_repeat(self):
  r,w,s=self.revised()
  # Model output failure affects current review only; keep current drafts and history.
  bad=validate_package_review('not JSON',s);s['review']=bad;s['reviews'][-1]=deepcopy(bad)
  for f in s['drafts'].values():f['review_status']='review_incomplete'
  # Restore mock accounting with one extra previously paid Reviewer, matching real V2.
  e=r.guard.claim('package_reviewer','0'*64);r.guard.complete(e,{'model':r.reviewer._model,
   'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}})
  s['turns']+=1;s['review_attempts']+=1
  capture=r.capture();before=deepcopy(capture);drafts=package_value(s)
  resumed=LivePackageRun(permission(),KEYS,tools=r.tools,wire_factory=w,now=NOW,checkpoint=(s,capture))
  n=len(w.calls);done=resumed.recheck_review(s['run_id'])
  self.assertEqual(len(w.calls),n+1);self.assertEqual(package_value(done),drafts)
  self.assertEqual(done['run_id'],s['run_id']);self.assertEqual(done['review_attempts'],4)
  self.assertEqual(resumed.capture()['controller'],before['controller']);self.assertEqual(resumed.capture()['writer'],before['writer'])
  self.assertEqual(resumed.capture()['revision'],before['revision']);self.assertEqual(resumed.guard.events[:-1],before['spending']['events'])
  with self.assertRaises(Exception):resumed.recheck_review(s['run_id'])
  self.assertEqual(len(w.calls),n+1)
 def test_malformed_whole_review_still_explicitly_incomplete(self):
  r,w,s=self.revised();checked=validate_package_review('not JSON',s)
  self.assertFalse(checked['review_complete']);self.assertFalse(checked['human_accepted'])
  self.assertTrue(any(h['human_clearance_required'] for h in checked['risk_scan']))

if __name__=='__main__':unittest.main()
