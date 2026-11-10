"""Explicit repeat revisions, exact-version permission and atomic spending; no APIs."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import json,socket,sys,tempfile,unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from launchlens.offline_ui_run import OfflineUIRun
from launchlens.offline_fixtures import request,ReviewFixtureTools
from launchlens.voice_policy import BRAND_POLICY_ID
from launchlens.gtm_registry import HarnessError,eligible_actions
from launchlens.package_content import package_value,authoritative_package_binding
from launchlens.package_presentation import restored_decisions,approve_internal,approval_issues,version_content
from launchlens.review_decisions import decision_book,grouped_findings,record_decision
from launchlens.live_package import RunBudget,StandingBudget,LiveGateError,LivePackageRun,profile
from launchlens.writer_comparison import ProtectedStore
from test_live_package import permission,NOW,Wire,KEYS,project,FrozenDateTime
class HumanRevisionTests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
 def offline(self):
  run=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True);return run,run.execute(run.snapshot()['run_id'])
 def test_repeated_human_cycles_preserve_history_and_always_return_for_review(self):
  r,s=self.offline();first=deepcopy(s);controller_calls=len(r.controller.calls)
  for version in (2,3,4):
   prior=deepcopy(s);s=r.revise(s['run_id'],'Human-requested wording change',version-1,s['package']['package_sha256'])
   self.assertEqual(s['package']['version'],version);self.assertEqual(s['review']['binding']['draft_version'],version)
   self.assertEqual(s['status'],'awaiting_human_review');self.assertEqual(len(r.controller.calls),controller_calls)
   self.assertEqual(s['draft_history'][:len(prior['draft_history'])],prior['draft_history'])
   self.assertEqual(version_content(s,1),package_value(first));self.assertNotIn('revise_package',eligible_actions(s))
   count=len(r.reviser.calls);r.execute(s['run_id']);self.assertEqual(len(r.reviser.calls),count)
  self.assertEqual(s['revision_attempts'],3);self.assertEqual(len(s['reviews']),4)
  calls=deepcopy(r.capture())
  with self.assertRaises(HarnessError):r.revise(s['run_id'],'Fourth revision must not run',4,s['package']['package_sha256'])
  self.assertEqual(r.capture(),calls);self.assertEqual(r.snapshot(),s)
 def test_stale_or_duplicate_commands_never_dispatch_an_extra_writer(self):
  r,s=self.offline();v2=r.revise(s['run_id'],'Fix wording',1,s['package']['package_sha256']);before=r.capture()
  with self.assertRaises(HarnessError):r.session.request_revision(s['run_id'],'Stale',draft_version=1,draft_sha256=s['package']['package_sha256'])
  r.session.request_revision(s['run_id'],'Next',draft_version=2,draft_sha256=v2['package']['package_sha256'])
  with self.assertRaises(HarnessError):r.session.request_revision(s['run_id'],'Duplicate',draft_version=2,draft_sha256=v2['package']['package_sha256'])
  self.assertEqual(r.capture(),before);v3=r.execute(s['run_id']);self.assertEqual(v3['package']['version'],3)
  r.execute(s['run_id']);self.assertEqual(len(r.reviser.calls),2)
 def test_human_keeps_can_approve_despite_reviewer_recommendations(self):
  r,s=self.offline();s=r.revise(s['run_id'],'Requested correction',1,s['package']['package_sha256']);book=decision_book(s)
  g=next(g for g in grouped_findings(s) if g['needs_attention'])
  change=record_decision(s,book,g['id'],'request_changes');self.assertTrue(approval_issues(s,change))
  for g in grouped_findings(s):
   if g['needs_attention']:book=record_decision(s,book,g['id'],'keep_wording')
  result=approve_internal(s,book,True);self.assertTrue(result['internal_approved']);self.assertFalse(result['publishing_allowed'])
  self.assertFalse(s['human_accepted'])
 def test_saved_choices_replay_only_for_matching_current_review(self):
  r,s=self.offline();book=decision_book(s)
  with tempfile.TemporaryDirectory() as tmp:
   store=ProtectedStore(Path(tmp)/'receipts')
   for i,g in enumerate(grouped_findings(s)):
    if g['needs_attention']:
     book=record_decision(s,book,g['id'],'request_changes');store.write('human-decision-'+str(i)+'.json',book)
   self.assertEqual(restored_decisions(s,store),book)
   s=r.revise(s['run_id'],'Next',1,s['package']['package_sha256']);self.assertIsNone(restored_decisions(s,store))
 def test_two_budget_guards_cannot_overreserve_a_complete_revision_cycle(self):
  with tempfile.TemporaryDirectory() as tmp,patch('launchlens.live_package.datetime',FrozenDateTime):
   path=Path(tmp)/'ledger.json';path.write_text(json.dumps({'ceiling_usd':'1.00','opening_accounted_usd':'0.80','claims':[],'accounted_usd':'0.80','remaining_usd':'0.20'}));path.chmod(0o600)
   guards=[RunBudget(permission(),now=NOW) for _ in range(2)]
   for b in guards:b.arm(request());b.standing=StandingBudget(path)
   def reserve(b):
    try:b.reserve_revision({'run_id':str(id(b)),'draft_version':2,'draft_sha256':'a'*64});return True
    except LiveGateError:return False
   with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(reserve,guards))
   self.assertEqual(sum(results),1);value=json.loads(path.read_text());self.assertEqual(len(value['claims']),2)
   b=guards[results.index(True)];claims=deepcopy(b.pending_revision_claims)
   for role in ('package_revision','package_reviewer'):
    e=b.claim(role,'b'*64);self.assertEqual(e['standing_claim_id'],claims[role]['id'])
    b.complete(e,{'model':profile()['roles'][role]['model_id'],'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}})
   self.assertFalse(b.pending_revision_claims);self.assertEqual(len(json.loads(path.read_text())['claims']),2)
 def test_same_bound_version_cannot_reserve_two_paid_revision_cycles(self):
  with tempfile.TemporaryDirectory() as tmp,patch('launchlens.live_package.datetime',FrozenDateTime):
   path=Path(tmp)/'ledger.json';path.write_text(json.dumps({'ceiling_usd':'1.00','opening_accounted_usd':'0','claims':[],'accounted_usd':'0','remaining_usd':'1.00'}));path.chmod(0o600)
   guards=[RunBudget(permission(),now=NOW) for _ in range(2)]
   for b in guards:b.arm(request());b.standing=StandingBudget(path)
   guards[0].reserve_revision({'draft_version':2,'draft_sha256':'c'*64})
   with self.assertRaises(LiveGateError):guards[1].reserve_revision({'draft_version':2,'draft_sha256':'c'*64})
   self.assertEqual(len(json.loads(path.read_text())['claims']),2)
 def test_same_run_pointer_advances_atomically_with_both_receipts(self):
  import hashlib
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);store=ProtectedStore(root/'data/generated/run');private=root/'data/private';private.mkdir()
   old={'run_id':'00000000-0000-0000-0000-000000000049','request':request(),'status':'awaiting_human_review'};store.write('state-09.json',old);store.write('capture-09.json',{})
   pointer=private/'current-live-run.json';spec={'state':{'path':'data/generated/run/state-09.json','sha256':'old'},'capture':{'path':'data/generated/run/capture-09.json','sha256':'old'},'store':'data/generated/run','authorization':{'path':'data/private/approval.json','sha256':'preserve'}}
   pointer.write_text(json.dumps(spec));pointer.chmod(0o600)
   store.write('state-100.json',old);store.write('capture-100.json',{'new':True})
   run=object.__new__(LivePackageRun);run.store=store
   with patch('launchlens.live_package.ROOT',root),patch('launchlens.run_archive.ROOT',root):run._advance_current_pointer(old,store.path/'state-100.json',store.path/'capture-100.json')
   updated=json.loads(pointer.read_text());self.assertEqual(updated['authorization'],spec['authorization'])
   self.assertTrue(updated['state']['path'].endswith('100.json'));self.assertEqual(updated['capture']['sha256'],hashlib.sha256((store.path/'capture-100.json').read_bytes()).hexdigest())
   self.assertEqual(pointer.stat().st_mode & 0o777,0o600)
 def test_no_budget_or_missing_permission_blocks_before_generation(self):
  with patch('launchlens.live_package.datetime',FrozenDateTime):
   b=RunBudget(permission(),now=NOW);b.arm(request());b.cost=Decimal('0.99')
   self.assertFalse(b.can_revise())
   with self.assertRaises(LiveGateError):b.reserve_revision({'draft_version':2})
   self.assertFalse(b.events)
 def test_mock_live_v3_has_only_writer_and_required_reviewer_no_extra_controller(self):
  with patch('launchlens.live_package.datetime',FrozenDateTime),patch('launchlens.live_package.project_writer_input',side_effect=project):
   wire=Wire();r=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW)
   s=r.execute(r.snapshot()['run_id'])
   for v in (2,3):s=r.revise(s['run_id'],'Apply the human direction',v-1,s['package']['package_sha256'])
   self.assertEqual(len(wire.calls),10);self.assertEqual(r.guard.counts,{'controller':4,'package_writer':1,'package_reviewer':3,'package_revision':2})
   self.assertEqual(s['turns'],10);self.assertEqual(s['review']['binding']['draft_version'],3)
   self.assertEqual(sum(r.guard.counts.values()),len(r.guard.events));self.assertFalse(s['human_accepted'])
 def test_live_guard_rejects_fourth_revision_before_reservation_or_call(self):
  with patch('launchlens.live_package.datetime',FrozenDateTime),patch('launchlens.live_package.project_writer_input',side_effect=project):
   wire=Wire();r=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW)
   s=r.execute(r.snapshot()['run_id'])
   for v in (2,3,4):s=r.revise(s['run_id'],'Human wording request',v-1,s['package']['package_sha256'])
   self.assertEqual(r.guard.counts['package_revision'],3);self.assertFalse(r.guard.can_revise())
   before=deepcopy(r.capture());calls=len(wire.calls)
   with self.assertRaises(LiveGateError):r.guard.reserve_revision({'draft_version':4,'draft_sha256':s['package']['package_sha256']})
   with self.assertRaises(HarnessError):r.request_revision(s['run_id'],'Fourth attempt',draft_version=4,draft_sha256=s['package']['package_sha256'])
   self.assertEqual(r.capture(),before);self.assertEqual(len(wire.calls),calls);self.assertFalse(r.guard.pending_revision_claims)
 def test_final_human_edit_revalidates_rescans_and_never_calls_models(self):
  from launchlens.package_content import verify_human_edit_review,risky_phrase_scan,reviewer_hint
  from launchlens.review_decisions import carry_unchanged_decisions
  r,s=self.offline()
  with self.assertRaises(HarnessError):r.edit_current_fields(s['run_id'],[{'format':'blog','content_field':'title','text':'Explore Cherry Float'}],draft_version=1,draft_sha256=s['package']['package_sha256'])
  for v in (2,3,4):s=r.revise(s['run_id'],'Apply human feedback',v-1,s['package']['package_sha256'])
  book=decision_book(s)
  for g in grouped_findings(s):
   if g['needs_attention']:book=record_decision(s,book,g['id'],'keep_wording')
  before=deepcopy(s);calls=deepcopy(r.capture())
  edited=r.edit_current_fields(s['run_id'],[{'format':'blog','content_field':'title','text':'Stay informed about Cherry Float'}],draft_version=4,draft_sha256=s['package']['package_sha256'])
  self.assertEqual(edited['package']['version'],4);self.assertEqual(edited['revision_attempts'],3)
  self.assertEqual(r.capture(),calls);self.assertEqual(edited['turns'],s['turns']);self.assertEqual(edited['draft_history'],before['draft_history'])
  self.assertTrue(edited['review']['no_new_model_review']);verify_human_edit_review(edited)
  self.assertTrue(any(h['quote']=='Stay informed' and h['human_clearance_required'] for h in edited['review']['risk_scan']))
  moved=carry_unchanged_decisions(before,edited,book)
  self.assertTrue(approval_issues(edited,moved))
  for g in grouped_findings(edited):
   if g['needs_attention']:moved=record_decision(edited,moved,g['id'],'keep_wording')
  self.assertFalse(approval_issues(edited,moved));self.assertTrue(approve_internal(edited,moved,True)['internal_approved'])
  tampered=deepcopy(edited);tampered['review']['risk_scan']=[]
  with self.assertRaises(Exception):verify_human_edit_review(tampered)
  with self.assertRaises(HarnessError):r.edit_current_fields(s['run_id'],[{'format':'blog','content_field':'title','text':'Stale'}],draft_version=4,draft_sha256=s['package']['package_sha256'])
  current=r.snapshot()
  with self.assertRaises(Exception):r.edit_current_fields(s['run_id'],[{'format':'linkedin','content_field':'cta','text':'Buy now at an invented store'}],draft_version=4,draft_sha256=current['package']['package_sha256'])
  self.assertEqual(r.snapshot(),current);self.assertEqual(r.capture(),calls)
  self.assertIsNone(reviewer_hint({'quote':'stay tuned','suggested_change':'stay informed'})[0])
 def test_live_final_human_edit_persists_and_restores_without_inference(self):
  from launchlens.package_content import verify_human_edit_review
  with tempfile.TemporaryDirectory() as tmp,patch('launchlens.live_package.datetime',FrozenDateTime),patch('launchlens.live_package.project_writer_input',side_effect=project):
   store=ProtectedStore(Path(tmp)/'mock');wire=Wire();r=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW,store=store)
   s=r.execute(r.snapshot()['run_id'])
   for v in (2,3,4):s=r.revise(s['run_id'],'Human choice',v-1,s['package']['package_sha256'])
   count=len(wire.calls);cost=r.guard.cost
   s=r.edit_current_fields(s['run_id'],[{'format':'blog','content_field':'title','text':'Explore Cherry Float'}],draft_version=4,draft_sha256=s['package']['package_sha256'])
   capture=r.capture();restored=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW,checkpoint=(s,capture),store=store)
   verify_human_edit_review(restored.snapshot());self.assertEqual(restored.snapshot(),s)
   self.assertEqual(restored.guard.cost,cost);self.assertEqual(len(wire.calls),count)
 def test_failed_first_draft_can_be_restored_for_display_without_execution(self):
  from launchlens.writer_comparison import WireResponse
  from launchlens.package_content import load_package_prompt
  from launchlens.offline_fixtures import package_cases
  with patch('launchlens.live_package.datetime',FrozenDateTime),patch('launchlens.live_package.project_writer_input',side_effect=project):
   data=deepcopy(package_cases()['initial_package'])
   data['blog']['content']['sections'][1]['heading']='Inspired by classic soda floats'
   data['blog']['content']['sections'][1]['body']='See https://example.com'  # Independent policy failure, not the now-allowed heading inheritance.
   data['blog']['claim_references']=[x for x in data['blog']['claim_references'] if x['content_field']!='sections.1.heading']
   wire=Wire()
   def factory(model,validator):
    http=wire(model,validator)
    def wrapped(payload):
     response=http(payload)
     if payload['messages'][0]['content']==load_package_prompt('package_writer'):
      value=json.loads(response.body);value['choices'][0]['message']['content']=json.dumps(data)
      response=WireResponse(response.status,json.dumps(value).encode(),response.headers)
     return response
    return wrapped
   r=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=factory,now=NOW)
   s=r.execute(r.snapshot()['run_id']);self.assertEqual(s['status'],'failed')
   count=len(wire.calls);capture=r.capture();resumed=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW,checkpoint=(s,capture),stopped_display=True)
   self.assertTrue(resumed.guard.closed);self.assertEqual(resumed.execute(s['run_id']),s)
   self.assertEqual(len(wire.calls),count);self.assertFalse(resumed.guard.can_revise());self.assertFalse(resumed.session.can_retry_writer())
   with tempfile.TemporaryDirectory() as tmp:
    import hashlib
    from launchlens.live_package import load_current_live_run
    root=Path(tmp);saved=ProtectedStore(root/'data/generated/stopped');private=ProtectedStore(root/'data/private')
    saved.write('state-01.json',s);saved.write('capture-01.json',capture);private.write('approval.json',permission())
    spec={'store':'data/generated/stopped'}
    for name,path in [('state',saved.path/'state-01.json'),('capture',saved.path/'capture-01.json'),('authorization',private.path/'approval.json')]:
     spec[name]={'path':str(path.relative_to(root)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    private.write('current-live-run.json',spec)
    with patch('launchlens.live_package.ROOT',root),patch('launchlens.run_archive.ROOT',root),patch('launchlens.live_package.read_selected_keys',return_value=KEYS):loaded=load_current_live_run()
    self.assertEqual(loaded.snapshot(),s);self.assertTrue(loaded.guard.closed)
if __name__=='__main__':unittest.main()
