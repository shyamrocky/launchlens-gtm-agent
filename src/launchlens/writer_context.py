"""Bounded Writer-specific field selection; complete authority stays outside this view.

No model/network/environment access. The reviewed frozen-source policy fails closed
on source drift. Selection uses exact source spans, never an LLM or ID substitution.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from launchlens.evidence_payload import storage_fields
from launchlens.gtm_registry import objective_claims, validate_request
from launchlens.model_context import canonical, expand_packet, structured_packet_text
from launchlens.retrieval import checked_packet

POLICY_PATH = Path(__file__).resolve().parents[2]/'data/templates/gtm/writer_context_projection.json'


class ProjectionError(ValueError):
    """Safe context-selection failure, not permission or an invitation to trim."""


def require(condition, message):
    if not condition:
        raise ProjectionError(message)


def identity(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def load_policy():
    return json.loads(POLICY_PATH.read_text())


def pmm_leaves(pmm):
    result = {}
    def walk(blocks, path):
        for i, block in enumerate(blocks):
            here=f'{path}.{i}';content=block.get('content',{})
            if 'rich_text' in content:
                result[here+'.content.rich_text'] = ''.join(v['text'] for v in content['rich_text'])
            for j, cell in enumerate(content.get('cells',[])):
                result[f'{here}.content.cells.{j}'] = ''.join(v['text'] for v in cell)
            walk(block.get('children',[]),here+'.children')
    walk(pmm['blocks'],'research_context.pmm.blocks')
    return result


def selected_text(value, spans, source, ledger, excluded_reason="Outside reviewed task-relevant spans; original retained in authority"):
    """Retain reviewed nonoverlapping source ranges; account for every omitted range."""
    cursor=0;parts=[]
    for start,end,reason in spans:
        require(type(start) is int and type(end) is int and cursor<=start<end<=len(value),
                'Invalid reviewed source span')
        if start>cursor:
            ledger.append({'source':source,'range':[cursor,start],'decision':'exclude',
                           'reason':excluded_reason})
        parts.append(value[start:end])
        ledger.append({'source':source,'range':[start,end],'decision':'include','reason':reason,
                       'text_sha256':hashlib.sha256(value[start:end].encode()).hexdigest()})
        cursor=end
    if cursor<len(value):
        ledger.append({'source':source,'range':[cursor,len(value)],'decision':'exclude',
                       'reason':excluded_reason})
    return parts


def project_writer_input(inputs, *, policy=None):
    """Return a model view plus audit manifest, never a replacement evidence authority."""
    policy=deepcopy(load_policy() if policy is None else policy)
    original=deepcopy(inputs);context=inputs['research_context'];request=validate_request(inputs['validated_request'])
    require(request['market_id']=='US' and set(inputs['draft_constraints']['allowed_claim_ids'])==set(objective_claims(request)),
            'Unsupported Writer projection scope')
    launch=context['launch'];pmm=context['pmm']
    require(launch.get('authority')=='synthetic_launch_decision' and launch.get('decision')=='Proceed' and launch.get('promotional_draft_allowed') is True
            and launch.get('publishing_allowed') is False and launch.get('conditions')==[]
            and all(launch.get(k)==request[k] for k in ['product_id','market_id','evaluation_date']),
            'Launch permission or scope is not sufficient')
    require(pmm.get('status')=='ok' and pmm.get('authority')=='synthetic_pmm_guidance',
            'Complete PMM context required')
    require(identity(pmm)==policy['pmm_sha256'] and identity(launch)==policy['launch_sha256'],
            'PMM or launch changed; review new caveats/conflicts before projection')
    ledger=[];leaves=pmm_leaves(pmm);chosen={s['source']:s for s in policy['pmm_selection']}
    require(set(chosen)<=set(leaves),'Reviewed PMM field is unavailable')
    guidance=[]
    for path,value in leaves.items():
        if path in chosen:
            spec=chosen[path]
            guidance.append({'purpose':spec['purpose'],
                'text':selected_text(value,spec['spans'],path,ledger,spec.get('excluded_reason','Duplicate or out-of-scope field content; essential caveats retained'))})
        else:
            ledger.append({'source':path,'range':[0,len(value)],'decision':'exclude',
                           'reason':policy.get('pmm_exclusion_reasons',{}).get(path,'Unselected reviewed fixture field; source frozen and retained')})
    claims=[];pool={};pool_index={};seen={}
    for result_index,result in enumerate(context['retrieval_results']):
        for row_index,row in enumerate(result['records']):
            p=expand_packet(context,row['packet_ref']);fields=storage_fields(p);unit=p['unit_id']
            require(unit in inputs['draft_constraints']['allowed_claim_ids'] and row['unit_id']==unit
                    and row['chunk_id']==p['chunk_id'] and row['authority']=='public_product_facts'
                    and row['evidence_sha256']==fields['evidence_sha256']
                    and row.get('usable_as_complete_evidence') is True
                    and row.get('reference_status') in {'resolved','not_expanded'},'Invalid or partial authoritative evidence')
            checked_packet({'id':p['chunk_id'],'metadata':fields},'public_product_facts')
            require(fields['evidence_sha256']==policy['evidence_sha256'].get(unit),
                    'Evidence changed; review qualifications before projection')
            require(structured_packet_text(p)==p['text'],'Unmatched evidence text cannot be silently excluded')
            require(unit not in seen,'Duplicate objective evidence')
            seen[unit]=fields['evidence_sha256'];refs=[]
            for i,segment in enumerate(p['segments']):
                source=f'research_context.packets.{row["packet_ref"]}.segments.{i}.text'
                value=segment['text'];spans=policy.get('segment_selection',{}).get(unit,{}).get(str(i),
                      [[0,len(value),'Preserve primary statement, source detail and all required qualifications']])
                for text in selected_text(value,spans,source,ledger,policy.get('segment_exclusion_reason','Reviewed source span omitted; full authority retained')):
                    key=canonical({'role':segment['role'],'text':text})
                    if key not in pool_index:
                        alias='q'+str(len(pool)+1);pool_index[key]=alias
                        pool[alias]={'role':segment['role'],'text':text}
                    refs.append(pool_index[key])
            claims.append({'claim_id':unit,'authority':p['authority'],'text':p['primary_text'],
                'source_references':deepcopy(p['source_references']),
                'claim_source_mappings':deepcopy(p['claim_source_mappings']),
                'context_refs':refs})
            for field in p:
                ledger.append({'source':f'authoritative_claims.{unit}.{field}',
                    'decision':'include' if field in {'primary_text','segments','source_references','claim_source_mappings','authority','unit_id'} else 'retain_in_authority',
                    'reason':'Meaning/citations in model view; full identity, provenance, links and acceptance bindings remain independently authoritative'})
    require(set(seen)==set(inputs['draft_constraints']['allowed_claim_ids']),'Required evidence missing')
    operations={k:deepcopy(launch[k]) for k in policy['launch_fields']}
    operational_restrictions=[]
    for i,row in enumerate(launch['readiness_evidence']):
        values=row['values'];item={k:deepcopy(values[k]) for k in policy['readiness_fields']}
        source=f'research_context.launch.readiness_evidence.{i}.values.Evidence / Reference'
        text=values['Evidence / Reference'];spans=policy.get('readiness_selection',{}).get(str(i),
              [[0,len(text),'Retain scope, caveats and conditional permission']])
        item['Evidence / Reference']=selected_text(text,spans,source,ledger)
        operational_restrictions.append(item)
    operations['readiness_restrictions']=operational_restrictions
    operations['calendar_restriction']=deepcopy(launch['calendar_evidence']['values']['Notes'])
    for field in launch:
        ledger.append({'source':'research_context.launch.'+field,
                       'decision':'include' if field in operations else 'retain_in_authority',
                       'reason':'Keep permission, scope and restrictions; omit operational trace/IDs/coordination metadata'})
    model=deepcopy(inputs)
    model['research_context']={'lower_trust_data_only':True,
        'pmm':{'authority':pmm['authority'],'guidance':guidance},
        'launch':operations,'claims':sorted(claims,key=lambda v:v['claim_id']),
        'claim_context':pool,'material_boundaries':deepcopy(policy['material_boundaries'])}
    visible=set(re.findall(r'PROD-\d{3}',canonical(model)))
    require(visible<=set(inputs['draft_constraints']['allowed_claim_ids']),
            'Ineligible claim ID remains; do not strip a material caveat to pass')
    require(inputs==original,'Authoritative input changed during projection')
    manifest={'projection_version':policy['version'],'policy_sha256':identity(policy),
        'authoritative_input_sha256':identity(inputs),'model_input_sha256':identity(model),
        'evidence_sha256':seen,'included_excluded':ledger,
        'pmm_structural_metadata':'Retained in authority; only exact selected source text is model-facing',
        'qualification_policy':'All required/source segments kept, except explicitly reviewed unrelated notice sentence','token_measurement':'bytes only; no provider token estimate'}
    return {'model_input':model,'manifest':manifest}
