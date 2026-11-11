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
 'human_edit':'Saved your edits and re-scanned','revise_linkedin':'Revised the draft','request_clarification':'Paused for your input','finish':'Checked completion'}
SOURCES={'read_pmm_brief':'PMM / GTM brief · Notion','check_launch':'Launch calendar and readiness tracker · Notion',
 'search_product_evidence':'Product Brief · Pinecone evidence'}


def rounded_budget_display(value):
    """Format display copies only; accounting/receipts retain exact precision."""
    from decimal import Decimal, InvalidOperation
    if isinstance(value,dict):
        result={}
        for key,item in value.items():
            if isinstance(key,str) and key.endswith('_usd') and isinstance(item,(str,int,float)):
                try:result[key]=format(Decimal(str(item)),'.2f');continue
                except InvalidOperation:pass
            result[key]=rounded_budget_display(item)
        return result
    if isinstance(value,list):return [rounded_budget_display(v) for v in value]
    return value


def clear_run():
    run=st.session_state.pop('offline_run',None)
    if run is not None:run.reset()
    for key in list(st.session_state):
        if key.startswith('run-'):del st.session_state[key]


def short_why(value,name):
    defaults={'read_pmm_brief':'Use the campaign audience, positioning and tone.',
        'check_launch':'Check whether this market is ready for drafting.',
        'search_product_evidence':'Find supported product claims before writing.',
        'generate_package':'Write the campaign brief and channel drafts.',
        'review_package':'Check the current drafts before human review.',
        'revise_package':'Apply your wording choices and notes.'}
    if not value or 'agent omitted explanation' in value or value.startswith('Registry purpose'):
        value=defaults.get(name,'Complete the next permitted step for this package.')
    words=value.split()
    return ' '.join(words[:20])+('…' if len(words)>20 else '')


def activity_phases(state):
    """Presentation-only phases; original events, failures and receipts stay intact."""
    import re
    phases={};admitted=0;review_index=0
    failures={'failed_safely','replay_conflict','turn_limit'}
    successful={'completed','revalidated_saved_candidate'}
    for event in state['events']:
        name=event['action'];outcome=event['outcome'];target=admitted
        explicit=re.search(r'(?:review|revision)-v(\d+)',event.get('action_id',''))
        if name in {'generate_package','generate_linkedin'}:target=1
        elif name in {'revise_package','revise_linkedin'}:
            target=admitted if outcome=='no_op' else int(explicit[1]) if explicit else admitted+1
        elif name in {'review_package','review_linkedin'}:
            reviews=state.get('reviews',[])
            target=(int(explicit[1]) if explicit else
                reviews[review_index]['binding']['draft_version'] if outcome=='completed' and review_index<len(reviews) else admitted)
            if outcome=='completed':review_index+=1
        label='Version '+str(target) if target else 'Research'
        rows=phases.setdefault(label,[])
        title=LABELS.get(name,'Checked the next action')
        if name in {'generate_package','revise_package'} and outcome in successful:title='Wrote Version '+str(target)
        if name=='revision_no_op':title='Writer returned no changes'
        if name=='revise_package' and outcome=='no_op':title='No revision used'
        if name=='revise_package' and outcome=='duplicate_suppressed':title='Skipped an already-used revision request'
        if name=='review_package' and outcome=='completed':
            title='Re-check (requested by you)' if event.get('origin')=='owner_command' else 'Reviewer checked Version '+str(target)
        if name=='revise_package' and outcome=='completed' and event.get('origin')!='agent' and state.get('revision_feedback'):
            rows.append({'action':'human_feedback','title':'You reviewed and asked for changes','failed':False,
                'icon':'✓','why':'Your exact replacement was applied and sent for fresh review.' if event.get('writer_called') is False else 'Your recorded choices and notes were sent to the revision Writer.','source':None})
        if name=='automatic_refinement':
            title='Agent changed '+str(event['fixed_count'])+' flagged phrases' if event.get('fixed_count') else 'Agent refined '+str(event['protected_removed_count'])+' protected phrases' if event.get('protected_removed_count') else 'Agent refinement checked'
        if name=='revise_package' and outcome=='completed' and event.get('writer_called') is False:title='Applied your exact replacement'
        if name=='revise_package' and event.get('origin')=='agent' and outcome=='completed':title='Agent created Version '+str(target)
        failed=outcome in failures
        if failed:
            title="Couldn’t draft the package" if name=='generate_package' else 'A required action could not finish'
            why=("A factual heading was missing its evidence reference. Research is saved; no package was admitted." if (state.get('draft_failure') or {}).get('code')=='field_claim_coverage' else
                 "The Writer returned a format LaunchLens couldn’t accept. No package was admitted; the research is kept."
                 if name=='generate_package' and (state.get('draft_failure') or {}).get('stage')=='draft_validation' else
                 'This action failed. Completed research is kept; missing information does not grant permission.')
        else:why=event.get('why')
        row={'action':name,'outcome':outcome,'title':title,'why':short_why(why,name),
            'failed':failed,'icon':'!' if failed else '?' if name=='request_clarification' else '✓','source':SOURCES.get(name)}
        if outcome in successful:
            # Only a later success of the SAME action/version recovers its failures.
            recovered=[r for r in rows if r['action']==name and r.get('outcome')=='failed_safely']
            if recovered:
                rows[:]=[r for r in rows if r not in recovered]
                row['recovery_note']=('Passed after the heading-citation rule update; no rewrite.'
                    if outcome=='revalidated_saved_candidate' else
                    'Passed on a later attempt; earlier failure retained in Technical details.')
            if name in {'generate_package','generate_linkedin','revise_package','revise_linkedin'}:admitted=target
        rows.append(row)
    pending=state.get('pending')
    current=(state.get('package') or {}).get('version',target if state['events'] else 0)
    if state['status'] in {'failed','draft_incomplete','stopped'} and phases and phases[next(reversed(phases))][-1]['failed']:
        current=target
    if state['status']=='running' and pending:
        name=pending['name'];target=current
        if name in {'generate_package','generate_linkedin'}:target=1
        elif name in {'revise_package','revise_linkedin'}:target=current+1
        label='Version '+str(target) if target else 'Research';current=target
        phases.setdefault(label,[]).append({'action':name,'title':{'generate_package':'Writing the GTM package',
            'review_package':'Reviewing the package','revise_package':'Revising the package'}.get(name,'Preparing the next action'),
            'why':short_why(pending.get('why'),name),'failed':False,'icon':'…','source':None,'pending':True})
    current_label='Version '+str(current) if current else 'Research'
    return [{'label':label,'expanded':label==current_label,'steps':rows} for label,rows in phases.items()]


def timeline(state):
    phases=activity_phases(state)
    if not phases:return '<p class="run-muted">The agent has not executed an action yet.</p>'
    rendered=[]
    for phase in phases:
        rows=[]
        for row in phase['steps']:
            tone='working' if row.get('pending') else 'hold' if row['failed'] else 'good'
            rows.append('<div class="run-step"><span class="step-icon '+tone+'">'+row['icon']+'</span><div><strong>'+escape(row['title'])+'</strong><p>'+escape(row['why'])+'</p>'+
                ('<small class="recovery-note">'+escape(row['recovery_note'])+'</small>' if row.get('recovery_note') else '')+
                ('<small>Source: '+escape(row['source'])+'</small>' if row.get('source') else '')+'</div></div>')
        recovered=sum(bool(r.get('recovery_note')) for r in phase['steps'])
        detail=str(len(rows))+' steps'+(' · '+str(recovered)+' recovered' if recovered else '')
        rendered.append('<details class="activity-phase"'+(' open' if phase['expanded'] else '')+'><summary><strong>'+escape(phase['label'])+'</strong><span>'+detail+'</span></summary><div class="phase-steps">'+''.join(rows)+'</div></details>')
    return '<div class="run-timeline">'+''.join(rendered)+'</div>'


def review_findings(state):
    review=state.get('review')
    if not review:return []
    if 'format_reviews' in review:return [dict(f,format=name) for name,item in review['format_reviews'].items() for f in item['assessment']['findings']]
    return review.get('assessment',{}).get('findings',[])


def package_progress(state,*,approved=False):
    from launchlens.package_content import FORMATS,LABELS
    rows=[];pending=(state.get('pending') or {}).get('name')
    for name in FORMATS:
        record=state['drafts'].get(name)
        if record:
            status='Approved ✓' if approved else 'Review incomplete' if record.get('review_status')=='review_incomplete' else 'Reviewed ✓' if state.get('review') and record['review_status']=='reviewed_for_human' else 'Changes requested' if record['review_status']=='changes_requested' else 'Human clearance required' if record['review_status']=='human_clearance_required' else 'Drafted'
        elif state['status']=='needs_clarification':status='Paused'
        elif state['status'] in {'failed','held','stopped'}:status='Not drafted'
        elif pending=='generate_package':status='Writing…' # One atomic Writer call, no fake per-channel sequence.
        else:status='Queued'
        tone='good' if status in {'Reviewed ✓','Approved ✓'} else 'warn' if status in {'Paused','Changes requested','Review incomplete'} else 'working' if status=='Writing…' else 'unknown'
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
        planned=(state.get('launch') or {}).get('planned_launch_date')
        if not planned:
            row=st.session_state.get('inventory',{}).get('markets',{}).get(request['market_id'],{})
            planned=row.get('planned_launch_date')
        from launchlens.inventory_ui import date_label
        st.caption(market+' package · '+display['product_name']+' · Planned launch: '+(date_label(planned) if planned else 'Not verified'))
        st.caption('Live agent · Human approval pending · Nothing published' if live else 'Demo simulation · Scripted actions and authored fixture drafts/reviews · No live calls')
        command=st.session_state.pop('run-command',None)
        with st.container(key='run-status-card'):
            active=state['status'] in {'created','running'} or command is not None
            status='running' if active else state['status']
            ready=status=='awaiting_human_review' and bool(state.get('review'))
            headline='Agent is working' if active else 'Run interrupted' if state['status']=='interrupted' else 'Waiting on you' if status=='needs_clarification' else 'Package ready for your review' if ready else 'Promotional drafts blocked' if status=='held' else 'Draft needs attention' if status=='draft_incomplete' else 'Run interrupted' if state['status']=='interrupted' else 'Run stopped'
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
                st.write(state['clarification'])
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
                'draft_history':state['draft_history'],'reviews':state['reviews'],'responses':rounded_budget_display(run.capture())})
            st.caption('No LangSmith trace is available for this checkpoint.')
            if live:st.json(rounded_budget_display(run.guard.summary()))
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

def revision_usage(state):
    used=state.get('revision_attempts',0)
    agent=sum(e.get('action')=='revise_package' and e.get('origin')=='agent' and e.get('outcome') in {'completed','failed_safely'} for e in state.get('events',[]))
    owners=[('agent' if e.get('origin')=='agent' else 'you') for e in state.get('events',[]) if e.get('action')=='revise_package' and e.get('outcome') in {'completed','failed_safely'}][:used]
    owners+=['you']*max(0,used-len(owners))
    detail=' · by '+owners[0] if len(owners)==1 else ''.join(' · '+str(i+1)+': '+owner for i,owner in enumerate(owners))
    return str(used)+' of 3 used'+detail


def run_summary_meta(state,run):
    version=(state.get('package') or {}).get('version')
    if getattr(run,'kind','demo')=='live':
        from decimal import Decimal
        remaining=run.guard.standing.read()['remaining_usd'] if run.guard.standing else str(Decimal(run.guard.permission['aggregate_ceiling_usd'])-run.guard.cost)
        budget='$'+format(Decimal(remaining),'.2f')
    else:budget='No model spending'
    return ('<dl class="run-summary-meta"><div><dt>Version</dt><dd>'+str(version if version else 'Not drafted')+
        '</dd></div><div><dt>Revisions used</dt><dd>'+escape(revision_usage(state))+'</dd></div>'+
        '<div><dt>Budget left</dt><dd>'+escape(budget)+'</dd></div></dl>')


def run_page(display):
    run=st.session_state.get('offline_run')
    if run is None or not getattr(run,'package',False):return _legacy_run_page(display)
    state=run.snapshot();request=state['request'];run_id=state['run_id'];live=getattr(run,'kind','demo')=='live'
    market='India' if request['market_id']=='IN' else request['market_id']
    from launchlens.package_presentation import effective_approval,restored_decisions,restored_approval
    from launchlens.review_decisions import decision_book
    decision_key='run-review-decisions-'+run_id
    if decision_key not in st.session_state and state.get('review'):
        recovered=restored_decisions(state,getattr(run,'store',None))
        if recovered is not None:st.session_state[decision_key]=recovered
    if state.get('package') and state.get('review') and 'run-internal-approval-'+run_id not in st.session_state:
        receipt=restored_approval(state,decision_book(state,st.session_state.get(decision_key)),getattr(run,'store',None))
        if receipt is not None:st.session_state['run-internal-approval-'+run_id]=receipt
    approved=effective_approval(state,store=getattr(run,'store',None),book=st.session_state.get(decision_key),record=st.session_state.get('run-internal-approval-'+run_id))
    with st.container(key='agent-run'):
        if st.button(f'‹ {market} package setup',key='run-back',type='tertiary'):
            st.session_state['selected_request']=deepcopy(request);st.session_state['screen']='brief';st.rerun()
        from launchlens.inventory_ui import date_label
        planned=(state.get('launch') or {}).get('planned_launch_date') or st.session_state.get('inventory',{}).get('markets',{}).get(request['market_id'],{}).get('planned_launch_date')
        st.caption(market+' package · '+display['product_name']+' · Planned launch: '+(date_label(planned) if planned else 'Not verified'))
        command=st.session_state.pop('run-command',None)
        read_only=getattr(run,'read_only',False)
        active=state['status'] in {'created','running'} or command is not None or getattr(run,'watching_worker',False)
        ready=not read_only and not active and state['status']=='awaiting_human_review' and bool(state.get('review'))
        recover=not active and callable(getattr(run,'can_review_saved',None)) and run.can_review_saved()
        tabkey='run-tabs-'+run_id
        phase=('working' if active else state['status'],(state.get('package') or {}).get('version'))
        if tabkey not in st.session_state or st.session_state.get('run-tab-phase')!=phase:
            st.session_state[tabkey]='Review' if ready or state['status']=='needs_clarification' else 'Activity'
            st.session_state['run-tab-phase']=phase
        if st.session_state.pop('run-show-package',False):st.session_state[tabkey]='Review'
        left,right=st.container(key='run-columns').columns([.65,.35],gap='small')
        with right, st.container(key='run-summary'):
            headline='Agent is working' if active else 'Waiting on you' if state['status']=='needs_clarification' else 'Package approved for internal use' if approved else ('Version '+str(state['package']['version'])+' ready for your review' if state['package']['version']>1 else 'Package ready for your review') if ready else 'Promotional drafts blocked' if state['status']=='held' else 'Draft needs attention' if state['status']=='draft_incomplete' else 'Run interrupted' if state['status']=='interrupted' else 'Run stopped'
            tone='working' if active else 'warn' if state['status']=='needs_clarification' else 'good' if ready else 'hold'
            st.html('<div class="gate-heading"><span class="readiness '+tone+'">●</span><h3>'+headline+'</h3></div>')
            if active:
                st.write('The agent chooses its research actions. Every draft receives a required independent review.')
                if read_only:
                    st.caption('Reattached to the saved run. Its worker is still active; no work will be started twice.')
                    if st.button('Check progress',key='run-check-progress'):
                        st.session_state.pop('offline_run',None);st.rerun()
                else:
                    if st.button('Stop run',key='run-stop'):run.stop(run_id);st.rerun()
                    if not command and st.button('Continue run',key='run-continue'):command='execute'
            elif ready:
                st.write(('Review incomplete · Human inspection required' if not state['review'].get('review_complete',False) else 'Approved for internal use' if approved else 'Human approval pending')+' · Nothing published')
                if not approved and st.button('Review package',key='run-review',type='tertiary',width='stretch'):
                    st.session_state[tabkey]='Review';st.rerun()
            elif state['status']=='needs_clarification':st.write('Answer the question in Review to continue this same run.')
            elif state['status']=='held':st.write('Marketing authorization is pending. No promotional drafts were created.')
            else:
                st.write('A factual heading had no supporting citation. Research is saved; no package was admitted.' if (state.get('draft_failure') or {}).get('code')=='field_claim_coverage' else 'The current version is saved. Its independent review has not completed; your research and earlier versions are kept.' if recover else 'The run stopped. Completed research and any admitted drafts are kept.')
                a,b=st.columns(2)
                if recover and a.button('Review Version '+str(state['package']['version']),key='run-recover-review',type='primary'):command='review_saved'
                elif run.session.can_retry_writer() and a.button('Try again',key='run-retry',type='primary'):command='retry'
                if b.button('Back to setup',key='run-setup',type='tertiary'):st.session_state['screen']='brief';st.rerun()
            if state.get('continuation_notice'):st.caption(state['continuation_notice'])
            summary=st.empty();summary.html(run_summary_meta(state,run))
            st.markdown('**Deliverables**')
            summary_progress=st.empty();summary_progress.html(package_progress(state,approved=approved))
            if ready:
                package_approval(state,run,compact=True)
                book=decision_book(state,st.session_state.get(decision_key))
                if not approved:
                    st.caption('Optional next version')
                    notes=st.session_state.get(f'run-feedback-text-{run_id}-{state["package"]["version"]}','')
                    revision_action(state,run,book,notes)
            if st.button('Archive & start fresh',key='run-archive',disabled=active,help='Stop the run first' if active else 'Archive this market package without changing its evidence.'):
                from launchlens.inventory_ui import open_archive,simulation_record
                if live:
                    from launchlens.run_archive import market_run
                    record=market_run(request['market_id'])
                    if record is not None:open_archive(record)
                    else:st.error('The saved run reference is unavailable. Nothing was archived.')
                else:open_archive(simulation_record(run))
        with left:
            activity,review,package=st.tabs(['Activity','Review','Package'],key=tabkey,default=st.session_state[tabkey],on_change='rerun')
            with activity:
                st.subheader('What the agent did');log=st.empty();log.html(timeline(state))
                if state.get('continuation_notice'):st.info(state['continuation_notice'])
            with review:
                if state['status']=='needs_clarification':
                    with st.container(key='run-question'):
                        st.write(state['clarification'])
                        st.write('Readiness does not confirm availability. Your answer cannot grant approval.')
                        with st.form('run-clarification-'+run_id):
                            choice=st.radio('Choose the next step',['Draft without availability wording','Recheck readiness','Stop this run'],key='run-choice',index=0)
                            answered=st.form_submit_button('Continue',type='primary')
                        if answered:command={'Draft without availability wording':'draft_without_availability','Recheck readiness':'recheck_readiness','Stop this run':'stop'}[choice]
                if read_only:st.info('Saved review is read-only while execution is active or interrupted. Saved drafts remain available under Package; technical details retain the assessment.')
                elif state.get('review'):review_page(state,run=run,embedded=True)
                elif state['status']!='needs_clarification':st.info('Independent review will appear here when it completes. Saved drafts are under Package.')
            with package:
                progress=st.empty()
                if state.get('package') and (read_only or not state.get('review')):draft_outputs(state)
                elif state.get('package'):package_panel(state,run,controls=False)
                else:st.info('Drafts will appear here when writing completes. Deliverable progress is shown in the run panel.')
        if command is not None:
            try:
                with activity,st.status('Agent is working',expanded=True) as status:
                    def update(event,current):
                        status.update(label=LABELS.get((current.get('pending') or {}).get('name'),'Agent is working'))
                        log.html(timeline(current));summary_progress.html(package_progress(current));summary.html(run_summary_meta(current,run))
                    if command=='review_saved':run.review_saved(run_id,on_update=update)
                    elif command=='retry':run.retry_writer(run_id,on_update=update)
                    elif command=='execute':
                        if state['status']=='running':run.continue_run(run_id,on_update=update)
                        else:run.execute(run_id,on_update=update)
                    else:run.resume(run_id,command,on_update=update)
                st.rerun()
            except HarnessError:st.error('This action is unavailable for the current run, permission or remaining budget.')
        with left:
            with st.expander('Technical details',expanded=False):
                st.caption('Live agent · Independent assessment' if live else 'Demo simulation · Scripted actions, authored fixture drafts and mock assessments · No live calls')
                st.caption('Writing voice: simulated brand channels · Neutral campaign brief · Policy v1')
                st.caption('Run '+run_id+' · Task calls '+str(state['turns']-state['review_attempts']-state['revision_attempts'])+'/12 · Revisions '+str(state['revision_attempts'])+'/3 · Required reviews '+str(state['review_attempts'])+' · Evidence searches '+str(state['searches'])+'/4')
                st.json({'events':state['events'],'review':state.get('review'),'failure_history':state.get('failure_history'),
                    'normalizations':state.get('normalizations'),'responses':rounded_budget_display(run.capture())})
                if live:st.json(rounded_budget_display(run.guard.summary()))
                for result in state['evidence']:
                    for item in result['records']:
                        p=item['evidence_payload'];st.markdown('**'+item['unit_id']+' · '+item['authority']+'**');st.text(p['primary_text'])
                st.caption('No LangSmith trace is available for this checkpoint.')
            if not live and st.button('Generate again · simulation',key='run-again-'+run_id):
                from launchlens.offline_ui_run import OfflineUIRun
                notes=state['user_notes'];scenario=run.scenario;policy=state.get('voice_policy_id')
                clear_run();st.session_state['offline_run']=OfflineUIRun(request,notes,scenario,voice_policy_id=policy,package=True)
                st.session_state['run-command']='execute';st.rerun()



@st.dialog('Full draft',width='large',on_dismiss='rerun')
def full_draft_dialog(state,name,focus=None):
    from launchlens.package_content import LABELS
    from launchlens.package_presentation import draft_modal_document
    record=state['drafts'][name]
    st.subheader(LABELS[name]+' · Version '+str(record['version']))
    st.caption('Highlighted wording is shown in context. Close this preview to return to your review.')
    st.iframe(draft_modal_document(state,name,focus=focus),height=520,alt=LABELS[name]+' full draft with highlights')


def draft_outputs(state, *, selected=None):
    from launchlens.package_content import FORMATS,LABELS
    from launchlens.package_presentation import draft_markup
    names=FORMATS if selected is None else (selected,)
    tabs=st.tabs([LABELS[f] for f in names]) if selected is None else [st.container()]
    for name,tab in zip(names,tabs):
        with tab:
            record=state['drafts'][name];st.subheader(LABELS[name]+' · Version '+str(record['version']))
            st.html(draft_markup(state,name))
            for warning in record['validation']['editorial_warnings']:
                st.caption(measurement_caption(warning))


def package_outputs(state):
    """Compatibility entry point; the package has one review screen."""
    review_page(state)


def review_page(state, *, run=None, saved=False, embedded=False):
    from launchlens.package_content import FORMATS,LABELS
    from launchlens.review_decisions import (grouped_findings,decision_book,record_decision,
        effective_choice,safe_hints,highlighted,revision_feedback,CATEGORY_LABELS,field_label)
    from launchlens.package_presentation import progress,must_decide,choice_label,current_review_matches,card_reason
    if run is not None:state=run.snapshot()
    from launchlens.package_content import current_revision_resolution
    resolution=current_revision_resolution(state)
    if resolution:
        if resolution.get('no_op'):st.info('Writer returned no text changes. The current version is preserved and no revision was used. Actual model usage remains spent.')
        requests=resolution['requests'];unresolved=[r for r in requests if r['status']=='unresolved']
        changed=len(requests)-len(unresolved)
        st.caption(f'{changed} requested occurrences changed wording · {len(unresolved)} unresolved. Fresh review checks meaning and new claims.')
        if unresolved:st.warning('Some requested rephrases remain unchanged. They are still listed below even if the Reviewer omitted them.')
        if requests:
            with st.expander('Requested wording results'):
                for request in requests:
                    label='Unresolved' if request['status']=='unresolved' else 'Wording changed; meaning requires review'
                    st.write(label+' · '+LABELS[request['format']]+' · '+field_label(request['content_field'])+' · “'+request['quote']+'”')
    if not current_review_matches(state):
        st.info('Version '+str(state['package']['version'])+' is current. Its review is not ready yet; no earlier-version decisions are shown.')
        return
    all_groups=grouped_findings(state);groups=[g for g in all_groups if must_decide(g)]
    optional=[g for g in all_groups if g['needs_attention'] and not must_decide(g)]
    key='run-review-decisions-'+state['run_id'];book=decision_book(state,st.session_state.get(key));st.session_state[key]=book
    position='run-review-position-'+state['run_id'];identity='run-review-position-binding-'+state['run_id']
    if st.session_state.get(identity)!=book['binding']:
        st.session_state[position]=next((i for i,g in enumerate(groups) if any(o['needs_attention'] and not effective_choice(book,g,o) for o in g['occurrences'])),len(groups));st.session_state[identity]=book['binding']
    index=min(max(st.session_state.get(position,0),0),len(groups));stats=progress(groups,book)
    if not embedded:
        market='India' if state['request']['market_id']=='IN' else state['request']['market_id']
        if st.button('‹ '+market+' run',key='review-back',type='tertiary'):
            if saved:st.session_state['screen']='inventory'
            else:st.session_state['run-show-package']=False
            st.rerun()
        st.caption('Review '+market+' package')
    st.caption(f"Version {state['package']['version']} · {stats['decided']} of {stats['total']} decided · {stats['must_left']} must-decide left")
    if saved:st.caption('Saved assessment · No agent execution connected')
    unverified=state['review'].get('unverified_finding_count',0)
    if state['review'].get('no_new_model_review'):st.caption('Human edits saved · Re-scanned; no new AI review.')
    if unverified:st.warning(f"{unverified} findings couldn't be verified. Valid findings are shown below.")
    dots=[]
    for i,g in enumerate(groups):
        label=choice_label(g,book);tone='kept' if label=='Kept as is' else 'changed' if label!='Not decided' else 'required' if must_decide(g) else 'pending'
        dots.append('<span class="decision-dot '+tone+(' current' if i==index else '')+'" title="'+escape(g['phrase']+': '+label,quote=True)+'"></span>')
    st.html('<div class="decision-dots" role="img" aria-label="'+str(stats['decided'])+' of '+str(stats['total'])+' decided">'+''.join(dots)+'</div>')
    def move(n):st.session_state[position]=n;st.rerun()
    def choose(group,choice,occurrence=None,suggestion=None):
        changed=record_decision(state,book,occurrence['id'] if occurrence else group['id'],choice,occurrence=occurrence is not None,suggestion=suggestion)
        from uuid import uuid4
        store=getattr(run,'store',None)
        if store is None and (saved or state['mode']=='live_package'):
            from launchlens.writer_comparison import ProtectedStore
            from launchlens.package_content import ROOT
            store=ProtectedStore(ROOT/'data/generated'/('human-review-'+uuid4().hex))
        if store is not None:store.write('human-decision-'+uuid4().hex+'.json',changed)
        from launchlens.observability import human_event
        human_event(state,"human review decision",{"choice":choice,"phrase":group['phrase'],"replacement":suggestion},store=store)
        st.session_state[key]=changed
        if occurrence is None:st.session_state[position]=index+1
        st.rerun()
    if index<len(groups):
        group=groups[index];occurrences=group['occurrences'];first=occurrences[0]
        with st.container(key='review-card-'+group['id']):
            st.html('<div class="decision-card-top"><span class="category-pill">'+escape(' / '.join(CATEGORY_LABELS.get(c,c) for c in group.get('categories',[group['category']])))+'</span><span>Card '+str(index+1)+' of '+str(len(groups))+'</span></div>')
            st.markdown('### “'+group['phrase']+'”')
            if must_decide(group):st.caption('Must decide · Your choice does not change evidence or launch permission')
            context=first['context'];start=first['start'];end=first['end']
            if isinstance(start,int):
                from launchlens.review_decisions import sentence_bounds
                lo,hi=sentence_bounds(context,start,end);excerpt=context[lo:hi]
                marked=highlighted(excerpt,[dict(first,start=start-lo,end=end-lo)])
                st.html('<div class="decision-context"><small>'+escape(LABELS[first['format']]+' · '+field_label(first['content_field']))+'</small><p>'+marked+'</p></div>')
            if len(occurrences)>1:
                st.caption('Also in '+str(len(occurrences)-1)+' other '+('place' if len(occurrences)==2 else 'places')+' · Your choice applies to all '+str(len(occurrences)))
            if st.button('See full draft ›',key='full-draft-'+group['id'],type='tertiary'):full_draft_dialog(state,first['format'],first)
            st.write('**Why:** '+card_reason(group,demo=state['mode']!='live_package'))
            hints=safe_hints(group);hint=hints[0] if hints else None
            if first.get('new_scan_match'):st.caption('New scan match · Not assessed in the saved AI review')
            if hint:
                from launchlens.review_decisions import replacement_preview
                preview=replacement_preview(first,hint)
                st.html('<div class="suggestion-box"><small>Phrase replacement · advisory</small><p><del>'+escape(first['quote'] or group['phrase'])+'</del> → <ins>'+escape(hint)+'</ins></p><small>Sentence after the change</small><p>'+escape(preview)+'</p></div>')
            else:st.caption('No scan-safe suggestion is available. Edit the wording yourself.' if state['revision_attempts']>=3 else 'No scan-safe suggestion is available. The Writer can rephrase it within the existing evidence restrictions.')
            final=state['revision_attempts']>=3
            if final:
                edit_key='manual-edit-'+group['id']
                keep,edit=st.columns(2)
                if keep.button('Keep wording',key='keep-'+group['id']):choose(group,'keep_wording')
                if edit.button('Edit it myself',key=edit_key,disabled=run is None or saved):st.session_state[edit_key+'-open']=True
                if st.session_state.get(edit_key+'-open'):
                    changes=[];seen=set()
                    for occurrence in occurrences:
                        field=(occurrence['format'],occurrence['content_field'])
                        if field in seen or field[1]=='$format':continue
                        seen.add(field)
                        text=st.text_area(LABELS[field[0]]+' · '+field_label(field[1]),value=occurrence['context'],
                            key='human-edit-text-'+book['binding']+'-'+field[0]+'-'+field[1],max_chars=20000)
                        if text!=occurrence['context']:changes.append({'format':field[0],'content_field':field[1],'text':text})
                    st.caption('Save updates the current version and scans it again. New scan matches still need your decision; no AI review is implied.')
                    if st.button('Save edits and re-scan',key='save-'+group['id'],type='primary',disabled=not changes):
                        try:
                            after=run.edit_current_fields(state['run_id'],changes,draft_version=state['package']['version'],draft_sha256=state['package']['package_sha256'])
                            from launchlens.review_decisions import carry_unchanged_decisions
                            changed_book=carry_unchanged_decisions(state,after,book)
                            store=getattr(run,'store',None)
                            if store is not None:
                                from uuid import uuid4
                                store.write('human-decision-'+uuid4().hex+'.json',changed_book)
                            st.session_state[key]=changed_book
                            st.session_state['run-approval-check-'+state['run_id']+'-'+str(state['package']['version'])]=False
                            st.session_state.pop('run-internal-approval-'+state['run_id'],None)
                            st.session_state[edit_key+'-open']=False;st.rerun()
                        except (ValueError,HarnessError):st.error('Edit not saved. Preserve required evidence, citations, CTA and launch restrictions; then try again.')
            else:
                cols=st.columns([1.15,1.6,1])
                if cols[0].button('Use “'+hint+'”' if hint else 'Use suggestion',key='use-'+group['id'],type='primary',disabled=hint is None or run is None or saved or (getattr(run,'kind','demo')=='live' and not run.guard.can_revise(writer_required=False))):choose(group,'request_changes',suggestion=hint)
                if cols[1].button('Let the Writer rephrase',key='changes-'+group['id']):choose(group,'request_changes')
                if cols[2].button('Keep wording',key='keep-'+group['id']):choose(group,'keep_wording')
                if choice_label(group,book)!='Not decided':st.caption('Your choice: '+choice_label(group,book))
                if len(occurrences)>1:
                    with st.expander('Inspect '+str(len(occurrences))+' places / override one occurrence',expanded=False):
                        for occurrence in occurrences:
                            st.markdown('**'+LABELS[occurrence['format']]+' · '+field_label(occurrence['content_field'])+'**')
                            st.html('<p class="review-context">'+highlighted(occurrence['context'],[occurrence])+'</p>')
                            if hint:st.caption('After the phrase replacement: '+replacement_preview(occurrence,hint))
                            a,b=st.columns(2)
                            if a.button('Change here only',key='change-'+occurrence['id']):choose(group,'request_changes',occurrence)
                            if b.button('Keep here only',key='keep-'+occurrence['id']):choose(group,'keep_wording',occurrence)
        a,b,c=st.columns([1,2,1])
        if a.button('‹ Previous',key='review-previous',disabled=index==0):move(index-1)
        b.caption('Card '+str(index+1)+' of '+str(len(groups)))
        if c.button('Next ›',key='review-next'):move(index+1)
        if st.button('Review choices',key='review-summary',type='tertiary'):move(len(groups))
        st.caption('Keep wording moves to the next card. Saved edits update the current draft; nothing is published.' if state['revision_attempts']>=3 else 'Choosing an option moves to the next card. Requested changes apply when you create the next version; nothing is published.')
    else:
        with st.container(key='review-end-card'):
            st.subheader("You’re through the stack")
            st.write(f"{stats['rewrite']} to rewrite · {stats['kept']} kept · {stats['skipped']} not decided")
            for i,group in enumerate(groups):
                if st.button('“'+group['phrase']+'” · '+choice_label(group,book),key='recap-'+group['id'],type='tertiary',width='stretch'):move(i)
            if not groups:st.write('No phrase decisions are required by the current assessment.')
            version,sha=draft_identity(state)
            notes=st.text_area('Anything else for Version '+str(version+1)+'? (optional)',key=f'run-feedback-text-{state["run_id"]}-{version}',max_chars=1500,placeholder='Guidance for selected fields only; notes cannot add other fields') if state['revision_attempts']<3 else ''
            if not embedded and not state.get('human_accepted'):revision_action(state,run,book,notes,saved=saved,primary=True)
            if st.button('Back to cards',key='review-back-cards',disabled=not groups):move(0)
            st.caption('Use suggestion applies the exact text and requests fresh review without a Writer call. Rephrase choices apply when you create another version.')
    if optional:
        with st.expander(str(len(optional))+' optional suggestions ›',expanded=False):
            st.caption('Optional only. These never require a choice or block approval.')
            for group in optional:
                first=group['occurrences'][0]
                st.markdown('**“'+group['phrase']+'”**')
                st.caption(LABELS[first['format']]+' · '+field_label(first['content_field'])+
                    (' · Also in '+str(len(group['occurrences'])-1)+' places' if len(group['occurrences'])>1 else ''))
                st.write(card_reason(group,demo=state['mode']!='live_package'))
                hints=safe_hints(group)
                if hints:
                    st.caption('Reviewer hint (advisory): '+hints[0])
                    from launchlens.review_decisions import replacement_preview
                    preview=replacement_preview(first,hints[0])
                    st.html('<div class="suggestion-box"><small>Sentence after the change</small><p>'+escape(preview)+'</p></div>')
                    if state['revision_attempts']<3 and st.button('Use “'+hints[0]+'”',key='use-'+group['id'],disabled=run is None or saved or (getattr(run,'kind','demo')=='live' and not run.guard.can_revise(writer_required=False))):
                        choose(group,'request_changes',suggestion=hints[0])
                if st.button('See full draft ›',key='optional-full-'+group['id'],type='tertiary'):full_draft_dialog(state,first['format'],first)
                a,b=st.columns(2)
                if state['revision_attempts']<3 and a.button('Request optional change',key='optional-change-'+group['id']):
                    changed=record_decision(state,book,group['id'],'request_changes')
                    from uuid import uuid4
                    store=getattr(run,'store',None)
                    if store is not None:store.write('human-decision-'+uuid4().hex+'.json',changed)
                    st.session_state[key]=changed;st.rerun()
                if b.button('Keep wording',key='optional-keep-'+group['id']):
                    changed=record_decision(state,book,group['id'],'keep_wording')
                    from uuid import uuid4
                    store=getattr(run,'store',None)
                    if store is not None:store.write('human-decision-'+uuid4().hex+'.json',changed)
                    st.session_state[key]=changed;st.rerun()
                if choice_label(group,book)!='Not decided':st.caption('Your choice: '+choice_label(group,book))
    if not embedded:
        with st.expander('Technical details',expanded=False):st.json({'review':state['review'],'wording_choices':book})


def revision_action(state,run,book,notes='',*,saved=False,primary=False):
    """Existing explicit revision command; rendering never starts a model call."""
    from launchlens.review_decisions import grouped_findings,revision_feedback,effective_choice
    from launchlens.package_presentation import progress
    version,sha=draft_identity(state);stats=progress(grouped_findings(state),book)
    eligible=run is not None and not saved and state['status']=='awaiting_human_review' and state.get('revision_request') is None and state['revision_attempts']<3
    if eligible and getattr(run,'kind','demo')=='live':
        replacements=book.get('replacements',{})
        writer_required=any(effective_choice(book,g,o)=='request_changes' and
            not replacements.get(o['id'],replacements.get(g['id'])) for g in grouped_findings(state) for o in g['occurrences'])
        eligible=run.guard.can_revise(writer_required=writer_required)
    submitted=st.button('Create Version '+str(version+1) if state['revision_attempts']<3 else 'Revision limit reached',key='create-next-version',type='primary' if primary else 'secondary',disabled=not eligible or stats['must_left']>0,width='stretch')
    if submitted:
        try:
            feedback=revision_feedback(state,book,notes)
            if not feedback:st.error('Select wording to change before creating the next version.')
            elif not any(effective_choice(book,g,o)=='request_changes' for g in grouped_findings(state) for o in g['occurrences']):
                st.error('Choose at least one phrase to change. Notes guide only the selected fields.')
            else:
                request_revision=getattr(run,'request_revision',run.session.request_revision)
                request_revision(state['run_id'],feedback,draft_version=version,draft_sha256=sha)
                history=st.session_state.setdefault('run-review-history-'+state['run_id'],{})
                history[version]={'book':deepcopy(book),'stats':stats,'notes':notes}
                store=getattr(run,'store',None)
                if store is not None:
                    from uuid import uuid4
                    store.write('human-revision-choices-'+uuid4().hex+'.json',history[version])
                st.session_state['run-command']='execute';st.session_state['run-show-package']=False;st.rerun()
        except ValueError as error:st.error(str(error))
        except HarnessError:st.error('Revision is unavailable for this run or version.')
    if stats['must_left']:st.caption('Complete required wording choices before requesting a rewrite. You can still approve the existing text as-is.')
    if state['revision_attempts']>=3:st.info('All 3 revisions have been used. You can still approve the current version as-is.')
    elif not eligible:st.caption('Another version requires the existing authorization and enough budget for writing and review.')


def measurement_caption(warning):
    """PMM-facing advisory text; schema paths stay out of the main UI."""
    target=warning['target'];low=target.get('min');high=target.get('max')
    expected=f"{low}–{high}" if low is not None and high is not None else f"≤{high}" if high is not None else f"≥{low}"
    fields=warning['fields'];metric=warning['metric'];field=fields[0] if len(fields)==1 else None
    label={'subject':'Subject','preview_text':'Preview','body':'Body'}.get(field,'Draft')
    if field and field.startswith('concepts.'):
        parts=field.split('.');label='Ad '+str(int(parts[1])+1)
        if len(parts)>2:label+=' '+{'cta':'CTA'}.get(parts[2],parts[2])
    if metric=='exclamation_marks':label=('Exclamation marks' if label=='Draft' else label+' exclamation marks');unit=''
    else:unit=' '+metric
    return f"Advisory · {label}: {warning['actual']}{unit}; target {expected}. Does not block approval."


def package_panel(state,run,*,controls=True):
    from launchlens.package_content import FORMATS,LABELS,text_fields
    from launchlens.package_presentation import (approval_issues,
        approve_current_version,current_wording_book,approval_matches,markdown_package,SIMULATION_LABEL)
    from launchlens.review_decisions import grouped_findings,decision_book,effective_choice
    from launchlens.linkedin_drafting import digest
    run_id=state['run_id'];version=state['package']['version'];book=decision_book(state,st.session_state.get('run-review-decisions-'+run_id))
    groups=grouped_findings(state);approval_key='run-internal-approval-'+run_id
    approved=approval_matches(state,book,st.session_state.get(approval_key))
    with st.container(key='package-deliverables'):
        st.subheader('Deliverables · Version '+str(version))
        st.caption('Human-edited current version · Re-scanned; no new AI review.' if state['review'].get('no_new_model_review') else 'Reviewer checked Version '+str(version) if state['review'].get('binding',{}).get('draft_version')==version else 'Current-version assessment')
        if not state['package'].get('tone_policy_sha256'):
            st.caption('Tone labels show current guidance. This saved package retains its original policy and approval.')
        for name in FORMATS:
            relevant=[g for g in groups if any(o['format']==name and o['needs_attention'] and effective_choice(book,g,o)!='keep_wording' for o in g['occurrences'])]
            record=state['drafts'][name]
            status='Review incomplete' if not state['review'].get('review_complete') else str(len(relevant))+' need attention' if relevant else 'Reviewed ✓'
            cols=st.columns([2,1.6,.5])
            cols[0].write(LABELS[name]);cols[1].caption(status)
            from launchlens.voice_policy import load_tone_policy
            tone_policy=load_tone_policy(state['package'].get('tone_policy_sha256'))
            cols[0].caption(tone_policy['format_specs'][name]['label'])
            for warning in record['validation']['editorial_warnings']:
                st.caption(measurement_caption(warning))
            if cols[2].button('View',key='package-view-'+name,type='tertiary'):full_draft_dialog(state,name)
    if controls:package_approval(state,run)


def package_approval(state,run,*,compact=False):
    from launchlens.package_presentation import (approval_issues,approve_current_version,current_wording_book,
        approval_matches,markdown_package,SIMULATION_LABEL)
    from launchlens.review_decisions import decision_book
    from launchlens.linkedin_drafting import digest
    run_id=state['run_id'];version=state['package']['version']
    book=decision_book(state,st.session_state.get('run-review-decisions-'+run_id))
    approval_key='run-internal-approval-'+run_id
    approved=approval_matches(state,book,st.session_state.get(approval_key))
    with st.container(key='package-approval'):
        if not (compact and approved):st.subheader('Approved' if approved else 'Approve as-is')
        if not compact:st.caption('Approve this version as it stands, including flagged wording. This replaces earlier wording-change requests; no rewrite is required.')
        if approved:
            if compact:st.caption('Approval recorded for Version '+str(version))
            else:
                st.success('Approved for internal use · Nothing published')
                st.caption('Your approval of Version '+str(version)+' is recorded. No further wording review is required for this version.')
        else:
            checked=st.checkbox("I’ve reviewed Version "+str(version)+', accept its current wording including flagged phrases, and approve it for internal use',
                key='run-approval-as-is-'+run_id+'-'+str(version)+'-'+digest(book['binding'])[:12])
            try:issues=approval_issues(state,current_wording_book(state,book))
            except ValueError:issues=['Wording choices belong to another review. Reopen the current version.']
            if st.button('Approve package',key='approve-package',type='primary',disabled=not checked or bool(issues) or approved):
                accepted,record=approve_current_version(state,book,checked)
                store=getattr(run,'store',None)
                if store is not None:
                    from uuid import uuid4
                    store.write('human-decision-'+uuid4().hex+'.json',accepted)
                    store.write('human-internal-approval-'+uuid4().hex+'.json',record)
                st.session_state['run-review-decisions-'+run_id]=accepted
                from launchlens.observability import human_event
                human_event(state,"approval",{"version":version},store=store)
                st.session_state[approval_key]=record;st.rerun()
            if issues:st.caption(' '.join(issues))
        if not compact:st.caption('Approval is recorded for this exact version. You can later request another revision; that version will need its own approval.')
        exported=markdown_package(state,approved=approved)
        from launchlens.observability import download_data
        st.download_button('Download Markdown',download_data(state,exported,store=getattr(run,'store',None)),file_name='launchlens-'+state['request']['market_id'].lower()+'-v'+str(version)+'.md',mime='text/markdown',key='package-download',on_click='ignore',type='primary' if approved else 'secondary',width='stretch' if compact else 'content')
        import json
        encoded=json.dumps(exported).replace('<','\\u003c')
        st.iframe('<style>body{margin:0;font:14px -apple-system,sans-serif;color:#b8c4d4}button{border:0;border-radius:999px;background:#2b3749;color:#f0f4fa;padding:10px 22px;cursor:pointer}span{margin-left:10px}</style><button id="copy" type="button">Copy all</button><span id="result" role="status" aria-live="polite"></span><script>document.getElementById("copy").onclick=async()=>{try{await navigator.clipboard.writeText('+encoded+');document.getElementById("result").textContent="Copied"}catch(e){document.getElementById("result").textContent="Copy unavailable. Use Download Markdown."}};</script>',height=48,alt='Copy all package text')
        st.caption('Simulation-labeled exports · Nothing is published.' if compact else 'Exports carry the label “'+SIMULATION_LABEL+'”. Approval and export never publish anything.')

def risk_scan_view(state):
    from launchlens.package_content import risky_phrase_scan, package_value
    review=state.get('review') or {}
    from launchlens.review_decisions import current_scan
    hits=current_scan(state)
    st.markdown('**Risky phrases · Deterministic scan**')
    st.caption('Scan matches are prompts for contextual review, not factual verdicts. Cleared matches remain visible.')
    if not hits:st.write('No configured risky phrases matched.')
    for hit in hits:
        st.write(hit['format'].replace('_',' ').title()+' · '+hit['content_field']+' · '+hit['category'].replace('_',' '))
        st.text(hit['quote'])
        st.caption('Reviewer: '+hit.get('reviewer_disposition','unassessed').replace('_',' '))
