"""M2-D026: deterministic quality boundary, not proof of live Reviewer quality."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from launchlens.offline_ui_run import OfflineUIRun
from launchlens.offline_fixtures import request,package_cases,fixture_package_review
from launchlens.voice_policy import BRAND_POLICY_ID
from launchlens.package_content import (FORMATS,HUMAN_CLEARANCE_CATEGORIES,risky_phrase_scan,
    assess_package_review,prepare_package_input,prepare_call,claims_length_compliance)
from launchlens.content_contracts import measured_lengths
from launchlens.live_package import profile

PHRASES=['is here','try it',"can't wait",'sure to','ready-to-drink','format','quench',
    'the difference','born from','lineup','available','now']
class ReviewerQualityTests(unittest.TestCase):
 def setUp(self):
  run=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True)
  self.state=run.execute(run.snapshot()['run_id'])
  self.inputs=prepare_package_input(self.state);self.package=deepcopy(package_cases()['revision_package'])
 def test_all_twelve_explicit_phrases_detected_with_exact_offsets(self):
  self.package['email']['content']['body']='. '.join(PHRASES)
  hits=[h for h in risky_phrase_scan(self.package) if h['format']=='email' and h['content_field']=='body']
  self.assertEqual({h['quote'].lower() for h in hits},set(PHRASES))
  for h in hits:self.assertEqual(h['context'][h['start']:h['end']],h['quote'])
 def test_high_risk_cannot_be_cleared_even_when_reviewer_approves(self):
  self.package['email']['content']['body']='The product is here now. Try it. It is sure to please in a ready-to-drink format.'
  raw=fixture_package_review(package_cases()['revision_review'],self.package)
  checked=assess_package_review(raw,self.package,self.inputs,{})
  protected=[h for h in checked['risk_scan'] if h['category'] in HUMAN_CLEARANCE_CATEGORIES]
  self.assertTrue(protected)
  self.assertTrue(all(h['reviewer_disposition']=='human_clearance_required' for h in protected))
  self.assertTrue(checked['human_clearance_required'])
  self.assertEqual(checked['raw_response'],raw)
  self.assertTrue(all(f['severity']!='cleared' for g in checked['format_reviews'].values() for f in g['assessment']['findings'] if f.get('human_clearance_required')))
 def test_omitted_or_malformed_reviewer_still_flags_every_protected_hit(self):
  self.package['email']['content']['body']='. '.join(PHRASES)
  for raw in [{},'broken JSON']:
   checked=assess_package_review(raw,self.package,self.inputs,{})
   expected={h['hit_id'] for h in checked['risk_scan'] if h['human_clearance_required']}
   flagged={i for g in checked['format_reviews'].values() for f in g['assessment']['findings'] if f.get('human_clearance_required') for i in f['scan_hit_ids']}
   self.assertEqual(expected,flagged);self.assertFalse(checked['review_complete'])
   self.assertFalse(checked['human_accepted']);self.assertFalse(checked['publishing_allowed'])
 def test_contradictory_length_praise_is_not_admitted_but_raw_is_preserved(self):
  self.package['linkedin']['content']['body']='Cherry and vanilla.'
  self.assertTrue(any(not x['meets_target'] for x in measured_lengths(self.package['linkedin']['content'],'linkedin')))
  raw=fixture_package_review(package_cases()['revision_review'],self.package)
  raw['linkedin']['findings'].append({'dimension':'completeness','content_field':'$format','quote':None,'severity':'advisory',
   'rationale':'The post meets advisory length targets.','suggested_change':'No changes needed.','claim_ids':[],'scan_hit_ids':[]})
  checked=assess_package_review(raw,self.package,self.inputs,{})
  self.assertIn('contradicts_computed_length',checked['format_reviews']['linkedin']['validation_issues'])
  self.assertFalse(any('meets advisory length' in f['rationale'] for f in checked['assessment']['linkedin']['findings']))
  self.assertEqual(raw,checked['raw_response'])
  self.assertFalse(claims_length_compliance('The post does not meet the length target.'))
 def test_reviewer_receives_computed_facts_not_editorial_warnings(self):
  payload=prepare_call(self.state,'package_reviewer')
  self.assertNotIn('editorial_warnings',payload)
  self.assertEqual(set(payload['computed_lengths']),set(FORMATS))
  for f in FORMATS:self.assertEqual(payload['computed_lengths'][f],measured_lengths(payload['package'][f]['content'],f))
 def test_role_model_is_different_writer_unchanged_and_reasoning_bounded(self):
  roles=profile()['roles'];self.assertEqual(roles['package_writer']['model_id'],'NousResearch/Hermes-4-405B')
  self.assertEqual(roles['package_reviewer']['model_id'],'Qwen/Qwen3-30B-A3B-Instruct-2507')
  self.assertNotIn('reasoning_effort',roles['package_reviewer'])
  self.assertEqual(roles['package_reviewer']['max_completion_tokens'],16384)
  self.assertNotEqual(roles['package_writer']['model_id'],roles['package_reviewer']['model_id'])
if __name__=='__main__':unittest.main()
