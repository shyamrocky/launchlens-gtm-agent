"""Compact Reviewer judgments; deterministic expansion preserves exact occurrences."""
from copy import deepcopy
import re
from launchlens.linkedin_drafting import digest
PROTOCOL='phrase_groups_v1'
DIMENSIONS=['grounding','qualifications','voice','tone','consistency','completeness']

def phrase_groups(package, *, scan_additions=True):
    from launchlens.package_content import risky_phrase_scan
    groups={}
    for hit in risky_phrase_scan(package,scan_additions=scan_additions):
        key=(hit['quote'].casefold(),hit['category'])
        group=groups.setdefault(key,{'group_id':'group-'+digest(key)[:16],
            'phrase':hit['quote'].casefold(),'category':hit['category'],'locations':[]})
        group['locations'].append({'location_id':hit['hit_id'],'format':hit['format'],
            'content_field':hit['content_field'],'start':hit['start'],'end':hit['end']})
    return list(groups.values())

def group_schema(groups):
    from launchlens.package_content import FORMATS
    def obj(properties):return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
    text={'type':'string','minLength':1}
    judgment={'dimension':{'type':'string','enum':DIMENSIONS},
        'severity':{'type':'string','enum':['blocking','advisory','cleared']},
        'reason':text,'suggestion':text,
        'claim_ids':{'type':'array','maxItems':2,'items':{'type':'string','enum':['PROD-002','PROD-003']}}}
    override=obj({'location_id':text,'meaning_differs':{'type':'boolean'},**judgment})
    group=obj({'group_id':{'type':'string',**({'enum':[g['group_id'] for g in groups]} if groups else {})},**judgment,
        'occurrence_judgments':{'type':'array','maxItems':40,'items':override}})
    additional=obj({'format':{'type':'string','enum':list(FORMATS)},'content_field':text,
        'quote':{'type':['string','null']},**judgment})
    return obj({'group_judgments':{'type':'array','minItems':len(groups),'maxItems':len(groups),'items':group},
        'additional_findings':{'type':'array','maxItems':12,'items':additional}})

def word_count(text):return len(re.findall(r'\S+',text)) if isinstance(text,str) else 10**9

def expand_judgments(value,package, *, scan_additions=True):
    """No model-invented locations, evidence, quotes, or inherited clearance."""
    from launchlens.package_content import FORMATS,risky_phrase_scan,resolve_field
    groups=phrase_groups(package,scan_additions=scan_additions);by_group={g['group_id']:g for g in groups}
    hits={h['hit_id']:h for h in risky_phrase_scan(package,scan_additions=scan_additions)}
    expanded={f:{'findings':[]} for f in FORMATS};errors=[];seen=set()
    allowed={'dimension','severity','reason','suggestion','claim_ids'}
    def valid(row):
        return (isinstance(row,dict) and isinstance(row.get('dimension'),str) and row.get('dimension') in DIMENSIONS and
            isinstance(row.get('severity'),str) and row.get('severity') in {'blocking','advisory','cleared'} and
            isinstance(row.get('reason'),str) and 0<word_count(row['reason'])<=25 and
            isinstance(row.get('suggestion'),str) and 0<word_count(row['suggestion'])<=12 and
            isinstance(row.get('claim_ids'),list) and len(row['claim_ids'])<=2 and
            all(isinstance(c,str) and c in ('PROD-002','PROD-003') for c in row['claim_ids']) and
            len(set(row['claim_ids']))==len(row['claim_ids']))
    def finding(row,path,quote,ids):
        return {'dimension':row['dimension'],'content_field':path,'quote':quote,
            'severity':row['severity'],'rationale':row['reason'],'suggested_change':row['suggestion'],
            'claim_ids':deepcopy(row['claim_ids']),'scan_hit_ids':ids}
    if not isinstance(value,dict) or set(value)!={'group_judgments','additional_findings'} or not isinstance(value.get('group_judgments'),list) or not isinstance(value.get('additional_findings'),list):
        return expanded,['malformed_group_review']
    for row in value['group_judgments']:
        if isinstance(row,dict) and isinstance(row.get('claim_ids'),list) and any(not isinstance(c,str) or c not in ('PROD-002','PROD-003') for c in row['claim_ids']):
            from launchlens.package_content import PackageError
            raise PackageError(code='structure_or_evidence_reference',field_path='claim_references',rule='invalid_claim_reference')
        if not isinstance(row,dict) or set(row)!=allowed|{'group_id','occurrence_judgments'} or not valid(row):
            errors.append('group_judgment_invalid_or_word_limit');continue
        gid=row['group_id']
        if gid not in by_group or gid in seen:errors.append('duplicate_or_unknown_group');continue
        seen.add(gid);group=by_group[gid];locations={l['location_id']:l for l in group['locations']};overrides={}
        if not isinstance(row['occurrence_judgments'],list):errors.append('invalid_occurrence_judgments');continue
        for o in row['occurrence_judgments']:
            if (not isinstance(o,dict) or set(o)!=allowed|{'location_id','meaning_differs'} or not valid(o)
                or o.get('meaning_differs') is not True or o['location_id'] not in locations or o['location_id'] in overrides):
                errors.append('occurrence_meaning_difference_required');continue
            overrides[o['location_id']]=o
        for location in group['locations']:
            hit=hits[location['location_id']];chosen=overrides.get(location['location_id'],row)
            expanded[hit['format']]['findings'].append(finding(chosen,hit['content_field'],hit['quote'],[hit['hit_id']]))
    if seen!=set(by_group):errors.append('group_coverage_missing')
    if len(value['additional_findings'])>12:errors.append('too_many_additional_findings')
    for row in value['additional_findings'][:12]:
        if isinstance(row,dict) and isinstance(row.get('claim_ids'),list) and any(not isinstance(c,str) or c not in ('PROD-002','PROD-003') for c in row['claim_ids']):
            from launchlens.package_content import PackageError
            raise PackageError(code='structure_or_evidence_reference',field_path='claim_references',rule='invalid_claim_reference')
        if not isinstance(row,dict) or set(row)!=allowed|{'format','content_field','quote'} or not valid(row) or row['format'] not in FORMATS:
            errors.append('additional_finding_invalid_or_word_limit');continue
        path=row['content_field'];quote=row['quote']
        if quote is None:
            if path!='$format':errors.append('format_scope_required');continue
        else:
            try:target=resolve_field(package[row['format']]['content'],path)
            except Exception:errors.append('exact_quote_or_path_invalid');continue
            if not isinstance(quote,str) or not quote or quote not in target:errors.append('exact_quote_or_path_invalid');continue
        expanded[row['format']]['findings'].append(finding(row,path,quote,[]))
    return expanded,list(dict.fromkeys(errors))


def isolate_judgments(value, package, *, scan_additions=True):
    """Drop one unverifiable judgment at a time; raw response stays in assessment.

    No obsolete quotes are repaired and no source IDs are substituted. A rejected
    occurrence exception falls back to its separately validated group judgment.
    """
    from launchlens.package_content import FORMATS, risky_phrase_scan, resolve_field
    groups=phrase_groups(package,scan_additions=scan_additions);by_group={g['group_id']:g for g in groups}
    hits={h['hit_id']:h for h in risky_phrase_scan(package,scan_additions=scan_additions)}
    expanded={f:{'findings':[]} for f in FORMATS};dropped=[];seen=set()
    keys={'dimension','severity','reason','suggestion','claim_ids'}
    def reject(path,rule):dropped.append({'path':path,'rule':rule})
    def valid(row):
        return (isinstance(row,dict) and isinstance(row.get('dimension'),str) and row.get('dimension') in DIMENSIONS and
            isinstance(row.get('severity'),str) and row.get('severity') in {'blocking','advisory','cleared'} and
            0<word_count(row.get('reason'))<=25 and 0<word_count(row.get('suggestion'))<=12 and
            isinstance(row.get('claim_ids'),list) and len(row['claim_ids'])<=2 and
            all(isinstance(c,str) and c in ('PROD-002','PROD-003') for c in row['claim_ids']) and
            len(set(row['claim_ids']))==len(row['claim_ids']))
    def finding(row,path,quote,ids):
        return {'dimension':row['dimension'],'content_field':path,'quote':quote,
            'severity':row['severity'],'rationale':row['reason'],'suggested_change':row['suggestion'],
            'claim_ids':deepcopy(row['claim_ids']),'scan_hit_ids':ids}
    if not isinstance(value,dict) or set(value)!={'group_judgments','additional_findings'} or not isinstance(value.get('group_judgments'),list) or not isinstance(value.get('additional_findings'),list):
        return expanded,[],['malformed_group_review']
    for i,row in enumerate(value['group_judgments'][:80]):
        path=f'group_judgments.{i}'
        if not valid(row) or set(row)!=keys|{'group_id','occurrence_judgments'}:
            reject(path,'group_judgment_invalid_or_word_limit');continue
        gid=row['group_id']
        if not isinstance(gid,str) or gid not in by_group or gid in seen:
            reject(path,'duplicate_or_unknown_group');continue
        seen.add(gid);group=by_group[gid];locations={l['location_id']:l for l in group['locations']};overrides={}
        exceptions=row['occurrence_judgments']
        if not isinstance(exceptions,list):reject(path+'.occurrence_judgments','invalid_occurrence_judgments');exceptions=[]
        for j,o in enumerate(exceptions[:40]):
            opath=path+f'.occurrence_judgments.{j}'
            if (not valid(o) or set(o)!=keys|{'location_id','meaning_differs'} or
                o.get('meaning_differs') is not True or not isinstance(o.get('location_id'),str) or
                o['location_id'] not in locations or o['location_id'] in overrides):
                reject(opath,'occurrence_meaning_difference_required');continue
            overrides[o['location_id']]=o
        if len(exceptions)>40:reject(path+'.occurrence_judgments','too_many_occurrence_judgments')
        for location in group['locations']:
            hit=hits[location['location_id']];chosen=overrides.get(location['location_id'],row)
            expanded[hit['format']]['findings'].append(finding(chosen,hit['content_field'],hit['quote'],[hit['hit_id']]))
    for gid in by_group.keys()-seen:reject('group_judgments.'+gid,'group_coverage_missing')
    if len(value['group_judgments'])>80:reject('group_judgments','too_many_groups')
    for i,row in enumerate(value['additional_findings'][:12]):
        path=f'additional_findings.{i}'
        if not valid(row) or set(row)!=keys|{'format','content_field','quote'} or row['format'] not in FORMATS:
            reject(path,'additional_finding_invalid_or_word_limit');continue
        field=row['content_field'];quote=row['quote']
        if isinstance(field,str) and field.startswith('content.'):field=field[8:]
        if quote is None:
            if field!='$format':reject(path,'format_scope_required');continue
        else:
            try:target=resolve_field(package[row['format']]['content'],field)
            except Exception:reject(path,'exact_quote_or_path_invalid');continue
            if not isinstance(quote,str) or not quote or quote not in target:
                reject(path,'exact_quote_or_path_invalid');continue
        expanded[row['format']]['findings'].append(finding(row,field,quote,[]))
    if len(value['additional_findings'])>12:reject('additional_findings','too_many_additional_findings')
    return expanded,dropped,[]
