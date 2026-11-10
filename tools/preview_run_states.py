"""Offline-only visual fixture launcher for the EXISTING run page, not an app route.

Run with tools/ui/.venv/bin/python -m streamlit run tools/preview_run_states.py
--server.port 8521. Optional ?case=activity|review|review_v2|summary|package|working|waiting|ready|stopped. No private inputs.
The working view pauses a real fixture graph at its selected Writer action.
"""
from pathlib import Path
import os
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import streamlit as st
from launchlens.offline_ui_run import OfflineUIRun,fixture_inventory,draft_identity
from launchlens.offline_fixtures import request
from launchlens.voice_policy import BRAND_POLICY_ID
from launchlens.inventory import load_display
from launchlens.inventory_ui import main
os.environ['LAUNCHLENS_UI_MODE']='offline'
case=st.query_params.get('case','activity')
if case not in {'activity','review','review_v2','summary','package','working','waiting','ready','stopped'}:raise ValueError('Unknown visual fixture')
if st.session_state.get('_visual_case')!=case:
    run=OfflineUIRun(request('UK' if case=='waiting' else 'US'),
        scenario='Bad Writer response' if case=='stopped' else 'Standard review',
        voice_policy_id=BRAND_POLICY_ID,package=True)
    def pause_before_writer(update,state):
        return False if (state.get('pending') or {}).get('name')=='generate_package' else None
    state=run.execute(run.snapshot()['run_id'],on_update=pause_before_writer if case=='working' else None)
    if case in {'ready','activity','package','review_v2'}:
        version,sha=draft_identity(state)
        run.revise(state['run_id'],'Remove unsupported novelty and intensity; keep simulated brand voice.',version,sha)
    st.session_state.update(_visual_case=case,offline_run=run,screen='run',selected_request=request('UK' if case=='waiting' else 'US'),
        inventory=fixture_inventory(load_display()),_data_mode='Demo simulation')
    if case in {'activity','review','review_v2','summary','package'}:
        from launchlens.review_decisions import decision_book,grouped_findings,record_decision,safe_hints
        from copy import deepcopy
        from launchlens.package_presentation import progress
        state=run.snapshot();book=decision_book(state)
        if case=='summary':
            for i,g in enumerate(g for g in grouped_findings(state) if g['needs_attention']):
                hint=next(iter(safe_hints(g)),None)
                book=record_decision(state,book,g['id'],'keep_wording' if i%3==0 else 'request_changes',suggestion=hint if i%3 else None)
        st.session_state['run-review-decisions-'+state['run_id']]=book
        tab='Activity' if case=='activity' else 'Package' if case=='package' else 'Review'
        st.session_state['run-tabs-'+state['run_id']]=tab
        st.session_state['run-tab-phase']=(state['status'],state['package']['version'])
        st.session_state['run-review-position-binding-'+state['run_id']]=book['binding']
        attention=[g for g in grouped_findings(state) if g['needs_attention']]
        st.session_state['run-review-position-'+state['run_id']]=len(attention) if case=='summary' else next((i for i,g in enumerate(attention) if g['phrase']=='introducing'),0) if case=='review' else 0
main()
