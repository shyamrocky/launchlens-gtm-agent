"""Owner-scoped section citation inheritance and one citation-only retry; no APIs."""
from copy import deepcopy
import json,socket,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from launchlens.package_content import check_field_claims,PackageError,citation_only_failures,prepare_package_input,admit_package,load_package_prompt
from launchlens.offline_fixtures import package_cases,ReviewFixtureTools,request
from launchlens.live_package import LivePackageRun,StandingBudget,LiveGateError
from launchlens.writer_comparison import WireResponse
from launchlens.gtm_registry import HarnessError
from test_live_package import permission,NOW,Wire,KEYS,project,FrozenDateTime

class CitationRecoveryTests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('Offline only'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  for target,value in [('launchlens.live_package.datetime',FrozenDateTime),('launchlens.live_package.project_writer_input',project)]:
   p=patch(target,value);p.start();self.addCleanup(p.stop)
 def blog(self):
  d=deepcopy(package_cases()['initial_package']['blog']);d['content']['sections'][1]['heading']='Inspired by classic soda floats'
  d['claim_references']=[v for v in d['claim_references'] if v['content_field']!='sections.1.heading']
  return d
 def test_section_heading_uses_only_own_body_citations(self):
  d=self.blog();d['claim_references'].append({'content_field':'sections.1.body','claim_ids':['PROD-003']})
  check_field_claims(d,'blog')
  d['claim_references']=[v for v in d['claim_references'] if v['content_field']!='sections.1.body']
  with self.assertRaises(PackageError):check_field_claims(d,'blog')
  d['claim_references'].append({'content_field':'sections.0.body','claim_ids':['PROD-003']})
  with self.assertRaises(PackageError):check_field_claims(d,'blog')
 def test_other_fields_still_require_own_reference(self):
  for name,path in [('linkedin','hook'),('email','subject'),('blog','title')]:
   d=deepcopy(package_cases()['initial_package'][name]);d['content'][path]='Inspired by classic soda floats'
   d['claim_references']=[v for v in d['claim_references'] if v['content_field']!=path]
   with self.subTest(name=name),self.assertRaises(PackageError):check_field_claims(d,name)
 def factory(self,wire,*,twice=False,mixed=False,citation_error=None):
  def factory(model,validator):
   http=wire(model,validator)
   def wrapped(payload):
    response=http(payload)
    if payload['messages'][0]['content']==load_package_prompt('package_writer'):
     count=sum(v['messages'][0]['content']==load_package_prompt('package_writer') for v in wire.calls)
     if count==1 or twice:
      v=json.loads(response.body);d=json.loads(v['choices'][0]['message']['content'])
      if citation_error:
       ref=d['campaign_brief']['claim_references'][3]
       if citation_error=='invalid_field':ref['content_field']='restrictions_and_unknowns'
       else:ref['claim_ids']=['PROD-004']
      else:
       d['linkedin']['content']['hook']='Cherry Float combines cherry with vanilla notes.'
       d['linkedin']['claim_references']=[r for r in d['linkedin']['claim_references'] if r['content_field']!='hook']
       if mixed:d['email']['content']['body']='Buy now at https://example.com'
      v['choices'][0]['message']['content']=json.dumps(d);return WireResponse(200,json.dumps(v).encode(),{})
    return response
   return wrapped
  return factory
 def run_case(self,**kwargs):
  wire=Wire();r=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=self.factory(wire,**kwargs),now=NOW)
  s=r.execute(r.snapshot()['run_id']);return r,s,wire
 def test_every_live_content_role_uses_one_writer_input_builder(self):
  r,_,_=self.run_case()
  self.assertIs(r.writer._projector,r.reviewer._projector)
  self.assertIs(r.writer._projector,r.reviser._projector)
 def test_missing_only_classifier_checks_all_formats_without_modification(self):
  r,s,_=self.run_case();candidate=deepcopy(r.writer.calls[0]['candidate']);original=deepcopy(candidate)
  gaps=citation_only_failures(candidate,prepare_package_input(s));self.assertEqual(len(gaps),1);self.assertEqual(gaps[0]['field_path'],'content.hook');self.assertEqual(candidate,original)
  for mutate in [lambda d:d['email']['content'].update(body='See https://example.com'),lambda d:d['email']['content'].update(body=12),lambda d:d['linkedin']['content'].update(cta='Other CTA')]:
   bad=deepcopy(candidate);mutate(bad);self.assertEqual(citation_only_failures(bad,prepare_package_input(s)),[])
  bad=deepcopy(candidate);bad['email']['claim_references'].append({'content_field':'body','claim_ids':['PROD-999']})
  self.assertTrue(any(g['field_path'].startswith('claim_references.') for g in citation_only_failures(bad,prepare_package_input(s))))
 def test_saved_uk_citation_failure_shapes_are_retryable_but_not_admitted(self):
  r,s,_=self.run_case();inputs=prepare_package_input(s)
  self.assertEqual(inputs['draft_constraints']['allowed_claim_ids'],['PROD-002','PROD-003'])
  original=package_cases()['initial_package']
  for field,claim,path,rule in [
      ('restrictions_and_unknowns','PROD-003','claim_references.3.content_field','invalid_content_field_reference'),
      ('messaging_pillars.1','PROD-004','claim_references.3.claim_ids.0','invalid_claim_reference')]:
   candidate=deepcopy(original);candidate['campaign_brief']['claim_references'][3]={'content_field':field,'claim_ids':[claim]}
   gaps=citation_only_failures(candidate,inputs)
   self.assertEqual(gaps[0]['field_path'],path);self.assertEqual(gaps[0]['rule'],rule)
   with self.assertRaises(PackageError) as rejected:
    admit_package(candidate,inputs)
   self.assertEqual(rejected.exception.diagnostic['field_path'],path)
   self.assertEqual(candidate['campaign_brief']['claim_references'][3],{'content_field':field,'claim_ids':[claim]})
 def test_standing_run_retries_once_with_diagnostic_and_keeps_research(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'ledger.json';path.write_text(json.dumps({'ceiling_usd':'1.00','opening_accounted_usd':'0','claims':[]}));path.chmod(0o600)
   with patch('launchlens.live_package.BUILD_LEDGER',path):
    p=permission();p['standing_budget']=True;wire=Wire();r=LivePackageRun(p,KEYS,tools=ReviewFixtureTools(),wire_factory=self.factory(wire),now=NOW)
    s=r.execute(r.snapshot()['run_id'])
    self.assertEqual(s['status'],'awaiting_human_review');self.assertEqual(s['retry_attempts'],1);self.assertEqual(r.guard.counts['package_writer'],2);self.assertEqual(r.guard.counts['controller'],4)
    self.assertEqual(s['searches'],1);self.assertEqual(len(s['failure_history']),1);self.assertEqual(r.writer.calls[1]['model_input']['previous_validation_diagnostic_data_only'],s['draft_failure'])
    self.assertEqual(r.writer.calls[1]['model_input']['eligible_claim_ids_for_retry_data_only'],['PROD-002','PROD-003'])
    n=len(wire.calls);r.execute(s['run_id']);self.assertEqual(len(wire.calls),n)
 def test_standing_retry_handles_both_saved_uk_citation_error_shapes(self):
  for kind,rule in [('invalid_field','invalid_content_field_reference'),('invalid_id','invalid_claim_reference')]:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/'ledger.json';path.write_text(json.dumps({'ceiling_usd':'1.00','opening_accounted_usd':'0','claims':[]}));path.chmod(0o600)
    with patch('launchlens.live_package.BUILD_LEDGER',path):
     p=permission();p['standing_budget']=True;wire=Wire()
     r=LivePackageRun(p,KEYS,tools=ReviewFixtureTools(),wire_factory=self.factory(wire,citation_error=kind),now=NOW)
     s=r.execute(r.snapshot()['run_id'])
     self.assertEqual(s['status'],'awaiting_human_review')
     self.assertEqual(s['retry_attempts'],1)
     self.assertEqual(r.guard.counts['package_writer'],2)
     self.assertEqual(s['failure_history'][0]['rule'],rule)
     second=r.writer.calls[1]['model_input']
     self.assertEqual(second['previous_validation_diagnostic_data_only']['rule'],rule)
     self.assertEqual(second['eligible_claim_ids_for_retry_data_only'],['PROD-002','PROD-003'])
 def test_second_citation_failure_never_causes_third_writer(self):
  r,s,wire=self.run_case(twice=True);after=r.retry_writer(s['run_id'])
  self.assertFalse(r.session.can_retry_writer());self.assertEqual(after['writing_attempts'],2);self.assertFalse(after['drafts']);self.assertEqual(after['retry_attempts'],1)
  with self.assertRaises(HarnessError):r.retry_writer(s['run_id'])
 def test_mixed_failure_never_retryable(self):
  r,s,wire=self.run_case(mixed=True);self.assertEqual(s['status'],'failed');self.assertFalse(r.session.can_retry_writer());self.assertTrue(r.guard.closed)
 def test_saved_revalidation_requires_bound_known_accounting_and_reviews_without_writer(self):
  r,s,wire=self.run_case();capture=r.capture();p=permission();p['bound_run_id']=s['run_id']
  # Simulates owner correcting a field-coverage rule after a captured rejection.
  candidate=r.writer.calls[0]['candidate'];candidate['linkedin']['claim_references'].append({'content_field':'hook','claim_ids':['PROD-002']})
  # Fixture capture now represents a candidate valid under the corrected rule.
  capture=r.capture();s['status']='failed'
  restored=LivePackageRun(p,KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW,checkpoint=(s,capture),stopped_display=True)
  calls=len(wire.calls);sources=deepcopy(restored.tools.calls);after=restored.recover_writer_candidate(s['run_id'])
  self.assertEqual(after['status'],'awaiting_human_review');self.assertEqual(len(wire.calls),calls+1);self.assertEqual(restored.guard.counts['package_writer'],1);self.assertEqual(restored.guard.counts['controller'],4)
  self.assertEqual(restored.tools.calls,sources);self.assertEqual(after['failure_history'],s['failure_history']);self.assertFalse(after['human_accepted'])
  with self.assertRaises(HarnessError):restored.recover_writer_candidate(s['run_id'])
 def test_unknown_usage_and_unbound_recovery_do_not_reopen(self):
  r,s,_=self.run_case();r.guard.stop();before=r.capture()
  with self.assertRaises(LiveGateError):r.guard.reopen_for_saved_writer(s)
  self.assertTrue(r.guard.closed);self.assertEqual(r.capture(),before)
  r.guard.permission['bound_run_id']=s['run_id'];r.guard.events[-1]['status']='attempted'
  with self.assertRaises(LiveGateError):r.guard.reopen_for_saved_writer(s)
  self.assertTrue(r.guard.closed)
