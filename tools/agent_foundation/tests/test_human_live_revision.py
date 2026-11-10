"""D028: offline evidence for exact-field instructions and owner-controlled live revision."""
from copy import deepcopy
import json,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/agent_foundation/tests')]
from test_live_package import Wire,permission,KEYS,NOW,project,FrozenDateTime
from launchlens.live_package import LivePackageRun,profile,create_live_run
from launchlens.offline_fixtures import ReviewFixtureTools,request
from launchlens.package_content import (load_package_prompt,prepare_call,authoritative_package_binding,
    PackageError,check_field_claims,package_value)
from launchlens.review_decisions import grouped_findings,decision_book,record_decision,revision_feedback
from launchlens.offline_ui_run import OfflineUIRun
from launchlens.voice_policy import BRAND_POLICY_ID
from launchlens.writer_comparison import WireResponse

class HumanLiveRevisionTests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No live network'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  p=patch('launchlens.live_package.datetime',FrozenDateTime);p.start();self.addCleanup(p.stop)
  p=patch('launchlens.live_package.project_writer_input',side_effect=project);p.start();self.addCleanup(p.stop)
 def run_case(self):
  w=Wire();r=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=w,now=NOW)
  return r,w,r.execute(r.snapshot()['run_id'])
 def test_explicit_writer_and_revision_field_instructions(self):
  for stage in ['package_writer','package_revision']:
   p=load_package_prompt(stage)
   for text in ['headlines, titles, subject lines and CTAs','concepts.0.headline','body citation does not cover','PROD-002','PROD-003']:
    self.assertIn(text,p)
 def test_original_missing_field_rejections_unchanged(self):
  for name,path,content in [('ads','concepts.0.headline',{'concepts':[{'headline':'Cherry Float Inspired by Classic Soda Floats','body':'Flavor'}]}),('blog','title',{'title':'Cherry Float Inspired by Classic Soda Floats','body':'Flavor'})]:
   value={'content':content,'claim_references':[{'content_field':'body','claim_ids':['PROD-002','PROD-003']}]}
   with self.assertRaises(PackageError) as e:check_field_claims(value,name)
   self.assertEqual(e.exception.diagnostic['field_path'],'content.'+path)
   value['claim_references'].append({'content_field':path,'claim_ids':['PROD-003']});check_field_claims(value,name)
 def test_all_decisions_overrides_notes_delivered_then_fresh_review(self):
  r,w,s=self.run_case();groups=grouped_findings(s);book=decision_book(s)
  for i,g in enumerate(groups):book=record_decision(s,book,g['id'],'request_changes' if i%2==0 else 'keep_wording')
  g=groups[0];o=g['occurrences'][0];book=record_decision(s,book,o['id'],'keep_wording',occurrence=True)
  feedback=revision_feedback(s,book,'Keep simulated brand voice and preserve every qualification. '*24)
  self.assertGreater(len(feedback),2000)
  self.assertIn('Change ',feedback);self.assertIn('Human prefers keeping ',feedback)
  for g in groups:
   for o in g['occurrences']:self.assertIn(o['format']+'.'+o['content_field'],feedback)
  initial_calls=len(w.calls);source_calls=deepcopy(r.tools.calls)
  r.request_revision(s['run_id'],feedback,draft_version=1,draft_sha256=s['package']['package_sha256'])
  self.assertEqual(len(w.calls),initial_calls)
  package_input=prepare_call(r.snapshot(),'package_revision',projector=project)
  self.assertEqual(package_input['owner_feedback_data_only'],feedback)
  final=r.execute(s['run_id']);self.assertEqual(final['package']['version'],2)
  self.assertEqual(final['status'],'awaiting_human_review');self.assertEqual(final['review']['binding']['draft_version'],2)
  self.assertEqual(len(final['reviews']),2);self.assertEqual(len(final['draft_history']),2)
  self.assertEqual(r.tools.calls,source_calls);self.assertEqual(r.guard.counts['package_revision'],1)
  self.assertEqual(r.guard.counts['package_reviewer'],2)
  revision=next(p for p in w.calls if p['messages'][0]['content']==load_package_prompt('package_revision'))
  self.assertEqual(json.loads(revision['messages'][1]['content'])['owner_feedback_data_only'],feedback)
  reviews=[json.loads(p['messages'][1]['content']) for p in w.calls if p['messages'][0]['content']==load_package_prompt('package_reviewer')]
  self.assertEqual(reviews[-1]['package'],package_value(final));self.assertNotIn('owner_feedback_data_only',reviews[-1]);self.assertNotIn('previous_review',reviews[-1])
  self.assertFalse(final['human_accepted']);self.assertFalse(final['package']['publishing_allowed'])
 def test_many_grouped_choices_not_silently_truncated(self):
  r,w,s=self.run_case();s['review']=None;s['drafts']['linkedin']['draft']['content']['body']='unique '*80
  g=next(x for x in grouped_findings(s) if x['phrase']=='unique');book=record_decision(s,decision_book(s),g['id'],'request_changes')
  text=revision_feedback(s,book,'Retain brand voice.')
  self.assertGreater(len(text),2000);self.assertLess(len(text),12000)
  for o in g['occurrences']:self.assertIn('['+str(o['start'])+':'+str(o['end'])+']',text)
 def test_first_review_never_automatically_revises_despite_blocking_finding(self):
  base=Wire()
  def factory(model,validator):
   http=base(model,validator)
   def call(payload):
    out=http(payload)
    if payload['messages'][0]['content']==load_package_prompt('package_reviewer'):
     value=json.loads(out.body);candidate=json.loads(value['choices'][0]['message']['content'])
     package=json.loads(payload['messages'][1]['content'])['package']
     candidate['linkedin']['findings'].append({'dimension':'grounding','content_field':'body',
       'quote':package['linkedin']['content']['body'],'severity':'blocking','rationale':'MOCK unsupported assertion requires owner inspection.',
       'suggested_change':'Remove unsupported wording.','claim_ids':['PROD-002'],'scan_hit_ids':[]})
     value['choices'][0]['message']['content']=json.dumps(candidate)
     return WireResponse(200,json.dumps(value).encode(),{})
    return out
   return call
  r=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=factory,now=NOW)
  r.guard.permission['standing_budget']=True # No StandingBudget instantiated; socket-free test only.
  s=r.execute(r.snapshot()['run_id'])
  self.assertTrue(any(f['severity']=='blocking' and f['dimension']=='grounding' for f in s['review']['format_reviews']['linkedin']['assessment']['findings']))
  self.assertEqual(s['status'],'awaiting_human_review');self.assertEqual(s['package']['version'],1)
  self.assertEqual(r.guard.counts['package_revision'],0);self.assertIsNone(s['revision_request'])
 def test_standing_permission_also_consumed_once_at_start(self):
  import tempfile
  from launchlens.gtm_registry import HarnessError
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'authorization.json';v=permission();v['standing_budget']=True
   p.write_text(json.dumps(v));p.chmod(0o600)
   ledger=root/'budget.json'
   ledger.write_text(json.dumps({'ceiling_usd':'1.00','opening_accounted_usd':'0','claims':[],'accounted_usd':'0','remaining_usd':'1.00'}));ledger.chmod(0o600)
   with patch('launchlens.live_package.ROOT',root),patch('launchlens.run_archive.ROOT',root),patch('launchlens.live_package.BUILD_LEDGER',ledger),patch('launchlens.live_package.read_selected_keys',return_value=KEYS):
    r=create_live_run(request(),authorization_path=p)
    self.assertFalse(r.guard.events)
    with self.assertRaises(HarnessError):create_live_run(request(),authorization_path=p)
if __name__=='__main__':unittest.main()
