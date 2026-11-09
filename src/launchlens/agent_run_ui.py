"""Read-only rendering and explicit commands for the existing offline run session."""
from html import escape
import streamlit as st
from launchlens.gtm_registry import HarnessError
from launchlens.offline_ui_run import draft_identity

LABELS = {'read_pmm_brief':'Read positioning and messaging', 'check_launch':'Check launch readiness',
    'search_product_evidence':'Retrieve product evidence', 'generate_linkedin':'Draft LinkedIn post',
    'review_linkedin':'Review current draft', 'revise_linkedin':'Revise using your feedback',
    'finish':'Check completion', 'request_clarification':'Request clarification'}
STATUS = {'awaiting_human_review':'Ready for your inspection', 'held':'Promotional drafting blocked',
    'needs_clarification':'Clarification required', 'failed':'Stopped safely', 'created':'Not started'}


def clear_run():
    run = st.session_state.pop('offline_run', None)
    if run is not None:
        run.reset()
    for key in list(st.session_state):
        if key.startswith('run-'):
            del st.session_state[key]


def run_page(display):
    run = st.session_state.get('offline_run')
    if run is None:
        st.info('No current simulation. Choose a market to begin.')
        return
    state = run.snapshot()
    if state is None:
        st.info('This run has been reset. Choose a market to begin.')
        return
    request = state['request']; run_id = state['run_id']
    with st.container(key='agent-run'):
        if st.button('‹ Market setup', key='run-back', type='tertiary'):
            from copy import deepcopy
            st.session_state['selected_request'] = deepcopy(request)
            st.session_state['screen'] = 'brief'; st.rerun()
        market_name = "India" if request["market_id"] == "IN" else request["market_id"]
        st.title(f"{market_name} GTM package")
        st.warning('OFFLINE SIMULATION — scripted decisions, fixture sources and authored mock drafts/reviews. No live AI or source calls.')
        st.caption(f"{display['product_name']} · Evaluation date: {request['evaluation_date']} · Run {run_id}")
        st.caption('Writing voice: simulated brand · Policy v1' if state.get('voice_policy_id') else 'Writing voice: historical neutral policy')
        st.subheader(STATUS.get(state['status'], 'Run status: ' + state['status']))
        launch = state.get('launch')
        if launch:
            st.write('Launch gate: ' + launch['decision'])
            for condition in launch['conditions']:
                if condition['message'] != state.get('clarification'):
                    st.write(condition['message'])
            for restriction in launch.get('restrictions', []): st.write(restriction)
        if state['status'] == 'needs_clarification':
            st.warning(state['clarification'])
            st.caption('Authoritative readiness evidence is required. Free-text notes cannot grant approval. This fixture cannot resolve the missing record.')
        if state['status'] == 'held':
            st.caption('No promotional draft was created. There is no research-only generation path in this checkpoint.')
        if state['status'] == 'failed':
            st.error('A required action failed. No automatic retry or repair was attempted.')
            diagnostic = state.get('draft_failure') or state.get('review_failure')
            if diagnostic: st.json(diagnostic)
        with st.expander('Your request and notes'):
            st.write('Campaign objective: ' + request['objective_id'])
            st.text(state['user_notes'] or 'No additional notes')
            st.caption('Notes are untrusted guidance. Scripted fixtures do not creatively interpret them.')
        st.subheader('Activity')
        for index, event in enumerate(state['events'], 1):
            label = LABELS.get(event['action'], event['action'].replace('_', ' '))
            st.write(f"{index}. {label} · {event['outcome']}")
            entry = state['ledger'].get(event.get('action_id'))
            if entry:
                with st.expander(f'Action {index}: inputs and result'):
                    st.json(entry)  # Actual harness ledger, not an invented progress timeline.
        st.caption(f"Harness model-call budget: {state['turns']}/12 simulated calls · {state['searches']}/4 evidence searches")
        record = state['drafts'].get('linkedin')
        if record:
            version, sha = draft_identity(state)
            st.subheader(f'LinkedIn draft · Version {version}')
            st.caption('Internal fixture draft · Human approval pending · Publishing disabled')
            content = record['draft']['content']
            # Escaped plain text prevents draft/user content from becoming executable UI.
            st.html('<article class="draft-copy">' + ''.join(f'<p>{escape(content[f])}</p>' for f in ('hook','body','cta')) +
                    '<p>' + escape(' '.join(content['hashtags'])) + '</p></article>')
            for warning in record['validation'].get('editorial_warnings', []):
                if warning.get('metric') == 'words':
                    target = warning['target']
                    st.caption(f"Length: {warning['actual']} words; suggested {target.get('min', 0)}–{target.get('max', 'no maximum')} words. This is advisory.")
                else:
                    st.caption('Editorial guidance is available in the draft validation details.')
            review = state.get('review')
            if review:
                st.subheader('Reviewer findings · Mock assessment')
                st.write('Changes requested' if review['review_status'] == 'changes_requested' else 'Reviewed — human inspection required')
                for finding in review['assessment']['findings']:
                    st.write(f"{finding['severity'].capitalize()} · {finding['dimension']} · {finding['content_field']}")
                    st.text(finding['quote'])
                    st.write(finding['rationale']); st.write('Suggested change: ' + finding['suggested_change'])
                if not review['assessment']['findings']:
                    st.write('This authored mock review reports no findings. It is not a live factual assessment or human approval.')
                with st.expander('Review scope and exact version binding'):
                    st.json(review)
            with st.expander('Supporting claims, citations and qualifications'):
                st.json(record['draft']['claim_references'])
                for result in state['evidence']:
                    for item in result['records']:
                        payload = item['evidence_payload']
                        st.write(f"{item['unit_id']} · {item['authority']}")
                        st.text(payload['primary_text'])
                        for segment in payload.get('segments', []):
                            if segment['role'] != 'primary': st.text(segment['text'])
                        for source in payload['source_references']:
                            st.write(f"{source['source_id']}: {source.get('url', '')}")
                        with st.expander('Complete fixture evidence: ' + item['unit_id']): st.json(item)
            if state['status'] == 'awaiting_human_review' and state['revision_attempts'] == 0:
                st.caption('One revision is available. The mock revision demonstrates wiring; it does not interpret arbitrary feedback.')
                with st.form(f'run-feedback-{run_id}-{version}'):
                    feedback = st.text_area('Feedback for revision', key=f'run-feedback-text-{run_id}-{version}', max_chars=2000)
                    submitted = st.form_submit_button('Request one revision', type='primary')
                if submitted:
                    if not feedback.strip(): st.error('Enter feedback before requesting a revision.')
                    else:
                        try:
                            with st.spinner('Running fixture revision and fresh review…'):
                                run.revise(run_id, feedback, version, sha)
                            st.rerun()
                        except HarnessError:
                            st.error('Revision was refused: the run/version changed or its one revision is already used.')
            elif state['revision_attempts']:
                st.caption('The one revision attempt is used. Start a fresh simulation to begin again.')
        if state['draft_history']:
            with st.expander('Draft and review history — current run only'):
                for old in state['draft_history']:
                    st.write(f"Draft version {old['version']}"); st.json(old)
                for review in state['reviews']:
                    st.write(f"Review of version {review['binding']['draft_version']}"); st.json(review)
        with st.expander('Complete available mock responses'):
            st.json(run.capture())
        left, right = st.columns(2)
        if left.button('Generate again · simulation', key='run-again-' + run_id):
            notes = state['user_notes']; scenario = run.scenario
            clear_run()
            from launchlens.offline_ui_run import OfflineUIRun
            fresh = OfflineUIRun(request, notes, scenario, voice_policy_id=state.get('voice_policy_id'))
            st.session_state['offline_run'] = fresh
            with st.spinner('Running a fresh offline simulation…'): fresh.execute(fresh.snapshot()['run_id'])
            st.rerun()
        if right.button('Reset demo', key='run-reset-' + run_id):
            clear_run(); st.session_state['screen'] = 'inventory'; st.rerun()
        st.caption('No human approval or publishing action is enabled. Results remain in this browser session only.')
