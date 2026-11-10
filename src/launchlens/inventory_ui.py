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


def checked_label(result, name="Product Brief"):
    status = result.get("status", "not_checked")
    labels = {"accessible": "✓ Accessible", "unavailable": "Access unavailable", "not_checked": "Not checked"}
    label = labels.get(status, "Not checked")
    if status == "changed":
        label = ("Product brief" if name == "Product Brief" else name) + " changed — evidence not re-indexed"
    when = result.get("checked_at")
    if when and status in {"accessible", "unavailable", "changed"}:
        stamp = datetime.fromisoformat(when).astimezone(ZoneInfo("America/Los_Angeles"))
        label += " · checked " + stamp.strftime("%b %d, %I:%M:%S %p %Z")
    return label


def indexed_date():
    """Read the existing successful corpus receipt; no provider read or mtime guess."""
    import json
    from launchlens.retrieval import INDEX, NAMESPACE, MODEL
    path = Path(__file__).resolve().parents[2] / 'data/generated/m15b4-full-corpus/receipt.json'
    try:
        receipt = json.loads(path.read_bytes())
        if (receipt['status'], receipt['index'], receipt['namespace'], receipt['model'], receipt['upserted_count']) != ('PASS', INDEX, NAMESPACE, MODEL, 45):
            return None
        stamp = datetime.fromisoformat(receipt['finished_utc'])
        if stamp.utcoffset() is None:
            return None
        return date_label(stamp.astimezone(ZoneInfo('America/Los_Angeles')).date().isoformat())
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        return None


def product_evidence_status(display, snapshot):
    """Home checksum summary, separate from live index health or launch permission."""
    from launchlens.source_access import APPROVED_PDFS
    checks = [(doc, snapshot.get('source_access', {}).get(doc['name'], {}))
              for doc in display['documents'] if doc['app'] == 'Google Drive']
    if any(c.get('status') == 'changed' or
           (c.get('sha256') and c.get('indexed_sha256') and c['sha256'] != c['indexed_sha256'])
           for _, c in checks):
        return 'Product brief changed · evidence not re-indexed', 'warn'
    indexed = indexed_date()
    if indexed is None:
        return 'Product evidence · index date unavailable · Not verified', 'unknown'
    matched = (snapshot.get('data_mode') != 'offline' and len(checks) == 2 and
               all(c.get('status') == 'accessible' and c.get('sha256') == c.get('indexed_sha256') == APPROVED_PDFS.get(doc['file_id'])
                   for doc, c in checks))
    return 'Product evidence · indexed ' + indexed + (' · ✓ Up to date' if matched else ' · Not checked'), 'good' if matched else 'unknown'


def source_documents(display, snapshot):
    with st.container(border=True, key="source-documents"):
        st.subheader("Source documents")
        st.caption(display["product_name"])
        with st.container(key="snapshot-caption"):
            stamp=datetime.fromisoformat(snapshot['fetched_at']).astimezone(ZoneInfo('America/Los_Angeles'))
            st.caption('Fixture snapshot · No live source checks performed.' if snapshot.get('data_mode')=='offline' else
                'Last checked '+stamp.strftime('%I:%M %p').lstrip('0')+' · '+stamp.strftime('%b %d, %Y %Z'))
            summary, tone = product_evidence_status(display, snapshot)
            st.html(f'<p class="product-evidence-status {tone}" title="Index date from the saved successful corpus receipt; status compares Drive checksums with indexed documents, without a Pinecone request.">{escape(summary)}</p>')
        if st.button('Rebuild evidence (planned) ›', key='source-rebuild', type='tertiary'):
            st.session_state['screen'] = 'rebuild'; st.rerun()
        blocked=refresh_blocked()
        if st.button('↻ Refresh',key='refresh',type='tertiary',disabled=blocked,help=REFRESH_BLOCKED_MESSAGE if blocked else 'Re-read launch data and check Drive access; keep current runs.'):
            refresh(display);st.rerun()
        refresh_result(snapshot)
        groups = []
        for app in ("Google Drive", "Notion"):
            items = []
            for index, doc in enumerate(display["documents"]):
                if doc["app"] == app:
                    result = snapshot.get("source_access", {}).get(doc["name"], {})
                    tone = "good" if result.get("status") == "accessible" else "warn" if result.get("status") == "changed" else "unknown"
                    detail = checked_label(result, doc["name"])
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


REFRESH_BLOCKED_MESSAGE = "Finish or stop the run to refresh"


def refresh_blocked():
    """Read-only lifecycle guard, including queued commands and clarification pauses."""
    if st.session_state.get("run-command") is not None:
        return True
    run = st.session_state.get("offline_run")
    if getattr(run,"watching_worker",False):return True
    if run is None:
        return False
    try:
        state = run.snapshot()
    except HarnessError:  # The harness lock is held by executing work.
        return True
    return bool(state and (state["status"] in {"created", "running", "needs_clarification"}
                           or state.get("revision_request") is not None))


def refresh_changes(previous, current):
    """Compare Home snapshots only; never read or mutate a run's evidence."""
    changes, incomplete = [], []
    for market in ("US", "UK", "IN"):
        name = "India" if market == "IN" else market
        old = previous.get("markets", {}).get(market, {})
        new = current.get("markets", {}).get(market, {})
        if old.get("source_status") != "ok" or new.get("source_status") != "ok":
            incomplete.append(name)
            continue
        if old.get("planned_launch_date") != new.get("planned_launch_date"):
            changes.append(f'{name} · Launch date: {date_label(old.get("planned_launch_date"))} → {date_label(new.get("planned_launch_date"))}')
        def checks(row):
            records = (row.get("context") or {}).get("readiness", [])
            values = [record.get("values", {}) for record in records]
            areas = [v.get("Readiness Area") for v in values]
            required = {area for area, _ in READINESS_LABELS}
            return {v["Readiness Area"]: v for v in values} if len(areas) == 4 and set(areas) == required else None
        before, after = checks(old), checks(new)
        if before is None or after is None:
            incomplete.append(name)
            continue
        for area, label in READINESS_LABELS:
            a, b = before[area], after[area]
            if a.get("Status") != b.get("Status"):
                changes.append(f'{name} · {label}: {a.get("Status", "Not verified")} → {b.get("Status", "Not verified")}')
            # Other operational edits matter even when the displayed status stays the same.
            for key, field in (("Blocker / Missing Information", "blocker / missing information"),
                               ("Evidence / Reference", "supporting reference"), ("Last Updated", "status date")):
                if a.get(key) != b.get(key):
                    changes.append(f'{name} · {label}: {field} updated')
    for name, new in current.get("source_access", {}).items():
        old = previous.get("source_access", {}).get(name, {})
        if new.get("status") in {"unavailable", "not_checked"}:
            incomplete.append(name)
        elif old.get("status") != new.get("status"):
            changes.append(f'{name} · Access: {old.get("status", "not_checked").replace("_", " ")} → {new["status"]}')
        elif new.get("sha256") != old.get("sha256"):
            changes.append(f'{name} · Document changed — evidence not re-indexed')
    return {"changes": changes, "incomplete": incomplete, "fetched_at": current.get("fetched_at")}


def refresh_result(snapshot):
    result = st.session_state.get("refresh-result")
    if not result or result["fetched_at"] != snapshot.get("fetched_at"):
        return
    prefix = "Simulation updated" if snapshot.get("data_mode") == "offline" else "Updated"
    if result["changes"]:
        st.success(prefix + " · " + "\n\n".join(result["changes"]))
    if result["incomplete"]:
        st.warning("Refresh incomplete · Could not fully compare/check: " + ", ".join(result["incomplete"]) + ". Check source access before relying on readiness.")
    elif not result["changes"]:
        st.info(prefix + " · No changes")


def refresh(display):
    """Replace only Home/source data. Never reset runs, decisions, approval or setup."""
    if refresh_blocked():
        st.warning(REFRESH_BLOCKED_MESSAGE)
        return False
    previous = st.session_state.get("inventory")
    st.session_state.pop("refresh-result", None)
    # Replace stale homepage permissions on failure, without touching run evidence.
    st.session_state.pop("inventory", None)
    if st.session_state.get("ui-mode") == "Demo simulation":
        from launchlens.offline_ui_run import fixture_inventory
        st.session_state["inventory"] = fixture_inventory(display)
    else:
        with st.spinner("Checking launch data and source access…"):
            st.session_state["inventory"] = fetch_inventory(display, verify_documents=True)
    if previous is not None:
        st.session_state["refresh-result"] = refresh_changes(previous, st.session_state["inventory"])
    return True


def rebuild_evidence_card(snapshot):
    """Roadmap placeholder only: deliberately no confirmation or execution handler."""
    with st.container(border=True, key="rebuild-evidence"):
        st.subheader("Planned rebuild process")
        st.caption("Not implemented · Preview of a future capability")
        changed = [name for name, check in snapshot.get("source_access", {}).items()
                   if check.get("status") == "changed"]
        if changed:
            st.warning("Changed source: " + ", ".join(changed) + ". The indexed evidence is unchanged.")
        st.write("Re-download approved Drive PDFs, re-chunk, re-embed, verify claim IDs and activate replacement Pinecone evidence.")
        st.markdown("**1. Approve changed content.** A changed checksum does not approve new claims. Preserve Product Brief facts, synthetic PRD intent and validated claim mappings.")
        st.markdown("**2. Build and verify first.** Activate only after chunks, embeddings, claim IDs and Pinecone checks pass. A failed rebuild must leave current evidence and runs usable.")
        st.markdown("**3. Export before replacing runs.** A future confirmation will list affected product runs and offer Download first. Remove them from active use only after successful activation; retain protected audit history.")
        st.button("Rebuild evidence · Coming later", key="rebuild-evidence-placeholder", disabled=True,
                  help="Not implemented. No files, embeddings, Pinecone records or runs will change.")
        st.caption("Blocked during an active run. Requires separate approval and an embedding budget. Nothing runs from this card.")


def inventory_page(display, snapshot):
    saved=ui_saved_runs()
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
                a, b, c, d = st.columns([0.5, 1.1, 1.5, 1.3], vertical_alignment="center")
                a.write("India" if market == "IN" else market)
                b.write(date_label(row["planned_launch_date"]))
                symbol = {"good": "●", "warn": "●", "hold": "●", "unknown": "○"}[row["tone"]]
                c.html(f'<span class="readiness {row["tone"]}">{symbol}</span> {escape(row["label"])}')
                record=next((x for x in saved if x['request']['market_id']==market),None)
                if record:
                    view, fresh = d.columns([1.25, 1], gap="small", vertical_alignment="center")
                    label = "View package ›" if record['status'] == 'approved' else "View run ›"
                    if view.button(label, type="tertiary", key=f"view-{market}", width="stretch"):
                        attached=st.session_state.get('offline_run')
                        if attached is None or attached.snapshot()['run_id'] != record['run_id']:
                            if st.session_state.get('ui-mode') == 'Demo simulation':
                                st.error('Saved simulation unavailable in this session.')
                                st.stop()
                            from launchlens.live_package import load_current_live_run
                            try:
                                attached=load_current_live_run()
                                if attached.snapshot()['run_id'] != record['run_id']:
                                    raise HarnessError('Different current run')
                            except (HarnessError, ValueError, TypeError, KeyError, OSError):
                                st.error('This saved package could not be opened. No model calls were made.')
                                st.stop()
                            st.session_state['offline_run']=attached
                        st.session_state['selected_request']=record['request']
                        st.session_state['screen']='run'
                        st.rerun()
                    if fresh.button('Start fresh', key='fresh-'+market, type='tertiary', width="stretch"):
                        open_archive(record)
                elif d.button("Open brief ›", type="tertiary", key=f"open-{market}", width="stretch", disabled=row["planned_launch_date"] is None):
                    prior=st.session_state.get('selected_request',{})
                    when=prior.get('evaluation_date') if prior.get('market_id')==market else None
                    st.session_state["selected_request"] = request_for_market(display, snapshot, market,when)
                    st.session_state["screen"] = "brief"
                    st.rerun()
        archives=ui_archived_runs()
        if st.button('Archived packages ('+str(len(archives))+') ›',key='archives',type='tertiary'):
            st.session_state['screen']='archives';st.rerun()
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
        package = "Campaign brief · LinkedIn · Email · Blog · Three ad variations"
        if result["decision"] == "Hold":
            package = "Promotional package blocked"
        elif result["decision"] != "Proceed" or tone == "unknown":
            package = "GTM package — paused pending readiness"
        objective = next(o["label"] for o in display["case"]["objectives"] if o["id"] == request["objective_id"])
        from launchlens.voice_policy import load_tone_policy
        tone_policy=load_tone_policy()
        with st.container(border=False, key="prepare-summary"):
            st.html('<dl class="prepare-summary">'
                f'<div><dt>Objective</dt><dd>{escape(objective)}</dd></div>'
                f'<div><dt>Package</dt><dd>{escape(package)}</dd></div>'
            f'<div><dt>Tone</dt><dd>{escape(tone_policy["core_tone"])}</dd></div></dl>')
            with st.expander("per format ›", expanded=False):
                from launchlens.package_content import LABELS
                for name,spec in tone_policy['format_specs'].items():
                    st.write(LABELS[name]+": "+spec['tone'])
                st.caption("Steer the writing through Notes for the agent. Required evidence and policy rules still apply.")
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
                edits=st.session_state.setdefault('preparation_date_edit',{})
                edits[market]=st.checkbox("Check a different date", key=f"prepare-edit-date-{market}",value=edits.get(market,False))
                if edits[market]:
                    st.date_input("Evaluation date", date.fromisoformat(request["evaluation_date"]), key=date_key,
                        help="Checks readiness for this date. Does not change the planned launch date.")
        notes = st.session_state.setdefault("preparation_notes", {})
        notes[market] = st.text_area("Notes for the agent (optional)", value=notes.get(market, ""),
            key=f"prepare-notes-{market}", max_chars=1000,
            placeholder="Lean into nostalgia; avoid health claims",
            help="Campaign guidance only. Notes cannot change supported tasks, evidence or launch permissions.")
        offline = st.session_state.get("ui-mode") == "Demo simulation"
        existing = st.session_state.get("offline_run")
        saved=next((x for x in ui_saved_runs() if x['request']['market_id']==market),None)
        if offline:
            from launchlens.offline_ui_run import OfflineUIRun, SCENARIOS
            scenario = st.selectbox("Simulation case", SCENARIOS, key="prepare-scenario")
        else:
            scenario = None
        from launchlens.live_package import readiness
        ready = readiness(request=request) if not offline else {'ready':False}
        live_allowed = ready['ready'] and ready.get('request') == request
        if st.button("Start simulation" if offline else "Start agent", key="prepare-start", type="primary",
                     disabled=(not offline and not live_allowed) or existing is not None or saved is not None):
            try:
                from launchlens.voice_policy import BRAND_POLICY_ID
                if offline:
                    run = OfflineUIRun(request, notes[market], scenario, voice_policy_id=BRAND_POLICY_ID, package=True)
                else:
                    from launchlens.live_package import create_live_run
                    run = create_live_run(request, notes[market])
                st.session_state["offline_run"] = run  # Own before execution; rerender never re-dispatches.
                st.session_state['run-command']='execute'
                st.session_state["screen"] = "run"
                st.rerun()
            except HarnessError:
                st.error("Run could not start. Check the registered task, archive any existing package and verify the remaining budget.")
        if saved is not None:
            from launchlens.run_archive import executing
            in_progress=executing(saved) if not offline else saved['status'] in {'created','running'}
            st.caption('A '+market_name+' run is in progress · View it' if in_progress else
                       'A '+market_name+' package is saved · View it or archive it before starting fresh.')
        elif existing is not None:
            st.caption('A current run is already attached · View it before starting another run.')
        if (existing is not None or saved is not None) and st.button("View current simulation" if offline else "View current run", key="prepare-view-run", type="tertiary"):
            if existing is None and not offline:
                from launchlens.live_package import load_current_live_run
                st.session_state['offline_run']=load_current_live_run()
            st.session_state["screen"] = "run"; st.rerun()
        st.caption("Scripted offline simulation only. No model or source calls; one current run. Archive it before starting fresh."
                   if offline else ready['message'])
        if result["decision"] == "Hold":
            st.caption("Promotional drafting is blocked. Research-only runs are not connected.")
        elif result["decision"] != "Proceed":
            st.caption("Missing information must be resolved through authoritative evidence; notes cannot grant approval.")


def ui_saved_runs():
    if st.session_state.get('ui-mode')=='Demo simulation':
        run=st.session_state.get('offline_run')
        return [simulation_record(run)] if run is not None else []
    from launchlens.run_archive import saved_runs
    return saved_runs()


def ui_archived_runs():
    if st.session_state.get('ui-mode')=='Demo simulation':return st.session_state.get('simulation-archives',[])
    from launchlens.run_archive import archived_runs
    return archived_runs()


def budget_caption():
    if st.session_state.get('ui-mode')=='Demo simulation':return
    from launchlens.run_archive import demo_budget
    from decimal import Decimal
    value=demo_budget()
    if value:st.caption('Demo budget left: $'+format(Decimal(value['remaining_usd']),'.2f')+' · shared by dry run and recording')


def simulation_record(run):
    state=run.snapshot()
    return {'run_id':state['run_id'],'request':state['request'],'version':(state.get('package') or {}).get('version',0),
        'status':state['status'],'date':datetime.now().astimezone().isoformat(),'simulation_state':state}


def archive_download(record):
    if 'simulation_state' not in record:
        from launchlens.run_archive import download_package
        return download_package(record)
    import io,json,zipfile
    from launchlens.package_presentation import markdown_package,SIMULATION_LABEL
    data=io.BytesIO();state=record['simulation_state']
    with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as out:
        out.writestr('README.txt',SIMULATION_LABEL+'\nOffline simulation archive; no live model result.')
        out.writestr('checkpoint.json',json.dumps(state,ensure_ascii=False,indent=2))
        if state.get('package'):out.writestr('Version-'+str(record['version'])+'.md',markdown_package(state))
    return data.getvalue()


def detach_archived_run():
    # Drop UI ownership only. Never call reset/_save on archived protected receipts.
    st.session_state.pop('offline_run',None)
    for key in list(st.session_state):
        if key.startswith('run-') or key.startswith('prepare-'):del st.session_state[key]
    st.session_state.pop('preparation_notes',None)
    st.session_state.pop('preparation_date_edit',None)


def open_archive(record):
    st.session_state['pending-archive-record']=record
    st.rerun()


@st.dialog('Archive & start fresh',width='large',on_dismiss='rerun')
def archive_confirmation(record,run=None):
    market=record['request']['market_id'];label='India' if market=='IN' else market
    active=st.session_state.get('run-command') is not None
    current=run or st.session_state.get('offline_run')
    if current is not None:
        try:
            state=current.snapshot()
            active=active or state['status'] in {'created','running'} or state.get('revision_request') is not None
            active=active or bool(getattr(getattr(current,'guard',None),'active',False))
        except HarnessError:active=True
    status='approved' if record['status']=='approved' else 'awaiting review' if record['status']=='awaiting_human_review' else record['status'].replace('_',' ')
    st.write('Archive '+label+' · Version '+str(record['version'])+' ('+status+') and start a new run? The archived package stays downloadable.')
    st.caption('Sources, product evidence and original receipts stay unchanged. This does not refill the demo budget or call a model.')
    if active:st.warning('Stop the run first')
    try:data=archive_download(record)
    except (HarnessError,ValueError,OSError,KeyError):
        st.error('The package could not be verified for archive. No run was moved.');return
    st.download_button('Download first',data,file_name='LaunchLens-'+market+'-V'+str(record['version'])+'.zip',mime='application/zip',key='archive-download-first')
    a,b=st.columns(2)
    if a.button('Archive & start fresh',key='archive-confirm',type='primary',disabled=active):
        try:
            if 'simulation_state' in record:
                value=dict(record,archived_at=datetime.now().astimezone().isoformat())
                st.session_state.setdefault('simulation-archives',[]).append(value)
            else:
                from launchlens.run_archive import archive_run
                archive_run(record,active=active,session_notes={'agent_notes':st.session_state.get('preparation_notes',{}).get(market,'')})
            detach_archived_run()
            st.session_state.pop('pending-archive-record',None)
            display=load_display();snapshot=st.session_state['inventory']
            st.session_state['selected_request']=request_for_market(display,snapshot,market)
            st.session_state['screen']='brief';st.rerun()
        except (HarnessError,ValueError,OSError):st.error('Archive could not complete. The original receipts are preserved; reopen the current package.')
    if b.button('Cancel',key='archive-cancel'):
        st.session_state.pop('pending-archive-record',None);st.rerun()


def archived_page():
    st.title('Archived packages')
    st.caption('Read-only packages · No restore in MVP · Nothing is published')
    rows=ui_archived_runs()
    if not rows:st.info('No archived packages yet.')
    for record in rows:
        market=record['request']['market_id'];name='India' if market=='IN' else market
        with st.container(border=True,key='archived-'+record['run_id']):
            a,b=st.columns([3,1])
            a.write(name+' · Version '+str(record['version'])+' · '+record['status'].replace('_',' '))
            stamp=datetime.fromisoformat(record['archived_at']).astimezone(ZoneInfo('America/Los_Angeles'))
            a.caption(stamp.strftime('%b %d, %Y · %I:%M %p %Z'))
            try:data=archive_download(record)
            except (HarnessError,ValueError,OSError,KeyError):st.warning('Download unavailable: an original receipt could not be verified.')
            else:b.download_button('Download',data,file_name='LaunchLens-'+market+'-'+record['run_id'][:8]+'.zip',mime='application/zip',key='archive-get-'+record['run_id'])
    if st.button('‹ GTM launches',key='archive-home',type='tertiary'):st.session_state['screen']='inventory';st.rerun()


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
    st.session_state['ui-mode']=st.session_state.get('ui-mode',st.session_state.get('_data_mode','Demo simulation' if default_offline else 'Live agent'))
    mode=st.session_state['ui-mode']
    if mode=='Live agent' and 'offline_run' not in st.session_state:
        from launchlens.live_package import current_resume_available,load_current_live_run
        if current_resume_available():
            try:
                restored=load_current_live_run()
                st.session_state.update(offline_run=restored,selected_request=restored.snapshot()['request'],screen='run')
            except (HarnessError,ValueError,TypeError,KeyError,OSError):
                st.warning('Saved run could not be verified. Original artifacts are kept; no model action was replayed.')
    with st.container(key="page-header"):
        brand, nav = st.columns([2, 3], vertical_alignment="center")
        brand.html('<div class="launchlens-brand">LaunchLens</div><p class="launchlens-tagline">Your launch-aware GTM agent.</p>')
        with nav, st.container(border=True, key="header-navigation"):
            back, current = st.columns(2)
            if back.button("GTM launches", key="home", type="tertiary"):
                st.session_state["screen"] = "inventory"
            from launchlens.review_decisions import saved_review_available
            from launchlens.live_package import current_resume_available,load_current_live_run
            has_saved=mode=='Live agent' and saved_review_available()
            has_resume=mode=='Live agent' and 'offline_run' not in st.session_state and current_resume_available()
            if current.button("Current run", key="current", type="tertiary"):
                if has_resume:
                    try:
                        restored=load_current_live_run();st.session_state['offline_run']=restored
                        st.session_state['selected_request']=restored.snapshot()['request']
                    except Exception:
                        st.error('The current package could not be resumed. No model calls were made.');st.stop()
                st.session_state["screen"] = "run" if "offline_run" in st.session_state else "saved-review" if has_saved else "empty-run"
        active = "current" if st.session_state["screen"] in {"brief","run","saved-review","empty-run"} else "home"
        st.html(f'<style>.st-key-{active} button:not(:disabled) {{ color: #f0f4fa; font-weight: 600; }}</style>')
    if st.session_state['screen']=='inventory':
        with st.container(key='launch-heading'):
            heading,control=st.columns([4,1],vertical_alignment='center')
            heading.title('GTM Launches')
            with heading:budget_caption()
            with control:
                mode=st.selectbox('Mode',['Live agent','Demo simulation'],key='ui-mode',format_func=lambda value:'Mode: '+value,label_visibility='collapsed', disabled=refresh_blocked())
    if mode=='Demo simulation':
        st.warning('OFFLINE SIMULATION — fixture inventory and scripted model choices. No live AI, Notion, Drive or Pinecone calls.')
    previous_mode=st.session_state.get('_data_mode')
    if previous_mode is not None and mode!=previous_mode:
        # Explicit mode replacement retains its existing lifecycle; never a Refresh effect.
        if refresh_blocked():
            st.warning(REFRESH_BLOCKED_MESSAGE);st.stop()
        from launchlens.agent_run_ui import clear_run
        clear_run()
        st.session_state.pop('selected_request', None)
        st.session_state.pop('preparation_notes', None)
        for key in list(st.session_state):
            if key.startswith('prepare-'):del st.session_state[key]
        st.session_state['screen']='inventory'
        st.session_state.pop('inventory',None)
        st.session_state.pop("refresh-result", None)
    st.session_state['_data_mode']=mode
    if 'inventory' not in st.session_state and not refresh(display):st.stop()
    snapshot=st.session_state['inventory']
    if snapshot["status"] != "ok":
        st.warning("Some launch data is unavailable. Missing dates/readiness do not grant permission. Refresh data after resolving source access.")
    if st.session_state["screen"] == "rebuild":
        st.title("Rebuild evidence")
        with st.container(key="rebuild-page"):
            rebuild_evidence_card(snapshot)
    elif st.session_state["screen"] == "archives":
        archived_page()
    elif st.session_state["screen"] == "empty-run":
        st.title('Current run')
        st.info('No current package. Choose a market from GTM Launches to start a fresh run.')
        budget_caption()
        if st.button('Go to GTM launches',key='empty-home',type='primary'):
            st.session_state['screen']='inventory';st.rerun()
    elif st.session_state["screen"] == "saved-review":
        from launchlens.review_decisions import load_saved_review
        from launchlens.agent_run_ui import review_page
        try:
            saved=load_saved_review()
        except Exception:
            st.error("Saved review is unavailable or has changed. No model calls were made.")
        else:
            left, _ = st.container(key="detail-layout").columns([2, 1], gap="small")
            with left, st.container(key="agent-run"):review_page(saved,saved=True)
    elif st.session_state["screen"] == "run" and "offline_run" in st.session_state:
        from launchlens.agent_run_ui import run_page
        with st.container(key="run-layout"):run_page(display)
    elif st.session_state["screen"] == "brief" and "selected_request" in st.session_state:
        left, _ = st.container(key="detail-layout").columns([2, 1], gap="small")
        with left:brief_page(display, snapshot)
    else:
        inventory_page(display, snapshot)
    if 'pending-archive-record' in st.session_state:
        archive_confirmation(st.session_state['pending-archive-record'])
    st.caption("Independent educational project using a fictional launch scenario. Not affiliated with The Coca-Cola Company. LaunchLens never publishes content.")
