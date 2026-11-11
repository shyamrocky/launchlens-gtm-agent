"""Deterministic fictional launch eligibility; no LLM, network or file access.

Applies the four required readiness areas and calendar/date rules in M1.4 design.
These results control draft scope, never real publishing or actual stock assertions.
"""
from launchlens.observability import step
from datetime import date
import re
from launchlens.notion_tools import PRODUCT, MARKETS

AREAS={'Product information':'PRODUCT','Regional availability':'AVAIL',
       'Messaging approval':'MESSAGE','Marketing communication authorization':'AUTH'}
STATUSES={'Approved','Pending','Missing','Blocked'}


def iso_date(value):
    if not isinstance(value,str) or re.fullmatch(r'\d{4}-\d{2}-\d{2}',value) is None:
        raise ValueError('An explicit ISO evaluation date is required')
    return date.fromisoformat(value)


@step('launch gate check', capture=())
def evaluate_launch(context, evaluation_date):
    """Compute Proceed/Clarify/Hold from source values; never accept a model verdict.

    Proceed permits internal promotional draft preparation within supported scope.
    Pre-launch Proceed cannot say available now. Future-dated readiness cannot be
    used retrospectively. No expiry policy is invented for these frozen snapshots.
    """
    result={'decision':'Clarify','product_id':PRODUCT,'market_id':context.get('market_id') if isinstance(context,dict) else None,
        'evaluation_date':evaluation_date if isinstance(evaluation_date,str) else None,
        'planned_launch_date':None,'promotional_draft_allowed':False,
        'availability_now_claim_allowed':False,'internal_research_allowed':True,
        'publishing_allowed':False,'conditions':[], 'readiness_evidence':[],
        'authority':'synthetic_launch_decision',
        'notice':'Fictional educational eligibility only; no actual inventory, legal approval or publishing permission.'}
    conditions=result['conditions'];known_hold=False
    def problem(code,message):conditions.append({'code':code,'message':message})
    try:when=iso_date(evaluation_date)
    except ValueError:
        problem('invalid_evaluation_date','Supply an explicit valid YYYY-MM-DD evaluation date')
        return result
    if not isinstance(context,dict) or context.get('status')!='ok' or context.get('product_id')!=PRODUCT or (not isinstance(context.get('market_id'),str) or context.get('market_id') not in MARKETS):
        problem('source_unavailable','Complete scoped launch context is required; missing data is not permission')
        return result
    market=context['market_id'];cal=context.get('calendar');ready=context.get('readiness')
    if not isinstance(cal,list) or not isinstance(ready,list):
        problem('malformed_source','Calendar and readiness records are both required')
        return result
    checks={}
    for record in ready:
        try:
            row=record['values']
            if not isinstance(row,dict):raise ValueError('Malformed readiness values')
            area=row['Readiness Area'];status=row['Status']
            if row.get('Product ID')!=PRODUCT or row.get('Market ID')!=market:
                raise ValueError('Wrong scope')
            if area not in AREAS or status not in STATUSES:
                raise ValueError('Unknown area/status')
            # Known blocking status wins over other contradictory/missing data.
            if status=='Blocked' or (area=='Marketing communication authorization' and status=='Pending'):
                known_hold=True
            if area in checks:raise ValueError('Duplicate readiness area')
            if row.get('Record ID')!=f'RDY-{market}-{AREAS[area]}':raise ValueError('Wrong stable readiness ID')
            checks[area]=row
            result['readiness_evidence'].append(record)
            updated=iso_date(row.get('Last Updated'))
            if updated>when:
                problem('future_readiness',f'{area}: approval/status snapshot is later than evaluation date')
            evidence=row.get('Evidence / Reference');blocker=row.get('Blocker / Missing Information')
            if not isinstance(row.get('Requirement'),str) or not row['Requirement'].strip() or not isinstance(evidence,str) or not evidence.startswith('SIMULATION') or not isinstance(blocker,str) or not blocker.strip():
                raise ValueError('Missing requirement/evidence/blocker')
            if status=='Approved' and blocker!='None':
                problem('contradictory_approval',f'{area}: Approved conflicts with recorded blocker')
            elif status!='Approved':
                problem('readiness_unresolved',f'{area}: {status}. {blocker}')
        except (KeyError,TypeError,ValueError):
            problem('invalid_readiness','Malformed, duplicate or wrongly scoped readiness record')
    if set(checks)!=set(AREAS) or len(ready)!=4:
        problem('missing_readiness','Exactly one record for each of the four required readiness areas is required')
    launches=[];stages=[]
    for record in cal:
        try:
            row=record['values']
            if not isinstance(row,dict):raise ValueError('Malformed calendar values')
            if row.get('Product ID')!=PRODUCT or row.get('Market ID')!=market:raise ValueError('Wrong calendar scope')
            stage=row.get('Launch Stage')
            if stage not in {'Preparation','Content review','Launch'}:raise ValueError('Unknown calendar stage')
            stages.append(stage)
            if not row.get('Event','').startswith(f'CAL-{market}-'):raise ValueError('Missing stable calendar ID')
            if row.get('Schedule Status')!='Planned':raise ValueError('Unrecognized schedule state')
            if stage=='Launch':
                planned=iso_date(row.get('Planned Launch Date'))
                if iso_date(row.get('Date'))!=planned:raise ValueError('Conflicting launch dates')
                launches.append((planned,record))
            elif row.get('Planned Launch Date'):
                raise ValueError('Competing planned launch date')
        except (KeyError,TypeError,ValueError):
            problem('invalid_calendar','Malformed, wrongly scoped or contradictory calendar record')
    if len(cal)!=3 or sorted(stages)!=sorted(['Preparation','Content review','Launch']):
        problem('incomplete_calendar','Exactly one preparation, review and launch milestone is required')
    if len(launches)!=1:
        problem('ambiguous_launch_date','Exactly one authoritative Launch-stage date is required')
    else:
        planned,launch_record=launches[0]
        result['planned_launch_date']=planned.isoformat();result['calendar_evidence']=launch_record
        available=checks.get('Regional availability',{})
        availability_evidence=available.get('Evidence / Reference','')
        if available.get('Status')=='Approved' and (not isinstance(availability_evidence,str) or planned.isoformat() not in availability_evidence):
            problem('availability_date_unbound','Approved availability lacks explicit matching fictional effective date')
    if known_hold:
        result['decision']='Hold'
    elif not conditions:
        result['decision']='Proceed';result['promotional_draft_allowed']=True
        result['availability_now_claim_allowed']=when>=launches[0][0]
        if not result['availability_now_claim_allowed']:
            result['restrictions']=['Future-launch planning only: withhold available-now wording before planned launch date']
    return result


def check_launch(reader, market, evaluation_date):
    """Read authoritative operational sources, then apply deterministic policy."""
    return evaluate_launch(reader.get_launch_context(market), evaluation_date)


def availability_only_gap(result):
    """Only frozen UK availability Missing; no other unresolved condition permitted."""
    if not (type(result) is dict and result.get('market_id')=='UK' and result.get('decision')=='Clarify'
            and result.get('authority')=='synthetic_launch_decision' and result.get('publishing_allowed') is False
            and result.get('planned_launch_date') and len(result.get('conditions',[]))==1
            and result['conditions'][0]['code']=='readiness_unresolved'):
        return False
    rows=[r.get('values',{}) for r in result.get('readiness_evidence',[])]
    return (len(rows)==4 and {r.get('Readiness Area') for r in rows}==set(AREAS)
        and all(r.get('Status')==('Missing' if r['Readiness Area']=='Regional availability' else 'Approved') for r in rows))
