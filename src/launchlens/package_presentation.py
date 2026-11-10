"""Pure run-page presentation, comparisons and internal exports; no inference/I/O."""
from copy import deepcopy
from difflib import SequenceMatcher
from html import escape
from launchlens.linkedin_drafting import digest
from launchlens.package_content import FORMATS,LABELS,text_fields
from launchlens.review_decisions import grouped_findings,effective_choice,review_identity
SIMULATION_LABEL='Simulated draft · fictional scenario · not affiliated with The Coca-Cola Company'


def must_decide_occurrence(occurrence):
    return occurrence['needs_attention'] and (occurrence['human_clearance_required'] or occurrence['severity'] in {'blocking','unassessed'})


def must_decide(group):
    return any(must_decide_occurrence(o) for o in group['occurrences'])


def progress(groups,book):
    groups=[g for g in groups if g['needs_attention']]
    decided=lambda g:all(not o['needs_attention'] or effective_choice(book,g,o) for o in g['occurrences'])
    return {'total':len(groups),'decided':sum(decided(g) for g in groups),
        'rewrite':sum(any(effective_choice(book,g,o)=='request_changes' for o in g['occurrences']) for g in groups),
        'kept':sum(decided(g) and all(effective_choice(book,g,o)=='keep_wording' for o in g['occurrences'] if o['needs_attention']) for g in groups),
        'skipped':sum(not decided(g) for g in groups),
        'must_left':sum(any(must_decide_occurrence(o) and not effective_choice(book,g,o) for o in g['occurrences']) for g in groups)}


def choice_label(group,book):
    choices={effective_choice(book,group,o) for o in group['occurrences'] if o['needs_attention']}
    if choices=={'keep_wording'}:return 'Kept as is'
    if choices=={'request_changes'}:
        hint=book.get('replacements',{}).get(group['id'])
        return 'Use “'+hint+'”' if hint else 'Writer will rephrase'
    return 'Mixed choices' if choices-{None} else 'Not decided'


def version_content(state,version):
    if (state.get('package') or {}).get('version')==version:return {f:state['drafts'][f]['draft'] for f in FORMATS}
    item=next((h for h in state.get('draft_history',[]) if h['version']==version),None)
    return {f:item['drafts'][f]['draft'] for f in FORMATS} if item else None


def changed_fields(state,format_name):
    current=(state.get('package') or {}).get('version',1)
    old=version_content(state,current-1);new=version_content(state,current)
    if old is None or new is None:return []
    a=dict(text_fields(old[format_name]['content']));b=dict(text_fields(new[format_name]['content']))
    return [p for p in dict.fromkeys([*a,*b]) if a.get(p)!=b.get(p)]


def word_diff(before,after):
    a=before.split();b=after.split();parts=[]
    for tag,i,j,k,l in SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
        if tag in {'delete','replace'}:parts.append('<del>'+escape(' '.join(a[i:j]))+'</del>')
        if tag in {'insert','replace'}:parts.append('<ins>'+escape(' '.join(b[k:l]))+'</ins>')
        if tag=='equal':parts.append(escape(' '.join(a[i:j])))
    return ' '.join(parts)


def approval_issues(state,book):
    review=state.get('review') or {};issues=[]
    from launchlens.package_content import authoritative_package_binding
    try:authoritative_package_binding(state)
    except Exception:issues.append('Current content or authoritative evidence binding is invalid.')
    if state.get('status')!='awaiting_human_review' or not review.get('review_complete'):issues.append('A complete current-version review is required.')
    if review.get('binding',{}).get('draft_sha256')!=(state.get('package') or {}).get('package_sha256'):issues.append('Review does not match the current package.')
    if book.get('binding')!=review_identity(state):issues.append('Wording choices belong to another review.')
    groups=grouped_findings(state);p=progress(groups,book)
    if review.get('assessment_policy')=='human_edit_rescan_v1':
        from launchlens.package_content import verify_human_edit_review
        try:verify_human_edit_review(state)
        except Exception:issues.append('The saved human edit or rescan is invalid.')
    if p['must_left']:issues.append('Decide on every must-decide phrase first.')
    if any(must_decide_occurrence(o) and effective_choice(book,g,o)=='request_changes' for g in groups for o in g['occurrences']):
        issues.append('Resolve must-decide wording with Keep wording or Edit it myself.' if state.get('revision_attempts',0)>=3 else 'Requested must-decide changes remain unresolved in this version.')
    if not state.get('launch') or state['launch'].get('decision')=='Hold':issues.append('Launch restrictions prevent approval.')
    return issues


def approve_internal(state,book,acknowledged):
    if acknowledged is not True or approval_issues(state,book):raise ValueError('Internal approval requirements are not met')
    return {'binding':review_identity(state),'decisions_sha256':digest(book),
        'version':state['package']['version'],'internal_approved':True,'publishing_allowed':False,
        'simulation_label':SIMULATION_LABEL}


def approval_matches(state,book,record):
    # Approval belongs to immutable content and its recorded disposition, not later
    # instructions the owner may prepare for another version.
    if not record or book.get('binding')!=review_identity(state):return False
    accepted=record.get('approval_decisions',book)
    return bool(record.get('binding')==review_identity(state) and
        record.get('decisions_sha256')==digest(accepted) and accepted.get('binding')==review_identity(state) and
        record.get('internal_approved') is True and record.get('publishing_allowed') is False and
        not approval_issues(state,accepted))


def current_wording_book(state,book):
    """Pure preview of explicit accept-as-is; never persist a choice on rendering."""
    from launchlens.review_decisions import record_decision
    if book.get('binding')!=review_identity(state):raise ValueError('Review version changed')
    accepted=deepcopy(book)
    for group in grouped_findings(state):
        if not group['needs_attention']:continue
        if accepted.get('groups',{}).get(group['id'])!='keep_wording':
            accepted=record_decision(state,accepted,group['id'],'keep_wording')
        for occurrence in group['occurrences']:
            if occurrence['needs_attention'] and effective_choice(accepted,group,occurrence)!='keep_wording':
                accepted=record_decision(state,accepted,occurrence['id'],'keep_wording',occurrence=True)
    return accepted


def approve_current_version(state,book,acknowledged):
    """Human approval explicitly supersedes wording requests, never evidence/policy."""
    from datetime import datetime,timezone
    if acknowledged is not True:raise ValueError('Explicit current-wording acceptance required')
    accepted=current_wording_book(state,book)
    record=approve_internal(state,accepted,True)  # Original authority/launch/review checks.
    record.update(wording_disposition='accepted_as_is',prior_decisions_sha256=digest(book),approval_decisions=deepcopy(accepted),
        approved_at=datetime.now(timezone.utc).isoformat())
    return accepted,record


def restored_approval(state,book,store):
    """Read only: restore a protected approval receipt for this exact version/choices."""
    if store is None:return None
    import json
    candidates=[]
    for path in store.path.glob('human-internal-approval-*.json'):
        if path.is_symlink() or path.stat().st_mode & 0o077 or path.stat().st_size>100_000:continue
        try:
            record=json.loads(path.read_text())
            if approval_matches(state,book,record):
                record.setdefault('approval_decisions',deepcopy(book))
                candidates.append((path.stat().st_mtime_ns,record))
        except (ValueError,KeyError,TypeError):continue
    return max(candidates,key=lambda item:item[0])[1] if candidates else None


def markdown_package(state,*,approved=False):
    request=state['request'];lines=['# Coca-Cola Cherry Float — '+request['market_id']+' GTM package',
        '',SIMULATION_LABEL,'','Version '+str(state['package']['version'])+' · '+('Approved for internal use' if approved else 'Human approval pending')+' · Nothing published',
        '','Evaluation date: '+request['evaluation_date'],'']
    if state.get('review',{}).get('no_new_model_review'):lines+=['Human-edited current version · Re-scanned; no new AI review.','']
    for f in FORMATS:
        lines+=['## '+LABELS[f],'']
        for path,text in text_fields(state['drafts'][f]['draft']['content']):
            lines+=['### '+path.replace('_',' ').replace('.',' · '), '',text,'']
        refs=state['drafts'][f]['draft']['claim_references']
        if refs:lines+=['Evidence references: '+'; '.join(x['content_field']+': '+', '.join(x['claim_ids']) for x in refs),'']
    lines+=['## Evidence and restrictions','','Product facts remain distinct from simulated launch approvals. Wording decisions do not change product evidence or authorize availability.','']
    seen=set()
    for result in state.get('evidence',[]):
        for row in result['records']:
            if row['unit_id'] not in {'PROD-002','PROD-003'} or row['unit_id'] in seen:continue
            seen.add(row['unit_id']);p=row['evidence_payload']
            lines+=['### '+row['unit_id'],'',p['primary_text'],'']
            for source in p.get('source_references',[]):
                url=source.get('source_url') or source.get('url')
                if url:lines.append('- '+url)
    return '\n'.join(lines)+'\n'


def current_review_matches(state):
    binding=(state.get('review') or {}).get('binding',{})
    package=state.get('package') or {}
    return binding.get('draft_version')==package.get('version') and binding.get('draft_sha256')==package.get('package_sha256')


def card_reason(group, *, demo=False):
    """Presentation only: raw fixture explanations remain under Technical details."""
    import re
    if not demo:
        reasons=list(dict.fromkeys(f['rationale'] for o in group['occurrences'] for f in o['findings']))
        reasons=[r for r in reasons if not re.search(r'fixture|mock assessment|scripted|demo simulation',r,re.I)]
        if reasons:return reasons[0]
    return {
        'availability_urgency':'Check whether this wording implies availability or launch timing that still needs confirmation.',
        'invented_product_facts':'Check whether the supplied product evidence supports this wording.',
        'preference_prediction':'Check whether this wording makes an unsupported claim about consumer preferences.',
        'ingredient_intensity':'Check whether flavor inspiration is being presented as an ingredient or intensity claim.',
        'novelty':'Check whether this wording suggests a new product or launch without supporting evidence.',
        'differentiation':'Check whether this wording implies a proven difference or advantage.'
    }.get(group['category'],'Check this wording against the supplied evidence, tone and campaign guidance.')


def draft_markup(state, name, *, focus=None):
    """Current-version escaped draft, with an exact optional scroll/highlight anchor."""
    from launchlens.review_decisions import grouped_findings,highlighted,field_label
    value=state if current_review_matches(state) else dict(state,review={})
    groups=grouped_findings(value);parts=[]
    for path,text in text_fields(state['drafts'][name]['draft']['content']):
        occurrences=[o for g in groups for o in g['occurrences'] if o['format']==name and o['content_field']==path]
        target=None
        if focus and focus.get('format')==name and focus.get('content_field')==path:
            start,end=focus.get('start'),focus.get('end')
            if isinstance(start,int) and isinstance(end,int) and 0<=start<end<=len(text) and text[start:end]==focus.get('quote'):
                target=(start,end)
        parts+=['<small class="review-field-label">'+escape(field_label(path))+'</small>',
            '<p>'+highlighted(text,occurrences,target=target)+'</p>']
    return '<article class="draft-copy">'+''.join(parts)+'</article>'


def draft_modal_document(state,name,*,focus=None):
    markup=draft_markup(state,name,focus=focus)
    return ('<!doctype html><html><head><meta charset="utf-8"><style>'
        'html{color-scheme:dark;scroll-behavior:auto}body{margin:8px 14px 30px;font:16px/1.65 -apple-system,BlinkMacSystemFont,sans-serif;background:#1b2430;color:#f0f4fa}'
        'p{white-space:pre-wrap;overflow-wrap:anywhere;margin:4px 0 22px}small{display:block;color:#b8c4d4;font-size:13px}'
        'mark{background:#654516;color:#fff1d6;border-bottom:2px solid #ff9f0a;border-radius:3px;padding:1px 2px}'
        '#selected-phrase{outline:2px solid #ff9f0a;scroll-margin:100px}'
        '</style></head><body>'+markup+
        '<script>requestAnimationFrame(()=>{const target=document.getElementById("selected-phrase");if(target)window.scrollTo(0,Math.max(0,target.getBoundingClientRect().top+window.scrollY-window.innerHeight/2));});</script></body></html>')


def restored_decisions(state,store):
    """Restore only replay-validated human receipts for the exact current review."""
    if store is None:return None
    from launchlens.review_decisions import decision_book,record_decision,review_identity
    import json
    candidates=[]
    for path in store.path.glob('human-decision-*.json'):
        if path.is_symlink() or path.stat().st_mode & 0o077 or path.stat().st_size>2_000_000:continue
        try:
            value=json.loads(path.read_text())
            if value.get('binding')!=review_identity(state):continue
            book=decision_book(state)
            for event in value['events']:
                book=record_decision(state,book,event['identity'],event['decision'],occurrence=event['scope']=='occurrence',suggestion=event.get('suggestion'))
            if book==value:candidates.append((len(book['events']),path.stat().st_mtime_ns,book))
        except (ValueError,KeyError,TypeError):continue
    return max(candidates,key=lambda v:(v[0],v[1]))[2] if candidates else None
