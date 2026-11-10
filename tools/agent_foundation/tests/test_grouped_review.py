"""Owner D027: small semantic-screening and exact-version human decision boundary."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from launchlens.offline_ui_run import OfflineUIRun
from launchlens.offline_fixtures import request
from launchlens.voice_policy import BRAND_POLICY_ID
from launchlens.package_content import (risky_phrase_scan,reviewer_hint,check_field_claims,PackageError,
    FORMATS,prepare_package_input,admit_package,authoritative_package_binding,HISTORICAL_CONFIG_SHA256)
from launchlens.review_decisions import (grouped_findings,decision_book,record_decision,effective_choice,
    highlighted,unresolved_groups,revision_feedback)
class GroupedReviewTests(unittest.TestCase):
 def state(self):
  run=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True)
  return run.execute(run.snapshot()['run_id'])
 def test_expanded_phrases_and_protected_announcement_no_duplicate_tokens(self):
  text='We announce the launch. Our family. The latest flavor stands out; adults fondly remember it.'
  hits=risky_phrase_scan({'linkedin':{'content':{'body':text}}})
  phrases={h['quote'].lower() for h in hits}
  self.assertTrue({'announce the launch','family','latest','stands out','fondly remember'}<=phrases)
  self.assertNotIn('announce',phrases);self.assertNotIn('launch',phrases)
  self.assertTrue(next(h for h in hits if h['quote']=='announce the launch')['human_clearance_required'])
  self.assertEqual({h['quote'] for h in risky_phrase_scan({'linkedin':{'content':{'body':'announce. launch.'}}})},{'announce','launch'})
 def test_hints_reject_risky_repeated_and_instructions_without_editing_raw(self):
  for hint in ['unique','Replace unique with distinct','our latest creation','new','may recall','smooth','Try it today']:
   f={'quote':'unique','suggested_change':hint};before=deepcopy(f)
   self.assertIsNone(reviewer_hint(f)[0]);self.assertEqual(f,before)
  self.assertEqual(reviewer_hint({'quote':'unique','suggested_change':'cherry and vanilla notes'})[0],'cherry and vanilla notes')
 def test_six_unique_occurrences_are_one_decision(self):
  s=self.state();s['review']=None
  s['drafts']['linkedin']['draft']['content']['body']='unique unique unique unique unique unique'
  group=next(g for g in grouped_findings(s) if g['phrase']=='unique')
  self.assertEqual(len(group['occurrences']),6)
  self.assertEqual(len({o['id'] for o in group['occurrences']}),6)
 def test_group_choice_and_individual_override_never_mutate_authority(self):
  s=self.state();s['review']=None;s['drafts']['linkedin']['draft']['content']['body']='unique unique';original=deepcopy(s);groups=grouped_findings(s);g=next(g for g in groups if len(g['occurrences'])>1)
  book=decision_book(s);book=record_decision(s,book,g['id'],'request_changes')
  o=g['occurrences'][0];book=record_decision(s,book,o['id'],'keep_wording',occurrence=True)
  self.assertEqual(effective_choice(book,g,o),'keep_wording')
  self.assertEqual(effective_choice(book,g,g['occurrences'][1]),'request_changes')
  book=record_decision(s,book,g['id'],'keep_wording')
  self.assertEqual(effective_choice(book,g,o),'keep_wording')
  self.assertEqual(s,original);self.assertFalse(s['human_accepted']);self.assertFalse(s['package']['publishing_allowed'])
 def test_content_or_review_change_invalidates_choices(self):
  s=self.state();book=decision_book(s);g=grouped_findings(s)[0]
  book=record_decision(s,book,g['id'],'keep_wording')
  for mutation in ['draft','review']:
   new=deepcopy(s)
   if mutation=='draft':new['drafts']['linkedin']['draft']['content']['body']+=' Modified'
   else:new['review']['review_complete']=not new['review']['review_complete']
   self.assertFalse(decision_book(new,book)['events'])
   with self.assertRaises(ValueError):record_decision(new,book,g['id'],'keep_wording')
 def test_highlighting_escapes_html_and_preserves_all_text(self):
  from html.parser import HTMLParser
  class Text(HTMLParser):
   def __init__(self):super().__init__();self.parts=[]
   def handle_data(self,text):self.parts.append(text)
  text='<script>alert(1)</script> unique';o={'quote':'unique','start':25,'end':31}
  o.update(start=text.index('unique'),end=len(text))
  value=highlighted(text,[o,o]);self.assertNotIn('<script>',value);self.assertEqual(value.count('<mark>'),1)
  reader=Text();reader.feed(value);self.assertEqual(''.join(reader.parts),text)
 def test_feedback_preserves_scope_and_does_not_apply_hints(self):
  s=self.state();g=grouped_findings(s)[0];book=record_decision(s,decision_book(s),g['id'],'request_changes')
  result=revision_feedback(s,book,'Keep brand voice.')
  self.assertIn('evidence and launch restrictions remain enforced',result);self.assertIn('Keep brand voice.',result)
  self.assertFalse(s['human_accepted'])
 def test_original_field_citation_rule_still_rejects_while_union_is_complete(self):
  for name,path,content in [('ads','concepts.0.headline',{'concepts':[{'headline':'Cherry Float Inspired by Classic Soda Floats','body':'Flavor story'}]}),('blog','title',{'title':'Cherry Float Inspired by Classic Soda Floats','body':'Flavor story'})]:
   draft={'content':content,'claim_references':[{'content_field':'body','claim_ids':['PROD-002','PROD-003']}]}
   with self.assertRaises(PackageError) as error:check_field_claims(draft,name)
   self.assertEqual(error.exception.diagnostic['code'],'field_claim_coverage')
   self.assertEqual(error.exception.diagnostic['field_path'],'content.'+path)
 def test_preserved_predecessor_binding_revalidated_not_silently_migrated(self):
  s=self.state();inputs=prepare_package_input(s);inputs['package_contract']['sha256']=HISTORICAL_CONFIG_SHA256
  # Recreate the actual historical input, not new tone rules under an old hash.
  from launchlens.content_contracts import load_template
  from launchlens.package_content import package_schema
  inputs.pop('tone_policy')
  from launchlens.voice_policy import POLICY_SHA256
  inputs['voice_policy'].update(version=1,policy_sha256=POLICY_SHA256)
  inputs['output_schema']=package_schema()
  inputs['template']={'format':'package','templates':{f:load_template(f) for f in FORMATS}}
  from launchlens.package_content import package_value
  drafts,meta=admit_package(package_value(s),inputs)
  s['drafts']=drafts;s['package']=meta
  actual,_,binding=authoritative_package_binding(s)
  self.assertEqual(actual['package_contract']['sha256'],HISTORICAL_CONFIG_SHA256)
  self.assertEqual(binding['authoritative_input_sha256'],meta['input_sha256'])
  s['drafts']['linkedin']['draft']['content']['body']+=' changed'
  with self.assertRaises(Exception):authoritative_package_binding(s)
 def test_saved_review_pointer_rejects_changed_or_escaping_inputs_before_validation(self):
  import tempfile,json,hashlib,os
  from unittest.mock import patch
  from launchlens.review_decisions import load_saved_review
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'data/private').mkdir(parents=True);(root/'data/generated').mkdir()
   data=root/'data/generated/source.json';data.write_text('{}');data.chmod(0o600)
   pointer=root/'data/private/current-review.json'
   entry={'path':'data/generated/source.json','sha256':hashlib.sha256(data.read_bytes()).hexdigest()}
   spec={'source':entry,'review':entry};pointer.write_text(json.dumps(spec));pointer.chmod(0o600)
   with patch('launchlens.package_content.ROOT',root),patch('launchlens.package_content.authoritative_package_binding',side_effect=AssertionError('Must reject before authority checks')):
    data.write_text('{"changed":true}')
    with self.assertRaises(ValueError):load_saved_review()
    spec['source']={'path':'../../.env','sha256':'0'*64};pointer.write_text(json.dumps(spec))
    with self.assertRaises(ValueError):load_saved_review()
 def test_clean_checkout_does_not_require_private_saved_review(self):
  import tempfile
  from unittest.mock import patch
  from launchlens.review_decisions import saved_review_available,load_saved_review
  with tempfile.TemporaryDirectory() as folder,patch('launchlens.package_content.ROOT',Path(folder)):
   self.assertFalse(saved_review_available())
   with self.assertRaises(ValueError):load_saved_review()
if __name__=='__main__':unittest.main()
