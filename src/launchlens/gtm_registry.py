"""Supported business tasks and action contracts for the bounded LaunchLens MVP."""
from dataclasses import asdict, dataclass
from datetime import date
import re

from launchlens.notion_tools import CALENDAR, MARKETS, PMM_PAGE, PRODUCT, READINESS
from launchlens.retrieval import HOST, NAMESPACE, SOURCES

USE_CASE = "cherry-float-gtm"
OBJECTIVE = "flavor_discovery"
MAX_TURNS = 12
MAX_SEARCHES = 4
# Fixed-corpus business prerequisites; never model-supplied search instructions.
OBJECTIVE_CLAIMS = {OBJECTIVE: {
    "PROD-002": "Supported Cherry Float flavor description",
    "PROD-003": "Classic soda-float inspiration",
}}


class HarnessError(ValueError):
    """Safe validation/lifecycle error; never includes source bodies or credentials."""


def require(condition, message):
    if not condition:
        raise HarnessError(message)


@dataclass(frozen=True)
class Request:
    use_case_id: str
    product_id: str
    market_id: str
    evaluation_date: str
    objective_id: str


def supported_use_cases():
    """Fresh public metadata, not mutable shared configuration or a job queue."""
    return [{"use_case_id": USE_CASE, "product_id": PRODUCT,
             "label": "Coca-Cola Cherry Float — GTM Package Preparation",
             "markets": sorted(MARKETS),
             "objectives": [{"id": OBJECTIVE, "label":
                 "Introduce Cherry Float's flavor and classic soda-float inspiration"}],
             "outputs": ["campaign_brief", "linkedin", "email", "blog", "ad_variations"],
             "sources": {"pinecone_host": HOST, "namespace": NAMESPACE,
                         "pmm_page": PMM_PAGE, "calendar": CALENDAR, "readiness": READINESS}}]


def validate_request(value):
    fields = set(Request.__dataclass_fields__)
    require(type(value) is dict and set(value) == fields, "Supply exactly the supported request fields")
    require(all(type(v) is str for v in value.values()), "Request fields must be text")
    require(value["use_case_id"] == USE_CASE and value["product_id"] == PRODUCT,
            "Unsupported GTM use case or product; no execution started")
    require(value["market_id"] in MARKETS, "Unsupported market")
    require(value["objective_id"] == OBJECTIVE, "Unsupported campaign objective")
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value["evaluation_date"]) is not None,
            "Supply an explicit YYYY-MM-DD evaluation date")
    try:
        date.fromisoformat(value["evaluation_date"])
    except ValueError:
        raise HarnessError("Invalid evaluation date") from None
    return asdict(Request(**value))


def action_registry(mode="live_research"):
    """Allowed model actions; internal run lifecycle operations are deliberately absent."""
    actions = {
        "read_pmm_brief": {"arguments": {}, "purpose": "Read approved PMM guidance"},
        "check_launch": {"arguments": {}, "purpose": "Compute scoped launch eligibility from source records"},
        "search_product_evidence": {"arguments": {"query": "text", "authority": "approved category"},
                                    "purpose": "Retrieve product facts or synthetic intent"},
        "request_clarification": {"arguments": {"market_id": "market code", "question": "text"}, "purpose": "Pause this market's task"},
        "finish": {"arguments": {}, "purpose": "Request research-stage completion; code verifies prerequisites"},
    }
    if mode in {"live_linkedin", "offline_review"}:
        actions["generate_linkedin"] = {"arguments": {}, "purpose":
            "Request one internal LinkedIn draft; harness checks eligibility and owns review state"}
        actions["finish"]["purpose"] = "Request completion with a validated, unreviewed LinkedIn draft"
    if mode == "offline_review":
        actions["review_linkedin"] = {"arguments": {}, "purpose":
            "Delegate independent review of the exact current draft; harness binds evidence and version"}
        actions["revise_linkedin"] = {"arguments": {}, "purpose":
            "Request one revision only after explicit owner feedback; harness owns permission"}
        actions["finish"]["purpose"] = "Completion requires current-version independent review; never grants human approval"
    if mode in {'offline_package','live_package'}:
        actions.update({
            'generate_package': {'arguments': {}, 'purpose': 'Draft the five-format GTM package after verified research and launch eligibility'},
            'review_package': {'arguments': {}, 'purpose': 'Delegate independent review of every format and cross-format consistency'},
            'revise_package': {'arguments': {}, 'purpose': 'Revise only for the exact current human request; fresh review is required'},
        })
        actions['finish']['purpose'] = 'Completion requires all five formats and current-version review; never grants approval'
    return actions


def validate_action(value, mode="live_research"):
    require(type(value) is dict and (set(value) == {'id','name','arguments'} or (mode in {'offline_package','live_package'} and set(value)=={'id','name','arguments','why'})),
            "Action must contain only id, name and arguments")
    require(type(value["id"]) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value["id"]),
            "Invalid action identifier")
    require(type(value["name"]) is str and value["name"] in action_registry(mode), "Unregistered action")
    if 'why' in value:
        require(type(value['why']) is str and 0 < len(value['why'].strip()) <= 300, 'Invalid action purpose')
    args = value["arguments"]
    require(type(args) is dict and set(args) == set(action_registry(mode)[value["name"]]["arguments"]),
            "Unexpected or missing action arguments")
    if value["name"] == "search_product_evidence":
        require(type(args["query"]) is str and args["query"].strip() and len(args["query"]) <= 2000,
                "Search query must contain 1–2000 characters")
        require(type(args["authority"]) is str and args["authority"] in SOURCES, "Unsupported evidence authority")
    if value["name"] == "request_clarification":
        require(type(args["market_id"]) is str and args["market_id"] in MARKETS, "Unsupported clarification market")
        require(type(args["question"]) is str and args["question"].strip() and len(args["question"]) <= 500,
                "Clarification requires 1–500 characters")
    return value


def objective_claims(request):
    """Fresh minimum-evidence configuration for the validated selected objective."""
    request = validate_request(request)
    return dict(OBJECTIVE_CLAIMS[request["objective_id"]])


def missing_objective_claim_ids(state):
    """IDs still needed for drafting, based on complete public claim records."""
    supported = {row.get('unit_id') for result in state.get('evidence', [])
                 for row in result.get('records', [])
                 if row.get('authority') == 'public_product_facts'
                 and row.get('usable_as_complete_evidence') is True
                 and row.get('reference_status') in {'resolved', 'not_expanded'}
                 and (row.get('evidence_payload') or {}).get('chunk_kind') == 'product_claim'
                 and (row.get('evidence_payload') or {}).get('claim_source_mappings')}
    return [claim for claim in objective_claims(state['request']) if claim not in supported]


def eligible_actions(state):
    """Application-owned options inside the registered task; not model policy."""
    actions=action_registry(state['mode'])
    if (state.get('launch') or {}).get('decision') != 'Clarify' or clarification_used(state):
        actions.pop('request_clarification',None)
    if state.get('feedback') in {'draft_without_availability', 'recheck_readiness'} and state.get('restricted_drafting'):
        actions.pop('search_product_evidence', None)
    if state['mode'] in {'offline_package','live_package'}:
        actions.pop('review_package',None)  # Required graph edge after every admission.
        actions.pop('revise_package',None)  # Explicit human command; never autonomous repetition.
        launch = state.get('launch') or {}
        may_draft = (launch.get('decision') == 'Proceed' or
                     (launch.get('decision') == 'Clarify' and
                      state.get('feedback') in {'draft_without_availability', 'recheck_readiness'} and
                      bool(state.get('restricted_drafting'))))
        if state.get('package') or state.get('pmm') is None or not may_draft or missing_objective_claim_ids(state):
            actions.pop('generate_package',None)
    return actions


def clarification_used(state):
    """A completed clarification is single-use even if feedback is lost on resume."""
    return bool(state.get('feedback')) or any(
        entry.get('action', {}).get('name') == 'request_clarification'
        and entry.get('status') == 'completed'
        for entry in state.get('ledger', {}).values()
    )
