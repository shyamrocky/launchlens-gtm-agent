"""Session-scoped LangGraph harness; adapters own provider and source access.

Adapters are trusted application code; model proposals and retrieved text are data.
The full LangGraph object/checkpointer are private, never exposed as model tools.
"""
from copy import deepcopy
import hashlib
import json
from threading import Lock
import time
from uuid import uuid4

from typing_extensions import TypedDict
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langsmith import tracing_context

from launchlens.content_review import (ReviewError, authoritative_binding, validate_review, prepare_revision)
from launchlens.evidence_payload import storage_fields
from launchlens.gtm_registry import (HarnessError, MAX_SEARCHES, MAX_TURNS,
    action_registry, objective_claims, missing_objective_claim_ids, require, validate_action, validate_request)
from launchlens.launch_checks import evaluate_launch
from launchlens.linkedin_drafting import DraftValidationError, prepare_input, admit_output, digest
from launchlens.notion_tools import PMM_PAGE, PRODUCT
from launchlens.retrieval import checked_packet
from launchlens.voice_policy import BRAND_POLICY_ID, voice_brief
from launchlens.package_content import (PackageError, admit_package, prepare_package_input,
    authoritative_package_binding, validate_package_review, prepare_call, configuration)


class State(TypedDict):
    run_id: str
    user_notes: str
    voice_policy_id: str | None
    request: dict
    mode: str
    status: str
    turns: int
    searches: int
    pmm: dict | None
    launch: dict | None
    evidence: list
    ledger: dict
    events: list
    feedback: str
    clarification: str
    pending: dict | None
    drafts: dict
    review: dict
    human_accepted: bool
    research_gaps: list
    writing_attempts: int
    draft_failure: dict | None
    draft_history: list
    reviews: list
    review_attempts: int
    revision_attempts: int
    revision_request: dict | None
    revision_feedback: str
    review_failure: dict | None
    package: dict | None
    restricted_drafting: dict | None
    writer_retry: bool
    retry_attempts: int
    failure_history: list
    continuation_notice: str
    normalizations: list


class DraftEligibilityError(Exception):
    """Stable, source-free reason for rejecting a draft before inference."""
    def __init__(self, code, field_path, rule):
        self.code = code
        self.diagnostic = {'field_path': field_path, 'rule': rule}
        super().__init__(code)


def initial_state(request, mode="offline_simulation", user_notes="", voice_policy_id=None):
    return State(run_id=str(uuid4()), request=request, mode=mode, user_notes=user_notes, voice_policy_id=voice_policy_id,
                 status="created", turns=0, searches=0, pmm=None, launch=None,
                 evidence=[], ledger={}, events=[], feedback="", clarification="",
                 pending=None, drafts={}, review={}, human_accepted=False, research_gaps=[], writing_attempts=0, draft_failure=None,
                 draft_history=[], reviews=[], review_attempts=0, revision_attempts=0,
                 revision_request=None, revision_feedback="", review_failure=None, package=None,
                 restricted_drafting=None, writer_retry=False, retry_attempts=0, failure_history=[], continuation_notice='', normalizations=[])


class FoundationSession:
    """One active run. Explicit fresh generation replaces it; no run history.

    model(snapshot) returns exactly one action. tools implements read_pmm(request),
    read_launch(request), search(query, authority). M2.1 uses safe fixtures only.
    Public run/resume methods accept a run ID, not model-provided graph updates.
    """
    def __init__(self, model, tools, *, max_turns=MAX_TURNS, max_searches=MAX_SEARCHES,
                 mode="offline_simulation", writer=None, reviewer=None, revision_writer=None, voice_policy_id=None, execution_guard=None, automatic_refinement=False):
        require(mode in {"offline_simulation", "live_research", "live_linkedin", "offline_review", "offline_package", "live_package"}, "Invalid execution mode")
        require(callable(model), "A model adapter is required")
        require(all(callable(getattr(tools, name, None)) for name in
                    ("read_pmm", "read_launch", "search")), "Missing tool adapter")
        require(type(max_turns) is int and 1 <= max_turns <= MAX_TURNS, "Invalid turn limit")
        require(type(max_searches) is int and 1 <= max_searches <= MAX_SEARCHES, "Invalid search limit")
        require(mode not in {"live_linkedin", "offline_review", "offline_package", "live_package"} or callable(writer), "Drafting mode requires a writer")
        require(mode in {"live_linkedin", "offline_review", "offline_package", "live_package"} or writer is None, "Writer unavailable in research-only mode")
        require((mode in {"offline_review", "offline_package", "live_package"} and callable(reviewer) and callable(revision_writer)) or
                (mode not in {"offline_review", "offline_package", "live_package"} and reviewer is None and revision_writer is None),
                "Review adapters are available only in the explicit offline review profile")
        require(voice_policy_id is None or (mode in {"offline_review", "offline_package", "live_package"} and voice_policy_id == BRAND_POLICY_ID),
                "New writing policy is offline-only and application-selected")
        if voice_policy_id is not None:
            voice_brief(voice_policy_id)  # Verify configured bytes before constructing the graph.
        require(mode not in {"offline_package", "live_package"} or voice_policy_id == BRAND_POLICY_ID,
                "Full package requires the application-selected writing policy")
        require((mode == "live_package" and callable(getattr(execution_guard, "arm", None))) or
                (mode != "live_package" and execution_guard is None), "Explicit live execution guard required")
        require(type(automatic_refinement) is bool and (not automatic_refinement or mode in {'offline_package','live_package'}), 'Invalid automatic refinement mode')
        self._automatic_refinement = automatic_refinement
        self._execution_guard = execution_guard
        self._voice_policy_id = voice_policy_id
        self._reviewer, self._revision_writer = reviewer, revision_writer
        self._writer = writer
        self._model, self._tools = model, tools
        self._mode = mode
        self._max_turns, self._max_searches = max_turns, max_searches
        self._lock = Lock()
        self._run_id = None
        self._initial = None
        self._saver = InMemorySaver()
        builder = StateGraph(State)
        builder.add_node("decide", self._decide)
        builder.add_node("dispatch", self._dispatch)
        builder.add_node("clarify", self._clarify)
        builder.add_node("required_objective_evidence", self._required_objective_evidence)
        builder.add_node("required_review", self._required_review)
        builder.add_node("required_refine", self._required_refine)
        builder.add_edge(START, "decide")
        builder.add_conditional_edges("decide", lambda s: "dispatch" if s["status"] == "running" else END)
        builder.add_conditional_edges("dispatch", self._route)
        builder.add_conditional_edges("required_review", self._route)
        builder.add_conditional_edges("required_refine", self._route)
        builder.add_conditional_edges("clarify", lambda s: "required_objective_evidence" if s["status"] == "running" and
            s.get('feedback') in {'draft_without_availability', 'recheck_readiness'} and s.get('restricted_drafting') else
            ("decide" if s["status"] == "running" else END))
        builder.add_conditional_edges("required_objective_evidence", lambda s: "decide" if s["status"] == "running" else END)
        # Suppress automatic tracing even if inherited environment enables LangSmith.
        with tracing_context(enabled=False):
            self._graph = builder.compile(checkpointer=self._saver)

    @staticmethod
    def _route(state):
        if state["status"] == "running":
            if (state.get('revision_request') or {}).get('origin')=='agent':return 'required_refine'
            if state.get('package') and state['mode'] in {'offline_package','live_package'} and not state.get('review'):
                return 'required_review'
            return "decide"
        return "clarify" if state["status"] == "needs_clarification" else END

    def _config(self):
        return {"configurable": {"thread_id": self._run_id}, "callbacks": [],
                "recursion_limit": 3 * self._max_turns + 10}

    def _check_id(self, run_id):
        require(type(run_id) is str and self._run_id is not None and run_id == self._run_id,
                "Unknown or discarded run; cannot resume")

    def _snapshot(self):
        if self._run_id is None:
            return None
        values = self._graph.get_state(self._config()).values
        return deepcopy(dict(values) if values else self._initial)

    def snapshot(self):
        require(self._lock.acquire(blocking=False), "Execution is running")
        try:
            return self._snapshot()
        finally:
            self._lock.release()

    def start(self, request, *, user_notes=""):
        request = validate_request(request)  # Reject before model/tool invocation or old-state deletion.
        require(type(user_notes) is str and len(user_notes) <= 1000, "Notes must be at most 1000 characters")
        require(self._lock.acquire(blocking=False), "Execution is running")
        try:
            require(self._run_id is None, "Use generate_again to replace the current task")
            if self._execution_guard is not None:
                self._execution_guard.arm(request)  # Single authorization, before any model/source call.
            self._initial = initial_state(request, self._mode, user_notes, self._voice_policy_id)
            self._run_id = self._initial["run_id"]
            return self._snapshot()
        finally:
            self._lock.release()

    def _discard(self):
        # Trusted lifecycle hooks do local cleanup only; never registered model actions.
        failed = False
        try:
            for adapter in (self._model, self._tools, self._writer, self._reviewer, self._revision_writer):
                cleanup = getattr(adapter, "reset_run", None)
                if callable(cleanup):
                    try:
                        cleanup()
                    except Exception:
                        failed = True
        finally:
            if self._run_id is not None:
                self._saver.delete_thread(self._run_id)
            self._run_id, self._initial = None, None
        require(not failed, "Local adapter cleanup failed; no active task remains")

    def generate_again(self, request, *, user_notes=""):
        require(type(user_notes) is str and len(user_notes) <= 1000, "Notes must be at most 1000 characters")
        request = validate_request(request)
        require(self._lock.acquire(blocking=False), "Execution is running; replacement disabled")
        try:
            self._discard()
            if self._execution_guard is not None:
                self._execution_guard.arm(request)  # Single authorization, before any model/source call.
            self._initial = initial_state(request, self._mode, user_notes, self._voice_policy_id)
            self._run_id = self._initial["run_id"]
            return self._snapshot()
        finally:
            self._lock.release()

    def reset(self):
        require(self._lock.acquire(blocking=False), "Execution is running; reset disabled")
        try:
            self._discard()
        finally:
            self._lock.release()

    def run(self, run_id, *, on_update=None):
        return self._execute(run_id, on_update=on_update)

    def continue_run(self,run_id,*,on_update=None):
        state=self.snapshot()
        require(state and state["status"]=="running", "No active checkpoint to continue")
        return self._execute(run_id,on_update=on_update,continue_checkpoint=True)

    def resume(self, run_id, reply, *, on_update=None):
        require(type(reply) is str and reply.strip() and len(reply) <= 2000,
                "Clarification reply must contain 1–2000 characters")
        return self._execute(run_id, reply=reply, on_update=on_update)

    def restore_review_checkpoint(self, state, *, review_recovery=False, stopped_display=False):
        """Trusted protected-receipt restore only; no model-supplied state or calls."""
        require(self._mode=='live_package' and self._run_id is None, 'No current run may be overwritten')
        require(type(state) is dict and set(state)==set(State.__annotations__) and
            state['mode']=='live_package' and
            ((stopped_display and state['status']=='failed' and state['package'] is None and not state['drafts']) or
             (not review_recovery and state['status']=='awaiting_human_review' and type(state['package']['version']) is int and state['package']['version']>=1) or
             (review_recovery and state['status'] in {'failed','stopped','interrupted'} and state['package']['version']>=1 and not state['review'])) and
            state['revision_request'] is None and state['pending'] is None and
            state['human_accepted'] is False, 'Only the current review checkpoint can resume')
        require(not stopped_display or (state['status']=='failed' and state['package'] is None and not state['drafts']),'Stopped restore is display-only')
        from uuid import UUID
        require(str(UUID(state['run_id']))==state['run_id'], 'Invalid checkpoint identity')
        if not stopped_display:authoritative_package_binding(state)
        require(self._execution_guard.armed and (not self._execution_guard.closed or review_recovery or stopped_display) and
            (sum(self._execution_guard.counts.values())==state['turns'] or
             (review_recovery and self._execution_guard.can_review_saved(state))), 'Checkpoint budget differs')
        self._run_id=state['run_id'];self._initial=None
        with tracing_context(enabled=False):
            self._graph.update_state(self._config(),deepcopy(state),as_node='dispatch')
        return self._snapshot()

    def recheck_package_review(self, run_id, reviewer, *, owner_requested=False):
        """One explicitly authorized Reviewer-only command; no planning/Writer calls."""
        require(self._lock.acquire(blocking=False), 'Execution is running')
        try:
            self._check_id(run_id);state=self._snapshot()
            command_id='harness-owner-recheck-'+self._execution_guard.permission['authorization_id']
            explicit=(owner_requested is True and self._execution_guard.permission.get('bound_run_id')==run_id and command_id not in state['ledger'])
            legacy=(((state['package']['version']==1 and state['review_attempts']==1 and state['revision_attempts']==0) or
                 (state['package']['version']==2 and state['review_attempts']==3 and state['revision_attempts']==1)) and not state['review'].get('review_complete'))
            require(self._mode=='live_package' and state['status']=='awaiting_human_review' and
                (explicit or (not owner_requested and legacy)) and
                (__import__('launchlens.package_content',fromlist=['configuration']).configuration()['limits']['review_attempts'] is None or state['review_attempts']<__import__('launchlens.package_content',fromlist=['configuration']).configuration()['limits']['review_attempts']), 'Reviewer-only recheck unavailable')
            authoritative_package_binding(state)
            if explicit:state['ledger'][command_id]={'status':'attempted','source_review_sha256':digest(state['review'])}
            state['turns']+=1;state['review_attempts']+=1
            try:candidate=reviewer(deepcopy(state))
            except ReviewError:
                if self._execution_guard.closed:raise
                candidate=reviewer.calls[-1].get('response_content') if reviewer.calls else None
            checked=validate_package_review(candidate,state)
            state['review']=checked;state['reviews'].append(deepcopy(checked))
            for f,item in checked['format_reviews'].items():
                state['drafts'][f]['review_status']=item['review_status'] if item['review_complete'] else 'review_incomplete'
            state['events'].append({'sequence':len(state['events'])+1,'action':'review_package',
                'origin':'owner_command','outcome':'completed',
                'why':'Owner requested a Reviewer-only recheck of this unchanged current version.'})
            state['status']='awaiting_human_review';state['human_accepted']=False
            with tracing_context(enabled=False):self._graph.update_state(self._config(),state,as_node='dispatch')
            return self._snapshot()
        finally:self._lock.release()

    def edit_current_fields(self,run_id,changes,*,draft_version,draft_sha256):
        """Owner-only final-version edits; validate and rescan without inference."""
        require(self._lock.acquire(blocking=False),'Execution is running')
        try:
            self._check_id(run_id);state=self._snapshot()
            require(self._mode in {'offline_package','live_package'} and state['status']=='awaiting_human_review'
                and state['revision_attempts']>=configuration()['limits']['revision_attempts']
                and state['revision_request'] is None and state.get('review',{}).get('review_complete') is True,
                'Manual editing requires the final reviewed version')
            inputs,_,binding=authoritative_package_binding(state)
            require(state['review'].get('binding')==binding,'Current review binding required')
            require(draft_version==binding['draft_version'] and draft_sha256==binding['draft_sha256'], 'Edit targets an outdated draft')
            require(type(changes) is list and 0<len(changes)<=30,'Bounded field edits required')
            from launchlens.package_content import package_value,text_fields,human_edit_review
            value=package_value(state);changed=[];seen=set()
            for edit in changes:
                require(type(edit) is dict and set(edit)=={'format','content_field','text'},'Invalid edit fields')
                name,path,text=edit['format'],edit['content_field'],edit['text']
                require(type(name) is str and name in value and type(path) is str and type(text) is str and text.strip() and len(text)<=20000,'Invalid edit value')
                fields=dict(text_fields(value[name]['content']))
                require(path in fields and (name,path) not in seen,'Unknown or duplicate edit field')
                seen.add((name,path))
                if fields[path]==text:continue
                target=value[name]['content'];parts=path.split('.')
                for part in parts[:-1]:target=target[int(part)] if isinstance(target,list) else target[part]
                leaf=int(parts[-1]) if isinstance(target,list) else parts[-1];target[leaf]=text
                changed.append({'format':name,'content_field':path})
            require(changed,'No text changes to save')
            drafts,metadata=admit_package(value,inputs,version=draft_version)
            source=deepcopy(state['review']);old_sha=state['package']['package_sha256']
            state['drafts']=drafts;state['package']=metadata
            checked=human_edit_review(state,source,changed)
            state['review']=checked;state['reviews'].append(deepcopy(checked));state['human_accepted']=False
            for name,item in checked['format_reviews'].items():state['drafts'][name]['review_status']=item['review_status']
            state['events'].append({'sequence':len(state['events'])+1,'action':'human_edit','origin':'owner_command',
                'outcome':'completed','why':'Your text edits were validated and scanned again. No new AI review was requested.',
                'before_sha256':old_sha,'after_sha256':metadata['package_sha256'],'fields':changed})
            with tracing_context(enabled=False):self._graph.update_state(self._config(),state,as_node='dispatch')
            return self._snapshot()
        finally:self._lock.release()

    def _revision_permission(self,state,feedback,draft_version,draft_sha256):
        require(self._mode in {"offline_review","offline_package","live_package"} and state['status']=='awaiting_human_review',
                'Current reviewed draft required before revision')
        package=self._mode in {'offline_package','live_package'}
        _,_,binding=authoritative_package_binding(state) if package else authoritative_binding(state)
        require(type(draft_version) is int and draft_version==binding['draft_version'] and draft_sha256==binding['draft_sha256'],
                'Feedback targets an outdated draft')
        from launchlens.package_content import MAX_PACKAGE_FEEDBACK
        require(type(feedback) is str and feedback.strip() and len(feedback)<=(MAX_PACKAGE_FEEDBACK if package else 2000),
                'Feedback exceeds the bounded revision limit')
        require(state['revision_attempts']<(configuration()['limits']['revision_attempts'] if package else 1) and state['revision_request'] is None and state['review'].get('binding')==binding,
                'Revision is unavailable or already requested')
        return {'binding':binding,'review_sha256':digest(state['review']),'feedback':feedback}

    def check_revision(self,run_id,feedback,*,draft_version,draft_sha256):
        require(self._lock.acquire(blocking=False),'Execution is running')
        try:
            self._check_id(run_id)
            return self._revision_permission(self._snapshot(),feedback,draft_version,draft_sha256)
        finally:self._lock.release()

    def request_revision(self,run_id,feedback,*,draft_version,draft_sha256):
        """One explicit human command per bound version; never an automatic loop."""
        require(self._lock.acquire(blocking=False),'Execution is running')
        try:
            self._check_id(run_id)
            permission=self._revision_permission(self._snapshot(),feedback,draft_version,draft_sha256)
            with tracing_context(enabled=False):
                self._graph.update_state(self._config(),{'revision_request':permission,
                    'human_accepted':False,'revision_feedback':feedback,'status':'created'})
            return self._snapshot()
        finally:self._lock.release()

    def _execute(self, run_id, reply=None, on_update=None, continue_checkpoint=False):
        require(self._lock.acquire(blocking=False), "Execution is already running")
        try:
            self._check_id(run_id)
            state = self._snapshot()
            if reply is None and state["status"] != "created" and not continue_checkpoint and not (state.get("writer_retry") and state.get("pending") and state["status"]=="running"):
                return state  # Rerender/replay never invokes or resumes the graph.
            require(reply is None or state["status"] == "needs_clarification",
                    "This run is not awaiting clarification")
            inputs = Command(resume=reply) if reply is not None else {**state, "status": "running"}
            with tracing_context(enabled=False):
                try:
                    if continue_checkpoint or (state.get('writer_retry') and state.get('pending')):
                        inputs = None  # Existing graph checkpoint already points to dispatch.
                    # Updates and checkpointer reads are not synchronized: a read
                    # here may lag/advance past the yielded node. Build the UI view
                    # from that node's actual update, never a second checkpoint read.
                    # This is observation only; the graph still owns execution state.
                    observed = deepcopy(state)
                    if inputs is not None and reply is None:
                        observed['status'] = 'running'
                    for update in self._graph.stream(inputs, self._config(), stream_mode='updates'):
                        for node in ('decide', 'dispatch', 'clarify', 'required_objective_evidence', 'required_review', 'required_refine'):
                            if node in update:
                                observed.update(deepcopy(update[node]))
                        if on_update is not None:
                            if on_update(deepcopy(update), deepcopy(observed)) is False:break
                except Exception:
                    # No exception bodies, source text or credentials in events.
                    self._graph.update_state(self._config(), {"status": "failed",
                        "events": [*self._snapshot()["events"],
                                   {"action": "execution", "outcome": "failed_safely"}]})
            self._initial = None
            return self._snapshot()
        finally:
            self._lock.release()

    @staticmethod
    def _event(state, action, outcome, started, **fields):
        state["events"].append({"sequence": len(state["events"]) + 1,
            "action": action, "outcome": outcome,
            "elapsed_seconds": round(time.monotonic() - started, 6), **fields})

    def _required_review(self, state):
        state = deepcopy(state)
        _, _, binding = authoritative_package_binding(state)
        state['pending'] = {'id':'harness-review-v'+str(binding['draft_version']),
            'name':'review_package', 'arguments':{},
            'why':'Required independent review of this exact draft version before returning to you.'}
        if state['pending']['id'] in state['ledger']:
            state['status']='failed';state['pending']=None
            state['review_failure']={'stage':'review_eligibility','code':'review_already_attempted','field_path':'$'}
            return state
        result = self._dispatch(state)
        for event in result['events'][len(state['events']):]:event['origin']='harness_required'
        if result['status']=='awaiting_human_review':
            result=self._after_required_review(result)
        return result

    def _after_required_review(self,state):
        from launchlens.package_content import blocking_findings,package_value,text_fields,MAX_PACKAGE_FEEDBACK,refinement_targets,protected_scan_hits,new_protected_hits
        marker=state['ledger'].get('harness-auto-refinement')
        if marker:
            if marker.get('status')=='revised':
                marker['status']='reviewed'
                package=package_value(state);fixed=0
                if state['review'].get('review_complete'):
                    for f in marker['findings']:
                        target=dict(text_fields(package[f['format']]['content'])).get(f['content_field'],'')
                        remaining=blocking_findings(state['review'])
                        field_blocked=any(n['format']==f['format'] and n['content_field'] in {f['content_field'],'$format'} for n in remaining)
                        if f.get('quote') and f['quote'].casefold() not in target.casefold() and not field_blocked:fixed+=1
                if 'protected_scan_hits' in marker:
                    current=protected_scan_hits(state)
                    marker['post_refinement_scan']={'protected_scan_hits':current,
                        'new_protected_scan_hits':new_protected_hits(marker['protected_scan_hits'],current)}
                    marker['protected_removed_count']=len(new_protected_hits(current,marker['protected_scan_hits']))
                marker['fixed_count']=fixed
                self._event(state,'automatic_refinement','completed',time.monotonic(),
                    origin='agent',version=state['package']['version'],fixed_count=fixed,
                    attempted_count=len(marker['findings']),protected_removed_count=marker.get('protected_removed_count',0),
                    new_protected_count=len(marker.get('post_refinement_scan',{}).get('new_protected_scan_hits',[])),review_complete=state['review'].get('review_complete',False),
                    why='Revised blocking wording and checked the new version; remaining protected wording still needs your decision.')
            return state
        if not self._automatic_refinement or state['human_accepted'] or not state['review'].get('review_complete'):return state
        inputs,_,_=authoritative_package_binding(state)
        if not configuration(inputs['package_contract']['sha256']).get('automatic_refinement'):return state
        targets=refinement_targets(state);findings=targets['blocking_findings'];protected=targets['protected_scan_hits']
        if not findings and not protected:return state
        # The same original evidence, exact-version permission and paired spending
        # reservation are reused. No keep dispositions or human approval are created.
        _,_,binding=authoritative_package_binding(state)
        permission={'binding':binding,'review_sha256':digest(state['review']),
            'feedback':'Correct blocking_findings_to_fix and protected_scan_hits_to_rewrite using full_avoid_list when supplied. Preserve facts, citations, qualifications and format tone. Never grant keep clearance or human approval.',
            'origin':'agent','blocking_findings':findings,**({'protected_scan_hits':protected} if configuration(inputs['package_contract']['sha256'])['automatic_refinement'].get('trigger')=='reviewer_blocking_or_protected_scan_hits' else {})}
        marker={'status':'deferred','source_binding':binding,'findings':deepcopy(findings),**({'protected_scan_hits':deepcopy(protected)} if 'protected_scan_hits' in permission else {})}
        state['ledger']['harness-auto-refinement']=marker  # one decision, including denial
        if state['revision_attempts']>=configuration()['limits']['revision_attempts'] or len(permission['feedback'])>MAX_PACKAGE_FEEDBACK:
            marker['reason']='revision_or_feedback_limit';return state
        if self._execution_guard is not None:
            try:self._execution_guard.reserve_automatic_revision(binding)
            except Exception:
                marker['reason']='budget_or_authorization_unavailable';return state
        marker.update(status='scheduled',permission_sha256=digest(permission))
        state['revision_request']=permission;state['status']='running'
        return state

    def resume_deferred_refinement(self,run_id,*,on_update=None):
        """Owner-authorized recovery of a never-attempted automatic handoff."""
        require(self._lock.acquire(blocking=False),'Execution is running')
        try:
            self._check_id(run_id);state=self._snapshot()
            marker=state['ledger'].get('harness-auto-refinement',{})
            require(self._automatic_refinement and state['status']=='awaiting_human_review' and
                state['revision_attempts']==0 and marker.get('status')=='deferred' and
                marker.get('reason')=='revision_or_feedback_limit' and
                state['review'].get('review_complete') and not state['human_accepted'],
                'No unattempted automatic handoff may resume')
            authoritative_package_binding(state)
            state['events'].append({'sequence':len(state['events'])+1,'action':'automatic_refinement_admission',
                'origin':'harness_required','outcome':'recovered','why':'Removed duplicated revision direction; retained all findings and original accounting.',
                'prior_admission':deepcopy(marker)})
            del state['ledger']['harness-auto-refinement']
            state=self._after_required_review(state)
            with tracing_context(enabled=False):self._graph.update_state(self._config(),state,as_node='required_review')
        finally:self._lock.release()
        if state['status']=='running':return self.continue_run(run_id,on_update=on_update)
        return state

    def _required_refine(self,state):
        state=deepcopy(state);permission=state.get('revision_request') or {}
        require(permission.get('origin')=='agent' and self._automatic_refinement,'Automatic refinement unavailable')
        state['pending']={'id':'agent-revision-v'+str(permission['binding']['draft_version']+1),
            'name':'revise_package','arguments':{},'origin':'agent',
            'why':'Rewrite blocking findings and protected scan wording once, preserving evidence and launch restrictions.'}
        result=self._dispatch(state)
        result['ledger']['harness-auto-refinement']['status']='revised' if result['status']=='running' else 'failed'
        return result

    def can_review_saved(self):
        state=self._snapshot()
        if state is None or state['mode'] not in {'offline_package','live_package'}:return False
        if state['status'] not in {'failed','stopped','interrupted'} or (state.get('package') or {}).get('version',0)<1:return False
        if state.get('review') or state['human_accepted']:return False
        if 'harness-review-v'+str(state['package']['version']) in state['ledger'] or any(r.get('binding',{}).get('draft_version')==state['package']['version'] for r in state['reviews']):return False
        try:authoritative_package_binding(state)
        except Exception:return False
        guard=self._execution_guard
        return ((__import__('launchlens.package_content',fromlist=['configuration']).configuration()['limits']['review_attempts'] is None or state['review_attempts']<__import__('launchlens.package_content',fromlist=['configuration']).configuration()['limits']['review_attempts'])
            and (guard.can_review_saved(state) if guard is not None else True))

    def review_saved(self, run_id, *, on_update=None):
        """Recover the saved current version's required review; no Writer call."""
        require(self._lock.acquire(blocking=False), 'Execution is running')
        try:
            self._check_id(run_id);require(self.can_review_saved(), 'Saved current-version review unavailable')
            state=self._snapshot();guard=self._execution_guard
            if guard is not None:
                paid=sum(guard.counts.values())
                if state['turns']!=paid:
                    state['normalizations'].append({'rule':'pre_http_attempt_separated_from_paid_calls',
                        'recorded_turns':state['turns'],'paid_calls':paid})
                    state['turns']=paid  # Preserve every paid counter and the rejected-attempt event.
                guard.reopen_for_saved_review(state)
            state['status']='running';state['pending']=None
            # Same existing LangGraph: start at its mandatory-review node.
            with tracing_context(enabled=False):
                self._graph.update_state(self._config(),state,as_node='dispatch')
                observed=deepcopy(state)
                for update in self._graph.stream(None,self._config(),stream_mode='updates'):
                    if 'required_review' in update:observed.update(deepcopy(update['required_review']))
                    if on_update is not None:on_update(deepcopy(update),deepcopy(observed))
            return self._snapshot()
        finally:self._lock.release()

    def _task_turns(self, state):
        return state['turns']-state['review_attempts']-state['revision_attempts'] if self._mode in {'offline_package','live_package'} else state['turns']

    def _decide(self, state):
        state = deepcopy(state)
        if self._mode in {'offline_package','live_package'} and state.get('revision_request'):
            binding=state['revision_request']['binding']
            state['pending']={'id':'human-revision-v'+str(binding['draft_version']+1)+'-'+binding['draft_sha256'][:12],
                'name':'revise_package','arguments':{},'why':'Apply your explicit changes to the current version, then obtain a fresh review.'}
            return state  # Human selected the task; no extra controller inference.
        if self._task_turns(state) >= self._max_turns:
            state["status"] = "failed"
            state["events"].append({"action": "budget", "outcome": "turn_limit"})
            return state
        view = deepcopy(state)
        view.pop("pending", None)
        from launchlens.gtm_registry import eligible_actions
        view["allowed_actions"] = eligible_actions(state)
        if not view['allowed_actions'] or (missing_objective_claim_ids(state) and
                state['searches'] >= self._max_searches and
                'search_product_evidence' not in view['allowed_actions']):
            state['status'] = 'failed'
            state['draft_failure'] = {'stage':'evidence_eligibility', 'code':'required_objective_evidence_unavailable',
                                      'field_path':'evidence', 'rule':'no_eligible_evidence_action'}
            self._event(state, 'evidence_eligibility', 'required_claims_unavailable', time.monotonic())
            return state
        view["remaining_limits"] = {"model_turns": self._max_turns - self._task_turns(state),
                                    "product_searches": self._max_searches - state["searches"]}
        state["turns"] += 1
        state["pending"] = None
        started = time.monotonic()
        try:
            proposal = deepcopy(self._model(view))
            # Bounded, JSON-only action boundary. Never merge a model state patch.
            require(len(json.dumps(proposal, allow_nan=False)) <= 8000, "Action exceeds size bound")
            checked = validate_action(proposal, self._mode)
            require(not checked['id'].startswith(('harness-','agent-revision-','human-revision-')), 'Harness action IDs are reserved')
            require(checked['name'] in view['allowed_actions'], 'Action unavailable in current state')
            state["pending"] = deepcopy(checked)
        except (HarnessError, TypeError, ValueError, OverflowError):
            self._event(state, "model_proposal", "rejected", started)
        except Exception:
            state["status"] = "failed"
            self._event(state, "model_adapter", "failed_safely", started)
        return state

    @staticmethod
    def _validate_evidence(value, authority):
        require(type(value) is dict and value.get("product_id") == PRODUCT and
                value.get("requested_authority") == authority and
                value.get("status") in {"evidence_found", "incomplete"} and
                type(value.get("records")) is list and len(value["records"]) <= 10,
                "Invalid evidence result")
        seen = set()
        for record in value["records"]:
            require(type(record) is dict and type(record.get("chunk_id")) is str and
                    record["chunk_id"] not in seen, "Duplicate or malformed evidence record")
            seen.add(record["chunk_id"])
            payload = record["evidence_payload"]
            metadata = storage_fields(payload)
            require(record["chunk_id"] == payload["chunk_id"] and
                    record.get("unit_id") == payload["unit_id"] and
                    record["authority"] == payload["authority"] and
                    record["evidence_sha256"] == metadata["evidence_sha256"], "Evidence identity/digest differs")
            checked_packet({"id": record["chunk_id"], "metadata": metadata}, record["authority"])
            require(record["authority"] == authority or
                    (authority == "synthetic_product_intent" and record["authority"] == "public_product_facts"),
                    "Evidence authority transition not allowed")
            require(type(record.get("usable_as_complete_evidence")) is bool, "Missing evidence completeness flag")
            require(record.get("reference_status") in {"resolved", "not_expanded", "incomplete", "invalid"},
                    "Missing reference completeness status")
            require(not record["usable_as_complete_evidence"] or
                    record["reference_status"] in {"resolved", "not_expanded"},
                    "Contradictory evidence completeness")
        return value

    @staticmethod
    def _objective_gaps(state):
        supported = {row["evidence_payload"]["unit_id"]
                     for result in state["evidence"] for row in result["records"]
                     if row["authority"] == "public_product_facts" and
                     row["usable_as_complete_evidence"] and
                     row["evidence_payload"].get("chunk_kind") == "product_claim" and
                     row["evidence_payload"].get("claim_source_mappings")}
        return [label for claim, label in objective_claims(state["request"]).items()
                if claim not in supported]

    def _dispatch(self, state):
        state = deepcopy(state)
        action = state["pending"]
        state["pending"] = None
        if action is None:
            return state
        name, args, action_id = action["name"], action["arguments"], action["id"]
        if name == 'search_product_evidence':
            query = ' '.join(args['query'].casefold().split())
            prior = {(' '.join(row['action']['arguments']['query'].casefold().split()))
                     for row in state['ledger'].values()
                     if row['action']['name'] == 'search_product_evidence' and row['status'] == 'completed'}
            if query in prior:
                self._event(state, name, 'rejected_repeated_query', time.monotonic(), action_id=action_id)
                return state
            if state.get('feedback') in {'draft_without_availability', 'recheck_readiness'} and state.get('restricted_drafting'):
                self._event(state, name, 'rejected_after_clarification', time.monotonic(), action_id=action_id)
                return state
        from launchlens.gtm_registry import clarification_used
        if name == 'request_clarification' and (
            (state.get('launch') or {}).get('decision') != 'Clarify' or
            clarification_used(state) or args.get('market_id') != state['request']['market_id']
        ):
            self._event(state, name, 'rejected', time.monotonic(), action_id=action_id,
                        why='Clarification is outside this run or has already been answered')
            return state
        fingerprint = hashlib.sha256(json.dumps({"name": name, "arguments": args},
            sort_keys=True, allow_nan=False).encode()).hexdigest()
        started = time.monotonic()
        previous = state["ledger"].get(action_id)
        if previous is not None:
            if previous["fingerprint"] != fingerprint or previous["status"] != "completed":
                state["status"] = "failed"
                self._event(state, name, "replay_conflict", started, action_id=action_id)
            else:
                self._event(state, name, "replayed", started, action_id=action_id)
            return state
        state["ledger"][action_id] = {"action": deepcopy(action), "fingerprint": fingerprint,
                                      "status": "pending", "result": None}
        outcome = "completed"
        failure_stage = "tool"
        try:
            if name == "read_pmm_brief":
                value = deepcopy(self._tools.read_pmm(deepcopy(state["request"])))
                require(type(value) is dict and value.get("status") == "ok" and
                        value.get("page_id") == PMM_PAGE and value.get("authority") == "synthetic_pmm_guidance" and
                        type(value.get("blocks")) is list and value["blocks"], "Complete PMM guidance required")
                state["pmm"] = value
            elif name == "check_launch":
                context = deepcopy(self._tools.read_launch(deepcopy(state["request"])))
                require(type(context) is dict and context.get("market_id") == state["request"]["market_id"] and
                        context.get("product_id") == PRODUCT, "Wrong operational scope")
                value = evaluate_launch(context, state["request"]["evaluation_date"])
                state["launch"] = value
                if value["decision"] == "Hold":
                    state["status"] = "held"
            elif name == "search_product_evidence":
                require(state["searches"] < self._max_searches, "Search limit reached")
                state["searches"] += 1
                value = self._validate_evidence(deepcopy(self._tools.search(**args)), args["authority"])
                state["evidence"].append(value)
                state["research_gaps"] = self._objective_gaps(state)
            elif name in {"generate_package", "review_package", "revise_package"}:
                require(self._mode in {"offline_package", "live_package"}, "Package action unavailable in this profile")
                failure_stage = "draft_eligibility" if name == "generate_package" else "review_eligibility"
                if name == "generate_package":
                    from launchlens.launch_checks import availability_only_gap
                    launch = state.get('launch')
                    restricted = (type(launch) is dict and availability_only_gap(launch)
                        and state.get('feedback') in {'draft_without_availability', 'recheck_readiness'}
                        and state.get('restricted_drafting') == {
                            'request_sha256':digest(state['request']),
                            'launch_sha256':digest(launch),
                            'availability_wording_allowed':False})
                    if not (type(launch) is dict and (
                        launch.get('decision') == 'Proceed' and launch.get('promotional_draft_allowed') is True
                        or restricted)):
                        raise DraftEligibilityError('draft_permission_denied', 'launch', 'launch_gate_or_human_answer_missing')
                    if state.get('pmm') is None:
                        raise DraftEligibilityError('pmm_guidance_missing', 'pmm', 'required_guidance_missing')
                    if missing_objective_claim_ids(state):
                        raise DraftEligibilityError('objective_evidence_missing', 'evidence', 'required_claim_missing')
                    inputs = prepare_package_input(state)
                    if state["writing_attempts"] and not state.get('writer_retry'):
                        require(state["writing_attempts"] in {1,2} and state["package"], "Writing already attempted; no retry")
                        authoritative_package_binding(state)
                        outcome = "duplicate_suppressed"
                    else:
                        require(self._task_turns(state) < self._max_turns, "No model-call budget for writing")
                        state["writing_attempts"] += 1; state["turns"] += 1
                        failure_stage = "draft_writing"
                        candidate = self._writer(deepcopy(state))
                        calls=getattr(self._writer,'calls',[])
                        if calls:state['normalizations'].extend(deepcopy(calls[-1].get('normalizations',[])))
                        failure_stage = "draft_validation"
                        drafts, metadata = admit_package(candidate, inputs)
                        state["drafts"], state["package"] = drafts, metadata
                        state['writer_retry'] = False
                        state["draft_history"].append({"version":1, "drafts":deepcopy(drafts), "package":deepcopy(metadata)})
                elif name == "review_package":
                    _, _, binding = authoritative_package_binding(state)
                    if state["review"].get("binding") == binding:
                        outcome = "duplicate_suppressed"
                    else:
                        require(__import__('launchlens.package_content',fromlist=['configuration']).configuration()['limits']['review_attempts'] is None or state["review_attempts"] < __import__('launchlens.package_content',fromlist=['configuration']).configuration()['limits']['review_attempts'],
                                "No model-call budget for review")
                        state["review_attempts"] += 1; state["turns"] += 1
                        failure_stage = "review_model"
                        try:
                            candidate = self._reviewer(deepcopy(state))
                        except ReviewError:
                            # Unknown transport/usage remains a budget boundary. A
                            # malformed review alone is never loss of the drafts.
                            if self._execution_guard is not None and self._execution_guard.closed:raise
                            calls=getattr(self._reviewer,'calls',[])
                            candidate=calls[-1].get('response_content') if calls else None
                        failure_stage = "review_validation"
                        review = validate_package_review(candidate, state)
                        state['normalizations'].extend(deepcopy(review.get('normalizations',[])))
                        state["review"] = review; state["reviews"].append(deepcopy(review))
                        for f, item in review["format_reviews"].items():
                            state["drafts"][f]["review_status"] = item["review_status"] if item.get('review_complete',True) else 'review_incomplete'
                    # Every review returns to the owner, including blocking findings.
                    # The model cannot grant approval or initiate an extra revision.
                    state["status"] = "awaiting_human_review"
                else:
                    prepare_call(state,'package_revision')  # Exact current-version human permission.
                    target_version=state['package']['version']+1
                    state['revision_attempts']+=1;state['turns']+=1
                    failure_stage='revision_model'
                    candidate=self._revision_writer(deepcopy(state))
                    calls=getattr(self._revision_writer,'calls',[])
                    if calls:state['normalizations'].extend(deepcopy(calls[-1].get('normalizations',[])))
                    failure_stage='revision_validation'
                    drafts,metadata=admit_package(candidate,prepare_package_input(state),version=target_version)
                    state['drafts'],state['package']=drafts,metadata
                    state['draft_history'].append({'version':target_version,'drafts':deepcopy(drafts),'package':deepcopy(metadata)})
                    state['review']={};state['revision_request']=None;state['human_accepted']=False
                value = {"draft_version":state["package"]["version"], "formats":list(state["drafts"]),
                         "status":state["review"].get("review_status", "unreviewed")}
            elif name == "generate_linkedin":
                require(self._mode in {"live_linkedin", "offline_review", "offline_package", "live_package"}, "Drafting unavailable in this mode")
                failure_stage = "draft_eligibility"
                inputs = prepare_input(state)  # No inference until all admission checks pass.
                if state["writing_attempts"]:
                    require(state["writing_attempts"] == 1 and state["drafts"].get("linkedin"),
                            "Writing already attempted; no retry")
                    outcome = "duplicate_suppressed"
                else:
                    require(state["turns"] < self._max_turns, "No model-call budget for writing")
                    state["writing_attempts"] = 1  # Count failures as attempts, before side effects.
                    state["turns"] += 1
                    failure_stage = "draft_writing"
                    result = self._writer(deepcopy(inputs))
                    failure_stage = "draft_validation"
                    state["drafts"]["linkedin"] = admit_output(result, inputs)
                    if self._mode == "offline_review":
                        state["draft_history"].append(deepcopy(state["drafts"]["linkedin"]))
                value = {"status":"unreviewed", "draft_version":state["drafts"]["linkedin"]["version"],
                         "input_sha256":state["drafts"]["linkedin"]["input_sha256"]}
            elif name == "review_linkedin":
                failure_stage = "review_eligibility"
                require(self._mode == "offline_review", "Review unavailable in this mode")
                _, _, binding = authoritative_binding(state)
                if state["review"].get("binding") == binding:
                    outcome = "duplicate_suppressed"
                else:
                    require(state["review_attempts"] < 2 and state["turns"] < self._max_turns,
                            "No model-call budget for review")
                    state["review_attempts"] += 1; state["turns"] += 1
                    failure_stage = "review_model"
                    candidate = self._reviewer(deepcopy(state))
                    failure_stage = "review_validation"
                    review = validate_review(candidate, state)
                    state["review"] = review; state["reviews"].append(deepcopy(review))
                    state["drafts"]["linkedin"]["review_status"] = review["review_status"]
                state["status"] = "awaiting_human_review"  # Required human boundary, never automatic revision.
                value = {"status":state["review"]["review_status"], "binding":binding}
            elif name == "revise_linkedin":
                failure_stage = "revision_eligibility"
                require(self._mode == "offline_review", "Revision unavailable in this mode")
                if state["revision_attempts"]:
                    require(state["revision_attempts"] == 1 and state["drafts"]["linkedin"]["version"] == 2,
                            "Revision already attempted; no retry")
                    outcome = "duplicate_suppressed"
                else:
                    prepare_revision(state)  # Original authority, exact review/version and owner permission.
                    require(state["turns"] < self._max_turns, "No model-call budget for revision")
                    state["revision_attempts"] = 1; state["turns"] += 1
                    failure_stage = "revision_model"
                    candidate = self._revision_writer(deepcopy(state))
                    failure_stage = "revision_validation"
                    revised = admit_output(candidate, prepare_input(state))
                    revised["version"] = 2
                    state["drafts"]["linkedin"] = revised
                    state["draft_history"].append(deepcopy(revised))
                    state["review"] = {}; state["revision_request"] = None
                    state["human_accepted"] = False
                value = {"status":"unreviewed", "draft_version":2}
            elif name == "request_clarification":
                value = {"question": args["question"]}
                state["clarification"] = args["question"]
                state["status"] = "needs_clarification"
            else:  # finish cannot supply status/approval; code determines the outcome.
                launch = state["launch"]
                require(launch is not None, "Launch eligibility must be checked")
                if launch["decision"] == "Clarify" and not state.get('feedback'):
                    state["status"] = "needs_clarification"
                    state["clarification"] = "; ".join(c["message"] for c in launch["conditions"])
                else:
                    require((launch["promotional_draft_allowed"] or state.get('restricted_drafting')) and state["pmm"] is not None,
                            "Research prerequisites remain incomplete")
                    state["research_gaps"] = self._objective_gaps(state)
                    if not state["research_gaps"]:
                        if self._mode not in {"live_linkedin", "offline_review", "offline_package", "live_package"}:
                            state["status"] = "research_complete"
                        elif self._mode == "live_linkedin" and state["drafts"].get("linkedin"):
                            state["status"] = "draft_complete"
                incomplete = "draft_incomplete" if self._mode in {"live_linkedin", "offline_review", "offline_package", "live_package"} else "research_incomplete"
                value = {"status": incomplete if state["status"] == "running" else state["status"],
                         "mode": state["mode"], "missing_requirements": list(state["research_gaps"])}
            state["ledger"][action_id].update(status="completed", result=deepcopy(value))
            self._event(state, name, outcome, started, action_id=action_id,
                        decision=state["launch"]["decision"] if name == "check_launch" else None, why=action.get('why',''), **({'origin':action.get('origin','human')} if name=='revise_package' else {}))
        except Exception as error:
            state["ledger"][action_id]["status"] = "failed"
            state["status"] = "failed"
            if name in {"generate_linkedin", "generate_package"}:
                detail = error.diagnostic if isinstance(error, (DraftValidationError, DraftEligibilityError)) else {
                    "field_path":None, "rule":"unknown_validation_failure"}
                state["draft_failure"] = {"stage":failure_stage,
                    "code":error.code if isinstance(error, (DraftValidationError, DraftEligibilityError)) else "operation_failed", **detail}
            if name in {"review_linkedin", "revise_linkedin", "review_package", "revise_package"}:
                if isinstance(error, ReviewError):
                    detail = error.diagnostic
                elif isinstance(error, DraftValidationError):
                    detail = {"code":error.code, **error.diagnostic}
                else:
                    detail = {"code":"operation_failed", "field_path":"$"}
                state["review_failure"] = {"stage":failure_stage, **detail}
            if isinstance(error, PackageError):
                target = "draft_failure" if name == "generate_package" else "review_failure"
                state[target] = {"stage":failure_stage, **error.diagnostic}
            if name=='generate_package':state['failure_history'].append(deepcopy(state['draft_failure']))
            if name=='generate_package':
                technical={'invalid_type','required_field_missing','unexpected_field','array_length_invalid','nonempty_text_required','unknown_validation_failure'}
                rule=(state.get('draft_failure') or {}).get('rule')
                code=(state.get('draft_failure') or {}).get('code')
                from launchlens.package_content import citation_only_failures
                calls=getattr(self._writer,'calls',[])
                missing_only=(failure_stage=='draft_validation' and code in {'field_claim_coverage','objective_claim_coverage'} and
                    calls and bool(citation_only_failures(calls[-1].get('candidate'),prepare_package_input(state))))
                if missing_only and (self._execution_guard is None or not self._execution_guard.closed):
                    state['status']='draft_incomplete'
                if failure_stage in {'draft_writing','draft_validation'} and rule in technical and code not in {'objective_claim_coverage','field_claim_coverage','prohibited_wording','prohibited_link','cta_mismatch'}:
                    if self._execution_guard is None or not self._execution_guard.closed:
                        state['status']='draft_incomplete'  # Recoverable format handoff, not policy stop.

            self._event(state, name, "failed_safely", started, action_id=action_id, why=action.get('why',''), **({'origin':action.get('origin','human')} if name=='revise_package' else {}))
        return state

    def _clarify(self, state):
        # Interrupt node has no side effects before interrupt: resume reexecutes it.
        reply = interrupt({"run_id": state["run_id"], "question": state["clarification"],
                           "notice": "Reply is guidance, never operational approval"})
        require(type(reply) is str and reply.strip() and len(reply) <= 2000, "Invalid clarification reply")
        if self._mode in {'offline_package','live_package'}:
            require(reply in {'draft_without_availability','recheck_readiness','stop'}, 'Unsupported clarification choice')
            if reply=='stop':return {'feedback':reply,'status':'stopped','clarification':''}
            from launchlens.launch_checks import availability_only_gap
            launch=state['launch'];notice='Continuing without availability wording.'
            try:
                if reply=='recheck_readiness':
                    launch=evaluate_launch(self._tools.read_launch(deepcopy(state['request'])),state['request']['evaluation_date'])
                    notice='Readiness still shows availability unconfirmed. Continuing without availability wording.'
                if availability_only_gap(launch):
                    permission={'request_sha256':digest(state['request']),'launch_sha256':digest(launch),'availability_wording_allowed':False}
                elif launch.get('decision')=='Proceed' and launch.get('promotional_draft_allowed'):
                    permission=None;notice='Authoritative readiness recheck passed. Availability wording remains excluded from this campaign.'
                else:
                    return {'launch':launch,'status':'held' if launch.get('decision')=='Hold' else 'stopped','clarification':'','continuation_notice':'Readiness remains unresolved. No promotional drafts created.'}
                return {'feedback':reply,'status':'running','clarification':'','launch':launch,'restricted_drafting':permission,'continuation_notice':notice}
            except Exception:
                return {'status':'failed','clarification':'','restricted_drafting':None,'continuation_notice':'Readiness could not be checked. Drafting remains paused.'}
        return {'feedback': reply, 'status': 'running', 'clarification': ''}

    def _required_objective_evidence(self, state):
        """Continue a UK restricted draft with exact approved claims, without controller search."""
        state = deepcopy(state)
        missing = missing_objective_claim_ids(state)
        if not missing:
            return state
        started = time.monotonic()
        try:
            require(callable(getattr(self._tools, 'fetch_objective_claims', None)),
                    'Exact objective evidence adapter missing')
            value = self._validate_evidence(
                deepcopy(self._tools.fetch_objective_claims(missing)), 'public_product_facts')
            state['evidence'].append(value)
            state['research_gaps'] = self._objective_gaps(state)
            require(not missing_objective_claim_ids(state), 'Required objective claims remain missing')
            self._event(state, 'fetch_required_objective_claims', 'completed', started,
                        origin='harness_required', claim_ids=missing)
        except Exception:
            state['status'] = 'failed'
            state['draft_failure'] = {'stage':'evidence_eligibility',
                'code':'required_objective_evidence_unavailable', 'field_path':'evidence',
                'rule':'exact_claim_fetch_failed'}
            self._event(state, 'fetch_required_objective_claims', 'failed_safely', started,
                        origin='harness_required')
        return state


    def _writer_failure_retryable(self,state):
        failure=state.get('draft_failure') or {}
        if failure.get('rule') in {'field_claim_coverage','objective_claim_coverage'}:
            from launchlens.package_content import citation_only_failures
            calls=getattr(self._writer,'calls',[])
            try:return bool(calls and citation_only_failures(calls[-1].get('candidate'),prepare_package_input(state)))
            except Exception:return False
        return failure.get('rule') not in {'invalid_claim_reference','evidence_validation_failed','prohibited_wording','prohibited_link','cta_mismatch'}

    def recover_writer_candidate(self,run_id,candidate,*,on_update=None):
        """Explicit saved-response revalidation; no research/Controller/Writer call."""
        require(self._lock.acquire(blocking=False),'Execution is running')
        try:
            self._check_id(run_id);state=self._snapshot()
            require(self._mode=='live_package' and state['status']=='failed' and not state['drafts'] and
                state['package'] is None and state['writing_attempts']==1 and state['retry_attempts']==0 and
                (state.get('draft_failure') or {}).get('rule') in {'field_claim_coverage','objective_claim_coverage'},
                'Saved Writer recovery unavailable')
            inputs=prepare_package_input(state);calls=getattr(self._writer,'calls',[])
            require(len(calls)==1 and calls[0].get('candidate')==candidate and
                calls[0]['binding']=={'run_id':run_id,'draft_version':0,'draft_sha256':None,
                    'authoritative_input_sha256':digest(inputs)},'Saved Writer binding differs')
            drafts,metadata=admit_package(candidate,inputs)
            self._execution_guard.reopen_for_saved_writer(state)
            state['drafts']=drafts;state['package']=metadata;state['status']='running'
            state['draft_history'].append({'version':1,'drafts':deepcopy(drafts),'package':deepcopy(metadata)})
            self._event(state,'generate_package','revalidated_saved_candidate',time.monotonic(),
                why='Revalidated the saved response using the approved section-heading citation rule; no new writing.')
            with tracing_context(enabled=False):self._graph.update_state(self._config(),state,as_node='dispatch')
        finally:self._lock.release()
        return self._execute(run_id,on_update=on_update,continue_checkpoint=True)

    def can_retry_writer(self):
        state=self.snapshot()
        return bool(state and self._mode in {'offline_package','live_package'} and state['status'] in {'failed','draft_incomplete'}
            and (state.get('draft_failure') or {}).get('stage')=='draft_validation' and not state['drafts']
            and self._writer_failure_retryable(state)
            and state['writing_attempts']==1 and state['retry_attempts']==0 and self._task_turns(state)+2<=self._max_turns
            and (self._execution_guard is None or self._execution_guard.can_retry_writer()))

    def retry_writer(self, run_id, *, on_update=None):
        require(self.can_retry_writer(),'Writer retry is unavailable')
        require(self._lock.acquire(blocking=False),'Execution is running')
        try:
            self._check_id(run_id);state=self._snapshot()
            require(state['status'] in {'failed','draft_incomplete'} and state['retry_attempts']==0,'Retry already consumed')
            prepare_package_input(state) # Independently verify original authority again.
            failed=[v['action'] for v in state['ledger'].values() if v['action']['name']=='generate_package' and v['status']=='failed']
            require(len(failed)==1,'One failed Writer action required')
            pending=deepcopy(failed[0]);pending['id']='retry-'+uuid4().hex
            pending['why']='Retry the rejected Writer output once, retaining the saved research and original diagnostic.'
            with tracing_context(enabled=False):
                self._graph.update_state(self._config(),{'status':'running','writer_retry':True,'retry_attempts':1,'pending':pending},as_node='decide')
        finally:self._lock.release()
        return self._execute(run_id,on_update=on_update)

    def stop(self,run_id):
        require(self._lock.acquire(blocking=False),'Execution is running; stop on rerun')
        try:
            self._check_id(run_id);state=self._snapshot()
            require(state['status'] in {'created','running','needs_clarification'},'Run is not active')
            with tracing_context(enabled=False):
                self._graph.update_state(self._config(),{**state,'status':'stopped','pending':None})
            if self._execution_guard is not None:self._execution_guard.stop()
        finally:self._lock.release()
