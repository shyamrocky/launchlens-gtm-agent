"""Reference-only retry: synthetic failure shapes, never saved run data."""
from copy import deepcopy
from pathlib import Path
import json,socket,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/agent_foundation/tests')]
from test_live_package import Wire,permission,KEYS,NOW,FrozenDateTime,project
from launchlens.live_package import LivePackageRun,LiveTransport,RunBudget,LiveGateError
from launchlens.offline_fixtures import ReviewFixtureTools,package_cases,request,action
from launchlens.package_content import load_package_prompt,package_value,citation_only_failures,prepare_package_input,admit_package,PackageError
from launchlens.citation_repair import prompt
from launchlens.writer_comparison import WireResponse
from launchlens.linkedin_drafting import digest

SHAPES={
    ('blog','title'):'A sketch inspired by classic soda floats',
    ('campaign_brief','positioning'):'This product has cherry and vanilla notes. The concept is inspired by classic soda floats.',
    ('email','subject'):'A note inspired by classic soda floats',
}

class CitationRepairTests(unittest.TestCase):
    def setUp(self):
        self.net=self.enterContext(patch.object(socket.socket,'connect',side_effect=AssertionError('No network')))
        self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
        self.enterContext(patch('launchlens.live_package.datetime',FrozenDateTime))
        self.enterContext(patch('launchlens.live_package.project_writer_input',side_effect=project))

    def candidate(self,fields):
        value=deepcopy(package_cases()['initial_package'])
        for fmt,field in fields:
            value[fmt]['content'][field]=SHAPES[(fmt,field)]
            value[fmt]['claim_references']=[r for r in value[fmt]['claim_references'] if r['content_field']!=field]
        return value

    def run_case(self,fields,*,market='US',corrupt=None):
        candidate=self.candidate(fields);wire=Wire()
        if market=='UK':wire.actions=[action('read_pmm_brief','pmm'),action('check_launch','launch'),
            action('request_clarification','ask',market_id='UK',question='How should this draft proceed?'),action('generate_package','write')]
        def factory(model,validator):
            http=wire(model,validator)
            def wrapped(payload):
                response=http(payload);system=payload['messages'][0]['content']
                if system==load_package_prompt('package_writer'):output=deepcopy(candidate)
                elif system==prompt():
                    inputs=json.loads(payload['messages'][1]['content'])
                    output={'source_package_sha256':inputs['source_package_sha256'],'references':{}}
                    for fmt,target in inputs['citation_repair_targets'].items():
                        output['references'][fmt]=[{'content_field':field,'claim_ids':(['PROD-002','PROD-003'] if field=='positioning' else ['PROD-003'])} for field in target['required_fields']]
                    if corrupt:output=corrupt(output,candidate)
                else:return response
                envelope=json.loads(response.body);envelope['choices'][0]['message']['content']=json.dumps(output)
                return WireResponse(200,json.dumps(envelope).encode(),{})
            return wrapped
        folder=self.enterContext(tempfile.TemporaryDirectory());ledger=Path(folder)/'ledger.json'
        ledger.write_text(json.dumps({'ceiling_usd':'2.00','opening_accounted_usd':'0','claims':[]}));ledger.chmod(0o600)
        self.enterContext(patch('launchlens.live_package.BUILD_LEDGER',ledger))
        grant=permission();grant['standing_budget']=True
        if market!='US':
            from launchlens.live_package import preflight
            grant['request']=request(market);grant['scope_sha256']=preflight(request=request(market))['scope_sha256']
        run=LivePackageRun(grant,KEYS,tools=ReviewFixtureTools(),wire_factory=factory,now=NOW)
        state=run.execute(run.snapshot()['run_id'])
        if market=='UK':state=run.resume(state['run_id'],'draft_without_availability')
        return run,state,wire,candidate

    def test_three_failure_shapes_repair_references_without_rewriting_any_market_copy(self):
        for market in ('US','UK'):
            for field in SHAPES:
                with self.subTest(market=market,field=field):
                    run,state,wire,source=self.run_case([field],market=market)
                    self.assertEqual(state['status'],'awaiting_human_review')
                    self.assertEqual(state['retry_attempts'],1);self.assertEqual(state['writing_attempts'],2)
                    self.assertEqual(len(run.reviewer.calls),1);self.assertEqual(state['revision_attempts'],0)
                    value=package_value(state)
                    for fmt in source:
                        self.assertEqual(value[fmt]['content'],source[fmt]['content'])
                        for ref in source[fmt]['claim_references']:self.assertIn(ref,value[fmt]['claim_references'])
                    self.assertEqual(run.writer.calls[0]['candidate'],source)
                    inputs=run.writer.calls[1]['model_input']
                    self.assertEqual(inputs['saved_candidate_data_only'],source)
                    self.assertEqual(len(inputs['citation_diagnostics_data_only']),1)
                    self.assertEqual(inputs['citation_diagnostics_data_only'][0]['field_path'],'content.'+field[1])
                    self.assertEqual(inputs['output_schema']['required'],['source_package_sha256','references'])
                    self.assertEqual(run.writer.calls[1]['raw_candidate']['source_package_sha256'],digest(source))
                    self.assertEqual(run.writer.calls[1]['candidate'],value)
                    self.assertEqual(run.reviewer.calls[0]['model_input']['package'],value)
                    self.assertEqual(len(state['failure_history']),1)
                    self.assertEqual(run.guard.counts['package_writer'],2)
                    budget=run.guard.standing.read();self.assertTrue(all(c['status']=='usage_accounted' for c in budget['claims']))
                    self.assertGreater(float(budget['accounted_usd']),0)
                    n=len(wire.calls);run.execute(state['run_id']);self.assertEqual(len(wire.calls),n)
                    self.assertFalse(state['human_accepted'])

    def test_all_uncited_fields_are_sent_together_and_all_are_repaired(self):
        run,state,_,source=self.run_case(list(SHAPES))
        inputs=run.writer.calls[1]['model_input']
        self.assertEqual({(d['format'],d['field_path']) for d in inputs['citation_diagnostics_data_only']},
                         {(f,'content.'+p) for f,p in SHAPES})
        self.assertEqual(state['status'],'awaiting_human_review')
        self.assertEqual(len(run.writer.calls),2);self.assertEqual(len(run.reviewer.calls),1)
        for fmt in source:self.assertEqual(package_value(state)[fmt]['content'],source[fmt]['content'])

    def test_retry_cannot_introduce_new_subject_omission_by_returning_a_rewritten_package(self):
        def legacy_rewrite(patch_value,source):
            rewritten=deepcopy(source)
            rewritten['campaign_brief']['claim_references'].append({'content_field':'positioning','claim_ids':['PROD-002','PROD-003']})
            rewritten['email']['content']['subject']=SHAPES[('email','subject')]
            rewritten['email']['claim_references']=[r for r in rewritten['email']['claim_references'] if r['content_field']!='subject']
            return rewritten
        run,state,wire,source=self.run_case([('campaign_brief','positioning')],corrupt=legacy_rewrite)
        self.assertIsNone(state['package']);self.assertFalse(state['drafts']);self.assertEqual(len(run.reviewer.calls),0)
        self.assertEqual(run.writer.calls[0]['candidate'],source)
        self.assertNotEqual(run.writer.calls[1]['raw_candidate']['email']['content']['subject'],source['email']['content']['subject'])
        self.assertEqual(run.writer.calls[1]['outcome'],'failed')
        self.assertEqual(len(run.writer.calls),2);self.assertEqual(state['retry_attempts'],1)
        self.assertFalse(run.session.can_retry_writer())
        self.assertGreater(float(run.guard.standing.read()['accounted_usd']),0)
        n=len(wire.calls);run.execute(state['run_id']);self.assertEqual(len(wire.calls),n)

    def test_malformed_partial_or_out_of_scope_patches_fail_once_without_review(self):
        def omit(p,s):p['references']['email']=[];return p
        def unknown_id(p,s):p['references']['email'][0]['claim_ids']=['PROD-999'];return p
        def wrong_field(p,s):p['references']['email'][0]['content_field']='body';return p
        def duplicate(p,s):p['references']['email']*=2;return p
        def stale(p,s):p['source_package_sha256']='0'*64;return p
        def prose(p,s):p['content']={'subject':'Changed prose'};return p
        def extra_format(p,s):p['references']['ads']=[];return p
        def missing_format(p,s):del p['references']['email'];return p
        for bad in (omit,unknown_id,wrong_field,duplicate,stale,prose,extra_format,missing_format):
            with self.subTest(bad=bad.__name__):
                run,state,_,source=self.run_case([('email','subject')],corrupt=bad)
                self.assertIsNone(state['package']);self.assertEqual(len(run.writer.calls),2)
                self.assertEqual(len(run.reviewer.calls),0);self.assertFalse(run.session.can_retry_writer())
                self.assertEqual(run.writer.calls[0]['candidate'],source)

    def test_collector_does_not_hide_missing_field_behind_invalid_reference(self):
        run,state,_,_=self.run_case([('blog','title')]);inputs=prepare_package_input(state)
        source=self.candidate([('email','subject')])
        source['email']['claim_references'].append({'content_field':'absent','claim_ids':['PROD-003']})
        gaps=citation_only_failures(source,inputs)
        self.assertTrue(any(d['rule']=='invalid_content_field_reference' for d in gaps))
        self.assertTrue(any(d['format']=='email' and d['field_path']=='content.subject' for d in gaps))
        before=deepcopy(source);citation_only_failures(source,inputs);self.assertEqual(source,before)

    def test_partial_multi_field_repair_is_not_admitted_or_reviewed(self):
        def omit_one(value,source):
            value['references']['email']=[]
            return value
        run,state,_,source=self.run_case(list(SHAPES),corrupt=omit_one)
        self.assertEqual(len(run.writer.calls[1]['model_input']['citation_diagnostics_data_only']),3)
        self.assertIsNone(state['package']);self.assertFalse(state['drafts'])
        self.assertEqual(len(run.reviewer.calls),0);self.assertEqual(len(run.writer.calls),2)
        self.assertEqual(run.writer.calls[0]['candidate'],source)

    def test_all_invalid_ids_and_uncited_fields_are_reported_in_one_format(self):
        run,state,_,_=self.run_case([('blog','title')]);inputs=prepare_package_input(state)
        source=self.candidate([('email','subject')])
        source['email']['claim_references'][0]['claim_ids']=['PROD-998','PROD-999']
        gaps=citation_only_failures(source,inputs)
        invalid=[d for d in gaps if d['format']=='email' and d['rule']=='invalid_claim_reference']
        self.assertEqual(len(invalid),2)
        self.assertTrue(any(d['format']=='email' and d['field_path']=='content.subject' for d in gaps))

    def test_repaired_checkpoint_restores_with_raw_patch_and_costs_without_calls(self):
        run,state,wire,_=self.run_case([('email','subject')]);capture=deepcopy(run.capture())
        grant=deepcopy(run.guard.permission);grant['bound_run_id']=state['run_id']
        calls=len(wire.calls)
        restored=LivePackageRun(grant,KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW,checkpoint=(state,capture))
        self.assertEqual(restored.snapshot(),state);self.assertEqual(restored.capture()['writer'],capture['writer'])
        self.assertEqual(restored.guard.cost,run.guard.cost);self.assertEqual(len(wire.calls),calls)
        self.assertIn('references',restored.writer.calls[1]['raw_candidate'])

    def test_whole_package_validation_still_rejects_policy_and_coverage_failures(self):
        run,state,_,_=self.run_case([('email','subject')]);inputs=prepare_package_input(state)
        repaired=package_value(state);repaired['blog']['content']['title']='Buy now'
        with self.assertRaises(PackageError):admit_package(repaired,inputs)
        source=self.candidate([('blog','title')]);source['email']['content']['body']='Buy now'
        self.assertEqual(citation_only_failures(source,inputs),[])

    def test_live_transport_rejects_citation_prompt_before_first_writer_and_after_retry(self):
        run,state,wire,_=self.run_case([('email','subject')])
        payload=deepcopy(next(p for p in wire.calls if p['messages'][0]['content']==prompt()))
        payload.pop('response_format',None);payload.pop('max_completion_tokens',None)
        for prior in (0,2):
            grant=permission();budget=RunBudget(grant,now=NOW);budget.counts['package_writer']=prior
            transport=LiveTransport('package_writer',budget,KEYS,wire_factory=wire)
            with self.subTest(prior=prior),self.assertRaises(LiveGateError):transport(payload)
            self.assertEqual(budget.events,[])

if __name__=='__main__':unittest.main()
