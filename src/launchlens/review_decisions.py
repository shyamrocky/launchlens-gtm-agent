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
        'drafts':{f:state['drafts'][f]['draft'] for f in FORMATS},'review':state.get('review')})


def phrase_key(quote, category):
    q=' '.join(quote.casefold().split())
    if category=='invented_product_facts' and re.search(r'\b(?:lineup|family)\b',q):return 'lineup / Coca-Cola family'
    if category=='novelty' and q!='introducing':return 'innovation / new / latest'
    if category=='differentiation' and q.startswith('unique'):return 'unique'
    if category=='preference_prediction' and q in {'favorite','favourite','classic favorite','classic favourite'}:return 'classic favorite'
    return q


def grouped_findings(state):
    review=state.get('review') or {};package=package_value(state)
    hits=review.get('risk_scan') or risky_phrase_scan(package)
    groups={};linked=set()
    findings=[dict(f,format=name) for name,item in review.get('format_reviews',{}).items()
              for f in item['assessment']['findings']]
    def put(name,path,quote,category,start,end,rows,protected=False):
        phrase=phrase_key(quote,category) if quote else LABELS[name]+' · '+CATEGORY_LABELS.get(category,category)
        gid='phrase-'+digest([phrase,category])[:16]
        group=groups.setdefault(gid,{'id':gid,'phrase':phrase,'category':category,'occurrences':[]})
        oid='occ-'+digest([name,path,start,end,quote,category])[:16]
        existing=next((o for o in group['occurrences'] if o['id']==oid),None)
        severity='blocking' if any(f.get('severity')=='blocking' for f in rows) else 'advisory' if any(f.get('severity')=='advisory' for f in rows) else 'cleared' if rows and all(f.get('severity')=='cleared' for f in rows) else 'unassessed'
        context=dict(text_fields(package[name]['content'])).get(path,'')
        occurrence={'id':oid,'format':name,'content_field':path,'quote':quote,'context':context,
            'start':start,'end':end,'findings':rows,'human_clearance_required':protected,
            'severity':severity,'needs_attention':protected or severity!='cleared'}
        if existing:existing['findings'].extend(r for r in rows if r not in existing['findings'])
        else:group['occurrences'].append(occurrence)
    for hit in hits:
        rows=[f for f in findings if hit['hit_id'] in f.get('scan_hit_ids',[])]
        linked.update(digest(f) for f in rows)
        put(hit['format'],hit['content_field'],hit['quote'],hit['category'],hit['start'],hit['end'],rows,hit.get('human_clearance_required',False))
    for f in findings:
        if digest(f) in linked:continue
        name=f['format'];quote=f.get('quote');path=f['content_field'];category=f['dimension']
        target=dict(text_fields(package[name]['content'])).get(path,'')
        starts=[m.start() for m in re.finditer(re.escape(quote),target)] if quote else [None]
        for start in starts:put(name,path,quote,category,start,start+len(quote) if quote else None,[f],f.get('human_clearance_required',False))
    # First merge overlapping spans within a field, regardless of category or
    # whether a row came from the scan or independent Reviewer. Raw rows stay intact.
    occurrences=[dict(o,categories=[g['category']]) for g in groups.values() for o in g['occurrences']]
    merged=[]
    for occurrence in sorted(occurrences,key=lambda o:(o['format'],o['content_field'],o['start'] if o['start'] is not None else -1,o['end'] or -1)):
        old=merged[-1] if merged else None
        overlap=(old is not None and occurrence['format']==old['format'] and occurrence['content_field']==old['content_field'] and
            isinstance(occurrence['start'],int) and isinstance(old['start'],int) and occurrence['start']<old['end'])
        if overlap:
            old['start']=min(old['start'],occurrence['start']);old['end']=max(old['end'],occurrence['end'])
            old['quote']=old['context'][old['start']:old['end']]
            old['categories']=sorted(set(old['categories']+occurrence['categories']))
            old['findings'].extend(f for f in occurrence['findings'] if f not in old['findings'])
            old['human_clearance_required'] |= occurrence['human_clearance_required']
            old['needs_attention'] |= occurrence['needs_attention']
            old['severity']=max((old['severity'],occurrence['severity']),key=lambda v:{'cleared':0,'unassessed':1,'advisory':2,'blocking':3}[v])
        else:merged.append(deepcopy(occurrence))
    combined={}
    for o in merged:
        categories=sorted(o['categories']);category=next((c for c in categories if c in {'availability_urgency','invented_product_facts','preference_prediction'}),categories[0])
        phrase=phrase_key(o['quote'],category) if o['quote'] else LABELS[o['format']]+' · '+CATEGORY_LABELS.get(category,category)
        # A larger merged wording span is shown verbatim, never reduced to an alias.
        if len(categories)>1 and o['quote']:phrase=o['quote']
        identity=phrase.casefold();g=combined.setdefault(identity,{'phrase':phrase,'category':category,'categories':[], 'occurrences':[]})
        g['categories']=sorted(set(g['categories']+categories))
        o['id']='occ-'+digest([o['format'],o['content_field'],o['start'],o['end'],o['quote'],categories])[:16]
        g['occurrences'].append(o)
    result=list(combined.values())
    for group in result:
        group['id']='phrase-'+digest([group['phrase'].casefold(),group['categories']])[:16]
        group['human_clearance_required']=any(o['human_clearance_required'] for o in group['occurrences'])
        group['needs_attention']=any(o['needs_attention'] for o in group['occurrences'])
    return sorted(result,key=lambda g:(not g['human_clearance_required'],not g['needs_attention'],g['phrase'].casefold()))


def decision_book(state, existing=None):
    binding=review_identity(state)
    if existing and existing.get('binding')==binding:return deepcopy(existing)
    return {'binding':binding,'groups':{},'overrides':{},'events':[]}


def record_decision(state, book, identity, choice, *, occurrence=False):
    if book.get('binding')!=review_identity(state):raise ValueError('Review version changed')
    if choice not in {'request_changes','keep_wording'}:raise ValueError('Unknown review choice')
    groups=grouped_findings(state)
    allowed={o['id'] for g in groups for o in g['occurrences']} if occurrence else {g['id'] for g in groups}
    if identity not in allowed:raise ValueError('Unknown occurrence or phrase')
    result=deepcopy(book);result['overrides' if occurrence else 'groups'][identity]=choice
    result['events'].append({'sequence':len(result['events'])+1,'scope':'occurrence' if occurrence else 'phrase',
        'identity':identity,'decision':choice,'binding':book['binding']})
    return result


def effective_choice(book, group, occurrence):
    return book.get('overrides',{}).get(occurrence['id'],book.get('groups',{}).get(group['id']))


def unresolved_groups(groups,book):
    return [g for g in groups if any(o['needs_attention'] and not effective_choice(book,g,o) for o in g['occurrences'])]


def safe_hints(group):
    """Advisory only: screened Reviewer hints, then at most two local alternatives.

    No extra inference or automatic edits. Unknown/grammatical cases fall back to
    the Writer instead of inventing a product claim or promising a safe rewrite.
    """
    hints=[]
    for occurrence in group['occurrences']:
        for finding in occurrence['findings']:
            hint,_=reviewer_hint(finding)
            if hint and hint not in hints:hints.append(hint)
    if hints:return hints[:2]
    alternatives={
        'unique':['float-inspired','cherry-and-vanilla'],
        'unique twist':['soda-float inspiration','cherry-and-vanilla notes'],
        'innovative':['float-inspired','cherry-and-vanilla'],
        'innovation':['soda-float inspiration','flavor exploration'],
        'new flavor':['cherry-and-vanilla flavor','float-inspired flavor'],
        'latest creation':['Cherry Float','float-inspired flavor'],
        'classic favorite':['classic soda-float idea','soda-float inspiration'],
        'favorite':['soda-float idea','flavor inspiration'],
        'where you can find':['the inspiration behind','the flavor notes in'],
        'the difference':['the flavor notes','the soda-float inspiration'],
    }
    originals=list(dict.fromkeys(o['quote'] for o in group['occurrences'] if o['quote']))
    candidates=alternatives.get(group['phrase'].casefold(),[])
    if not candidates and len(originals)==1:candidates=alternatives.get(originals[0].casefold(),[])
    for candidate in candidates[:2]:
        # Test against EVERY merged original, not just a short alias.
        if all(reviewer_hint({'quote':original,'suggested_change':candidate})[0] for original in originals):
            hints.append(candidate)
    return hints[:2]


def highlighted(text, occurrences):
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
        parts.extend([escape(text[cursor:start]),'<mark>'+escape(text[start:end])+'</mark>']);cursor=end
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
    checked=validate_package_review(result['raw_response'],state,isolate_findings=result.get('assessment_policy')=='isolated_findings_v1')
    state=deepcopy(state);state['review']=checked
    for f in FORMATS:state['drafts'][f]['review_status']=checked['format_reviews'][f]['review_status']
    state['human_accepted']=False
    return state
