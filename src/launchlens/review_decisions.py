"""Pure grouped human decisions over exact draft/review bindings; no model calls.

Choices are human annotations, never evidence, launch permission or package approval.
All original findings remain intact. Revisions invalidate these choices by binding.
"""
from copy import deepcopy
from html import escape
import re
from launchlens.linkedin_drafting import digest
from launchlens.package_content import FORMATS, LABELS, risky_phrase_scan, package_value, text_fields, reviewer_hint

CATEGORY_LABELS={'availability_urgency':'Availability / urgency','invented_product_facts':'Product / portfolio claim',
 'preference_prediction':'Consumer claim','differentiation':'Differentiation','novelty':'Novelty / launch language',
 'ingredient_intensity':'Ingredient / intensity','grounding':'Factual support','completeness':'Completeness',
 'qualifications':'Qualifications','voice':'Brand voice','tone':'Tone','consistency':'Consistency'}


def field_label(path):
    if path=='$format':return 'Whole draft'
    parts=path.split('.')
    if len(parts)>=3 and parts[0] in {'concepts','sections'} and parts[1].isdigit():
        return ('Ad ' if parts[0]=='concepts' else 'Section ')+str(int(parts[1])+1)+' · '+parts[2].replace('_',' ').capitalize()
    if len(parts)==2 and parts[1].isdigit():return parts[0].replace('_',' ').capitalize()+' '+str(int(parts[1])+1)
    return {'cta':'CTA','primary_cta':'Primary CTA'}.get(path,path.replace('_',' ').capitalize())


def review_identity(state):
    """Full current content and review identity; never trust a model-provided ID alone."""
    return digest({'run_id':state['run_id'],'package':state.get('package'),
        'drafts':{f:state['drafts'][f]['draft'] for f in FORMATS},'review':state.get('review'),'card_policy':'phrase_spans_v2'})


def phrase_key(quote, category):
    return ' '.join(quote.casefold().split())


def current_scan(state):
    """Fresh deterministic matches; historical AI dispositions are not invented."""
    recorded={h['hit_id']:h for h in (state.get('review') or {}).get('risk_scan',[])}
    current_policy=bool((state.get('package') or {}).get('tone_policy_sha256'))
    hits=risky_phrase_scan(package_value(state),scan_additions='tone_v2' if current_policy else True)
    for hit in hits:
        prior=recorded.get(hit['hit_id'])
        if prior:hit['reviewer_disposition']=prior.get('reviewer_disposition','unassessed')
        else:hit['reviewer_disposition']='new_scan_match'
    return hits


def grouped_findings(state):
    review=state.get('review') or {};package=package_value(state);hits=current_scan(state)
    findings=[dict(f,format=name) for name,item in review.get('format_reviews',{}).items()
              for f in item['assessment']['findings']]
    occurrences={}
    def put(name,path,start,end,category,rows,protected=False,new_scan=False):
        context=dict(text_fields(package[name]['content'])).get(path,'')
        quote=context[start:end] if isinstance(start,int) else None
        key=(name,path,start,end);o=occurrences.setdefault(key,{'format':name,'content_field':path,
            'quote':quote,'context':context,'start':start,'end':end,'findings':[],
            'categories':[],'human_clearance_required':False,'new_scan_match':False})
        o['categories']=sorted(set(o['categories']+[category]));o['human_clearance_required'] |= protected
        o['new_scan_match'] |= new_scan
        o['findings'].extend(f for f in rows if f not in o['findings'])
    linked=set()
    for hit in hits:
        start,end=hit['start'],hit['end']
        # The key word is the editable span, not the rest of a novelty phrase.
        if hit['category']=='novelty' and hit['quote'].casefold().startswith('new '):end=start+3
        rows=[]
        for f in findings:
            if f['format']!=hit['format'] or f['content_field']!=hit['content_field']:continue
            text=dict(text_fields(package[f['format']]['content'])).get(f['content_field'],'')
            quote=f.get('quote')
            spans=[(m.start(),m.end()) for m in re.finditer(re.escape(quote),text)] if quote else []
            if hit['hit_id'] in f.get('scan_hit_ids',[]) or (hit.get('reviewer_disposition')!='new_scan_match' and any(a<=start and end<=b for a,b in spans)):
                rows.append(f);linked.add(digest(f))
        rows.sort(key=lambda f:(hit['hit_id'] not in f.get('scan_hit_ids',[]),hit['quote'].casefold() not in f.get('rationale','').casefold(),len(f.get('quote') or '')))
        put(hit['format'],hit['content_field'],start,end,hit['category'],rows,
            hit.get('human_clearance_required',False),hit.get('reviewer_disposition')=='new_scan_match')
    for f in findings:
        if digest(f) in linked:continue
        name,path,quote=f['format'],f['content_field'],f.get('quote')
        if not quote:put(name,path,None,None,f['dimension'],[f],f.get('human_clearance_required',False));continue
        target=dict(text_fields(package[name]['content'])).get(path,'')
        # Prefer a short exact term explicitly quoted by the Reviewer, then a
        # known key word inside its longer quote. Never invent text or offsets.
        terms=[m.group(1) for m in re.finditer(r"[‘'“\"]([^’'”\"]{1,60})[’'”\"]",f.get('rationale',''))]
        term=next((t for t in terms if len(t.split())<=6 and t.casefold() in quote.casefold()),None)
        if term is None:
            m=re.search(r'\b(?:new|designed (?:to|for)|guided the development|unique|lineup|family|presenting|introducing)\b',quote,re.I)
            term=m.group() if m else quote
        if term.casefold().startswith('new '):term='new'
        for match in re.finditer(re.escape(quote),target):
            inner=re.search(re.escape(term),match.group(),re.I)
            if inner:put(name,path,match.start()+inner.start(),match.start()+inner.end(),f['dimension'],[f],f.get('human_clearance_required',False))
    combined={}
    for o in occurrences.values():
        cats=o['categories'];o['severity']='blocking' if any(f.get('severity')=='blocking' for f in o['findings']) else 'advisory' if any(f.get('severity')=='advisory' for f in o['findings']) else 'cleared' if o['findings'] and all(f.get('severity')=='cleared' for f in o['findings']) else 'unassessed'
        o['needs_attention']=o['human_clearance_required'] or o['severity']!='cleared'
        category=next((c for c in cats if c in {'availability_urgency','invented_product_facts','preference_prediction'}),cats[0])
        phrase=phrase_key(o['quote'],category) if o['quote'] else LABELS[o['format']]+' · '+CATEGORY_LABELS.get(category,category)
        g=combined.setdefault(phrase,{'phrase':phrase,'category':category,'categories':[],'occurrences':[]})
        g['categories']=sorted(set(g['categories']+cats));o['id']='occ-'+digest([o['format'],o['content_field'],o['start'],o['end'],o['quote'],cats])[:16]
        g['occurrences'].append(o)
    result=list(combined.values())
    for g in result:
        g['id']='phrase-'+digest([g['phrase'],g['categories']])[:16]
        g['human_clearance_required']=any(o['human_clearance_required'] for o in g['occurrences'])
        g['needs_attention']=any(o['needs_attention'] for o in g['occurrences'])
    return sorted(result,key=lambda g:(not g['human_clearance_required'],not g['needs_attention'],g['phrase']))


def decision_book(state, existing=None):
    binding=review_identity(state)
    if existing and existing.get('binding')==binding:return deepcopy(existing)
    return {'binding':binding,'groups':{},'overrides':{},'events':[]}


def record_decision(state, book, identity, choice, *, occurrence=False, suggestion=None):
    if book.get('binding')!=review_identity(state):raise ValueError('Review version changed')
    if choice not in {'request_changes','keep_wording'}:raise ValueError('Unknown review choice')
    groups=grouped_findings(state)
    allowed={o['id'] for g in groups for o in g['occurrences']} if occurrence else {g['id'] for g in groups}
    if identity not in allowed:raise ValueError('Unknown occurrence or phrase')
    group=next(g for g in groups if (any(o['id']==identity for o in g['occurrences']) if occurrence else g['id']==identity))
    if suggestion is not None and (choice!='request_changes' or suggestion not in safe_hints(group)):
        raise ValueError('Suggestion is not an available screened hint')
    result=deepcopy(book);result['overrides' if occurrence else 'groups'][identity]=choice
    result.setdefault('replacements',{}).pop(identity,None)
    if suggestion is not None:result['replacements'][identity]=suggestion
    result['events'].append({'sequence':len(result['events'])+1,'scope':'occurrence' if occurrence else 'phrase',
        'identity':identity,'decision':choice,'binding':book['binding'],**({'suggestion':suggestion} if suggestion is not None else {})})
    return result


def effective_choice(book, group, occurrence):
    return book.get('overrides',{}).get(occurrence['id'],book.get('groups',{}).get(group['id']))


def unresolved_groups(groups,book):
    return [g for g in groups if any(o['needs_attention'] and not effective_choice(book,g,o) for o in g['occurrences'])]


def sentence_bounds(text,start,end):
    """Keep the complete sentence around an exact phrase, without character cuts."""
    lo=max(text.rfind('. ',0,start),text.rfind('! ',0,start),text.rfind('? ',0,start))+2
    if lo==1:lo=0
    ends=[v+1 for v in (text.find('. ',end),text.find('! ',end),text.find('? ',end)) if v>=0]
    return lo,min(ends) if ends else len(text)


def replacement_preview(occurrence, replacement):
    """Replace exactly one verified phrase span and return its full sentence.

    This conservative lexical fit check is not a claim of semantic/grammar proof.
    Complete-sentence substitutions, repeated boundary words and stale spans fail.
    """
    text=occurrence['context'];start,end=occurrence['start'],occurrence['end'];quote=occurrence['quote']
    if not isinstance(start,int) or not isinstance(end,int) or text[start:end]!=quote:return None
    if not isinstance(replacement,str) or not replacement.strip() or len(replacement.split())>len(quote.split())+3:return None
    if any(c in replacement for c in '.!?;\n'):return None
    if reviewer_hint({'quote':quote,'suggested_change':replacement})[0] is None:return None
    left=re.findall(r"[\w'-]+",text[:start].casefold());words=re.findall(r"[\w'-]+",replacement.casefold());right=re.findall(r"[\w'-]+",text[end:].casefold())
    if any(words[-n:]==right[:n] for n in range(1,min(len(words),len(right))+1)):return None
    if any(left[-n:]==words[:n] for n in range(1,min(len(left),len(words))+1)):return None
    lo,hi=sentence_bounds(text,start,end)
    # A phrase replacement must not repeat an existing phrase elsewhere in the
    # sentence (e.g. 'distinct option ... Coca-Cola distinct option').
    rest=' '.join(re.findall(r"[\w'-]+",(text[lo:start]+' '+text[end:hi]).casefold()))
    normalized=' '.join(words)
    if normalized and re.search(r'(?<!\w)'+re.escape(normalized)+r'(?!\w)',rest):return None
    return text[lo:start]+replacement+text[end:hi]


def _phrase_hint(finding,occurrence):
    quote=finding.get('quote');suggestion=finding.get('suggested_change')
    if not isinstance(quote,str) or not isinstance(suggestion,str):return None
    text=occurrence['context'];start,end=occurrence['start'],occurrence['end']
    if not isinstance(start,int):return None
    # Narrow a larger Reviewer replacement ONLY when all text outside the
    # selected phrase is preserved exactly. Otherwise it cannot replace that span.
    for match in re.finditer(re.escape(quote),text):
        if not match.start()<=start<end<=match.end():continue
        prefix=text[match.start():start];suffix=text[end:match.end()]
        if not suggestion.casefold().startswith(prefix.casefold()) or not suggestion.casefold().endswith(suffix.casefold()):continue
        candidate=suggestion[len(prefix):len(suggestion)-len(suffix) if suffix else None].strip()
        if occurrence['quote'][:1].islower() and candidate:candidate=candidate[:1].lower()+candidate[1:]
        if replacement_preview(occurrence,candidate) is not None:return candidate
    return None


def safe_hints(group):
    """Only phrase-sized suggestions that fit every affected occurrence."""
    occurrences=group['occurrences'];hints=[]
    for o in occurrences:
        for finding in o['findings']:
            hint=_phrase_hint(finding,o)
            if hint and all(replacement_preview(other,hint) is not None for other in occurrences) and hint not in hints:hints.append(hint)
    alternatives={'introducing':['Meet','Explore'],'unique':['float-inspired','cherry-and-vanilla'],
        'innovative':['float-inspired'],'innovation':['soda-float inspiration'],
        'favorite':['soda-float idea'],'classic favorite':['classic soda-float idea'],
        'where you can find':['the inspiration behind'],'the difference':['the flavor notes']}
    if not hints:
        for candidate in alternatives.get(group['phrase'],[])[:2]:
            if all(replacement_preview(o,candidate) is not None for o in occurrences):hints.append(candidate)
    return hints[:2]


def highlighted(text, occurrences, *, target=None):
    """Escape first, merge overlapping source spans, never replace or truncate draft text."""
    spans=sorted((o['start'],o['end']) for o in occurrences if o['quote'] and
        isinstance(o['start'],int) and isinstance(o['end'],int) and
        0<=o['start']<o['end']<=len(text) and text[o['start']:o['end']]==o['quote'])
    merged=[]
    for start,end in spans:
        if merged and start<=merged[-1][1]:merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
        else:merged.append((start,end))
    parts=[];cursor=0
    for start,end in merged:
        anchor=' id="selected-phrase"' if target and start<=target[0]<target[1]<=end else ''
        parts.extend([escape(text[cursor:start]),'<mark'+anchor+'>'+escape(text[start:end])+'</mark>']);cursor=end
    return ''.join(parts)+escape(text[cursor:])


def revision_feedback(state,book,notes=''):
    if book.get('binding')!=review_identity(state):raise ValueError('Review version changed')
    lines=[]
    for group in grouped_findings(state):
        for choice in ('request_changes','keep_wording'):
            occurrences=[o for o in group['occurrences'] if effective_choice(book,group,o)==choice]
            if occurrences:
                locations=', '.join(o['format']+'.'+o['content_field']+'['+str(o['start'])+':'+str(o['end'])+']' for o in occurrences)
                lines.append(('Change ' if choice=='request_changes' else 'Human prefers keeping ')+
                    '“'+group['phrase']+'” at '+locations)
    for group in grouped_findings(state):
        for o in group['occurrences']:
            if effective_choice(book,group,o)!='request_changes':continue
            selected=book.get('replacements',{}).get(o['id'],book.get('replacements',{}).get(group['id']))
            if selected:
                if selected not in safe_hints(group):raise ValueError('Selected hint changed; review the current wording again')
                lines.append('Requested phrase replacement at '+o['format']+'.'+o['content_field']+'['+str(o['start'])+':'+str(o['end'])+']: replace only “'+o['quote']+'” with “'+selected+'”; preserve the rest of the sentence (human preference; retain evidence and qualifications)')
    if notes.strip():lines.append('Other owner notes: '+notes.strip())
    if not lines:return ''
    result='Human wording feedback only; evidence and launch restrictions remain enforced.\n'+'\n'.join(lines)
    from launchlens.package_content import MAX_PACKAGE_FEEDBACK
    if len(result)>MAX_PACKAGE_FEEDBACK:raise ValueError('Selected feedback exceeds 12000 characters; narrow the choices or notes')
    return result


def saved_review_available():
    from launchlens.package_content import ROOT
    return (ROOT/'data/private/current-review.json').is_file()


def load_saved_review():
    """Optional explicitly provisioned artifact; read-only display, never graph restore.

    Clean checkouts work without it. Source and raw review must hash-match the local
    pointer and revalidate against original authority before any content is shown.
    """
    from pathlib import Path
    import hashlib,json
    from launchlens.package_content import ROOT,authoritative_package_binding,validate_package_review
    pointer=ROOT/'data/private/current-review.json'
    if not pointer.is_file() or pointer.is_symlink() or pointer.stat().st_mode&0o077:raise ValueError('Saved review is unavailable')
    spec=json.loads(pointer.read_text());loaded={}
    for key in ['source','review']:
        entry=spec[key];relative=Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('Invalid saved review path')
        path=ROOT/relative
        if not path.resolve().is_relative_to((ROOT/'data/generated').resolve()) or path.is_symlink():raise ValueError('Invalid saved review path')
        if not path.is_file() or path.stat().st_size>8_000_000 or path.stat().st_mode&0o077:raise ValueError('Saved review is unavailable')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Saved review has changed')
        loaded[key]=json.loads(raw)
    state=loaded['source'];result=loaded['review'];_,_,binding=authoritative_package_binding(state)
    if binding!=result['binding']:raise ValueError('Saved review binding differs')
    checked=validate_package_review(result['raw_response'],state,isolate_findings=result.get('assessment_policy')=='isolated_findings_v1',scan_additions=result.get('scan_additions',False))
    state=deepcopy(state);state['review']=checked
    for f in FORMATS:state['drafts'][f]['review_status']=checked['format_reviews'][f]['review_status']
    state['human_accepted']=False
    return state


def carry_unchanged_decisions(before,after,book):
    """Transfer only decisions for byte-identical fields, never edited context."""
    result=decision_book(after);old={}
    def key(o):return (o['format'],o['content_field'],o['context'],o['quote'],o['start'],o['end'],tuple(o['categories']))
    for group in grouped_findings(before):
        for occurrence in group['occurrences']:
            choice=effective_choice(book,group,occurrence)
            if choice:old[key(occurrence)]=choice
    for group in grouped_findings(after):
        for occurrence in group['occurrences']:
            choice=old.get(key(occurrence))
            if choice:result=record_decision(after,result,occurrence['id'],choice,occurrence=True)
    return result
