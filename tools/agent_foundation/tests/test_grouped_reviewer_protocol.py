"""D029: compact judgments, exact expansion and same-run recovery; all network mocked."""
from copy import deepcopy
import json,socket,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/agent_foundation/tests')]
from test_live_package import Wire,permission,KEYS,NOW,project,FrozenDateTime
from launchlens.live_package import LivePackageRun,profile,RunBudget,load_current_live_run
from launchlens.offline_fixtures import ReviewFixtureTools,request
from launchlens.offline_ui_run import OfflineUIRun
from launchlens.voice_policy import BRAND_POLICY_ID
from launchlens.package_content import (prepare_call,prepare_package_input,package_value,
    assess_package_review,authoritative_package_binding,PackageError,load_package_prompt)
from launchlens.reviewer_groups import phrase_groups,group_schema,expand_judgments
from launchlens.writer_comparison import WireResponse,ProtectedStore

def judgments(groups):
 return {'group_judgments':[{'group_id':g['group_id'],'dimension':'grounding','severity':'cleared',
  'reason':'Fixture contextual judgment; no semantic quality is claimed.', 'suggestion':'No replacement',
  'claim_ids':[],'occurrence_judgments':[]} for g in groups],'additional_findings':[]}

class CompactWire(Wire):
 def __init__(self,truncate_first=True):super().__init__();self.reviews=0;self.truncate_first=truncate_first
 def __call__(self,model,validator):
  base=super().__call__(model,validator)
  def http(payload):
   response=base(payload)
   if payload['messages'][0]['content']==load_package_prompt('package_reviewer'):
    self.reviews+=1;inputs=json.loads(payload['messages'][1]['content']);v=json.loads(response.body)
    if self.truncate_first and self.reviews==1:
     v['choices'][0]['finish_reason']='length';text='{"unfinished":'
    else:text=json.dumps(judgments(inputs['phrase_groups']))
    v['choices'][0]['message']['content']=text
    return WireResponse(200,json.dumps(v).encode(),{})
   return response
  return http

class GroupedProtocolTests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  p=patch('launchlens.live_package.datetime',FrozenDateTime);p.start();self.addCleanup(p.stop)
  p=patch('launchlens.live_package.project_writer_input',side_effect=project);p.start();self.addCleanup(p.stop)
 def state(self):
  r=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True);return r.execute(r.snapshot()['run_id'])
 def checked(self,raw,state):
  inputs,_,binding=authoritative_package_binding(state)
  return assess_package_review(raw,package_value(state),inputs,binding)
 def test_input_deduplicates_phrase_context_and_schema_is_valid(self):
  import jsonschema
  s=self.state();p=prepare_call(s,'package_reviewer');groups=p['phrase_groups']
  self.assertNotIn('risk_scan',p);self.assertEqual(len({(g['phrase'],g['category']) for g in groups}),len(groups))
  self.assertTrue(all('context' not in l for g in groups for l in g['locations']))
  self.assertLessEqual(len(groups),sum(len(g['locations']) for g in groups))
  repeated=phrase_groups({'linkedin':{'content':{'body':'unique unique unique unique unique unique'}}})
  self.assertEqual(len(repeated),1);self.assertEqual(len(repeated[0]['locations']),6)
  jsonschema.Draft202012Validator.check_schema(p['output_schema'])
  jsonschema.validate(judgments(groups),p['output_schema'])
  self.assertEqual(profile()['roles']['package_reviewer']['max_completion_tokens'],16384)
 def test_one_judgment_expands_every_occurrence_and_protected_never_model_cleared(self):
  s=self.state();raw=judgments(phrase_groups(package_value(s)));r=self.checked(raw,s)
  self.assertTrue(r['review_complete']);self.assertEqual(r['raw_response'],raw)
  hits=r['risk_scan'];findings=[f for v in r['format_reviews'].values() for f in v['assessment']['findings']]
  self.assertTrue(all(any(h['hit_id'] in f['scan_hit_ids'] for f in findings) for h in hits))
  self.assertTrue(all(h['reviewer_disposition']=='human_clearance_required' for h in hits if h['human_clearance_required']))
  self.assertFalse(r['human_accepted']);self.assertFalse(r['publishing_allowed'])
 def test_explicit_meaning_difference_only_applies_to_that_location(self):
  package={'linkedin':{'content':{'body':'unique unique'}},'email':{'content':{'body':'unique'}}}
  groups=phrase_groups(package);raw=judgments(groups);g=groups[0]
  raw['group_judgments'][0]['occurrence_judgments']=[{'location_id':g['locations'][0]['location_id'],
   'meaning_differs':True,'dimension':'tone','severity':'advisory','reason':'This occurrence describes inspiration; other locations describe the product.',
   'suggestion':'flavor','claim_ids':[]}]
  expanded,errors=expand_judgments(raw,package);self.assertFalse(errors)
  rows=[f for v in expanded.values() for f in v['findings']]
  self.assertEqual(sum(f['severity']=='advisory' for f in rows),1);self.assertEqual(len(rows),3)
  raw['group_judgments'][0]['occurrence_judgments'][0]['meaning_differs']=False
  _,errors=expand_judgments(raw,package);self.assertIn('occurrence_meaning_difference_required',errors)
 def test_word_limits_duplicates_missing_groups_and_unknown_locations_stay_incomplete(self):
  s=self.state();raw=judgments(phrase_groups(package_value(s)))
  for change in ['reason','suggestion','duplicate','missing','location']:
   bad=deepcopy(raw)
   if change=='reason':bad['group_judgments'][0]['reason']='word '*26
   elif change=='suggestion':bad['group_judgments'][0]['suggestion']='word '*13
   elif change=='duplicate':bad['group_judgments'].append(deepcopy(bad['group_judgments'][0]))
   elif change=='missing':bad['group_judgments'].pop()
   else:bad['group_judgments'][0]['occurrence_judgments']=[{'location_id':'foreign','meaning_differs':True,'dimension':'tone','severity':'advisory','reason':'Different context.','suggestion':'No replacement','claim_ids':[]}]
   checked=self.checked(bad,s);self.assertTrue(checked['review_complete'],change);self.assertTrue(checked['unverified_finding_count'] or any(f['unassessed_scan_hit_ids'] for f in checked['format_reviews'].values()),change)
 def test_bad_evidence_id_rejected_and_quoted_json_preserved(self):
  s=self.state();raw=judgments(phrase_groups(package_value(s)))
  quoted=json.dumps(raw);checked=self.checked(quoted,s);self.assertTrue(checked['review_complete']);self.assertEqual(checked['raw_response'],quoted)
  raw['group_judgments'][0]['claim_ids']=['PROD-099']
  checked=self.checked(raw,s);self.assertGreater(checked['unverified_finding_count'],0);self.assertFalse(any('PROD-099' in f['claim_ids'] for v in checked['assessment'].values() for f in v['findings']))
 def test_additional_wording_requires_exact_quote_and_lengths_remain_computed(self):
  s=self.state();raw=judgments(phrase_groups(package_value(s)))
  extra={'format':'linkedin','content_field':'body','quote':'not in this draft','dimension':'grounding','severity':'blocking','reason':'Unsupported claim.','suggestion':'No replacement','claim_ids':[]}
  raw['additional_findings']=[extra];self.assertTrue(self.checked(raw,s)['review_complete']);self.assertGreater(self.checked(raw,s)['unverified_finding_count'],0)
  extra.update(content_field='$format',quote=None,reason='This post meets all length targets.')
  self.assertTrue(self.checked(raw,s)['review_complete']);self.assertGreater(self.checked(raw,s)['unverified_finding_count'],0)
 def test_recheck_same_package_no_writer_or_research_then_revision_keeps_12_call_limit(self):
  wire=CompactWire();run=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW)
  s=run.execute(run.snapshot()['run_id']);self.assertFalse(s['review']['review_complete']);self.assertEqual(s['turns'],6)
  source=deepcopy(s);capture=run.capture();sources=deepcopy(run.tools.calls);package=deepcopy(package_value(s))
  resumed=LivePackageRun(permission(),KEYS,tools=run.tools,wire_factory=wire,now=NOW,checkpoint=(s,capture))
  self.assertEqual(resumed.snapshot(),source);self.assertEqual(len(wire.calls),6)
  final=resumed.recheck_review(s['run_id']);self.assertTrue(final['review']['review_complete']);self.assertEqual(final['turns'],7)
  self.assertEqual(package_value(final),package);self.assertEqual(run.tools.calls,sources)
  self.assertEqual(resumed.guard.counts['package_writer'],1);self.assertEqual(final['revision_attempts'],0)
  self.assertEqual(len(final['reviews']),2);self.assertEqual(resumed.guard.counts['package_reviewer'],2)
  self.assertEqual(final['run_id'],source['run_id']);self.assertTrue(resumed.guard.can_revise())
  before=len(wire.calls)
  with self.assertRaises(Exception):resumed.recheck_review(s['run_id'])
  self.assertEqual(len(wire.calls),before)
  revised=resumed.revise(s['run_id'],'Keep brand voice, remove unsupported assertions.',1,final['package']['package_sha256'])
  self.assertEqual(revised['package']['version'],2);self.assertTrue(revised['review']['review_complete'])
  self.assertEqual(revised['turns'],9);self.assertEqual(sum(resumed.guard.counts.values()),9)
  self.assertEqual(resumed.guard.counts['package_reviewer'],3);self.assertFalse(revised['human_accepted'])
 def test_restored_budget_rejects_counter_billing_and_state_tampering(self):
  wire=CompactWire();r=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW)
  s=r.execute(r.snapshot()['run_id']);c=r.capture()
  for kind in ['count','billing','state']:
   state=deepcopy(s);capture=deepcopy(c)
   if kind=='count':capture['spending']['attempts']['controller']=0
   elif kind=='billing':capture['spending']['events'][0]['status']='unknown'
   else:state['drafts']['linkedin']['draft']['content']['body']+=' changed'
   before=len(wire.calls)
   with self.assertRaises(Exception):LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW,checkpoint=(state,capture))
   self.assertEqual(len(wire.calls),before)
 def test_protected_resume_revalidates_result_and_rejects_stale_or_tampered_receipts(self):
  import hashlib
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);private=root/'data/private';private.mkdir(parents=True)
   store=ProtectedStore(root/'data/generated/run');wire=CompactWire()
   run=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW,store=store)
   original=run.execute(run.snapshot()['run_id']);done=run.recheck_review(original['run_id'])
   self.assertTrue(done['review']['review_complete']);before=len(wire.calls)
   auth=private/'permission.json';auth.write_text(json.dumps(permission()));auth.chmod(0o600)
   statefile=sorted(store.path.glob('state-*.json'))[-1];capturefile=sorted(store.path.glob('capture-*.json'))[-1]
   entry=lambda p:{'path':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
   spec={'state':entry(statefile),'capture':entry(capturefile),'authorization':entry(auth),'store':'data/generated/run'}
   pointer=private/'current-live-run.json';pointer.write_text(json.dumps(spec));pointer.chmod(0o600)
   with patch('launchlens.live_package.ROOT',root),patch('launchlens.live_package.read_selected_keys',return_value=KEYS) as keys:
    restored=load_current_live_run();self.assertEqual(restored.snapshot(),done)
    self.assertEqual(restored.guard.counts,run.guard.counts);self.assertEqual(len(wire.calls),before)
    self.assertTrue(restored.guard.can_revise())
    newer=store.path/'state-99.json';newer.write_text('{}');newer.chmod(0o600)
    with self.assertRaises(Exception):load_current_live_run()
    self.assertEqual(keys.call_count,1);newer.unlink()
    statefile.write_text('{}')
    with self.assertRaises(Exception):load_current_live_run()
    self.assertEqual(keys.call_count,1)
if __name__=='__main__':unittest.main()
