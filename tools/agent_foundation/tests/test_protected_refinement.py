"""D048 scan targets/full avoid list and current-V2 Reviewer-only command; no network."""
from copy import deepcopy
import json,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/agent_foundation/tests')]
from test_live_package import permission,KEYS,NOW,project,FrozenDateTime
from test_automatic_refinement import BlockingWire
from test_grouped_reviewer_protocol import CompactWire
from launchlens.live_package import LivePackageRun
from launchlens.offline_fixtures import ReviewFixtureTools
from launchlens.package_content import (prepare_call,protected_scan_hits,refinement_targets,refinement_avoid_list,
 risk_patterns,new_protected_hits,load_package_prompt,package_value)
class ProtectedRefinementTests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  for name,value in [('datetime',FrozenDateTime),('project_writer_input',project)]:
   p=patch('launchlens.live_package.'+name,value);p.start();self.addCleanup(p.stop)
 def make(self,enabled=True,wire=None):
  p=permission();p['allow_automatic_refinement']=enabled;w=wire or BlockingWire('advisory')
  r=LivePackageRun(p,KEYS,tools=ReviewFixtureTools(),wire_factory=w,now=NOW)
  return r,w,r.execute(r.snapshot()['run_id'])
 def test_protected_scan_hits_trigger_even_if_reviewer_only_advisory_or_cleared(self):
  r,w,s=self.make();self.assertEqual(s['package']['version'],2);self.assertEqual(s['revision_attempts'],1)
  v=w.revision_inputs[0];self.assertEqual(v['blocking_findings_to_fix'],[])
  self.assertTrue(v['protected_scan_hits_to_rewrite']);self.assertTrue(all(h['human_clearance_required'] for h in v['protected_scan_hits_to_rewrite']))
  self.assertFalse(s['human_accepted']);self.assertTrue(s['review']['human_clearance_required'])
  self.assertEqual(r.guard.counts['package_revision'],1)
 def test_full_avoid_list_matches_the_shared_policy_and_scan_exactly(self):
  r,w,s=self.make();v=w.revision_inputs[0];p=v['writer_brief']['tone_policy'];avoid=v['full_avoid_list']
  self.assertEqual(avoid['per_format'],{f:x['avoid'] for f,x in p['format_specs'].items()})
  self.assertEqual(avoid['all_formats_never'],p['all_formats']['never'])
  self.assertEqual(avoid['scan_patterns'],risk_patterns(scan_additions='tone_v2'))
  self.assertIn('Before returning your single final response',load_package_prompt('package_revision'))
  self.assertTrue(avoid['no_links']);self.assertLess(len(v['owner_feedback_data_only']),300)
 def test_post_scan_is_current_version_only_and_does_not_start_another_writer(self):
  r,w,s=self.make();payloads=[json.loads(p['messages'][1]['content']) for p in w.calls if p['messages'][0]['content']==load_package_prompt('package_reviewer')]
  self.assertNotIn('post_refinement_scan',payloads[0]);scan=payloads[-1]['post_refinement_scan']
  self.assertEqual(scan['current_version'],2);self.assertEqual(scan['protected_scan_hits'],protected_scan_hits(s))
  self.assertEqual(s['ledger']['harness-auto-refinement']['post_refinement_scan']['protected_scan_hits'],scan['protected_scan_hits'])
  self.assertNotIn('owner_feedback_data_only',payloads[-1]);self.assertNotIn('review',payloads[-1])
  before=len(w.calls);self.assertEqual(r.execute(s['run_id']),s);self.assertEqual(len(w.calls),before)
 def test_new_phrase_detection_ignores_offset_changes_but_counts_new_occurrences(self):
  from launchlens.package_content import risky_phrase_scan
  before=protected_scan_hits(self.make()[2])
  a=risky_phrase_scan({'linkedin':{'content':{'body':'Try it today.'}}},scan_additions='tone_v2')
  b=risky_phrase_scan({'linkedin':{'content':{'body':'Some words. Try it today. Stay tuned.'}}},scan_additions='tone_v2')
  self.assertEqual({h['quote'].casefold() for h in new_protected_hits(a,b)},{'stay tuned'})
  c=risky_phrase_scan({'linkedin':{'content':{'body':'Try it today. Try it today.'}}},scan_additions='tone_v2')
  self.assertEqual(len(new_protected_hits(a,c)),len(a))
 def test_explicit_current_v2_recheck_preserves_copy_counts_and_never_refines(self):
  r,w,s=self.make();copy=deepcopy(package_value(s));counts=deepcopy(r.guard.counts);before=len(w.calls)
  r.guard.permission['bound_run_id']=s['run_id']
  final=r.recheck_review(s['run_id'],owner_requested=True)
  self.assertEqual(package_value(final),copy);self.assertEqual(final['package']['version'],2)
  self.assertEqual(final['revision_attempts'],1);self.assertEqual(r.guard.counts['package_revision'],counts['package_revision'])
  self.assertEqual(r.guard.counts['package_writer'],counts['package_writer']);self.assertEqual(r.guard.counts['controller'],counts['controller'])
  self.assertEqual(len(w.calls),before+1);self.assertEqual(r.guard.counts['package_reviewer'],counts['package_reviewer']+1)
  self.assertEqual(final['events'][-1]['origin'],'owner_command')
  with self.assertRaises(Exception):r.recheck_review(s['run_id'],owner_requested=True)
  self.assertEqual(len(w.calls),before+1)
if __name__=='__main__':unittest.main()
