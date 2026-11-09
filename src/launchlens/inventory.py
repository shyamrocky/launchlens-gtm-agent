"""Read-only launch inventory. No model, generation, fixture fallback or workspace input."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

from launchlens.gtm_registry import supported_use_cases, validate_request
from launchlens.launch_checks import evaluate_launch, iso_date
from launchlens.notion_tools import (NotionHTTP, NotionReader, PMM_PAGE,
    CALENDAR_DATABASE, READINESS_DATABASE)

from launchlens.source_access import access_result, check_drive_pdf

ROOT = Path(__file__).resolve().parents[2]
MARKET_NAMES = {"US": "United States", "UK": "United Kingdom", "IN": "India"}
OUTPUT_NAMES = {"campaign_brief": "Campaign brief", "linkedin": "LinkedIn",
    "email": "Email", "blog": "Blog", "ad_variations": "Ad variations"}


class InventoryError(ValueError):
    """Safe inventory/configuration failure; no credential or source body."""


def load_display(root=ROOT):
    """Approved display metadata only; calendar and readiness are never configured here."""
    try:
        value = json.loads((root / "data/templates/gtm/launch_inventory.json").read_text())
        cases = supported_use_cases()
        case = next(c for c in cases if c["use_case_id"] == value["use_case_id"])
        if value["version"] != 1 or value["product_id"] != case["product_id"]:
            raise ValueError
        binding = value["product_brief"]
        if binding["path"] != "data/public_sources/coca_cola_cherry_float_product_brief.md":
            raise ValueError
        raw = (root / binding["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != binding["sha256"]:
            raise ValueError
        if value["description_claim_ids"] != ["PROD-002", "PROD-003"]:
            raise ValueError
        if not all(c in raw.decode() for c in value["description_claim_ids"]):
            raise ValueError
        if not all(isinstance(value[k], str) and value[k].strip()
                   for k in ("product_name", "brand", "description")):
            raise ValueError
        docs = []
        if len(value["drive_documents"]) != 2:
            raise ValueError
        for doc in value["drive_documents"]:
            if not re.fullmatch(r"[A-Za-z0-9_-]{20,80}", doc["file_id"]):
                raise ValueError
            docs.append({"app": "Google Drive", "name": doc["name"], "role": doc["role"],
                         "kind": "PDF", "file_id": doc["file_id"], "url": f'https://drive.google.com/file/d/{doc["file_id"]}/view'})
        for name, role, kind, resource in [
            ("PMM / GTM Brief", "Positioning and messaging", "Page", PMM_PAGE),
            ("Launch Calendar", "Planned launch dates", "Database", CALENDAR_DATABASE),
            ("Readiness Tracker", "Launch approvals and blockers", "Database", READINESS_DATABASE),
        ]:
            docs.append({"app": "Notion", "name": name, "role": role, "kind": kind,
                         "url": "https://www.notion.so/" + resource.replace("-", "")})
        return {**value, "case": case, "documents": docs}
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, StopIteration):
        raise InventoryError("Approved product display information is unavailable or has changed.") from None


def read_notion_key(env_file=ROOT / ".env"):
    """One credential only; do not expose keys to session state, HTML, telemetry or logs."""
    key = os.environ.get("NOTION_API_KEY")
    if key is None:
        try:
            if env_file.stat().st_mode & 0o077:
                raise ValueError
            values = []
            for line in env_file.read_text().splitlines():
                if "=" not in line or line.lstrip().startswith("#"):
                    continue
                name, value = line.split("=", 1)
                if name.strip().removeprefix("export ").strip() == "NOTION_API_KEY":
                    values.append(value.strip().strip("\"'"))
            if len(values) != 1:
                raise ValueError
            key = values[0]
        except (OSError, UnicodeError, ValueError):
            raise InventoryError("Notion access is unavailable. Check local NOTION_API_KEY configuration and private file permissions.") from None
    if not isinstance(key, str) or not key or any(c.isspace() for c in key):
        raise InventoryError("Notion access is unavailable. Check local NOTION_API_KEY configuration.")
    return key


def unavailable_row(market):
    return {"market_id": market, "planned_launch_date": None, "evaluation_date": None,
            "source_status": "unavailable", "label": "Readiness unavailable", "tone": "unknown",
            "context": None, "decision": None}


def market_row(context, market):
    """Find the source's sole launch date and reuse the accepted policy at that date."""
    row = unavailable_row(market)
    try:
        if context.get("status") != "ok" or context.get("market_id") != market:
            return row
        launches = [r["values"] for r in context["calendar"] if r["values"].get("Launch Stage") == "Launch"]
        if len(launches) != 1:
            return row
        when = iso_date(launches[0]["Planned Launch Date"]).isoformat()
        result = evaluate_launch(context, when)
        invalid = {"invalid_calendar", "incomplete_calendar", "ambiguous_launch_date"}
        if result["planned_launch_date"] != when or any(c["code"] in invalid for c in result["conditions"]):
            return row
        decision = result["decision"]
        label = {"Proceed": "Drafting permitted", "Clarify": "Clarification needed", "Hold": "Promotional drafting on hold"}[decision]
        areas = {r["values"]["Readiness Area"]: r["values"]["Status"] for r in context["readiness"]}
        if decision == "Clarify" and areas.get("Regional availability") == "Missing":
            label = "Availability confirmation missing"
        if decision == "Hold" and areas.get("Marketing communication authorization") == "Pending":
            label = "Marketing approval pending"
        return {**row, "planned_launch_date": when, "evaluation_date": when, "source_status": "ok",
                "label": label, "tone": {"Proceed": "good", "Clarify": "warn", "Hold": "hold"}[decision],
                "context": deepcopy(context), "decision": result}
    except (KeyError, TypeError, ValueError, AttributeError):
        return row


def fetch_inventory(display, reader=None, *, verify_documents=False):
    """Bounded live reads only. The caller owns session refresh; no cache or retry here."""
    result = {"status": "unavailable", "started_at": datetime.now(timezone.utc).isoformat(),
              "fetched_at": None, "error": None, "markets": {}, "read_events": [],
              "source_access": {d["name"]: access_result() for d in display["documents"]}}
    contexts_read = []
    try:
        if reader is None:
            reader = NotionReader(NotionHTTP(read_notion_key()))
        for market in display["case"]["markets"]:
            context = reader.get_launch_context(market)
            contexts_read.append(context.get("status") == "ok")
            result["markets"][market] = market_row(context, market)
        ok = sum(r["source_status"] == "ok" for r in result["markets"].values())
        result["status"] = "ok" if ok == len(result["markets"]) else "partial" if ok else "unavailable"
    except (InventoryError, ValueError, TypeError, OSError):
        result["error"] = "Notion launch data is unavailable. No dates or readiness permissions were inferred."
    # Conservative complete-read check; operational validation/permission stays separate.
    complete = len(contexts_read) == len(display["case"]["markets"]) and all(contexts_read)
    for name in ("Launch Calendar", "Readiness Tracker"):
        result["source_access"][name] = access_result("accessible" if complete else "unavailable",
            detail="complete_scoped_read" if complete else "scoped_read_incomplete")
    if verify_documents:
        try:
            pmm = reader.get_pmm_brief() if reader is not None else {}
            accessible = pmm.get("status") == "ok" and bool(pmm.get("blocks"))
            result["source_access"]["PMM / GTM Brief"] = access_result(
                "accessible" if accessible else "unavailable", detail="complete_pmm_read" if accessible else "pmm_read_incomplete",
                block_count=pmm.get("block_count") if accessible else None)
        except (ValueError, TypeError, OSError, AttributeError):
            result["source_access"]["PMM / GTM Brief"] = access_result("unavailable", detail="pmm_read_incomplete")
        for doc in display["documents"]:
            if doc["app"] == "Google Drive":
                result["source_access"][doc["name"]] = check_drive_pdf(doc["file_id"])
    for market in display["case"]["markets"]:
        result["markets"].setdefault(market, unavailable_row(market))
    transport = getattr(reader, "transport", None)
    result["read_events"] = deepcopy(getattr(transport, "events", []))
    result["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return result


def launch_window(snapshot):
    dates = [row["planned_launch_date"] for row in snapshot["markets"].values()]
    if not dates or any(d is None for d in dates):
        return None
    return min(dates), max(dates)


def request_for_market(display, snapshot, market, evaluation_date=None):
    """Registry admission before brief selection; no tool or model invocation."""
    if market not in display["case"]["markets"]:
        raise InventoryError("Unsupported market; no execution started.")
    when = evaluation_date or snapshot["markets"][market]["planned_launch_date"]
    return validate_request({"use_case_id": display["case"]["use_case_id"],
        "product_id": display["case"]["product_id"], "market_id": market,
        "objective_id": display["case"]["objectives"][0]["id"], "evaluation_date": when})
