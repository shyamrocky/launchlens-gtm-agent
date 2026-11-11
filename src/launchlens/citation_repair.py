"""Single citation-only Writer retry: immutable copy, source-bound reference patch."""
from copy import deepcopy
import hashlib
from pathlib import Path
import re

from launchlens.content_review import check
from launchlens.content_contracts import validate_draft, ContractError
from launchlens.linkedin_drafting import digest
from launchlens.package_content import citation_only_failures, prepare_package_input, text_fields, evidence_records

PROTOCOL = 'citation_references_v1'
PROMPT_SHA256 = 'cac30e755ed26913f9b3aabc091137b99ab2e3737610c8a9bc89d8aa145dcb71'


def prompt():
    raw=Path(__file__).with_name('prompts').joinpath('package_citation_repair_v1.txt').read_bytes()
    check(hashlib.sha256(raw).hexdigest()==PROMPT_SHA256,'stale_binding')
    return raw.decode()


def valid_references(draft,format_name,records):
    """Retain valid entries byte-for-value; never manufacture reference support."""
    result=[];seen=set()
    for entry in draft['claim_references']:
        trial=deepcopy(draft);trial['claim_references']=[entry]
        try:validate_draft(trial,format_name=format_name,evidence_records=records)
        except ContractError:continue
        if entry['content_field'] in seen:continue
        seen.add(entry['content_field']);result.append(deepcopy(entry))
    return result


def prepare(state,inputs,candidate):
    original=prepare_package_input(state)
    diagnostics=citation_only_failures(candidate,original)
    check(bool(diagnostics),'permission_denied')
    fields={f:dict(text_fields(d['content'])) for f,d in candidate.items()}
    targets={}
    for diagnostic in diagnostics:
        fmt=diagnostic['format'];target=targets.setdefault(fmt,{'required_fields':[], 'allowed_fields':[]})
        path=diagnostic['field_path'];field=None
        if diagnostic['rule']=='field_claim_coverage':field=path.removeprefix('content.')
        else:
            match=re.search(r'claim_references\.([0-9]+)',path)
            if match:
                entry=candidate[fmt]['claim_references'][int(match[1])]
                if type(entry) is dict:field=entry.get('content_field')
        if field in fields[fmt]:
            target['required_fields'].append(field);target['allowed_fields'].append(field)
        else:
            # An aggregate missing-ID or invalid-path error has no exact text path.
            # Only references in that diagnosed format can change; copy is immutable.
            target['allowed_fields'].extend(fields[fmt])
    for target in targets.values():
        target['required_fields']=sorted(set(target['required_fields']))
        target['allowed_fields']=sorted(set(target['allowed_fields']))
    allowed=original['draft_constraints']['allowed_claim_ids']
    props={fmt:{'type':'array','maxItems':len(target['allowed_fields']),'items':{
        'type':'object','properties':{'content_field':{'type':'string','enum':target['allowed_fields']},
        'claim_ids':{'type':'array','items':{'type':'string','enum':allowed},'minItems':1,'maxItems':len(allowed),'uniqueItems':True}},
        'required':['content_field','claim_ids'],'additionalProperties':False}} for fmt,target in targets.items()}
    result=deepcopy(inputs)
    result['writer_brief'].pop('output_schema',None)
    result.update(citation_repair_protocol=PROTOCOL,source_package_sha256=digest(candidate),
        saved_candidate_data_only=deepcopy(candidate),citation_diagnostics_data_only=diagnostics,
        citation_repair_targets=targets,
        output_schema={'type':'object','properties':{'source_package_sha256':{'type':'string','enum':[digest(candidate)]},
            'references':{'type':'object','properties':props,'required':list(props),'additionalProperties':False}},
            'required':['source_package_sha256','references'],'additionalProperties':False})
    return result


def merge(state,inputs,patch):
    candidate=inputs['saved_candidate_data_only']
    check(inputs.get('citation_repair_protocol')==PROTOCOL and digest(candidate)==inputs['source_package_sha256'],'stale_binding')
    # Recompute targets/diagnostics against original authority, not model declarations.
    expected=prepare(state,inputs,candidate)
    check(expected['citation_repair_targets']==inputs['citation_repair_targets'] and
          expected['citation_diagnostics_data_only']==inputs['citation_diagnostics_data_only'],'stale_binding')
    check(type(patch) is dict and set(patch)=={'source_package_sha256','references'})
    check(patch['source_package_sha256']==digest(candidate),'stale_binding')
    targets=inputs['citation_repair_targets'];patches=patch['references']
    check(type(patches) is dict and set(patches)==set(targets),'invalid_reference')
    original=prepare_package_input(state);records=evidence_records(original)
    allowed=set(original['draft_constraints']['allowed_claim_ids']);result=deepcopy(candidate)
    for fmt,target in targets.items():
        entries=patches[fmt];check(type(entries) is list and len(entries)<=len(target['allowed_fields']),'invalid_reference')
        seen=set();existing=valid_references(candidate[fmt],fmt,records)
        by_field={e['content_field']:e for e in existing}
        for entry in entries:
            check(type(entry) is dict and set(entry)=={'content_field','claim_ids'},'invalid_reference')
            field=entry['content_field'];ids=entry['claim_ids']
            check(type(field) is str and field in target['allowed_fields'] and field not in seen,'invalid_reference')
            check(type(ids) is list and bool(ids) and all(type(c) is str and c in allowed for c in ids) and len(ids)==len(set(ids)),'invalid_reference')
            seen.add(field)
            if field in by_field:
                # Existing valid reference IDs may only be augmented, never removed.
                by_field[field]['claim_ids']=list(dict.fromkeys([*by_field[field]['claim_ids'],*ids]))
            else:
                by_field[field]=deepcopy(entry);existing.append(by_field[field])
        check(set(target['required_fields'])<=seen,'invalid_reference')
        result[fmt]['claim_references']=existing
    check(all(result[f]['content']==candidate[f]['content'] for f in result),'stale_binding')
    return result
