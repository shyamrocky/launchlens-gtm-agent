"""Live UI wiring under explicit mocked permission; no real keys or network."""
from copy import deepcopy
from pathlib import Path
import os
import socket
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/agent_foundation/tests')]
from streamlit.testing.v1 import AppTest
from test_live_package import Wire,permission,KEYS,NOW,project,FrozenDateTime
from launchlens.live_package import LivePackageRun
from launchlens.offline_fixtures import ReviewFixtureTools,request
from launchlens.inventory import fetch_inventory,load_display
from launchlens.writer_comparison import WireResponse


from ui_review_helpers import finish_stack,show_card

class LivePackageUITests(unittest.TestCase):
    def setUp(self):
        self.block=patch.object(socket.socket,'connect',side_effect=AssertionError('No UI network'))
        self.network=self.block.start();self.addCleanup(self.block.stop)
        self.addCleanup(lambda:self.assertEqual(self.network.call_count,0))
        saved=patch('launchlens.inventory_ui.ui_saved_runs',return_value=[]);saved.start();self.addCleanup(saved.stop)
        self.clock=patch('launchlens.live_package.datetime',FrozenDateTime)
        self.clock.start();self.addCleanup(self.clock.stop)
        self.env=patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'offline','LANGSMITH_TRACING':'true'})
        self.env.start();self.addCleanup(self.env.stop)
        self.projection=patch('launchlens.live_package.project_writer_input',side_effect=project)
        self.projection.start();self.addCleanup(self.projection.stop)
        snapshot_write=patch('launchlens.run_archive.write_private',return_value=None)
        snapshot_write.start();self.addCleanup(snapshot_write.stop)

    def start_live(self,wire=None,*,market="US",authorization=None):
        import tempfile
        from launchlens.writer_comparison import ProtectedStore
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        wire=wire or Wire();grant=authorization or permission()
        if market!='US':
            from launchlens.live_package import preflight
            grant['request']=request(market);grant['scope_sha256']=preflight(request=request(market))['scope_sha256']
        run=LivePackageRun(grant,KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW,
            store=ProtectedStore(Path(folder.name)/'mock-live-run'))
        class Reader:
            def get_launch_context(self,market):return ReviewFixtureTools().read_launch({'market_id':market})
        snapshot=fetch_inventory(load_display(),Reader())
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
        with patch('launchlens.inventory_ui.fetch_inventory',return_value=snapshot),             patch('launchlens.live_package.readiness',return_value={'ready':True,'request':request(market),'message':'MOCK authorization'}),             patch('launchlens.live_package.create_live_run',return_value=run) as factory:
            app.selectbox(key='ui-mode').select('Live agent').run()
            app.button(key='open-'+market).click().run()
            self.assertFalse(app.button(key='prepare-start').disabled)
            self.assertEqual(factory.call_count,0);self.assertFalse(wire.calls)
            app.button(key='prepare-start').click().run()
            self.assertEqual(factory.call_count,1)
        self.assertEqual(len(app.exception),0)
        if any(b.label=='Review package' for b in app.button):app.button(key='run-review').click().run()
        return app,run,wire

    def test_interrupted_draft_renders_without_review_or_execution_controls(self):
        from launchlens.live_package import SavedRunView
        app,run,wire=self.start_live()
        state=run.snapshot();state.update(status='interrupted',review=None,pending=None,revision_request=None)
        view=SavedRunView({'state':state,'capture':run.capture(),'authorization':run.guard.permission},run.store.path)
        calls=len(wire.calls);app.session_state['offline_run']=view;app.session_state['screen']='run'
        app.run();self.assertFalse(app.exception)
        self.assertFalse(any(b.label in ['Continue agent','Create Version 2','Review Version 2'] for b in app.button))
        self.assertEqual(len(wire.calls),calls)

    def clarification_wire(self):
        from launchlens.offline_fixtures import action
        return Wire(actions=[action('read_pmm_brief','pmm'),action('check_launch','launch'),
            action('request_clarification','ask',market_id='UK',question='How should the UK run proceed?'),
            action('generate_package','write')])

    def test_real_approval_receipt_allows_other_market_in_session_and_after_reload(self):
        from launchlens.live_package import SavedRunView
        from launchlens.package_presentation import effective_approval
        import json
        for source,target in [('US','UK'),('UK','US')]:
            with self.subTest(source=source):
                app,run,wire=self.start_live(self.clarification_wire() if source=='UK' else None,market=source)
                if source=='UK':next(b for b in app.button if b.label=='Continue').click().run()
                state=run.snapshot();calls=len(wire.calls)
                app.button(key='home').click().run();app.button(key='open-'+target).click().run()
                with patch('launchlens.live_package.readiness',return_value={'ready':True,'request':app.session_state['selected_request'],'message':'MOCK authorization'}):app.run()
                self.assertTrue(app.button(key='prepare-start').disabled)  # No approval yet.
                app.button(key='current').click().run()
                next(c for c in app.checkbox if (c.key or '').startswith('run-approval-as-is-')).check().run()
                app.button(key='approve-package').click().run();self.assertFalse(app.exception)
                receipts=list(run.store.path.glob('human-internal-approval-*.json'))
                self.assertEqual(len(receipts),1);receipt=json.loads(receipts[0].read_text())
                self.assertTrue(receipt['internal_approved']);self.assertEqual(receipt['version'],state['package']['version'])
                self.assertFalse(state['human_accepted']);self.assertEqual(state['status'],'awaiting_human_review')
                self.assertEqual(run.snapshot(),state);self.assertEqual(len(wire.calls),calls)
                app.button(key='home').click().run();app.button(key='open-'+source).click().run()
                with patch('launchlens.live_package.readiness',return_value={'ready':True,'request':state['request'],'message':'MOCK authorization'}):app.run()
                self.assertTrue(app.button(key='prepare-start').disabled)  # Same market still needs archive.
                for reload in (False,True):
                    if reload:
                        view=SavedRunView({'state':state,'capture':run.capture(),'authorization':run.guard.permission},run.store.path)
                        snapshot=fetch_inventory(load_display(),type('Reader',(),{'get_launch_context':lambda _,m:ReviewFixtureTools().read_launch({'market_id':m})})())
                        with patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'live'}),patch('launchlens.live_package.current_resume_available',return_value=True),patch('launchlens.live_package.load_current_live_run',return_value=view),patch('launchlens.inventory_ui.fetch_inventory',return_value=snapshot):
                            app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
                            self.assertFalse(app.exception)
                            self.assertIn('run-internal-approval-'+state['run_id'],app.session_state)
                            app.button(key='home').click().run()
                    else:app.button(key='home').click().run()
                    app.button(key='open-'+target).click().run()
                    selected=app.session_state['selected_request']
                    with patch('launchlens.live_package.readiness',return_value={'ready':True,'request':selected,'message':'MOCK authorization'}):app.run()
                    self.assertFalse(app.exception);self.assertFalse(app.button(key='prepare-start').disabled)
                    self.assertEqual(len(wire.calls),calls)
                # The actual receipt cannot authorize a different version, even with old UI state.
                stale=deepcopy(state);stale['package']['version']+=1
                self.assertFalse(effective_approval(stale,store=run.store,record=receipt))
                app.session_state['offline_run']=SavedRunView({'state':stale,'capture':run.capture(),'authorization':run.guard.permission},run.store.path)
                with patch('launchlens.live_package.readiness',return_value={'ready':True,'request':selected,'message':'MOCK authorization'}):app.run()
                self.assertTrue(app.button(key='prepare-start').disabled)
                # Return to the actual approved receipt, then start the other market.
                app.session_state['offline_run']=SavedRunView({'state':state,'capture':run.capture(),'authorization':run.guard.permission},run.store.path)
                from launchlens.live_package import preflight
                grant=permission();grant['request']=selected;grant['scope_sha256']=preflight(request=selected)['scope_sha256']
                next_wire=self.clarification_wire() if target=='UK' else Wire()
                next_run=LivePackageRun(grant,KEYS,tools=ReviewFixtureTools(),wire_factory=next_wire,now=NOW)
                with patch('launchlens.live_package.readiness',return_value={'ready':True,'request':selected,'message':'MOCK authorization'}),patch('launchlens.live_package.create_live_run',return_value=next_run) as create:
                    app.run();app.button(key='prepare-start').click().run()
                    self.assertFalse(app.exception);self.assertEqual(create.call_count,1)
                self.assertIs(app.session_state['offline_run'],next_run)
                self.assertEqual(next_run.snapshot()['request']['market_id'],target)
                self.assertEqual(run.snapshot(),state);self.assertEqual(len(wire.calls),calls)

    def test_live_mode_and_demo_mode_labels_and_no_unapproved_start(self):
        class Reader:
            def get_launch_context(self,market):return ReviewFixtureTools().read_launch({'market_id':market})
        snapshot=fetch_inventory(load_display(),Reader())
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
        self.assertEqual(app.selectbox(key='ui-mode').value,'Demo simulation')
        with patch('launchlens.inventory_ui.fetch_inventory',return_value=snapshot),             patch('launchlens.live_package.readiness',return_value={'ready':False,'request':None,'message':'Not authorized'}),             patch('launchlens.live_package.create_live_run',side_effect=AssertionError('No live construction')) as create:
            app.selectbox(key='ui-mode').select('Live agent').run()
            app.button(key='open-US').click().run()
            self.assertTrue(app.button(key='prepare-start').disabled)
            app.run();self.assertEqual(create.call_count,0)

    def test_explicit_start_actual_harness_output_not_mislabeled_as_simulated(self):
        app,run,wire=self.start_live()
        self.assertEqual(run.snapshot()['mode'],'live_package');self.assertEqual(len(wire.calls),6)
        self.assertTrue(any('Live agent' in x.value for x in app.caption))
        self.assertFalse(any('OFFLINE SIMULATION' in x.value for x in app.warning))
        self.assertTrue(any('Independent assessment' in x.value for x in app.caption))
        self.assertFalse(any('Mock assessment' in x.value for x in app.caption))
        self.assertFalse(any(b.label=='Generate again · simulation' for b in app.button))
        self.assertTrue(any(b.label=='Archive & start fresh' for b in app.button))
        for _ in range(3):app.run()
        self.assertEqual(len(wire.calls),6)

    def test_live_feedback_uses_same_guard_and_fresh_all_format_review(self):
        app,run,wire=self.start_live()
        finish_stack(app,request_changes=True)
        next(x for x in app.text_area if x.label=='Anything else for Version 2? (optional)').input('Remove unsupported intensity.')
        next(b for b in app.button if b.label=='Create Version 2').click().run()
        self.assertEqual(len(app.exception),0);self.assertEqual(run.snapshot()['package']['version'],2)
        self.assertEqual(len(wire.calls),8);self.assertEqual(run.guard.counts['package_revision'],1)
        self.assertEqual(run.guard.counts['package_reviewer'],2)
        app.run();self.assertEqual(len(wire.calls),8)
        # Archive persistence is tested with hash-bound saved records separately.
        app.button(key='home').click().run();app.button(key='current').click().run()
        self.assertEqual(len(app.exception),0);self.assertEqual(run.snapshot()['package']['version'],2)
        self.assertEqual(len(wire.calls),8)

    def test_grouped_choices_reach_live_revision_and_version_two_on_same_page(self):
        from launchlens.review_decisions import grouped_findings
        app,run,wire=self.start_live();before=run.snapshot();groups=grouped_findings(before)
        group=groups[0];occurrence=group['occurrences'][0]
        app.button(key='changes-'+group['id']).click().run()
        show_card(app,group)
        if len(group['occurrences'])>1:app.button(key='keep-'+occurrence['id']).click().run()
        else:app.button(key='keep-'+group['id']).click().run()
        other=next((g for g in groups[1:] if g['needs_attention']),None)
        if other:show_card(app,other);app.button(key='changes-'+other['id']).click().run()
        finish_stack(app)
        next(x for x in app.text_area if x.label=='Anything else for Version 2? (optional)').input('Retain brand voice, no invented availability.')
        initial=len(wire.calls)
        next(b for b in app.button if b.label=='Create Version 2').click().run()
        self.assertFalse(app.exception);after=run.snapshot()
        self.assertEqual(app.title[0].value,'US package')
        self.assertTrue(any('Version 2' in x.value for x in app.caption))
        self.assertEqual(after['run_id'],before['run_id']);self.assertEqual(after['package']['version'],2)
        self.assertIn('Human prefers keeping ',after['revision_feedback'])
        self.assertIn('Retain brand voice',after['revision_feedback'])
        self.assertEqual(after['review']['binding']['draft_version'],2)
        self.assertEqual(len(wire.calls),initial+2);self.assertEqual(len(after['reviews']),2)
        self.assertFalse(app.session_state['run-review-decisions-'+after['run_id']]['events'])
        app.run();self.assertEqual(len(wire.calls),initial+2)
        self.assertFalse(any(b.label=='Create Version 2' for b in app.button))

    def test_reopening_automatically_resumes_same_package_without_any_calls(self):
        app,run,wire=self.start_live();before=run.snapshot();count=len(wire.calls)
        del app.session_state['offline_run']
        if 'selected_request' in app.session_state:del app.session_state['selected_request']
        app.session_state['screen']='inventory';app.session_state['run-show-package']=False
        with patch('launchlens.live_package.current_resume_available',return_value=True),patch('launchlens.live_package.load_current_live_run',return_value=run) as resume:
            app.run();self.assertEqual(resume.call_count,1)
            app.button(key='current').click().run();self.assertEqual(resume.call_count,1)
        self.assertFalse(app.exception);self.assertEqual(run.snapshot(),before)
        self.assertEqual(len(wire.calls),count);self.assertEqual(app.title[0].value,'US package')
        app.button(key='run-review').click().run()
        self.assertEqual(app.title[0].value,'US package');self.assertEqual(len(wire.calls),count)

    def test_live_provider_failure_never_falls_back_to_demo(self):
        wire=Wire(lambda p:WireResponse(429,b'{"error":"MOCK"}',{}))
        app,run,wire=self.start_live(wire)
        self.assertEqual(run.snapshot()['status'],'failed');self.assertFalse(run.snapshot()['drafts'])
        self.assertEqual(app.session_state['_data_mode'],'Live agent')
        self.assertNotEqual(app.session_state['inventory'].get('data_mode'),'offline')
        self.assertTrue(run.guard.closed);app.run();self.assertEqual(len(wire.calls),1)
        self.assertFalse(any('Generate again' in b.label for b in app.button))

    def test_exact_suggestion_submission_only_needs_fresh_reviewer_budget(self):
        import tempfile,json
        from launchlens.review_decisions import grouped_findings,safe_hints
        from ui_review_helpers import finish_pending
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ledger.json';path.write_text(json.dumps({'ceiling_usd':'1.00','opening_accounted_usd':'0','claims':[],'accounted_usd':'0','remaining_usd':'1.00'}));path.chmod(0o600)
            grant=permission();grant['standing_budget']=True
            with patch('launchlens.live_package.BUILD_LEDGER',path):
                app,run,wire=self.start_live(authorization=grant);before=run.snapshot()
                group=next(g for g in grouped_findings(before) if g['needs_attention'] and safe_hints(g))
                ledger=json.loads(path.read_text());ledger['opening_accounted_usd']='0.90'
                from decimal import Decimal
                ledger['accounted_usd']=str(Decimal('.90')+Decimal(ledger['accounted_usd']));ledger['remaining_usd']=str(Decimal('1')-Decimal(ledger['accounted_usd']))
                path.write_text(json.dumps(ledger));unchanged=path.read_bytes()
                self.assertFalse(run.guard.can_revise());self.assertTrue(run.guard.can_revise(writer_required=False))
                show_card(app,group);app.button(key='use-'+group['id']).click().run()
                self.assertEqual(run.snapshot(),before);self.assertEqual(path.read_bytes(),unchanged)
                finish_pending(app);self.assertFalse(app.button(key='create-next-version').disabled)
                app.button(key='create-next-version').click().run();self.assertFalse(app.exception)
                self.assertEqual(run.snapshot()['package']['version'],2);self.assertEqual(len(run.reviser.calls),0)
                self.assertEqual(len(run.reviewer.calls),2)

    def test_actual_continue_automatically_retries_missing_blog_title_once(self):
        import tempfile,json
        from launchlens.package_content import load_package_prompt
        for kind in ('missing_title','twice','mixed','no_permission','unknown_usage','exhausted'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'ledger.json'
                # setUp prevents catalog writes; create this synthetic ledger directly.
                path.write_text(json.dumps({'ceiling_usd':'1.00','opening_accounted_usd':'0','claims':[],'accounted_usd':'0','remaining_usd':'1.00'}));path.chmod(0o600)
                wire=self.clarification_wire()
                class CitationWire:
                    calls=wire.calls
                    def __call__(_,model,validator):
                        http=wire(model,validator)
                        def wrapped(payload):
                            response=http(payload)
                            if 'citation repair Writer' in payload['messages'][0]['content'] and kind=='twice':
                                value=json.loads(response.body);patch=json.loads(value['choices'][0]['message']['content'])
                                patch['references']={k:[] for k in patch['references']}
                                value['choices'][0]['message']['content']=json.dumps(patch)
                                return WireResponse(200,json.dumps(value).encode(),{})
                            if payload['messages'][0]['content']==load_package_prompt('package_writer'):
                                count=sum(p['messages'][0]['content']==load_package_prompt('package_writer') for p in wire.calls)
                                if count==1 or kind=='twice':
                                    value=json.loads(response.body);candidate=json.loads(value['choices'][0]['message']['content'])
                                    candidate['blog']['content']['title']='Cherry Float combines cherry with vanilla notes.'
                                    candidate['blog']['claim_references']=[r for r in candidate['blog']['claim_references'] if r['content_field']!='title']
                                    if kind=='mixed':candidate['email']['content']['body']='Buy now at https://example.com'
                                    if kind=='unknown_usage':value.pop('usage')
                                    if kind=='exhausted':
                                        ledger=json.loads(path.read_text());ledger['opening_accounted_usd']='0.98';path.write_text(json.dumps(ledger))
                                    value['choices'][0]['message']['content']=json.dumps(candidate)
                                    return WireResponse(200,json.dumps(value).encode(),{})
                            return response
                        return wrapped
                grant=permission();grant['standing_budget']=True
                if kind=='no_permission':grant['allow_one_explicit_writer_retry']=False
                with patch('launchlens.live_package.BUILD_LEDGER',path):
                    app,run,_=self.start_live(CitationWire(),market='UK',authorization=grant)
                    paused=run.snapshot();self.assertEqual(paused['status'],'needs_clarification')
                    next(b for b in app.button if b.label=='Continue').click().run()
                    self.assertFalse(app.exception);after=run.snapshot()
                    retry=kind in {'missing_title','twice'}
                    self.assertEqual(len(run.writer.calls),2 if retry else 1)
                    self.assertEqual(after['retry_attempts'],1 if retry else 0)
                    self.assertFalse(after['restricted_drafting']['availability_wording_allowed'])
                    self.assertTrue(after['failure_history'])
                    if retry:
                        diagnostic=after['failure_history'][0]
                        self.assertEqual((diagnostic['stage'],diagnostic['format'],diagnostic['rule'],diagnostic['field_path']),('draft_validation','blog','field_claim_coverage','content.title'))
                        self.assertEqual(run.writer.calls[1]['model_input']['previous_validation_diagnostic_data_only'],diagnostic)
                    if kind=='missing_title':self.assertEqual(after['status'],'awaiting_human_review')
                    else:self.assertFalse(after['package'])
                    calls=len(wire.calls);app.run();self.assertEqual(len(wire.calls),calls)
                    ledger=json.loads(path.read_text());self.assertEqual(len(ledger['claims']),len(run.guard.events))
                    self.assertGreater(float(ledger['accounted_usd']),0)

    def test_suggestion_choices_batch_on_create_with_exact_only_and_mixed_requests(self):
        from launchlens.review_decisions import grouped_findings,safe_hints
        from launchlens.package_content import package_value
        for mixed in (False,True):
            with self.subTest(mixed=mixed):
                app,run,wire=self.start_live();before=run.snapshot();calls=deepcopy(run.capture())
                groups=[g for g in grouped_findings(before) if g['needs_attention'] and safe_hints(g)]
                chosen=groups[:1];self.assertEqual(len(chosen),1)
                expected=[]
                for g in chosen:
                    show_card(app,g);app.button(key='use-'+g['id']).click().run()
                    expected.extend((o,safe_hints(g)[0]) for o in g['occurrences'] if o['needs_attention'])
                    self.assertEqual(run.snapshot(),before);self.assertEqual(run.capture(),calls)
                if mixed:
                    other=next(g for g in grouped_findings(before) if g['needs_attention'] and g['id'] not in {x['id'] for x in chosen})
                    show_card(app,other);app.button(key='changes-'+other['id']).click().run()
                from ui_review_helpers import finish_pending
                finish_pending(app);app.button(key='create-next-version').click().run()
                self.assertFalse(app.exception);after=run.snapshot()
                self.assertEqual(after['package']['version'],2);self.assertEqual(after['revision_attempts'],1)
                self.assertEqual(len(run.reviser.calls),1 if mixed else 0)
                self.assertEqual(len(run.reviewer.calls),2)
                self.assertEqual(after['review']['binding']['draft_version'],2)
                for occurrence,replacement in expected:
                    from launchlens.package_content import text_fields
                    text=dict(text_fields(after['drafts'][occurrence['format']]['draft']['content']))[occurrence['content_field']]
                    self.assertIn(replacement,text)
                calls=len(wire.calls);app.run();self.assertEqual(len(wire.calls),calls)

    def test_uk_ui_continue_retrieves_missing_claims_then_writes_without_availability(self):
        """Exercise the UI's actual Continue value and live adapter, not a fabricated state."""
        from launchlens.gtm_registry import eligible_actions
        from launchlens.live_package import preflight
        from launchlens.offline_fixtures import action
        actions=[action('read_pmm_brief','pmm'),action('check_launch','launch'),
            action('request_clarification','ask',market_id='UK',question='How should the UK run proceed?'),
            action('generate_package','write')]
        wire=Wire(actions=actions)
        authorization=permission();authorization['request']=request('UK')
        authorization['scope_sha256']=preflight(request=request('UK'))['scope_sha256']
        run=LivePackageRun(authorization,KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW)
        class Reader:
            def get_launch_context(self,market):return ReviewFixtureTools().read_launch({'market_id':market})
        snapshot=fetch_inventory(load_display(),Reader())
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
        with patch('launchlens.inventory_ui.fetch_inventory',return_value=snapshot), \
             patch('launchlens.live_package.readiness',return_value={'ready':True,'request':request('UK'),'message':'MOCK authorization'}), \
             patch('launchlens.live_package.create_live_run',return_value=run):
            app.selectbox(key='ui-mode').select('Live agent').run()
            app.button(key='open-UK').click().run()
            app.button(key='prepare-start').click().run()
        paused=run.snapshot();self.assertEqual(paused['status'],'needs_clarification')
        self.assertNotIn('generate_package',eligible_actions(paused))
        self.assertEqual(paused['request']['market_id'],'UK')
        self.assertEqual(paused['clarification'],'How should the UK run proceed?')
        self.assertEqual(run.writer.calls,[])
        premature=run.session._dispatch({**paused,'pending':action('generate_package','premature')})
        self.assertEqual(premature['draft_failure'],{
            'stage':'draft_eligibility','code':'draft_permission_denied',
            'field_path':'launch','rule':'launch_gate_or_human_answer_missing'})
        self.assertEqual(run.writer.calls,[])
        app.button(key='run-review').click().run() if any(b.key=='run-review' for b in app.button) else None
        app.button(key='run-activity').click().run() if any(b.key=='run-activity' for b in app.button) else None
        next(b for b in app.button if b.label=='Continue').click().run()
        completed=run.snapshot()
        self.assertFalse(app.exception)
        self.assertEqual(completed['feedback'],'draft_without_availability')
        self.assertEqual(completed['restricted_drafting']['availability_wording_allowed'],False)
        self.assertEqual(completed['writing_attempts'],1)
        self.assertEqual(completed['review_attempts'],1)
        self.assertTrue(completed['review'])
        self.assertIsNotNone(completed['package'])
        self.assertEqual(completed['status'],'awaiting_human_review')
        self.assertEqual(completed['research_gaps'],[])
        self.assertEqual(completed['searches'],0)
        self.assertTrue(any(event['action']=='fetch_required_objective_claims' and event['outcome']=='completed'
                            for event in completed['events']))
        self.assertEqual(len(run.writer.calls),1)
        self.assertFalse(run.writer.calls[0]['input']['writer_brief']['draft_constraints']['availability_wording_allowed'])
        blocked=run.session._dispatch({**completed,'pending':action('search_product_evidence','late-search',
            query='UK availability date confirmation',authority='public_product_facts')})
        self.assertEqual(blocked['searches'],0)
        self.assertEqual(blocked['events'][-1]['outcome'],'rejected_after_clarification')


if __name__=='__main__':unittest.main()
