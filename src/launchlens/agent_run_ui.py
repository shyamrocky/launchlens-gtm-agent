"""PMM run view over the existing graph: explicit commands, no background worker."""
from copy import deepcopy
from html import escape
import streamlit as st
from launchlens.gtm_registry import HarnessError
from launchlens.offline_ui_run import draft_identity

LABELS={'read_pmm_brief':'Read your PMM positioning','check_launch':'Checked the launch gate',
 'search_product_evidence':'Pulled product evidence','generate_package':'Wrote the GTM package',
 'generate_linkedin':'Wrote the LinkedIn draft','review_package':'Independent Reviewer checked the package',
 'review_linkedin':'Independent Reviewer checked the draft','revise_package':'Revised the package',
 'revise_linkedin':'Revised the draft','request_clarification':'Paused for your input','finish':'Checked completion'}
SOURCES={'read_pmm_brief':'PMM / GTM brief · Notion','check_launch':'Launch calendar and readiness tracker · Notion',
 'search_product_evidence':'Product Brief · Pinecone evidence'}


def clear_run():
    run=st.session_state.pop('offline_run',None)
    if run is not None:run.reset()
    for key in list(st.session_state):
        if key.startswith('run-'):del st.session_state[key]


def timeline(state):
    rows=[]
    for event in state['events']:
        name=event['action'];outcome=event['outcome'];failed=outcome in {'failed_safely','replay_conflict','turn_limit'}
        title=LABELS.get(name,'Checked the next action')
        if failed:
            title="Couldn’t draft the package" if name=='generate_package' else 'A required action could not finish'
            why=("The Writer returned a format LaunchLens couldn’t accept. No package was admitted; the research is kept."
                 if name=='generate_package' and (state.get('draft_failure') or {}).get('stage')=='draft_validation'
                 else 'This action failed. Completed research is kept; missing information does not grant permission.')
        else:
            why=event.get('why') or 'Completed this recorded action. No business-purpose explanation was supplied.'
        icon='!' if failed else '?' if name=='request_clarification' else '✓'
        source=SOURCES.get(name)
        rows.append('<div class="run-step"><span class="step-icon '+('hold' if failed else 'good')+'">'+icon+'</span><div><strong>'+escape(title)+'</strong><p>'+escape(why)+'</p>'+
            ('<small>Source: '+escape(source)+'</small>' if source else '')+'</div></div>')
    pending=state.get('pending')
    if state['status']=='running' and pending:
        rows.append('<div class="run-step"><span class="step-icon working">…</span><div><strong>'+escape({'generate_package':'Writing the GTM package','review_package':'Reviewing the package','revise_package':'Revising the package'}.get(pending['name'],'Preparing the next action'))+'</strong><p>'+escape(pending.get('why') or 'The agent selected this action.')+'</p></div></div>')
    if not rows:return '<p class="run-muted">The agent has not executed an action yet.</p>'
    return '<div class="run-timeline">'+''.join(rows)+'</div>'


def review_findings(state):
    review=state.get('review')
    if not review:return []
    if 'format_reviews' in review:return [dict(f,format=name) for name,item in review['format_reviews'].items() for f in item['assessment']['findings']]
    return review.get('assessment',{}).get('findings',[])


def package_progress(state):
    from launchlens.package_content import FORMATS,LABELS
    rows=[];pending=(state.get('pending') or {}).get('name')
    for name in FORMATS:
        record=state['drafts'].get(name)
        if record:
            status='Review incomplete' if record.get('review_status')=='review_incomplete' else 'Reviewed ✓' if state.get('review') and record['review_status']=='reviewed_for_human' else 'Changes requested' if record['review_status']=='changes_requested' else 'Human clearance required' if record['review_status']=='human_clearance_required' else 'Drafted'
        elif state['status']=='needs_clarification':status='Paused'
        elif state['status'] in {'failed','held','stopped'}:status='Not drafted'
        elif pending=='generate_package':status='Writing…' # One atomic Writer call, no fake per-channel sequence.
        else:status='Queued'
        tone='good' if status=='Reviewed ✓' else 'warn' if status in {'Paused','Changes requested','Review incomplete'} else 'working' if status=='Writing…' else 'unknown'
        rows.append('<div class="package-row"><span>'+escape(LABELS[name])+'</span><span class="'+tone+'">'+status+'</span></div>')
    return '<div class="package-progress">'+''.join(rows)+'</div>'


def _legacy_run_page(display):
    run=st.session_state.get('offline_run')
    if run is None or run.snapshot() is None:
        st.info('Choose a market to start a run.');return
    state=run.snapshot();request=state['request'];run_id=state['run_id'];live=getattr(run,'kind','demo')=='live'
    market='India' if request['market_id']=='IN' else request['market_id']
    if state.get('package') and st.session_state.get('run-show-package',False):
        with st.container(key='agent-run'):
            review_page(state,run=run)
        return
    with st.container(key='agent-run'):
        if st.button(f'‹ {market} package setup',key='run-back',type='tertiary'):
            st.session_state['selected_request']=deepcopy(request);st.session_state['screen']='brief';st.rerun()
        st.title(f'{market} package')
        planned=(state.get('launch') or {}).get('planned_launch_date')
        if not planned:
            row=st.session_state.get('inventory',{}).get('markets',{}).get(request['market_id'],{})
            planned=row.get('planned_launch_date')
        from launchlens.inventory_ui import date_label
        st.caption(display['product_name']+' · Planned launch: '+(date_label(planned) if planned else 'Not verified'))
        st.caption('Live agent · Human approval pending · Nothing published' if live else 'Demo simulation · Scripted actions and authored fixture drafts/reviews · No live calls')
        command=st.session_state.pop('run-command',None)
        with st.container(key='run-status-card'):
            active=state['status'] in {'created','running'} or command is not None
            status='running' if active else state['status']
            ready=status=='awaiting_human_review' and bool(state.get('review'))
            headline='Agent is working' if active else 'Waiting on you' if status=='needs_clarification' else 'Package ready for your review' if ready else 'Promotional drafts blocked' if status=='held' else 'Draft needs attention' if status=='draft_incomplete' else 'Run stopped'
            tone='working' if active else 'warn' if status=='needs_clarification' else 'good' if ready else 'hold'
            st.html('<div class="gate-heading"><span class="readiness '+tone+'">●</span><h3>'+headline+'</h3></div>')
            if active:
                st.write('Progress is kept in this current browser session. An in-flight model request may finish before stopping.')
                if st.button('Stop run',key='run-stop'):
                    run.stop(run_id);st.rerun()
                if not command and state['status'] in {'created','running'}:
                    if st.button('Continue run',key='run-continue'):command='execute'
            elif status=='needs_clarification':st.write('Answer the question below to continue this same run.')
            elif ready:
                if not state['review'].get('review_complete',True):st.warning('Review incomplete. Drafts are available for human inspection.')
                count=len([f for f in review_findings(state) if f.get('severity')!='cleared']);st.write(('5 formats drafted · Review incomplete · Human inspection required' if not state['review'].get('review_complete',True) else f'5 formats drafted · Reviewer reported {count} finding(s) · Human approval pending') if run.package else 'Draft and independent assessment are available for inspection.')
                if st.button('Review package',key='run-review',type='primary'):st.session_state['run-show-package']=True;st.rerun()
            elif status=='held':st.write('Marketing authorization is pending. No promotional drafts were created.')
            else:
                st.write('The run stopped. Completed research is kept in this session.' if not state.get('draft_failure') else 'The Writer’s answer was rejected. Research is kept; an eligible retry starts at drafting.')
                retry_action,setup_action=st.columns(2)
                if run.session.can_retry_writer() and retry_action.button('Try again',key='run-retry',type='primary'):command='retry'
                if setup_action.button('Back to setup',key='run-setup',type='tertiary'):
                    st.session_state['screen']='brief';st.rerun()
        st.subheader('What the agent did')
        log=st.empty();log.html(timeline(state))
        if state['status']=='needs_clarification':
            with st.container(key='run-question'):
                st.markdown('**How should the agent proceed while UK availability is unconfirmed?**')
                st.write('The calendar has a planned date; readiness does not confirm availability. Your answer cannot grant approval.')
                with st.form('run-clarification-'+run_id):
                    choice=st.radio('Choose the next step',['Draft without availability wording','Recheck readiness','Stop this run'],key='run-choice',index=0)
                    st.caption('If readiness still says Missing, rechecking continues only without availability wording.')
                    answered=st.form_submit_button('Continue',type='primary')
                if answered:command={'Draft without availability wording':'draft_without_availability','Recheck readiness':'recheck_readiness','Stop this run':'stop'}[choice]
        if state.get('continuation_notice'):st.info(state['continuation_notice'])
        if state.get('review') and not state.get('package'):
            if not state['review'].get('review_complete',True):
                st.warning('Review incomplete. Drafts are available; inspect the raw Reviewer findings below.')
                with st.expander('Raw Reviewer findings',expanded=False):
                    st.json(state['review'].get('raw_response',{}))
            st.markdown('**Reviewer findings · Independent assessment**' if live else '**Reviewer findings · Mock assessment**')
            findings=review_findings(state)
            if not findings:st.write('No issues found in this assessment. Human inspection is still required.')
            for item in findings:
                if item.get('severity')=='cleared':continue
                if item.get('quote') is not None:st.text(item['quote'])
                st.write(item['rationale'])
            if len(state['reviews'])==2:st.caption('Revised and re-checked against the current package version. Original findings are retained in Technical details.')
        st.subheader('Package')
        progress=st.empty();progress.html(package_progress(state))
        if command is not None:
            try:
                with st.status('Agent is working',expanded=True) as progress_status:
                    def update(event,current):
                        pending=current.get('pending') or {}
                        progress_status.update(label=LABELS.get(pending.get('name'),'Agent is working'))
                        log.html(timeline(current));progress.html(package_progress(current))
                    if command=='execute':
                        if state['status']=='running':run.continue_run(run_id,on_update=update)
                        else:run.execute(run_id,on_update=update)
                    elif command=='retry':run.retry_writer(run_id,on_update=update)
                    else:run.resume(run_id,command,on_update=update)
                if st.session_state.pop('run-open-review-after-command',False) and run.snapshot().get('package') and run.snapshot()['status']=='awaiting_human_review':st.session_state['run-show-package']=True
                st.rerun()
            except HarnessError:st.error('This action is unavailable for the current run, permission or remaining budget.')
        state=run.snapshot()
        if state['drafts'] and st.session_state.get('run-show-package',False):
            if run.package:package_outputs(state)
            else:st.text('\n\n'.join(state['drafts']['linkedin']['draft']['content'][k] for k in ['hook','body','cta']))
        if not state.get('package') and state['status']=='awaiting_human_review' and state['revision_attempts']==0 and state['turns']+3<=12 and (not live or run.guard.can_revise()):
            version,sha=draft_identity(state)
            with st.form(f'run-feedback-{run_id}-{version}'):
                feedback=st.text_area('Feedback for revision',key=f'run-feedback-text-{run_id}-{version}',max_chars=2000)
                submitted=st.form_submit_button('Request one revision',type='primary')
            if submitted:
                if not feedback.strip():st.error('Enter feedback before requesting a revision.')
                else:
                    try:
                        run.session.request_revision(run_id,feedback,draft_version=version,draft_sha256=sha)
                        st.session_state['run-command']='execute';st.session_state['run-show-package']=True;st.rerun()
                    except HarnessError:st.error('Revision is unavailable for this run or version.')
        with st.expander('Technical details',expanded=False):
            if state.get('package'):risk_scan_view(state)
            st.caption('Writing voice: simulated brand channels · Neutral campaign brief · Policy v1' if state.get('voice_policy_id') else 'Writing voice: historical neutral policy')
            st.caption(f"Run {run_id} · Writing voice policy {state.get('voice_policy_id')} · Model calls {state['turns']}/12 · Evidence searches {state['searches']}/4")
            st.json({'request':state['request'],'notes_data_only':state['user_notes'],'launch':state['launch'],
                'draft_failure':state['draft_failure'],'failure_history':state.get('failure_history',[]),'normalizations':state.get('normalizations',[]),
                'review_failure':state['review_failure'],'events':state['events'],'ledger':state['ledger'],
                'draft_history':state['draft_history'],'reviews':state['reviews'],'responses':run.capture()})
            st.caption('No LangSmith trace is available for this checkpoint.')
            if live:st.json(run.guard.summary())
        with st.expander('Supporting claims, citations and qualifications',expanded=False):
            for result in state['evidence']:
                for item in result['records']:
                    p=item['evidence_payload'];st.write(item['unit_id']+' · '+item['authority']);st.text(p['primary_text'])
                    st.json({'source_references':p['source_references'],'qualifications':p['segments']})
        if not live and st.button('Generate again · simulation',key='run-again-'+run_id):
            from launchlens.offline_ui_run import OfflineUIRun
            notes=state['user_notes'];scenario=run.scenario;policy=state.get('voice_policy_id');package=run.package
            clear_run();st.session_state['offline_run']=OfflineUIRun(request,notes,scenario,voice_policy_id=policy,package=package)
            st.session_state['run-command']='execute';st.rerun()
        if st.button('Reset current run' if live else 'Reset demo',key='run-reset-'+run_id):
            clear_run();st.session_state['screen']='inventory';st.rerun()

def run_page(display):
    run=st.session_state.get('offline_run')
    if run is None or not getattr(run,'package',False):return _legacy_run_page(display)
    state=run.snapshot();request=state['request'];run_id=state['run_id'];live=getattr(run,'kind','demo')=='live'
    market='India' if request['market_id']=='IN' else request['market_id']
    with st.container(key='agent-run'):
        if st.button(f'‹ {market} package setup',key='run-back',type='tertiary'):
            st.session_state['selected_request']=deepcopy(request);st.session_state['screen']='brief';st.rerun()
        st.title(market+' package')
        from launchlens.inventory_ui import date_label
        planned=(state.get('launch') or {}).get('planned_launch_date') or st.session_state.get('inventory',{}).get('markets',{}).get(request['market_id'],{}).get('planned_launch_date')
        st.caption(display['product_name']+' · Planned launch: '+(date_label(planned) if planned else 'Not verified'))
        st.caption('Live agent · Human approval pending · Nothing published' if live else 'Demo simulation · Scripted actions and authored fixture drafts/reviews · No live calls')
        command=st.session_state.pop('run-command',None)
        active=state['status'] in {'created','running'} or command is not None
        ready=not active and state['status']=='awaiting_human_review' and bool(state.get('review'))
        recover=not active and callable(getattr(run,'can_review_saved',None)) and run.can_review_saved()
        tabkey='run-tabs-'+run_id
        phase=('working' if active else state['status'],(state.get('package') or {}).get('version'))
        if tabkey not in st.session_state or st.session_state.get('run-tab-phase')!=phase:
            st.session_state[tabkey]='Review' if ready or state['status']=='needs_clarification' else 'Activity'
            st.session_state['run-tab-phase']=phase
        if st.session_state.pop('run-show-package',False):st.session_state[tabkey]='Review'
        with st.container(key='run-status-card'):
            headline='Agent is working' if active else 'Waiting on you' if state['status']=='needs_clarification' else 'Package ready for your review' if ready else 'Promotional drafts blocked' if state['status']=='held' else 'Draft needs attention' if state['status']=='draft_incomplete' else 'Run stopped'
            tone='working' if active else 'warn' if state['status']=='needs_clarification' else 'good' if ready else 'hold'
            st.html('<div class="gate-heading"><span class="readiness '+tone+'">●</span><h3>'+headline+'</h3></div>')
            if active:
                st.write('The agent chooses its research actions. Every draft receives a required independent review.')
                if st.button('Stop run',key='run-stop'):run.stop(run_id);st.rerun()
                if not command and st.button('Continue run',key='run-continue'):command='execute'
            elif ready:
                if not state['review'].get('review_complete',False):st.warning('Review incomplete. Drafts remain available for human inspection.')
                st.write('Version '+str(state['package']['version'])+' · 5 drafts · Human approval pending · Nothing published')
                if st.button('Review package',key='run-review',type='primary'):
                    st.session_state[tabkey]='Review';st.rerun()
            elif state['status']=='needs_clarification':st.write('Answer the question in Review to continue this same run.')
            elif state['status']=='held':st.write('Marketing authorization is pending. No promotional drafts were created.')
            else:
                st.write('Version 2 is saved. Its independent review has not completed; your research and both draft versions are kept.' if recover else 'The run stopped. Completed research and any admitted drafts are kept.')
                a,b=st.columns(2)
                if recover and a.button('Review Version 2',key='run-recover-review',type='primary'):command='review_saved'
                elif run.session.can_retry_writer() and a.button('Try again',key='run-retry',type='primary'):command='retry'
                if b.button('Back to setup',key='run-setup',type='tertiary'):st.session_state['screen']='brief';st.rerun()
        activity,review,package=st.tabs(['Activity','Review','Package'],key=tabkey,default=st.session_state[tabkey],on_change='rerun')
        with activity:
            st.subheader('What the agent did');log=st.empty();log.html(timeline(state))
            if state.get('continuation_notice'):st.info(state['continuation_notice'])
        with review:
            if state['status']=='needs_clarification':
                with st.container(key='run-question'):
                    st.markdown('**How should the agent proceed while UK availability is unconfirmed?**')
                    st.write('Readiness does not confirm availability. Your answer cannot grant approval.')
                    with st.form('run-clarification-'+run_id):
                        choice=st.radio('Choose the next step',['Draft without availability wording','Recheck readiness','Stop this run'],key='run-choice',index=0)
                        answered=st.form_submit_button('Continue',type='primary')
                    if answered:command={'Draft without availability wording':'draft_without_availability','Recheck readiness':'recheck_readiness','Stop this run':'stop'}[choice]
            if state.get('review'):review_page(state,run=run,embedded=True)
            elif state['status']!='needs_clarification':st.info('Independent review will appear here when it completes. Saved drafts are under Package.')
        with package:
            st.subheader('Package');progress=st.empty();progress.html(package_progress(state))
            if state.get('package'):draft_outputs(state)
        if command is not None:
            try:
                with activity,st.status('Agent is working',expanded=True) as status:
                    def update(event,current):
                        status.update(label=LABELS.get((current.get('pending') or {}).get('name'),'Agent is working'))
                        log.html(timeline(current));progress.html(package_progress(current))
                    if command=='review_saved':run.review_saved(run_id,on_update=update)
                    elif command=='retry':run.retry_writer(run_id,on_update=update)
                    elif command=='execute':
                        if state['status']=='running':run.continue_run(run_id,on_update=update)
                        else:run.execute(run_id,on_update=update)
                    else:run.resume(run_id,command,on_update=update)
                st.rerun()
            except HarnessError:st.error('This action is unavailable for the current run, permission or remaining budget.')
        with st.expander('Technical details',expanded=False):
            st.caption('Writing voice: simulated brand channels · Neutral campaign brief · Policy v1')
            st.caption('Run '+run_id+' · Task calls '+str(state['turns']-state['review_attempts'])+'/12 · Required reviews '+str(state['review_attempts'])+'/4 · Evidence searches '+str(state['searches'])+'/4')
            st.json({'events':state['events'],'review':state.get('review'),'failure_history':state.get('failure_history'),
                'normalizations':state.get('normalizations'),'responses':run.capture()})
            if live:st.json(run.guard.summary())
            for result in state['evidence']:
                for item in result['records']:
                    p=item['evidence_payload'];st.markdown('**'+item['unit_id']+' · '+item['authority']+'**');st.text(p['primary_text'])
            st.caption('No LangSmith trace is available for this checkpoint.')
        if not live and st.button('Generate again · simulation',key='run-again-'+run_id):
            from launchlens.offline_ui_run import OfflineUIRun
            notes=state['user_notes'];scenario=run.scenario;policy=state.get('voice_policy_id')
            clear_run();st.session_state['offline_run']=OfflineUIRun(request,notes,scenario,voice_policy_id=policy,package=True)
            st.session_state['run-command']='execute';st.rerun()
        if st.button('Reset current run' if live else 'Reset demo',key='run-reset-'+run_id):
            clear_run();st.session_state['screen']='inventory';st.rerun()


def draft_outputs(state):
    from launchlens.package_content import FORMATS,LABELS,text_fields
    from launchlens.review_decisions import grouped_findings,highlighted,field_label
    groups=grouped_findings(state)
    tabs=st.tabs([LABELS[f] for f in FORMATS])
    for name,tab in zip(FORMATS,tabs):
        with tab:
            record=state['drafts'][name];st.subheader(LABELS[name]+' · Version '+str(record['version']))
            parts=[]
            for path,text in text_fields(record['draft']['content']):
                occurrences=[o for g in groups for o in g['occurrences'] if o['format']==name and o['content_field']==path]
                parts.extend(['<small class="review-field-label">'+escape(field_label(path))+'</small>','<p>'+highlighted(text,occurrences)+'</p>'])
            st.html('<article class="draft-copy">'+''.join(parts)+'</article>')
            for warning in record['validation']['editorial_warnings']:
                target=warning['target'];low=target.get('min');high=target.get('max')
                expected=f"{low}–{high}" if low is not None and high is not None else f"up to {high}" if high is not None else f"at least {low}"
                st.caption(f"Length: {warning['actual']} {warning['metric']}; suggested {expected}. Advisory only.")


def package_outputs(state):
    """Compatibility entry point; the package has one review screen."""
    review_page(state)


def review_page(state, *, run=None, saved=False, embedded=False):
    from launchlens.package_content import FORMATS, LABELS, text_fields
    from launchlens.review_decisions import (grouped_findings,decision_book,record_decision,
        effective_choice,unresolved_groups,safe_hints,highlighted,revision_feedback,CATEGORY_LABELS,field_label)
    groups=grouped_findings(state)
    key='run-review-decisions-'+state['run_id']
    book=decision_book(state,st.session_state.get(key));st.session_state[key]=book
    pending=unresolved_groups(groups,book)
    market='India' if state['request']['market_id']=='IN' else state['request']['market_id']
    if not embedded and st.button('‹ '+market+' run',key='review-back',type='tertiary'):
        if saved:st.session_state['screen']='inventory'
        else:st.session_state['run-show-package']=False
        st.rerun()
    if not embedded:st.title('Review '+market+' package')
    st.caption('Version '+str(state['package']['version'])+' · Independent review of this exact version')
    st.caption(f"{len(state['drafts'])} drafts · {len(pending)} need your attention · nothing published")
    st.caption('Live agent · Independent assessment · Human approval pending · Publishing disabled' if state['mode']=='live_package' else 'Mock assessment · Authored fixture drafts · Human approval pending · Publishing disabled')
    if saved:st.caption('Saved Reviewer assessment · No live call is running')
    stats=st.columns(3)
    stats[0].metric('Decisions left',len(pending))
    stats[1].metric('Need your clearance',sum(g['human_clearance_required'] for g in pending))
    stats[2].metric('Changes requested',sum(any(effective_choice(book,g,o)=='request_changes' for o in g['occurrences']) for g in groups))
    if not (state.get('review') or {}).get('review_complete',False):
        st.warning('Review incomplete. The drafts and scan matches remain available for human inspection.')
    unverified=(state.get('review') or {}).get('unverified_finding_count',0)
    if unverified:st.warning(f"{unverified} findings couldn't be verified. Valid findings are shown below.")
    unassessed=sum(len(f.get('unassessed_scan_hit_ids',[])) for f in (state.get('review') or {}).get('format_reviews',{}).values())
    if unassessed:st.info(f'{unassessed} scan matches still need human assessment.')
    st.subheader('Decide on flagged wording')
    st.caption('One phrase decision applies across the package. Open occurrences to treat a particular use differently. Keeping wording records your choice; it does not approve the package or override launch rules.')
    def choose(group,choice,occurrence=None):
        changed=record_decision(state,book,occurrence['id'] if occurrence else group['id'],choice,occurrence=occurrence is not None)
        # Protected local audit receipt only on explicit human interaction; never inference.
        from uuid import uuid4
        from launchlens.writer_comparison import ProtectedStore
        from launchlens.package_content import ROOT
        store=getattr(run,'store',None)
        if store is None and (saved or state['mode']=='live_package'):
            store=ProtectedStore(ROOT/'data/generated'/('human-review-'+uuid4().hex))
        if store is not None:store.write('human-decision-'+uuid4().hex+'.json',changed)
        st.session_state[key]=changed;st.rerun()
    for group in groups:
        if not group['needs_attention']:continue
        occurrences=group['occurrences'];formats=list(dict.fromkeys(LABELS[o['format']] for o in occurrences))
        with st.container(border=True,key='review-card-'+group['id']):
            st.markdown('### “'+group['phrase']+'”')
            st.caption(' / '.join(CATEGORY_LABELS.get(c,c) for c in group.get('categories',[group['category']]))+' · '+str(len(occurrences))+' '+('place' if len(occurrences)==1 else 'places')+' · '+', '.join(formats)+(' · Only you can clear this' if group['human_clearance_required'] else ''))
            reasons=list(dict.fromkeys(f['rationale'] for o in occurrences for f in o['findings']))
            st.write(reasons[0] if reasons else 'The scan found this wording. Its meaning and support need human inspection.')
            hints=safe_hints(group)
            from launchlens.package_content import reviewer_hint
            original_hints={reviewer_hint(f)[0] for o in occurrences for f in o['findings']}
            for hint in hints:st.write(('Reviewer hint (advisory): ' if hint in original_hints else 'Alternative wording (advisory): ')+hint)
            if not hints:st.caption('The Writer will rephrase it')
            with st.expander('Show '+str(len(occurrences))+' '+('occurrence' if len(occurrences)==1 else 'occurrences'),expanded=False):
                for occurrence in occurrences:
                    st.markdown('**'+LABELS[occurrence['format']]+' · '+field_label(occurrence['content_field'])+'**')
                    if occurrence['quote'] is not None:
                        st.html('<p class="review-context">'+highlighted(occurrence['context'],[occurrence])+'</p>')
                    for reason in list(dict.fromkeys(f['rationale'] for f in occurrence['findings'])):st.caption(reason)
                    choice=effective_choice(book,group,occurrence)
                    st.caption(('Will be rewritten in Version '+str(state['package']['version']+1)) if choice=='request_changes' and state['revision_attempts']==0 else 'Kept as is' if choice=='keep_wording' else 'Needs your decision')
                    if len(occurrences)>1:
                        a,b,_=st.columns([1,1,2])
                        if a.button('Change here only',key='change-'+occurrence['id']):choose(group,'request_changes',occurrence)
                        if b.button('Keep here only',key='keep-'+occurrence['id']):choose(group,'keep_wording',occurrence)
            a,b,_=st.columns([1,1,2])
            if a.button('Request changes',key='changes-'+group['id']):choose(group,'request_changes')
            if b.button('Keep wording',key='keep-'+group['id']):choose(group,'keep_wording')
            choices={effective_choice(book,group,o) for o in occurrences if o['needs_attention']}
            if choices=={'keep_wording'}:st.caption('Kept as is')
            elif choices=={'request_changes'}:st.caption('Will be rewritten in Version 2' if state['revision_attempts']==0 else 'Change requested; this run’s revision is already used')
            elif any(choices):st.caption('Your decisions: Mixed across occurrences; open the list to inspect.')
    cleared=[g for g in groups if not g['needs_attention']]
    with st.expander('Cleared by Reviewer ('+str(len(cleared))+')',expanded=False):
        for group in cleared:
            st.write('“'+group['phrase']+'” · '+str(len(group['occurrences']))+' places')
            for o in group['occurrences']:
                for f in o['findings']:st.caption(LABELS[o['format']]+' · '+f['rationale'])
        if not cleared:st.caption('No phrase groups were cleared in this assessment.')
    if not embedded:
        st.subheader('Drafts');draft_outputs(state)
    can_revise=run is not None and state['status']=='awaiting_human_review' and state['revision_attempts']==0 and state['turns']-state['review_attempts']+2<=12 and (getattr(run,'kind','demo')!='live' or run.guard.can_revise())
    if can_revise:
        version,sha=draft_identity(state)
        with st.form(f'run-feedback-{state["run_id"]}-{version}'):
            notes=st.text_area('Other notes for the revision (optional)',key=f'run-feedback-text-{state["run_id"]}-{version}',max_chars=1500)
            submitted=st.form_submit_button('Create Version 2',type='primary')
        st.caption('Your choices and notes apply across all five drafts. One revision per run, followed by a fresh review; hints are never applied automatically.')
        if submitted:
            try:
                feedback=revision_feedback(state,book,notes)
                if not feedback:st.error('Request changes on a phrase or enter feedback before requesting a revision.')
                else:
                    request_revision=getattr(run,'request_revision',run.session.request_revision)
                    request_revision(state['run_id'],feedback,draft_version=version,draft_sha256=sha)
                    st.session_state['run-command']='execute';st.session_state['run-show-package']=False;st.session_state['run-open-review-after-command']=True;st.rerun()
            except ValueError as e:st.error(str(e))
            except HarnessError:st.error('Revision is unavailable for this run or version.')
    elif saved:st.info('This saved assessment is available for wording decisions and inspection. Resuming its agent or making a paid revision is not connected here.')
    if embedded:return
    with st.expander('Technical details',expanded=False):
        st.caption('Writing voice: simulated brand channels · Neutral campaign brief · Policy v1')
        st.json({'run_id':state['run_id'],'review':state.get('review'),'human_wording_choices':book,
            'events':state.get('events'), 'failure_history':state.get('failure_history',[])})
        risk_scan_view(state)
        st.caption('No LangSmith trace is available for this checkpoint.')
    with st.expander('Supporting claims, citations and qualifications',expanded=False):
        for result in state['evidence']:
            for item in result['records']:
                p=item['evidence_payload'];st.markdown('**'+item['unit_id']+' · '+item['authority']+'**');st.text(p['primary_text'])
                st.json({'source_references':p['source_references'],'qualifications':p['segments']})
    if run is not None:
        if getattr(run,'kind','demo')!='live' and st.button('Generate again · simulation',key='run-again-'+state['run_id']):
            from launchlens.offline_ui_run import OfflineUIRun
            clear_run();st.session_state['offline_run']=OfflineUIRun(state['request'],state['user_notes'],run.scenario,voice_policy_id=state.get('voice_policy_id'),package=True)
            st.session_state['run-command']='execute';st.rerun()
        if st.button('Reset current run' if getattr(run,'kind','demo')=='live' else 'Reset demo',key='run-reset-'+state['run_id']):
            clear_run();st.session_state['screen']='inventory';st.rerun()


def risk_scan_view(state):
    from launchlens.package_content import risky_phrase_scan, package_value
    review=state.get('review') or {}
    hits=review.get('risk_scan') or risky_phrase_scan(package_value(state))
    st.markdown('**Risky phrases · Deterministic scan**')
    st.caption('Scan matches are prompts for contextual review, not factual verdicts. Cleared matches remain visible.')
    if not hits:st.write('No configured risky phrases matched.')
    for hit in hits:
        st.write(hit['format'].replace('_',' ').title()+' · '+hit['content_field']+' · '+hit['category'].replace('_',' '))
        st.text(hit['quote'])
        st.caption('Reviewer: '+hit.get('reviewer_disposition','unassessed').replace('_',' '))
