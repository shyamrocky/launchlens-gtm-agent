"""Phrase-only grouping and exact replacement previews; no live/private input."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import sys,unittest
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from launchlens.package_content import FORMATS,risky_phrase_scan,reviewer_hint,assess_package_review
from launchlens.review_decisions import grouped_findings,safe_hints,replacement_preview,_phrase_hint,decision_book,record_decision,revision_feedback

class PhraseSpanTests(unittest.TestCase):
 def state(self):
  content={f:{'body':'Creative text.'} for f in FORMATS}
  content['linkedin']={'hook':'Introducing a new way to enjoy cherry soda.','body':'An addition to the Coca-Cola family offers a unique flavor.'}
  content['email']={'subject':'Discover a new cherry-vanilla soda.','body':'Introducing Cherry Float.'}
  content['blog']={'body':'The inspiration guided the development of a unique flavor. A distinct option within the Coca-Cola lineup.'}
  s={'run_id':'test','package':{'version':1},'drafts':{f:{'draft':{'content':c}} for f,c in content.items()}}
  hits=risky_phrase_scan({f:{'content':c} for f,c in content.items()})
  # Historical scan excludes additions; full-sentence Reviewer quotes must not
  # swallow shorter key phrases or pretend to judge new scan matches.
  s['review']={'risk_scan':[h for h in hits if h['quote']!='guided the development'],'format_reviews':{f:{'assessment':{'findings':[]}} for f in FORMATS}}
  for f,p,q,hint in [('linkedin','body',content['linkedin']['body'],'Distinct flavor combination'),('email','subject',content['email']['subject'],'Cherry-vanilla soda')]:
   s['review']['format_reviews'][f]['assessment']['findings'].append({'dimension':'grounding','content_field':p,'quote':q,'severity':'advisory','rationale':"'New' or differentiation needs support.",'suggested_change':hint,'claim_ids':[],'scan_hit_ids':[]})
  return s
 def test_six_phrase_cards_with_exact_spans_and_complete_context(self):
  s=self.state();before=deepcopy(s);groups=grouped_findings(s)
  self.assertEqual({g['phrase'] for g in groups},{'family','lineup','unique','new','introducing','guided the development'})
  for g in groups:
   for o in g['occurrences']:self.assertEqual(o['context'][o['start']:o['end']],o['quote']);self.assertLessEqual(len(o['quote'].split()),4)
  self.assertEqual(s,before);self.assertEqual(len(next(g for g in groups if g['phrase']=='introducing')['occurrences']),2)
 def test_new_scan_match_is_protected_but_has_no_fabricated_review(self):
  g=next(g for g in grouped_findings(self.state()) if g['phrase']=='guided the development');o=g['occurrences'][0]
  self.assertTrue(g['human_clearance_required']);self.assertTrue(o['new_scan_match']);self.assertFalse(o['findings'])
 def test_new_terms_and_suggestion_screening(self):
  p={'linkedin':{'content':{'body':'Presenting this product. It guided the development and is designed to delight.'}}}
  hits=risky_phrase_scan(p);self.assertEqual({h['quote'].casefold() for h in hits},{'presenting','guided the development','designed to'})
  self.assertTrue(all(h['human_clearance_required'] for h in hits if h['category']=='invented_product_facts'))
  self.assertFalse(risky_phrase_scan(p,scan_additions=False))
  self.assertIsNone(reviewer_hint({'quote':'Introducing','suggested_change':'Presenting'})[0])
  self.assertEqual(reviewer_hint({'quote':'Introducing','suggested_change':'Presenting'},scan_additions=False)[0],'Presenting')
 def occurrence(self,text,quote):
  start=text.index(quote);return {'context':text,'quote':quote,'start':start,'end':start+len(quote)}
 def test_full_sentence_preview_preserves_everything_outside_span(self):
  o=self.occurrence('One thought. A unique flavor combination tells the story. Another thought.','unique');before=deepcopy(o)
  self.assertEqual(replacement_preview(o,'float-inspired'),'A float-inspired flavor combination tells the story.')
  self.assertEqual(o,before);self.assertIsNone(replacement_preview(o,'Distinct flavor combination'))
  self.assertIsNone(replacement_preview(dict(o,start=0),'float-inspired'))
 def test_large_reviewer_hint_cannot_replace_short_span(self):
  text='Coca-Cola offers a unique flavor combination.';o=self.occurrence(text,'unique')
  self.assertIsNone(_phrase_hint({'quote':text,'suggested_change':'Distinct flavor combination'},o))
  self.assertEqual(_phrase_hint({'quote':'unique flavor combination','suggested_change':'Distinct flavor combination'},o),'distinct')
 def test_repeated_or_risky_replacement_rejected(self):
  o=self.occurrence('A distinct option within the Coca-Cola lineup.','lineup')
  self.assertIsNone(replacement_preview(o,'distinct option'))
  o=self.occurrence('Introducing Cherry Float.','Introducing')
  self.assertIsNone(replacement_preview(o,'Presenting'));self.assertEqual(replacement_preview(o,'Meet'),'Meet Cherry Float.')
 def test_hint_must_fit_every_grouped_occurrence(self):
  g=next(g for g in grouped_findings(self.state()) if g['phrase']=='unique');before=deepcopy(g)
  for hint in safe_hints(g):self.assertTrue(all(replacement_preview(o,hint) for o in g['occurrences']))
  self.assertEqual(g,before)
 def test_feedback_requests_only_exact_phrase_span_not_entire_field(self):
  s=self.state();g=next(g for g in grouped_findings(s) if g['phrase']=='introducing');hint=safe_hints(g)[0]
  b=record_decision(s,decision_book(s),g['id'],'request_changes',suggestion=hint);feedback=revision_feedback(s,b)
  self.assertIn('Requested phrase replacement',feedback);self.assertIn('preserve the rest of the sentence',feedback)
 def test_legacy_assessment_remains_reproducible_and_new_scan_is_marked(self):
  package={f:{'content':{'body':'Presenting this idea, designed to inspire.'}} for f in FORMATS}
  raw={f:{'findings':[]} for f in FORMATS};inputs={'draft_constraints':{'allowed_claim_ids':['PROD-002','PROD-003']}}
  with patch('launchlens.content_contracts.measured_lengths',return_value=[]):
   old=assess_package_review(raw,package,inputs,{},scan_additions=False);self.assertNotIn('scan_additions',old);self.assertFalse(old['risk_scan'])
   self.assertEqual(old,assess_package_review(raw,package,inputs,{},scan_additions=False))
   new=assess_package_review(raw,package,inputs,{});self.assertTrue(new['scan_additions']);self.assertTrue(new['human_clearance_required'])
