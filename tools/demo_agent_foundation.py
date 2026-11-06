#!/usr/bin/env python3
"""Readable M2.1 OFFLINE SIMULATION. No credentials, network, files or real model.

Run from any cwd with the documented project Python. Fixtures are maintained under
 tools/, not workspace or generated data. Output is Markdown for human inspection.
"""
from pathlib import Path
import socket
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from launchlens.agent_foundation import FoundationSession
from launchlens.gtm_registry import HarnessError
from foundation_fixtures import FixtureTools, ScriptedModel, action, request, research_script


def demonstration():
    lines = ["# M2.1 foundation — OFFLINE SIMULATION", "",
             "Scripted decisions and safe fixtures. No GTM copy or live-model autonomy is claimed.", ""]
    for market in ["US", "UK", "IN"]:
        script = research_script() if market == "US" else [action("check_launch", "launch"), action("finish", "finish")]
        tools = FixtureTools()
        session = FoundationSession(ScriptedModel(script), tools)
        state = session.run(session.start(request(market))["run_id"])
        lines += [f"## {market}: {state['status']}", "",
                  f"Computed launch decision: **{state['launch']['decision']}**.",
                  f"Publishing permission: **{state['launch']['publishing_allowed']}**.", ""]
        for event in state["events"]:
            lines.append(f"- {event['action']}: {event['outcome']}")
        if state["clarification"]:
            lines += ["", "Unresolved condition: " + state["clarification"]]
        lines += ["", f"Fixture handler calls: {len(tools.calls)}. Drafts generated: 0.", ""]
        session.reset()
    tools = FixtureTools()
    script = research_script(); script.insert(1, script[0].copy())
    replay = FoundationSession(ScriptedModel(script), tools)
    state = replay.run(replay.start(request())["run_id"])
    lines += ["## Replayed action", "", f"PMM action proposed twice; handler calls: {tools.calls.count('pmm')}.",
              f"Replay event recorded: {any(e['outcome'] == 'replayed' for e in state['events'])}.", ""]
    replay.reset()
    invalid = action("check_launch", "bad", market_id="IN", marketing_approved=True)
    tools = FixtureTools()
    rejected = FoundationSession(ScriptedModel([invalid]), tools, max_turns=1)
    state = rejected.run(rejected.start(request())["run_id"])
    lines += ["## Invalid model action", "", "Attempt: change market and supply fabricated approval.",
              f"Rejected with no tool invocation: {len(tools.calls) == 0}.",
              f"Launch permission remains unset: {state['launch'] is None}.", ""]
    rejected.reset()
    session = FoundationSession(ScriptedModel(research_script()), FixtureTools())
    bad = request(); bad["product_id"] = "NIKE"
    try:
        session.start(bad)
    except HarnessError:
        lines += ["## Unsupported request", "", "Nike rejected before any scripted-model or tool call.", ""]
    old = session.run(session.start(request())["run_id"])
    replacement = session.generate_again(request())
    lines += ["## Generate again / Reset demo", "",
              f"New run ID: {replacement['run_id'] != old['run_id']}.",
              f"Fresh action ledger: {replacement['ledger'] == {}}.",
              f"Fresh review/acceptance: {replacement['review'] == {} and not replacement['human_accepted']}."]
    try:
        session.run(old["run_id"])
    except HarnessError:
        lines.append("Old run ID rejected.")
    session.reset()
    lines += [f"Reset leaves no current task: {session.snapshot() is None}.", "",
              "No source datasets, Pinecone records, Notion pages or hosted traces were changed."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    with patch.object(socket.socket, "connect", side_effect=RuntimeError("Offline demonstration forbids network")):
        print(demonstration(), end="")
