"""Streamlit presentation for the real registry and read-only Notion launch inventory."""
from datetime import date, datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from launchlens.gtm_registry import HarnessError
from launchlens.inventory import (InventoryError, MARKET_NAMES, OUTPUT_NAMES,
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
    st.session_state["screen"] = "inventory"
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


def brief_page(display, snapshot):
    request = st.session_state["selected_request"]
    market = request["market_id"]
    row = snapshot["markets"][market]
    st.title("Launch brief")
    st.subheader(display["product_name"])
    left, right = st.container(key="brief-layout").columns([2, 1], gap="small")
    with left, st.container(border=True):
        st.write(f'Market: {MARKET_NAMES[market]}')
        st.write(f'Planned launch: {date_label(row["planned_launch_date"])}')
        st.write("Campaign objective: Introduce Cherry Float’s flavor")
        st.caption(display["case"]["objectives"][0]["label"])
        with st.form("launch-brief"):
            when = st.date_input("Evaluation date", date.fromisoformat(request["evaluation_date"]))
            submitted = st.form_submit_button("Save brief")
        if submitted:
            try:
                request = request_for_market(display, snapshot, market, when.isoformat())
                st.session_state["selected_request"] = request
                st.success("Brief saved in this session. No agent or generation has started.")
            except (InventoryError, HarnessError, ValueError):
                st.error("Choose a valid date within the supported task.")
        result = evaluate_launch(row["context"], request["evaluation_date"])
        st.markdown(f'#### Launch decision: {result["decision"]}')
        st.caption(f'Evaluated for {date_label(request["evaluation_date"])} using the fetched Notion snapshot shown above.')
        if result["decision"] == "Proceed":
            st.success("Internal drafting permitted by these fictional records. Publishing remains disabled.")
        else:
            st.warning("Promotional drafting is withheld while these conditions remain unresolved.")
        for condition in result["conditions"]:
            st.text(condition["message"])
        with st.expander("Readiness checks and source records"):
            for record in row["context"]["readiness"]:
                values = record["values"]
                st.text(f'{values["Readiness Area"]}: {values["Status"]}')
                st.text(values["Blocker / Missing Information"])
        st.info("This checkpoint provides the real inventory and brief selection. Agent execution, drafting and Reviewer controls will be connected in a later checkpoint.")
    with right:
        source_documents(display, snapshot)


def main():
    st.set_page_config(page_title="LaunchLens — GTM Launches", page_icon="🚀", layout="wide")
    st.html(Path(__file__).with_name("inventory_ui.css"))
    try:
        display = load_display()
    except InventoryError:
        st.error("Approved product information is unavailable or has changed. No source reads or execution started.")
        st.stop()
    st.session_state.setdefault("screen", "inventory")
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
            if current.button("Current brief", key="current", type="tertiary", disabled="selected_request" not in st.session_state):
                st.session_state["screen"] = "brief"
            if reload.button("Refresh data", key="refresh", type="tertiary"):
                refresh(display)
                snapshot = st.session_state["inventory"]
        active = "current" if st.session_state["screen"] == "brief" else "home"
        st.html(f'<style>.st-key-{active} button:not(:disabled) {{ color: #f0f4fa; font-weight: 600; }}</style>')
        stamp = datetime.fromisoformat(snapshot["fetched_at"]).astimezone(ZoneInfo("America/Los_Angeles"))
        st.caption(f'Source checks completed {stamp.strftime("%b %d, %Y · %I:%M:%S %p %Z")} · Explicit refresh; navigation reuses this snapshot.')
    if snapshot["status"] != "ok":
        st.warning("Some launch data is unavailable. Missing dates/readiness do not grant permission. Refresh data after resolving source access.")
    if st.session_state["screen"] == "brief" and "selected_request" in st.session_state:
        brief_page(display, snapshot)
    else:
        inventory_page(display, snapshot)
    st.caption("Independent educational project using a fictional launch scenario. Not affiliated with The Coca-Cola Company. LaunchLens never publishes content.")
