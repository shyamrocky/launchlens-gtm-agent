#!/usr/bin/env python3
"""M2.2a: one authorized US run. Default preflight never reads keys or calls APIs.

--execute uses the existing private .env, native Nebius tool calls, Notion reads and
Pinecone retrieval. Fixed output directory refuses reruns. No publishing or writes
outside local audit output. No corpus/preparation/workspace inputs are needed.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from launchlens.agent_foundation import FoundationSession
from launchlens.gtm_registry import MAX_SEARCHES, MAX_TURNS, validate_request
from launchlens.live_research import (MODEL, PROMPT_SHA256, MAX_OUTPUT_TOKENS,
    LiveResearchTools, NebiusHTTP, ResearchModel, load_prompt, tool_schemas)
from launchlens.notion_tools import NotionHTTP, NotionReader
from launchlens.retrieval import PineconeHTTP

OUTPUT = ROOT / "data/generated/m22a-us-research"
REQUEST = {"use_case_id": "cherry-float-gtm", "product_id": "CC-CHERRY-FLOAT",
           "market_id": "US", "evaluation_date": "2026-12-14", "objective_id": "flavor_discovery"}


def read_keys(path):
    if not path.is_file() or path.stat().st_mode & 0o077:
        raise ValueError("Credential file missing or not private")
    names = {"NEBIUS_API_KEY", "NOTION_API_KEY", "PINECONE_API_KEY"}
    found = {}
    for line in path.read_text().splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        name, value = line.split("=", 1)
        name = name.strip().removeprefix("export ").strip()
        if name not in names:
            continue
        value = value.strip().strip("\"'")
        if name in found or not value or any(c.isspace() for c in value):
            raise ValueError("Credential missing, duplicated or malformed")
        found[name] = value
    if set(found) != names:
        raise ValueError("Three existing service credentials are required")
    return found


def evidence_rows(state):
    rows = {}
    for result in state.get("evidence", []):
        for row in result["records"]:
            rows.setdefault(row["chunk_id"], row)
    return list(rows.values())


def evaluate(state):
    usable = {r["unit_id"] for r in evidence_rows(state)
              if r["authority"] == "public_product_facts" and r["usable_as_complete_evidence"]}
    checks = {
        "live_research_completed": state["mode"] == "live_research" and state["status"] == "research_complete",
        "scoped_request_preserved": state["request"] == REQUEST,
        "pmm_obtained": bool(state["pmm"] and state["pmm"]["status"] == "ok"),
        "code_computed_proceed": bool(state["launch"] and state["launch"]["decision"] == "Proceed"
                                      and state["launch"]["promotional_draft_allowed"]),
        "publishing_disabled": bool(state["launch"] and state["launch"]["publishing_allowed"] is False),
        # Evaluator expectations ONLY: never supplied as queries or agent instructions.
        "flavor_and_inspiration_evidence": {"PROD-002", "PROD-003"} <= usable,
        "within_execution_limits": state["turns"] <= MAX_TURNS and state["searches"] <= MAX_SEARCHES,
        "no_draft_review_or_acceptance": not state["drafts"] and not state["review"] and not state["human_accepted"],
    }
    issues = [i for result in state.get("evidence", []) for i in result["issues"]]
    passed = all(checks.values())
    return {"verdict": ("PASS_WITH_LIMITATIONS" if issues else "PASS") if passed else "REVIEW_REQUIRED",
            "checks": checks, "retrieval_issues": issues,
            "usable_public_units": sorted(usable)}


def render_report(receipt, state):
    lines = ["# M2.2a — One live US research run", "",
        "Observed execution; no marketing copy, Reviewer or publishing.", "",
        f"- Verdict: **{receipt['status']}**; run state: **{state['status']}**.",
        f"- Model: `{MODEL}`; evaluation date: `{REQUEST['evaluation_date']}` (fictional scenario).",
        f"- Execution started: {receipt['started_local']}.",
        f"- Model turns: {state['turns']}/{MAX_TURNS}; product searches: {state['searches']}/{MAX_SEARCHES}.",
        f"- Elapsed: {receipt['elapsed_seconds']} seconds.", "",
        "## Actual model-selected actions", "",
        "| Turn | Proposed action | Arguments | Harness outcome |", "|---|---|---|---|"]
    for call in receipt['model_actions']:
        action = call.get('action', {})
        outcomes = [e['outcome'] for e in state['events'] if e.get('action_id') == action.get('id')]
        arguments = json.dumps(action.get('arguments', {}), ensure_ascii=False).replace('|', r'\|').replace('\n', ' ')
        lines.append(f"| {call['turn']} | {action.get('name', call['outcome'])} | {arguments} | {', '.join(outcomes) or 'not dispatched'} |")
    lines.extend(["", "## Launch and evidence", ""])
    if state['launch']:
        launch = state['launch']
        lines.extend([f"Harness decision: **{launch['decision']}**; draft preparation: {launch['promotional_draft_allowed']}; "
            f"publishing: {launch['publishing_allowed']}.", "",
            "This is fictional operational permission, not verified real stock or company authorization.", ""])
    rows = evidence_rows(state)
    lines.append(f"Unique returned evidence records: **{len(rows)}**. Full packets remain in the local state audit.")
    for row in rows:
        if row['evidence_payload'].get('chunk_kind') != 'product_claim':
            continue
        p = row['evidence_payload']
        lines.extend(["", f"### {row['unit_id']} — {row['authority']}", "", p['primary_text'], "",
            f"Complete evidence flag: {row['usable_as_complete_evidence']}; reference status: {row['reference_status']}."])
        for source in p['claim_source_mappings']:
            lines.append(f"- Direct support {source.get('source_id')}: {source.get('source_url')}. "
                         f"Scope: {source.get('market_scope')}. Limitation: {source.get('notes_or_limitations')}.")
    lines.extend(["", "## Verification and limitations", ""])
    for name, passed in receipt['evaluation']['checks'].items():
        lines.append(f"- {name}: {'PASS' if passed else 'NOT SATISFIED'}.")
    for issue in receipt['evaluation']['retrieval_issues']:
        lines.append(f"- Retrieval issue: {issue['code']} — {issue['message']}")
    lines.extend(["", "No general retrieval-accuracy or semantic-entailment guarantee. UK/India live behavior, "
        "controlled live failure handling, drafting, Reviewer and UI remain later checkpoints.", "",
        "## Usage", "", json.dumps(receipt['usage'], ensure_ascii=False), "",
        "Actual currency charges were not obtained from billing; no dollar-cost claim is made.", ""])
    return '\n'.join(lines)


def execute(*, output=None):
    output = OUTPUT if output is None else Path(output)
    validate_request(REQUEST)
    load_prompt()
    if output.exists():
        raise ValueError("Execution output already exists; no rerun without new owner approval")
    keys = read_keys(ROOT / '.env')
    output.mkdir(parents=True)
    os.chmod(output, 0o700)
    receipt = {"status": "IN_PROGRESS", "model": MODEL, "prompt_sha256": PROMPT_SHA256,
        "request": REQUEST, "started_local": datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(),
        "limits": {"model_turns": MAX_TURNS, "product_searches": MAX_SEARCHES,
                   "max_output_tokens_per_call": MAX_OUTPUT_TOKENS},
        "model_http_events": [], "notion_http_events": [], "pinecone_http_events": [],
        "model_actions": []}
    def save():
        (output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    save()
    model_http = NebiusHTTP(keys['NEBIUS_API_KEY'], on_event=save)
    notion_http = NotionHTTP(keys['NOTION_API_KEY'])
    pinecone_http = PineconeHTTP(keys['PINECONE_API_KEY'])
    model = ResearchModel(model_http)
    receipt.update(model_http_events=model_http.events, notion_http_events=notion_http.events,
                   pinecone_http_events=pinecone_http.events, model_actions=model.calls)
    tools = LiveResearchTools(NotionReader(notion_http), pinecone_http)
    session = FoundationSession(model, tools, mode='live_research')
    started = time.monotonic()
    try:
        state = session.run(session.start(REQUEST)['run_id'])
        receipt.update(run_id=state['run_id'], elapsed_seconds=round(time.monotonic()-started, 3),
            finished_local=datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(),
            evaluation=evaluate(state))
        receipt['status'] = receipt['evaluation']['verdict']
        receipt['usage'] = {k: sum(e.get('usage', {}).get(k, 0) for e in model_http.events)
                            for k in ['prompt_tokens', 'completion_tokens', 'total_tokens']}
        receipt['usage']['pinecone_query_tokens'] = sum(
            e.get('usage', {}).get('total_tokens', 0) for e in pinecone_http.events)
        (output/'state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n')
        (output/'review.md').write_text(render_report(receipt, state))
        receipt['state_sha256'] = hashlib.sha256((output/'state.json').read_bytes()).hexdigest()
        receipt['review_sha256'] = hashlib.sha256((output/'review.md').read_bytes()).hexdigest()
        save()
        print(json.dumps({k: receipt[k] for k in ['status','run_id','elapsed_seconds','usage','evaluation']}, indent=2))
        print('Readable audit:', output/'review.md')
    except Exception:
        receipt['status'] = 'STOPPED'
        receipt['failure'] = 'Execution or local audit failed; no retry or fallback.'
        save()
        raise ValueError(receipt['failure']) from None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.execute:
        execute()
    else:
        validate_request(REQUEST)
        load_prompt()
        print(json.dumps({'status':'OFFLINE_PREFLIGHT_PASS','model':MODEL,
            'registered_actions':len(tool_schemas()),'request':REQUEST,
            'live_calls':0,'credentials_read':False},indent=2))
