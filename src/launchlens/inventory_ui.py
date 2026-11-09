"""Streamlit presentation for the real registry and read-only Notion launch inventory."""
from datetime import date, datetime
from html import escape
from pathlib import Path
import os
from zoneinfo import ZoneInfo

import streamlit as st

from launchlens.gtm_registry import HarnessError
from launchlens.inventory import (InventoryError, OUTPUT_NAMES,
    fetch_inventory, launch_window, load_display, request_for_market)
from launchlens.launch_checks import evaluate_launch


def date_label(value):
    if not value:
        return "Date unavailable"
    d = date.fromisoformat(value)
    return f'{d.strftime("%b")} {d.day}, {d.year}'


def checked_label(result):
    status = result.get("status", "not_checked")
    labels = {"accessible": "✓ Accessible", "unavailable": "Access unavailable", "not_checked": "Not checked"}
    label = labels.get(status, "Not checked")
    when = result.get("checked_at")
    if when and status in {"accessible", "unavailable"}:
        stamp = datetime.fromisoformat(when).astimezone(ZoneInfo("America/Los_Angeles"))
        label += " · checked " + stamp.strftime("%b %d, %I:%M:%S %p %Z")
    return label


def source_documents(display, snapshot):
    with st.container(border=True, key="source-documents"):
        st.subheader("Source documents")
        st.caption(display["product_name"])
        groups = []
        for app in ("Google Drive", "Notion"):
            items = []
            for index, doc in enumerate(display["documents"]):
                if doc["app"] == app:
                    result = snapshot.get("source_access", {}).get(doc["name"], {})
                    tone = "good" if result.get("status") == "accessible" else "unknown"
                    detail = checked_label(result)
                    label = detail.split(" · checked ", 1)[0]
                    tooltip = f"source-check-{index}"
                    items.append(f'<div class="source-item"><a href="{escape(doc["url"], quote=True)}" target="_blank" rel="noopener noreferrer">'
                        f'{escape(doc["name"])} · {escape(doc["kind"])} ↗</a>'
                        f'<p class="source-role">{escape(doc["role"])}</p>'
                        f'<span class="source-check" tabindex="0" aria-label="{escape(doc["name"] + ": " + label, quote=True)}" aria-describedby="{tooltip}">'
                        f'<span class="source-access {tone}">{escape(label)}</span>'
                        f'<span class="source-tooltip" id="{tooltip}" role="tooltip">{escape(detail)}</span></span></div>')
            groups.append(f'<section class="source-group" aria-label="{escape(app)}"><h4>{escape(app)}</h4>{"".join(items)}</section>')
        st.html(f'<div class="source-grid">{"".join(groups)}</div>')


def refresh(display):
    # Remove any preceding snapshot first: a failed refresh cannot keep an old green label.
    st.session_state.pop("inventory", None)
    st.session_state.pop("selected_request", None)
    st.session_state.pop("preparation_notes", None)
    for key in list(st.session_state):
        if key.startswith("prepare-"):
            del st.session_state[key]
    st.session_state["screen"] = "inventory"
    if "offline_run" in st.session_state:
        from launchlens.agent_run_ui import clear_run
        clear_run()
    if st.session_state.get("ui-mode") == "Offline simulation":
        from launchlens.offline_ui_run import fixture_inventory
        st.session_state["inventory"] = fixture_inventory(display)
    else:
        with st.spinner("Checking launch data and source access…"):
            st.session_state["inventory"] = fetch_inventory(display, verify_documents=True)


def inventory_page(display, snapshot):
    st.title("GTM Launches")
    left, right = st.container(key="inventory-layout").columns([2, 1], gap="small")
    with left, st.container(border=True, key="launch-card"):
        st.subheader(display["product_name"])
        st.html(f'<p class="brand-line">Brand: {escape(display["brand"])}</p>')
        st.html(f'<p class="product-description">{escape(display["description"])}</p>')
        window = launch_window(snapshot)
        window_text = "Dates incomplete — refresh to check" if window is None else " – ".join(date_label(d) for d in window)
        outputs = " · ".join(OUTPUT_NAMES[o] for o in display["case"]["outputs"])
        st.html('<dl class="launch-meta">'
            f'<div><dt>Markets</dt><dd>{" · ".join("India" if m == "IN" else m for m in ("US", "UK", "IN") if m in display["case"]["markets"])}</dd></div>'
            f'<div><dt>Planned launch window</dt><dd>{escape(window_text)}</dd></div>'
            f'<div><dt>Planned deliverables</dt><dd>{escape(outputs)}</dd></div></dl>')
        st.html('<div class="launch-section-divider" aria-hidden="true"></div>'
            '<div class="campaign-objective"><p class="objective-label">Campaign objective</p>'
            '<p class="objective-value">Introduce Cherry Float’s flavor</p></div>')
        st.caption("Choose a market to prepare its brief. Readiness below is evaluated at each planned launch date, not today.")
        for market in ("US", "UK", "IN"):
            if market not in snapshot["markets"]:
                continue
            row = snapshot["markets"][market]
            with st.container(key=f"market-row-{market}"):
                a, b, c, d = st.columns([0.5, 1.2, 1.7, 0.7], vertical_alignment="center")
                a.write("India" if market == "IN" else market)
                b.write(date_label(row["planned_launch_date"]))
                symbol = {"good": "●", "warn": "●", "hold": "●", "unknown": "○"}[row["tone"]]
                c.html(f'<span class="readiness {row["tone"]}">{symbol}</span> {escape(row["label"])}')
                if d.button("Open brief ›", type="tertiary", key=f"open-{market}", width="stretch", disabled=row["planned_launch_date"] is None):
                    st.session_state["selected_request"] = request_for_market(display, snapshot, market)
                    st.session_state["screen"] = "brief"
                    st.rerun()
        st.caption("Product description: approved Product Brief, PROD-002 and PROD-003. Flavor notes and float inspiration do not establish ingredients or dairy content.")
    with right:
        source_documents(display, snapshot)


# Presentation only: permissions always come from evaluate_launch, never UI notes.
READINESS_LABELS = (
    ("Marketing communication authorization", "Marketing authorization"),
    ("Messaging approval", "Messaging approval"),
    ("Regional availability", "Regional availability"),
    ("Product information", "Product information"),
)
INCOMPLETE_GATE_CODES = {
    "source_unavailable", "malformed_source", "invalid_readiness", "missing_readiness",
    "invalid_calendar", "incomplete_calendar", "ambiguous_launch_date",
}


def preparation_gate(row, result):
    """Readable copy for an existing policy result; cannot grant any permission."""
    decision = result["decision"]
    if decision == "Hold":
        pending = any(r["values"].get("Readiness Area") == "Marketing communication authorization"
                      and r["values"].get("Status") == "Pending"
                      for r in result["readiness_evidence"])
        return "hold", "Promotional drafts blocked", (
            "Marketing approval is pending. Promotional drafting remains blocked until the required approval is recorded."
            if pending else "A required readiness check is blocked. Promotional drafting cannot proceed.")
    if row["source_status"] != "ok" or any(c["code"] in INCOMPLETE_GATE_CODES for c in result["conditions"]):
        return "unknown", "Unable to verify readiness", "Required launch information is unavailable or incomplete. Drafting remains paused."
    if decision == "Proceed":
        return "good", "Drafting permitted", "All 4 readiness checks passed."
    availability_missing = any(r["values"].get("Readiness Area") == "Regional availability"
                               and r["values"].get("Status") == "Missing"
                               for r in result["readiness_evidence"])
    if availability_missing and all(c["code"] == "readiness_unresolved" for c in result["conditions"]):
        return "warn", "Availability not confirmed", "Availability confirmation is missing. Promotional drafting remains paused until resolved."
    return "warn", "Readiness needs clarification", "The selected date or readiness records leave unresolved conditions. Promotional drafting remains paused."


def brief_page(display, snapshot):
    # Same preparation route; execution is explicit and offline-only in this checkpoint.
    request = st.session_state["selected_request"]
    market = request["market_id"]
    row = snapshot["markets"][market]
    market_name = "India" if market == "IN" else market
    with st.container(key="prepare-package"):
        if st.button("‹ Launches", key="prepare-back", type="tertiary"):
            st.session_state["screen"] = "inventory"
            st.rerun()
        st.title(f"Prepare {market_name} package")
        st.caption(f'{display["product_name"]} · Planned launch: {date_label(row["planned_launch_date"])}')

        # Date editing uses this same cached authoritative snapshot, with no source reads.
        # Process the widget value before rendering the summary/gate so one rerun suffices.
        date_key = f"prepare-date-{market}"
        if date_key in st.session_state:
            try:
                request = request_for_market(display, snapshot, market, st.session_state[date_key].isoformat())
                st.session_state["selected_request"] = request
            except (InventoryError, HarnessError, ValueError):
                st.error("Choose a valid date within the supported task.")
        result = evaluate_launch(row["context"], request["evaluation_date"])
        tone, headline, explanation = preparation_gate(row, result)
        package = "LinkedIn post (email, blog and ads coming next)"
        if result["decision"] == "Hold":
            package = "Promotional package blocked"
        elif result["decision"] != "Proceed" or tone == "unknown":
            package = "LinkedIn post — paused pending readiness"
        objective = next(o["label"] for o in display["case"]["objectives"] if o["id"] == request["objective_id"])
        with st.container(border=False, key="prepare-summary"):
            st.html('<dl class="prepare-summary">'
                f'<div><dt>Objective</dt><dd>{escape(objective)}</dd></div>'
                f'<div><dt>Package</dt><dd>{escape(package)}</dd></div></dl>')
        with st.container(border=False, key="prepare-gate"):
            st.html(f'<div class="gate-heading"><span class="readiness {tone}" aria-hidden="true">●</span>'
                f'<h3>{escape(headline)}</h3></div><p class="gate-explanation">{escape(explanation)}</p>')
            with st.expander("Details", expanded=False):
                for area, label in READINESS_LABELS:
                    matches = [r["values"] for r in result["readiness_evidence"] if r["values"].get("Readiness Area") == area]
                    value = matches[0] if len(matches) == 1 else {}
                    status = value.get("Status", "Not verified")
                    icon = "✓" if status == "Approved" else "!" if status in {"Pending", "Blocked"} else "?"
                    st.write(f"{icon} {label}: {status}")
                    blocker = value.get("Blocker / Missing Information")
                    if isinstance(blocker, str) and blocker.strip() and blocker.strip().lower() != "none":
                        st.caption(f"Blocker: {blocker}")
                for condition in result["conditions"]:
                    if condition["code"] != "readiness_unresolved":
                        st.write(condition["message"])
                for restriction in result.get("restrictions", []):
                    st.write(restriction)
                st.caption(f'From the readiness tracker and launch calendar, checked for {date_label(request["evaluation_date"])} using this source snapshot.')
                if st.checkbox("Check a different date", key=f"prepare-edit-date-{market}"):
                    st.date_input("Evaluation date", date.fromisoformat(request["evaluation_date"]), key=date_key,
                        help="Checks readiness for this date. Does not change the planned launch date.")
        notes = st.session_state.setdefault("preparation_notes", {})
        notes[market] = st.text_area("Notes for the agent (optional)", value=notes.get(market, ""),
            key=f"prepare-notes-{market}", max_chars=1000,
            placeholder="Lean into nostalgia; avoid health claims",
            help="Campaign guidance only. Notes cannot change supported tasks, evidence or launch permissions.")
        offline = st.session_state.get("ui-mode") == "Offline simulation"
        existing = st.session_state.get("offline_run")
        if offline:
            from launchlens.offline_ui_run import OfflineUIRun, SCENARIOS
            scenario = st.selectbox("Simulation case", SCENARIOS, key="prepare-scenario")
        else:
            scenario = None
        if st.button("Start simulation" if offline else "Start agent", key="prepare-start", type="primary",
                     disabled=not offline or existing is not None):
            try:
                from launchlens.voice_policy import BRAND_POLICY_ID
                run = OfflineUIRun(request, notes[market], scenario, voice_policy_id=BRAND_POLICY_ID)
                st.session_state["offline_run"] = run  # Own before execution; rerender never re-dispatches.
                with st.spinner("Running offline harness actions…"):
                    run.execute(run.snapshot()["run_id"])
                st.session_state["screen"] = "run"
                st.rerun()
            except HarnessError:
                st.error("Run could not start. Check the registered task and reset any current run.")
        if existing is not None and st.button("View current simulation", key="prepare-view-run", type="tertiary"):
            st.session_state["screen"] = "run"; st.rerun()
        st.caption("Scripted offline simulation only. No model or source calls; one current run. Reset it before changing tasks."
                   if offline else "Live agent execution is not connected yet. Choose Offline simulation to inspect the tested harness flow.")
        if result["decision"] == "Hold":
            st.caption("Promotional drafting is blocked. Research-only runs are not connected.")
        elif result["decision"] != "Proceed":
            st.caption("Missing information must be resolved through authoritative evidence; notes cannot grant approval.")


def main():
    st.set_page_config(page_title="LaunchLens — GTM Launches", page_icon="🚀", layout="wide")
    st.html(Path(__file__).with_name("inventory_ui.css"))
    try:
        display = load_display()
    except InventoryError:
        st.error("Approved product information is unavailable or has changed. No source reads or execution started.")
        st.stop()
    st.session_state.setdefault("screen", "inventory")
    default_offline = os.environ.get("LAUNCHLENS_UI_MODE") == "offline"
    mode = st.selectbox("Execution data", ["Real inventory", "Offline simulation"],
        index=1 if default_offline else 0, key="ui-mode",
        help="Switching modes clears the current setup and simulation. Real inventory never dispatches a model.")
    if mode == "Offline simulation":
        try:
            from launchlens.offline_ui_run import fixture_inventory
        except ImportError:
            st.error("Offline harness dependencies are unavailable. Run: uv sync --project tools/ui --locked --group offline-agent")
            st.stop()
        st.warning("OFFLINE SIMULATION — fixture inventory and scripted model choices. No live AI, Notion, Drive or Pinecone calls.")
    previous_mode = st.session_state.get("_data_mode")
    if previous_mode is not None and mode != previous_mode:
        st.session_state.pop("inventory", None)
    st.session_state["_data_mode"] = mode
    if "inventory" not in st.session_state:
        refresh(display)
    snapshot = st.session_state["inventory"]
    with st.container(key="page-header"):
        brand, nav = st.columns([3, 2], vertical_alignment="center")
        brand.html('<div class="launchlens-brand">LaunchLens</div><p class="launchlens-tagline">Your launch-aware GTM agent.</p>')
        with nav, st.container(border=True, key="header-navigation"):
            back, current, reload = st.columns(3)
            if back.button("GTM launches", key="home", type="tertiary"):
                st.session_state["screen"] = "inventory"
            if current.button("Current run" if "offline_run" in st.session_state else "Current setup", key="current", type="tertiary", disabled="selected_request" not in st.session_state):
                st.session_state["screen"] = "run" if "offline_run" in st.session_state else "brief"
            if reload.button("Refresh data", key="refresh", type="tertiary"):
                refresh(display)
                snapshot = st.session_state["inventory"]
        active = "current" if st.session_state["screen"] == "brief" else "home"
        st.html(f'<style>.st-key-{active} button:not(:disabled) {{ color: #f0f4fa; font-weight: 600; }}</style>')
        stamp = datetime.fromisoformat(snapshot["fetched_at"]).astimezone(ZoneInfo("America/Los_Angeles"))
        if mode == "Offline simulation":
            st.caption("Fixture snapshot · All access badges remain Not checked · No live source checks performed.")
        else:
            st.caption(f'Source checks completed {stamp.strftime("%b %d, %Y · %I:%M:%S %p %Z")} · Explicit refresh; navigation reuses this snapshot.')
    if snapshot["status"] != "ok":
        st.warning("Some launch data is unavailable. Missing dates/readiness do not grant permission. Refresh data after resolving source access.")
    if st.session_state["screen"] == "run" and "offline_run" in st.session_state:
        from launchlens.agent_run_ui import run_page
        run_page(display)
    elif st.session_state["screen"] == "brief" and "selected_request" in st.session_state:
        brief_page(display, snapshot)
    else:
        inventory_page(display, snapshot)
    st.caption("Independent educational project using a fictional launch scenario. Not affiliated with The Coca-Cola Company. LaunchLens never publishes content.")
