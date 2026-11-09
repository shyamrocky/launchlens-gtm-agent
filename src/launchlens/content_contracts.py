"""M2.3a content contracts: stdlib-only structural/evidence-reference validation.

No model calls, generation, Reviewer, permissions or approval state. Templates are
canonical application configuration. This intentionally implements only the small
JSON Schema subset used by these five contracts, not a general schema engine.
"""
from copy import deepcopy
import json
from pathlib import Path
import re

from launchlens.evidence_payload import storage_fields
from launchlens.retrieval import checked_packet

VERSION = "1.0"
SHARED_CONTRACT = "launchlens.content_contracts/v1"
TEMPLATES = {"campaign_brief":"campaign_brief.json", "linkedin":"linkedin_post.json",
             "email":"promotional_email.json", "blog":"short_blog.json", "ads":"ad_variations.json"}
TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "data/templates/gtm"
COMMON_REVIEW_CRITERIA = (
    "Every material factual assertion must be supported by retrieved public product evidence with its qualifications.",
    "Use PRD intent and PMM positioning as synthetic guidance, not actual product facts or measured audience response.",
    "Campaign brief is creative direction, never product truth or operational permission.",
    "Preserve the harness-owned product, market, variant, serving, date and launch restrictions.",
    "Do not invent discounts, offers, purchase destinations, stock, launch dates or performance claims.",
    "A purchase/offer CTA requires both evidence of its terms and an authorized destination; neither is established by a public product announcement.",
    "Prefer an evidenced product-information or engagement CTA; invent no destination URL when one has not been supplied.",
    "Distinguish ordinary creative language from factual assertions; unsupported factual or promotional assertions require correction.",
    "Check consistency with campaign direction, tone, required fields and other channel drafts.",
    "Only the application owns draft version, review findings/status and human approval; structural validity never grants permission.",
)
_SCHEMA_KEYS = {"type", "properties", "required", "additionalProperties", "items",
                "minItems", "maxItems", "minLength", "enum", "uniqueItems"}


# Bounded metadata vocabulary. Never copy model keys, values, claim IDs or exception
# text into diagnostics. Names mirror maintained schemas, not retrieved source data.
_DIAGNOSTIC_NAMES = frozenset(['angle', 'audience_hypothesis', 'body', 'claim_ids', 'claim_references', 'concepts', 'conclusion', 'content', 'content_field', 'cta', 'evidence_records', 'format', 'hashtags', 'heading', 'headline', 'hook', 'introduction', 'messaging_pillars', 'objective', 'positioning', 'preview_text', 'primary_cta', 'restrictions_and_unknowns', 'sections', 'subject', 'title', 'tone'])
DIAGNOSTIC_RULES = frozenset({
    "required_field_missing", "invalid_type", "unexpected_field", "array_length_invalid",
    "duplicate_array_item", "nonempty_text_required", "invalid_enum_value",
    "invalid_content_field_reference", "duplicate_field_reference", "invalid_claim_reference",
    "evidence_validation_failed", "objective_claim_coverage", "cta_mismatch",
    "prohibited_link", "prohibited_wording", "unknown_validation_failure",
})


def validation_detail(field_path=None, rule="unknown_validation_failure"):
    """Accept only bounded, known path tokens/rules; no parsing of exception text."""
    if type(field_path) is str and field_path.startswith("draft."):
        field_path = field_path[6:]
    elif field_path == "draft":
        field_path = "$"
    safe = (type(field_path) is str and len(field_path) <= 160 and
        (field_path == "$" or (len(field_path.split(".")) <= 12 and all(
            part in _DIAGNOSTIC_NAMES or re.fullmatch(r"0|[1-9][0-9]{0,5}", part)
            for part in field_path.split(".")))))
    if not safe or type(rule) is not str or rule not in DIAGNOSTIC_RULES:
        return {"field_path":None, "rule":"unknown_validation_failure"}
    return {"field_path":field_path, "rule":rule}


class ContractError(ValueError):
    """Existing exception behavior plus safe, validator-authored diagnostic fields."""
    def __init__(self, message, *, field_path=None, rule="unknown_validation_failure"):
        super().__init__(message)
        self.diagnostic = validation_detail(field_path, rule)


def require(condition, message, *, field_path=None, rule="unknown_validation_failure"):
    if not condition:
        raise ContractError(message, field_path=field_path, rule=rule)


def _check_schema(schema):
    require(type(schema) is dict and set(schema) <= _SCHEMA_KEYS, "Unsupported contract rule")
    kind = schema.get("type")
    require(kind in {"object", "array", "string"}, "Unsupported contract type")
    if kind == "object":
        props, required = schema.get("properties"), schema.get("required")
        require(type(props) is dict and props and type(required) is list and
                all(type(k) is str and k in props for k in required) and
                len(required) == len(set(required)) and schema.get("additionalProperties") is False,
                "Object contract must explicitly bound its fields")
        for child in props.values():
            _check_schema(child)
    elif kind == "array":
        _check_schema(schema.get("items"))
        for key in ("minItems", "maxItems"):
            require(key not in schema or type(schema[key]) is int and schema[key] >= 0, "Invalid array bound")
        require(schema.get("maxItems", float("inf")) >= schema.get("minItems", 0), "Conflicting array bounds")
    else:
        require(type(schema.get("minLength", 1)) is int and schema.get("minLength", 1) >= 1,
                "Text contract must require nonempty content")


def _shape(value, schema, path):
    kind = schema["type"]
    expected = {"object":dict, "array":list, "string":str}[kind]
    require(type(value) is expected, path + ": invalid type", field_path=path, rule="invalid_type")
    if kind == "object":
        for key in schema["required"]:
            require(key in value, path + ": missing required field",
                    field_path=path + "." + key, rule="required_field_missing")
        # Report the known parent, never an arbitrary unexpected key (which may be sensitive).
        require(set(value) <= set(schema["properties"]), path + ": unexpected fields",
                field_path=path, rule="unexpected_field")
        for key, item in value.items():
            _shape(item, schema["properties"][key], path + "." + key)
    elif kind == "array":
        require(schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", float("inf")),
                path + ": invalid array length", field_path=path, rule="array_length_invalid")
        if schema.get("uniqueItems"):
            require(len(value) == len({json.dumps(v, sort_keys=True) for v in value}),
                    path + ": duplicate values", field_path=path, rule="duplicate_array_item")
        for index, item in enumerate(value):
            _shape(item, schema["items"], path + "." + str(index))
    else:
        require(len(value.strip()) >= schema.get("minLength", 1), path + ": nonempty text required",
                field_path=path, rule="nonempty_text_required")
    if "enum" in schema:
        require(value in schema["enum"], path + ": unregistered value",
                field_path=path, rule="invalid_enum_value")


def _object(properties):
    return {"type":"object", "properties":properties, "required":list(properties), "additionalProperties":False}


def _read_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "Duplicate JSON field")
            value[key] = item
        return value
    def constant(_):
        raise ContractError("Non-finite JSON value")
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, TypeError) as error:
        raise ContractError("Invalid template JSON") from error


def load_template(format_name):
    require(type(format_name) is str and format_name in TEMPLATES, "Unsupported content format")
    try:
        value = _read_json((TEMPLATE_DIR / TEMPLATES[format_name]).read_text())
    except OSError:
        raise ContractError("Canonical template is unavailable; no fallback") from None
    require(type(value) is dict and set(value) == {"template_version", "format", "purpose",
        "shared_contract", "content_schema", "editorial_guidelines", "review_criteria"}, "Malformed template")
    require(value["format"] == format_name and value["template_version"] == VERSION and
            value["shared_contract"] == SHARED_CONTRACT, "Contract identity/version differs")
    _check_schema(value["content_schema"])
    editorial = value["editorial_guidelines"]
    require(type(editorial) is dict and editorial.get("enforcement") == "advisory_only" and
            type(editorial.get("length_targets")) is list and
            type(editorial.get("guidance")) is list and type(value["review_criteria"]) is list,
            "Missing editorial/review guidance")
    return deepcopy(value)


def model_output_schema(format_name):
    """Only model-authored fields; never version, review/approval metadata or launch permission."""
    template = load_template(format_name)
    text = {"type":"string", "minLength":1}
    return _object({"format":{**text, "enum":[format_name]}, "content":template["content_schema"],
        "claim_references":{"type":"array", "items":_object({"content_field":text,
            "claim_ids":{"type":"array", "items":text, "minItems":1, "uniqueItems":True}})}})


def _field(content, path):
    require(type(path) is str and bool(path) and all(re.fullmatch(r"[a-z_]+|0|[1-9][0-9]*", p)
        for p in path.split(".")), "Invalid content field path")
    value = content
    try:
        for part in path.split("."):
            if type(value) is list:
                value = value[int(part)]
            else:
                require(type(value) is dict, "Field path must resolve within content")
                value = value[part]
        return value
    except (KeyError, IndexError, ValueError):
        raise ContractError("Content field does not exist") from None


def _texts(value):
    if type(value) is str:
        return [value]
    if type(value) is list:
        return [s for v in value for s in _texts(v)]
    if type(value) is dict:
        return [s for v in value.values() for s in _texts(v)]
    raise ContractError("Unsupported editorial content")


def _eligible_claims(records):
    require(type(records) is list, "Caller must supply retrieved evidence records",
            field_path="evidence_records", rule="invalid_type")
    claims = {}
    for index, row in enumerate(records):
        require(type(row) is dict, "Malformed retrieved evidence",
                field_path="evidence_records." + str(index), rule="invalid_type")
        if row.get("authority") != "public_product_facts" or row.get("usable_as_complete_evidence") is not True:
            continue
        try:
            p = row["evidence_payload"]
            fields = storage_fields(p)
            checked_packet({"id":row["chunk_id"], "metadata":fields}, "public_product_facts")
            require(row.get("unit_id") == p["unit_id"] and row.get("evidence_sha256") == fields["evidence_sha256"],
                    "Evidence identity/digest differs")
            require(row.get("reference_status") in {"resolved", "not_expanded"}, "Evidence references incomplete")
            if p.get("chunk_kind") != "product_claim":
                continue
            require(re.fullmatch(r"PROD-[0-9]{3}", p["unit_id"]) and p["claim_source_mappings"], "Invalid public claim")
            require(p["unit_id"] not in claims or claims[p["unit_id"]] == fields["evidence_sha256"],
                    "Conflicting claim evidence")
            claims[p["unit_id"]] = fields["evidence_sha256"]
        except (KeyError, TypeError, ValueError):
            raise ContractError("Retrieved public evidence failed validation",
                field_path="evidence_records." + str(index), rule="evidence_validation_failed") from None
    return claims


def validate_draft(draft, *, format_name, evidence_records):
    """Check shape and reference bindings, then return advisory editorial findings.

    Does NOT evaluate prose entailment, identify every factual assertion, prove CTA
    safety, compute launch eligibility or perform review. M2.3b/c must wire those gates.
    Empty claim_references is structurally allowed for purely creative text; the
    Reviewer must reject factual prose without support. This never marks a draft approved.
    """
    template = load_template(format_name)
    _shape(draft, model_output_schema(format_name), "draft")
    claims = _eligible_claims(evidence_records)
    seen = set()
    for index, reference in enumerate(draft["claim_references"]):
        path = reference["content_field"]
        slot = "claim_references." + str(index)
        require(path not in seen, "Reference must identify one unique text field",
                field_path=slot + ".content_field", rule="duplicate_field_reference")
        try:
            target = _field(draft["content"], path)
        except ContractError:
            raise ContractError("Invalid referenced content field", field_path=slot + ".content_field",
                                rule="invalid_content_field_reference") from None
        require(type(target) is str, "Reference must identify a text field",
                field_path=slot + ".content_field", rule="invalid_content_field_reference")
        seen.add(path)
        for claim_index, claim in enumerate(reference["claim_ids"]):
            require(claim in claims, "Claim reference lacks complete retrieved public evidence",
                    field_path=slot + ".claim_ids." + str(claim_index), rule="invalid_claim_reference")
    warnings = []
    for target in template["editorial_guidelines"]["length_targets"]:
        values = [_field(draft["content"], field) for field in target["fields"]]
        metric = target["metric"]
        if metric == "items":
            require(len(values) == 1 and type(values[0]) is list, "Invalid editorial array target")
            actual = len(values[0])
        else:
            joined = " ".join(s for v in values for s in _texts(v))
            require(metric in {"words", "characters"}, "Unsupported editorial metric")
            actual = len(joined.split()) if metric == "words" else len(joined)
        if actual < target.get("min", 0) or actual > target.get("max", float("inf")):
            warnings.append({"fields":target["fields"], "metric":metric, "actual":actual,
                "target":{k:v for k,v in target.items() if k in {"min", "max"}}, "severity":"advisory"})
    return {"structural_validation":"passed", "editorial_warnings":warnings,
            "semantic_review_required":True}
