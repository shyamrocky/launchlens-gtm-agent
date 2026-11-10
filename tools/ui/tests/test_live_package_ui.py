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


class LivePackageUITests(unittest.TestCase):
    def setUp(self):
        self.block=patch.object(socket.socket,'connect',side_effect=AssertionError('No UI network'))
        self.network=self.block.start();self.addCleanup(self.block.stop)
        self.addCleanup(lambda:self.assertEqual(self.network.call_count,0))
        self.clock=patch('launchlens.live_package.datetime',FrozenDateTime)
        self.clock.start();self.addCleanup(self.clock.stop)
        self.env=patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'offline','LANGSMITH_TRACING':'true'})
        self.env.start();self.addCleanup(self.env.stop)
        self.projection=patch('launchlens.live_package.project_writer_input',side_effect=project)
        self.projection.start();self.addCleanup(self.projection.stop)

    def start_live(self,wire=None):
        import tempfile
        from launchlens.writer_comparison import ProtectedStore
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        wire=wire or Wire();run=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW,
            store=ProtectedStore(Path(folder.name)/'mock-live-run'))
        class Reader:
            def get_launch_context(self,market):return ReviewFixtureTools().read_launch({'market_id':market})
        snapshot=fetch_inventory(load_display(),Reader())
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
        with patch('launchlens.inventory_ui.fetch_inventory',return_value=snapshot),             patch('launchlens.live_package.readiness',return_value={'ready':True,'request':request(),'message':'MOCK authorization'}),             patch('launchlens.live_package.create_live_run',return_value=run) as factory:
            app.selectbox(key='ui-mode').select('Live agent').run()
            app.button(key='open-US').click().run()
            self.assertFalse(app.button(key='prepare-start').disabled)
            self.assertEqual(factory.call_count,0);self.assertFalse(wire.calls)
            app.button(key='prepare-start').click().run()
            self.assertEqual(factory.call_count,1)
        self.assertEqual(len(app.exception),0)
        if any(b.label=='Review package' for b in app.button):app.button(key='run-review').click().run()
        return app,run,wire

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
        self.assertTrue(any(b.label=='Reset current run' for b in app.button))
        for _ in range(3):app.run()
        self.assertEqual(len(wire.calls),6)

    def test_live_feedback_uses_same_guard_and_fresh_all_format_review(self):
        app,run,wire=self.start_live()
        next(x for x in app.text_area if x.label=='Other notes for the revision (optional)').input('Remove unsupported intensity.')
        next(b for b in app.button if b.label=='Create Version 2').click().run()
        self.assertEqual(len(app.exception),0);self.assertEqual(run.snapshot()['package']['version'],2)
        self.assertEqual(len(wire.calls),9);self.assertEqual(run.guard.counts['package_revision'],1)
        self.assertEqual(run.guard.counts['package_reviewer'],2)
        app.run();self.assertEqual(len(wire.calls),9)
        next(b for b in app.button if b.label=='Reset current run').click().run()
        self.assertEqual(len(app.exception),0);self.assertTrue(run.guard.closed)
        self.assertNotIn('offline_run',app.session_state)

    def test_grouped_choices_reach_live_revision_and_version_two_on_same_page(self):
        from launchlens.review_decisions import grouped_findings
        app,run,wire=self.start_live();before=run.snapshot();groups=grouped_findings(before)
        group=groups[0];occurrence=group['occurrences'][0]
        app.button(key='changes-'+group['id']).click().run()
        if len(group['occurrences'])>1:app.button(key='keep-'+occurrence['id']).click().run()
        else:app.button(key='keep-'+group['id']).click().run()
        other=next((g for g in groups[1:] if g['needs_attention']),None)
        if other:app.button(key='changes-'+other['id']).click().run()
        next(x for x in app.text_area if x.label=='Other notes for the revision (optional)').input('Retain brand voice, no invented availability.')
        initial=len(wire.calls)
        next(b for b in app.button if b.label=='Create Version 2').click().run()
        self.assertFalse(app.exception);after=run.snapshot()
        self.assertEqual(app.title[0].value,'US package')
        self.assertTrue(any('Version 2' in x.value for x in app.caption))
        self.assertEqual(after['run_id'],before['run_id']);self.assertEqual(after['package']['version'],2)
        self.assertIn('Human prefers keeping ',after['revision_feedback'])
        self.assertIn('Retain brand voice',after['revision_feedback'])
        self.assertEqual(after['review']['binding']['draft_version'],2)
        self.assertEqual(len(wire.calls),initial+3);self.assertEqual(len(after['reviews']),2)
        self.assertFalse(app.session_state['run-review-decisions-'+after['run_id']]['events'])
        app.run();self.assertEqual(len(wire.calls),initial+3)
        self.assertFalse(any(b.label=='Create Version 2' for b in app.button))

    def test_explicit_current_navigation_resumes_same_package_without_any_calls(self):
        app,run,wire=self.start_live();before=run.snapshot();count=len(wire.calls)
        del app.session_state['offline_run']
        if 'selected_request' in app.session_state:del app.session_state['selected_request']
        app.session_state['screen']='inventory';app.session_state['run-show-package']=False
        with patch('launchlens.live_package.current_resume_available',return_value=True),patch('launchlens.live_package.load_current_live_run',return_value=run) as resume:
            app.run();self.assertEqual(resume.call_count,0)
            app.button(key='current').click().run();self.assertEqual(resume.call_count,1)
        self.assertFalse(app.exception);self.assertEqual(run.snapshot(),before)
        self.assertEqual(len(wire.calls),count);self.assertEqual(app.title[0].value,'US package')
        app.button(key='run-review').click().run()
        self.assertEqual(app.title[0].value,'US package');self.assertEqual(len(wire.calls),count)

    def test_live_provider_failure_never_falls_back_to_demo(self):
        wire=Wire(lambda p:WireResponse(429,b'{"error":"MOCK"}',{}))
        app,run,wire=self.start_live(wire)
        self.assertEqual(run.snapshot()['status'],'failed');self.assertFalse(run.snapshot()['drafts'])
        self.assertEqual(app.selectbox(key='ui-mode').value,'Live agent')
        self.assertNotEqual(app.session_state['inventory'].get('data_mode'),'offline')
        self.assertTrue(run.guard.closed);app.run();self.assertEqual(len(wire.calls),1)
        self.assertFalse(any('Generate again' in b.label for b in app.button))


if __name__=='__main__':unittest.main()
