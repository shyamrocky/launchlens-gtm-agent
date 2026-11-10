"""Offline-only visual fixture launcher for the EXISTING run page, not an app route.

Run with tools/ui/.venv/bin/python -m streamlit run tools/preview_run_states.py
--server.port 8521. Optional ?case=working|waiting|ready|stopped. No private inputs.
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
case=st.query_params.get('case','working')
if case not in {'working','waiting','ready','stopped'}:raise ValueError('Unknown visual fixture')
if st.session_state.get('_visual_case')!=case:
    run=OfflineUIRun(request('UK' if case=='waiting' else 'US'),
        scenario='Bad Writer response' if case=='stopped' else 'Standard review',
        voice_policy_id=BRAND_POLICY_ID,package=True)
    def pause_before_writer(update,state):
        return False if (state.get('pending') or {}).get('name')=='generate_package' else None
    state=run.execute(run.snapshot()['run_id'],on_update=pause_before_writer if case=='working' else None)
    if case=='ready':
        version,sha=draft_identity(state)
        run.revise(state['run_id'],'Remove unsupported novelty and intensity; keep simulated brand voice.',version,sha)
    st.session_state.update(_visual_case=case,offline_run=run,screen='run',selected_request=request('UK' if case=='waiting' else 'US'),
        inventory=fixture_inventory(load_display()),_data_mode='Demo simulation')
main()
