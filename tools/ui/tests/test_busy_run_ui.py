"""Busy snapshot recovery through actual Streamlit reruns; no live services."""
from copy import deepcopy
from pathlib import Path
from threading import Event, Thread
import os
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from streamlit.testing.v1 import AppTest
from launchlens import agent_run_ui
from launchlens.gtm_registry import HarnessError
from launchlens.offline_fixtures import request
from launchlens.offline_ui_run import OfflineUIRun
from launchlens.voice_policy import BRAND_POLICY_ID


class BusyRunUITests(unittest.TestCase):
    def setUp(self):
        self.network = self.enterContext(patch.object(
            socket.socket, 'connect', side_effect=AssertionError('No network')))
        self.addCleanup(lambda: self.assertEqual(self.network.call_count, 0))
        self.enterContext(patch.dict(os.environ, {
            'LAUNCHLENS_UI_MODE': 'offline', 'LANGSMITH_TRACING': 'false'}))

    def app(self):
        app = AppTest.from_file(str(ROOT / 'streamlit_app.py'), default_timeout=20).run()
        self.assertFalse(app.exception)
        return app

    def start(self, market='UK'):
        app = self.app()
        app.button(key='open-' + market).click().run()
        app.button(key='prepare-start').click().run()
        self.assertFalse(app.exception)
        return app, app.session_state['offline_run']

    def hold_lock(self, run):
        acquired, release = Event(), Event()
        def worker():
            with run.session._lock:
                acquired.set()
                release.wait(15)
        thread = Thread(target=worker, daemon=True)
        thread.start()
        self.assertTrue(acquired.wait(3))
        def cleanup():
            release.set()
            thread.join(3)
        self.addCleanup(cleanup)
        return release, thread

    def recover(self, app, run, *, command=None):
        before = deepcopy(run.snapshot())
        captured = deepcopy(run.capture())
        release, worker = self.hold_lock(run)
        polls = []
        def wait(seconds):
            import streamlit as st
            polls.append(seconds)
            self.assertIs(st.session_state['offline_run'], run)
            self.assertEqual(st.session_state.get('run-command'), command)
            self.assertEqual(run.capture(), captured)
            self.assertTrue(worker.is_alive())
            if len(polls) == 2:
                release.set()
                worker.join(3)
                self.assertFalse(worker.is_alive())
        with patch.object(agent_run_ui, 'sleep', side_effect=wait), \
                patch.object(agent_run_ui.st, 'info', wraps=agent_run_ui.st.info) as info:
            app.run()  # Both retries must be automatic, with no subsequent test click/run.
        self.assertFalse(app.exception)
        self.assertEqual(polls, [2, 2])
        self.assertEqual(sum(c.args == ('Agent is still working…',) for c in info.call_args_list), 2)
        self.assertIs(app.session_state['offline_run'], run)
        return before, captured

    def test_busy_snapshot_automatically_recovers_without_changing_paused_run(self):
        app, run = self.start()
        before, captured = self.recover(app, run)
        self.assertEqual(run.snapshot(), before)
        self.assertEqual(run.capture(), captured)
        self.assertTrue(any(b.label == 'Continue' for b in app.button))
        for tab in ('home', 'current', 'home', 'current'):
            app.button(key=tab).click().run()
            self.assertFalse(app.exception)
            self.assertIs(app.session_state['offline_run'], run)
            self.assertEqual(run.snapshot(), before)
            self.assertEqual(run.capture(), captured)

    def test_queued_command_is_untouched_while_busy_then_runs_once(self):
        app = self.app()
        run = OfflineUIRun(request('UK'), voice_policy_id=BRAND_POLICY_ID, package=True)
        app.session_state['offline_run'] = run
        app.session_state['screen'] = 'run'
        app.session_state['run-command'] = 'execute'
        with patch.object(run, 'execute', wraps=run.execute) as execute:
            self.recover(app, run, command='execute')
        self.assertEqual(execute.call_count, 1)
        self.assertEqual(run.snapshot()['status'], 'needs_clarification')
        self.assertNotIn('run-command', app.session_state)

    def test_other_harness_errors_surface_without_retry(self):
        app, run = self.start()
        for message in ('Different failure', 'Execution is already running', 'Execution is running '):
            with self.subTest(message=message), \
                    patch.object(run, 'snapshot', side_effect=HarnessError(message)), \
                    patch.object(agent_run_ui, 'sleep') as wait:
                app.run()
                self.assertTrue(app.exception)
                wait.assert_not_called()
                # Production intentionally redacts app.exception text. Verify the
                # UI boundary itself rethrows the original exception unchanged.
                error = HarnessError(message)
                with patch.object(agent_run_ui.st, 'session_state', {'offline_run': run}), \
                        patch.object(run, 'snapshot', side_effect=error):
                    with self.assertRaises(HarnessError) as raised:
                        agent_run_ui.run_page({})
                self.assertIs(raised.exception, error)

    def test_non_harness_error_surfaces_without_retry(self):
        app, run = self.start()
        with patch.object(run, 'snapshot', side_effect=ValueError('Synthetic unexpected error')), \
                patch.object(agent_run_ui, 'sleep') as wait:
            app.run()
        self.assertTrue(app.exception)
        wait.assert_not_called()
        error = ValueError('Synthetic unexpected error')
        with patch.object(agent_run_ui.st, 'session_state', {'offline_run': run}), \
                patch.object(run, 'snapshot', side_effect=error):
            with self.assertRaises(ValueError) as raised:
                agent_run_ui.run_page({})
        self.assertIs(raised.exception, error)

    def answer(self, app):
        app.radio(key='run-choice').set_value('Draft without availability wording').run()
        next(b for b in app.button if b.label == 'Continue').click().run()
        self.assertFalse(app.exception)

    def test_uk_start_fresh_pause_answer_resume_drafts_and_navigation(self):
        app, old = self.start()
        self.answer(app)
        old_state, old_capture = deepcopy(old.snapshot()), deepcopy(old.capture())
        app.button(key='home').click().run()
        app.button(key='fresh-UK').click().run()
        app.button(key='archive-confirm').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, 'Prepare UK package')
        app.button(key='prepare-start').click().run()
        self.assertFalse(app.exception)
        run = app.session_state['offline_run']
        before, _ = self.recover(app, run)
        self.assertNotEqual(before['run_id'], old_state['run_id'])
        self.assertEqual(before['status'], 'needs_clarification')
        for tab in ('home', 'current'):
            app.button(key=tab).click().run()
            self.assertFalse(app.exception)
            self.assertIs(app.session_state['offline_run'], run)
            self.assertEqual(run.snapshot(), before)
        self.answer(app)
        after = run.snapshot()
        self.assertEqual(after['run_id'], before['run_id'])
        self.assertEqual(after['status'], 'awaiting_human_review')
        self.assertEqual(after['launch']['decision'], 'Clarify')
        self.assertTrue(after['restricted_drafting'])
        self.assertEqual(len(after['drafts']), 5)
        self.assertEqual(old.snapshot(), old_state)
        self.assertEqual(old.capture(), old_capture)

    def test_us_and_india_recover_and_keep_state_across_tabs(self):
        for market, status, decision in (
                ('US', 'awaiting_human_review', 'Proceed'), ('IN', 'held', 'Hold')):
            with self.subTest(market=market):
                app, run = self.start(market)
                before, captured = self.recover(app, run)
                self.assertEqual(before['status'], status)
                self.assertEqual(before['launch']['decision'], decision)
                self.assertEqual(len(before['drafts']), 5 if market == 'US' else 0)
                for tab in ('home', 'current'):
                    app.button(key=tab).click().run()
                    self.assertFalse(app.exception)
                    self.assertIs(app.session_state['offline_run'], run)
                    self.assertEqual(run.snapshot(), before)
                    self.assertEqual(run.capture(), captured)


if __name__ == '__main__':
    unittest.main()
