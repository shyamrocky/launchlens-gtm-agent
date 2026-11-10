"""Owner M2-D025 rules: normalize shape only; preserve policy and visible uncertainty."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import json,sys,tempfile,unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from launchlens.package_content import normalize_package,risky_phrase_scan,assess_package_review,package_schema,load_package_prompt
from launchlens.offline_fixtures import package_cases,fixture_package_review,request
from launchlens.live_package import StandingBudget,LiveGateError
from launchlens.offline_ui_run import OfflineUIRun
from launchlens.voice_policy import BRAND_POLICY_ID
from launchlens.content_review import ContentCall

class OutputHandlingTests(unittest.TestCase):
 def setUp(self):
  self.enterContext(patch('socket.socket.connect',side_effect=AssertionError('offline only')))
  self.package=package_cases()['initial_package']
  self.inputs={'draft_constraints':{'allowed_claim_ids':['PROD-002','PROD-003']}}
 def test_bounded_normalization_and_original_preservation(self):
  original=deepcopy(self.package)
  value=deepcopy(self.package)
  value['linkedin']['claim_references'].append({'content_field':'cta','claim_ids':[]})
  value['linkedin']['claim_references'][0]['content_field']='content.'+value['linkedin']['claim_references'][0]['content_field']
  value['linkedin']=json.dumps(value['linkedin']);value=json.dumps(value)
  fixed,log=normalize_package(value)
  self.assertEqual(fixed,original)
  self.assertEqual({x['rule'] for x in log},{'quoted_json_decoded','empty_citation_removed','content_prefix_removed'})
  self.assertEqual(normalize_package(fixed),(fixed,[]))
  self.assertEqual(self.package,original)
 def test_never_repairs_ineligible_evidence_or_rewrites_creative_text(self):
  value=deepcopy(self.package);value['linkedin']['claim_references'][0]['claim_ids']=['PROD-999']
  value['linkedin']['content']['hook']='{"creative":"text"}'
  fixed,log=normalize_package(value)
  self.assertEqual(fixed,value);self.assertFalse(log)
 def test_findings_only_nullable_quotes_and_code_owned_status(self):
  raw=fixture_package_review(package_cases()['revision_review'],self.package)
  raw['linkedin']['findings'].append({'dimension':'completeness','content_field':'$format','quote':None,
   'severity':'advisory','rationale':'SAFE format note','suggested_change':'Inspect structure','claim_ids':[],'scan_hit_ids':[]})
  raw['linkedin']['assessments']=[{'dimension':'grounding','status':'needs_changes'}]
  checked=assess_package_review(raw,self.package,self.inputs,{'version':1})
  self.assertTrue(checked['review_complete']);self.assertEqual(checked['review_status'],'human_clearance_required')
  self.assertTrue(all(x['status']=='pass' for x in checked['assessment']['linkedin']['assessments']))
  self.assertIn('model_statuses_ignored',[x['rule'] for x in checked['normalizations']])
  self.assertTrue(all(x['reviewer_disposition']==('human_clearance_required' if x['human_clearance_required'] else 'cleared') for x in checked['risk_scan']))
 def test_invalid_wording_quote_preserves_raw_and_review_incomplete(self):
  raw=fixture_package_review(package_cases()['revision_review'],self.package)
  raw['linkedin']['findings'].append({'dimension':'grounding','content_field':'body','quote':'not the draft',
   'severity':'blocking','rationale':'SAFE malformed','suggested_change':'Inspect','claim_ids':[],'scan_hit_ids':[]})
  checked=assess_package_review(raw,self.package,self.inputs,{})
  self.assertTrue(checked['review_complete']);self.assertEqual(checked['unverified_finding_count'],1);self.assertEqual(checked['raw_response'],raw)
  self.assertNotEqual(checked['format_reviews']['linkedin']['review_status'],'review_incomplete')
 def test_invalid_evidence_reference_remains_fatal(self):
  raw=fixture_package_review(package_cases()['revision_review'],self.package)
  raw['linkedin']['findings'][0]['claim_ids']=['PROD-999']
  checked=assess_package_review(raw,self.package,self.inputs,{});self.assertEqual(checked['unverified_finding_count'],1);self.assertFalse(any('PROD-999' in f['claim_ids'] for f in checked['assessment']['linkedin']['findings']))
 def test_scan_covers_all_requested_categories_and_stays_visible(self):
  self.package['email']['content']['body']='Try it today. Introducing a new flavor, an innovative unique twist, sure to become a new favorite with real ice cream and bold intensity.'
  hits=risky_phrase_scan(self.package)
  self.assertEqual({x['category'] for x in hits if x['format']=='email'},
   {'availability_urgency','novelty','preference_prediction','differentiation','ingredient_intensity','invented_product_facts'})
  raw=fixture_package_review(package_cases()['revision_review'],self.package)
  checked=assess_package_review(raw,self.package,self.inputs,{})
  self.assertEqual(len(checked['risk_scan']),len(hits))
  self.assertTrue(all(x['reviewer_disposition']==('human_clearance_required' if x['human_clearance_required'] else 'cleared') for x in checked['risk_scan']))
 def test_malformed_reviewer_does_not_stop_package_or_reuse_old_review(self):
  run=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True)
  run.reviewer._transport=lambda p:{'model':p['model'],'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'broken JSON'}}]}
  state=run.execute(run.snapshot()['run_id'])
  self.assertEqual(state['status'],'awaiting_human_review');self.assertEqual(len(state['drafts']),5)
  self.assertFalse(state['review']['review_complete'])
  self.assertEqual(state['review']['raw_response'],'broken JSON')
  self.assertFalse(state['human_accepted']);self.assertFalse(state['package']['publishing_allowed'])
  reviewer_input=run.reviewer.calls[0]['model_input']
  self.assertNotIn('editorial_warnings',reviewer_input);self.assertIn('phrase_groups',reviewer_input);self.assertNotIn('risk_scan',reviewer_input)
 def test_persistent_concurrent_budget_never_refunds_unknown_charge(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'budget.json';path.write_text(json.dumps({'ceiling_usd':'1.00','opening_accounted_usd':'0.0437376','claims':[]}));path.chmod(0o600)
   guard=StandingBudget(path)
   def claim(i):
    try:return guard.claim('writer','0.2',str(i))
    except LiveGateError:return None
   with ThreadPoolExecutor(max_workers=8) as pool:ids=list(pool.map(claim,range(8)))
   self.assertEqual(sum(x is not None for x in ids),4)
   self.assertEqual(guard.read()['accounted_usd'],'0.8437376')
   identity=next(x for x in ids if x)
   guard.complete(identity,Decimal('0.01'),{'prompt_tokens':1,'completion_tokens':1})
   self.assertEqual(StandingBudget(path).read()['accounted_usd'],'0.6537376')
   self.assertEqual(sum(x['status']=='reserved_unknown_until_usage' for x in guard.read()['claims']),3)


class ActionPurposeNormalizationTests(unittest.TestCase):
 def test_only_display_reason_is_shortened_and_action_remains_validated(self):
  from launchlens.live_research import ResearchModel
  from launchlens.gtm_registry import validate_action
  from launchlens.offline_ui_run import OfflineUIRun
  run=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True)
  state=run.execute(run.snapshot()['run_id']);state['mode']='live_package'
  state['allowed_actions']=[];state['remaining_limits']={'model_turns':5,'product_searches':3}
  reason='A safe public business-purpose explanation. '*20
  response={'model':'Qwen/Qwen3-30B-A3B-Instruct-2507','choices':[{'finish_reason':'tool_calls','message':{'role':'assistant',
   'tool_calls':[{'id':'safe-test-action','type':'function','function':{'name':'read_pmm_brief','arguments':json.dumps({'why':reason})}}]}}]}
  model=ResearchModel(lambda payload:response,mode='live_package')
  action=model(state)
  self.assertEqual(action['name'],'read_pmm_brief');self.assertEqual(action['arguments'],{})
  self.assertLessEqual(len(action['why']),300);validate_action(action,'live_package')
  self.assertEqual(model.calls[0]['original_action_purpose'],reason)
  self.assertEqual(model.calls[0]['normalizations'][0]['rule'],'action_purpose_display_shortened')
  response['choices'][0]['message']['tool_calls'][0]['function']['name']='bypass_launch'
  with self.assertRaises(Exception):model(state)

 def test_missing_display_reason_uses_labeled_registry_purpose_without_changing_action(self):
  from launchlens.live_research import ResearchModel
  run=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True)
  state=run.execute(run.snapshot()['run_id']);state['mode']='live_package'
  state['remaining_limits']={'model_turns':5,'product_searches':3}
  response={'model':'Qwen/Qwen3-30B-A3B-Instruct-2507','choices':[{'finish_reason':'tool_calls','message':{'role':'assistant',
   'tool_calls':[{'id':'safe-missing-purpose','type':'function','function':{'name':'read_pmm_brief','arguments':'{}'}}]}}]}
  model=ResearchModel(lambda payload:response,mode='live_package');action=model(state)
  self.assertEqual(action['name'],'read_pmm_brief');self.assertEqual(action['arguments'],{})
  self.assertNotIn('Registry purpose',action['why']);self.assertTrue(action['why'].strip())
  self.assertEqual(model.calls[0]['normalizations'][0]['rule'],'missing_action_purpose_labeled_registry_fallback')
  response['choices'][0]['message']['tool_calls'][0]['function']['arguments']='{"approval":"fabricated"}'
  with self.assertRaises(Exception):model(state)
