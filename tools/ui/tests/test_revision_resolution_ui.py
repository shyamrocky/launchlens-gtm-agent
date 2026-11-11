"""Render deterministic request results without inference or state mutation."""
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from streamlit.testing.v1 import AppTest


class RevisionResolutionUITests(unittest.TestCase):
    def test_use_suggestion_click_applies_exact_text_and_reviews_without_writer(self):
        code = '''
import sys
from pathlib import Path
import streamlit as st
sys.path.insert(0,str(Path.cwd()/'tools/agent_foundation/tests'))
from test_revision_convergence import RevisionConvergenceTests
from launchlens.agent_run_ui import review_page
from launchlens.review_decisions import grouped_findings,review_identity
from launchlens.package_presentation import must_decide
class Run:
    kind='demo'
    store=None
    def __init__(self):
        self.session,self.initial,self.revisions,self.reviews=RevisionConvergenceTests().session()
    def snapshot(self):return self.session.snapshot()
    def request_revision(self,*args,**kwargs):return self.session.request_revision(*args,**kwargs)
if 'fixture_run' not in st.session_state:
    run=Run();st.session_state['fixture_run']=run
    state=run.snapshot();groups=[g for g in grouped_findings(state) if must_decide(g)]
    st.session_state['favorite_id']=next(g['id'] for g in groups if g['phrase']=='favorite')
    st.session_state['run-review-position-binding-'+state['run_id']]=review_identity(state)
    st.session_state['run-review-position-'+state['run_id']]=next(i for i,g in enumerate(groups) if g['phrase']=='favorite')
run=st.session_state['fixture_run']
if st.session_state.pop('run-command',None)=='execute':run.session.run(run.snapshot()['run_id'])
review_page(run.snapshot(),run=run,embedded=True)
'''
        with patch.object(socket.socket,'connect',side_effect=AssertionError('No network')) as net:
            app=AppTest.from_string(code,default_timeout=20).run()
            self.assertFalse(app.exception)
            app.button(key='use-'+app.session_state['favorite_id']).click().run()
            self.assertFalse(app.exception)
            run=app.session_state['fixture_run'];state=run.snapshot()
            self.assertEqual(state['package']['version'],2)
            self.assertEqual(len(run.revisions),0);self.assertEqual(len(run.reviews),2)
            text=state['drafts']['blog']['draft']['content']['sections'][1]['body']
            self.assertIn('soda-float idea',text);self.assertNotIn('favorite',text)
            self.assertEqual(net.call_count,0)

    def test_partial_results_and_omitted_phrase_remain_visible_without_writes(self):
        code = '''
from copy import deepcopy
import streamlit as st
from launchlens.offline_ui_run import OfflineUIRun
from launchlens.agent_run_ui import review_page
from launchlens.offline_fixtures import request
from launchlens.voice_policy import BRAND_POLICY_ID
run=OfflineUIRun(request(), package=True, voice_policy_id=BRAND_POLICY_ID)
state=run.execute(run.snapshot()['run_id'])
field=state['drafts']['blog']['draft']['content']['sections'][1]['body']
state['ledger']['revision-resolution-v1']={
    'draft_sha256':state['package']['package_sha256'],
    'requests':[
        {'format':'blog','content_field':'sections.1.body','quote':field[:8],
         'start':0,'end':8,'current_start':0,'current_end':8,'status':'unresolved'},
        {'format':'blog','content_field':'sections.1.body','quote':'removed phrase',
         'start':0,'end':14,'status':'wording_changed'}]}
before=deepcopy(state)
review_page(state, embedded=True)
st.session_state['unchanged']=state==before and run.snapshot()['ledger']!=state['ledger']
'''
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('No network')) as net:
            for incomplete in (False, True):
                source = code.replace('before=deepcopy(state)', "state['review']={}\nbefore=deepcopy(state)") if incomplete else code
                app = AppTest.from_string(source, default_timeout=20).run()
                self.assertFalse(app.exception)
                self.assertTrue(app.session_state['unchanged'])
                self.assertTrue(any('1 requested occurrences changed wording · 1 unresolved' in x.value for x in app.caption))
                self.assertTrue(any('Reviewer omitted' in x.value for x in app.warning))
                self.assertIn('Requested wording results', [x.label for x in app.expander])
                self.assertTrue(any('Unresolved · ' in x.value for x in app.markdown))
            self.assertEqual(net.call_count, 0)


if __name__ == '__main__':
    unittest.main()
