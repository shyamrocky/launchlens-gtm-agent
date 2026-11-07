"""Session-scoped LangGraph harness; adapters own provider and source access.

Adapters are trusted application code; model proposals and retrieved text are data.
The full LangGraph object/checkpointer are private, never exposed as model tools.
"""
from copy import deepcopy
import hashlib
import json
from threading import Lock
import time
from uuid import uuid4

from typing_extensions import TypedDict
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langsmith import tracing_context

from launchlens.evidence_payload import storage_fields
from launchlens.gtm_registry import (HarnessError, MAX_SEARCHES, MAX_TURNS,
    action_registry, objective_claims, require, validate_action, validate_request)
from launchlens.launch_checks import evaluate_launch
from launchlens.notion_tools import PMM_PAGE, PRODUCT
from launchlens.retrieval import checked_packet


class State(TypedDict):
    run_id: str
    request: dict
    mode: str
    status: str
    turns: int
    searches: int
    pmm: dict | None
    launch: dict | None
    evidence: list
    ledger: dict
    events: list
    feedback: str
    clarification: str
    pending: dict | None
    drafts: dict
    review: dict
    human_accepted: bool
    research_gaps: list


def initial_state(request, mode="offline_simulation"):
    return State(run_id=str(uuid4()), request=request, mode=mode,
                 status="created", turns=0, searches=0, pmm=None, launch=None,
                 evidence=[], ledger={}, events=[], feedback="", clarification="",
                 pending=None, drafts={}, review={}, human_accepted=False, research_gaps=[])


class FoundationSession:
    """One active run. Explicit fresh generation replaces it; no run history.

    model(snapshot) returns exactly one action. tools implements read_pmm(request),
    read_launch(request), search(query, authority). M2.1 uses safe fixtures only.
    Public run/resume methods accept a run ID, not model-provided graph updates.
    """
    def __init__(self, model, tools, *, max_turns=MAX_TURNS, max_searches=MAX_SEARCHES,
                 mode="offline_simulation"):
        require(mode in {"offline_simulation", "live_research"}, "Invalid execution mode")
        require(callable(model), "A model adapter is required")
        require(all(callable(getattr(tools, name, None)) for name in
                    ("read_pmm", "read_launch", "search")), "Missing tool adapter")
        require(type(max_turns) is int and 1 <= max_turns <= MAX_TURNS, "Invalid turn limit")
        require(type(max_searches) is int and 1 <= max_searches <= MAX_SEARCHES, "Invalid search limit")
        self._model, self._tools = model, tools
        self._mode = mode
        self._max_turns, self._max_searches = max_turns, max_searches
        self._lock = Lock()
        self._run_id = None
        self._initial = None
        self._saver = InMemorySaver()
        builder = StateGraph(State)
        builder.add_node("decide", self._decide)
        builder.add_node("dispatch", self._dispatch)
        builder.add_node("clarify", self._clarify)
        builder.add_edge(START, "decide")
        builder.add_conditional_edges("decide", lambda s: "dispatch" if s["status"] == "running" else END)
        builder.add_conditional_edges("dispatch", self._route)
        builder.add_edge("clarify", "decide")
        # Suppress automatic tracing even if inherited environment enables LangSmith.
        with tracing_context(enabled=False):
            self._graph = builder.compile(checkpointer=self._saver)

    @staticmethod
    def _route(state):
        if state["status"] == "running":
            return "decide"
        return "clarify" if state["status"] == "needs_clarification" else END

    def _config(self):
        return {"configurable": {"thread_id": self._run_id}, "callbacks": [],
                "recursion_limit": 3 * self._max_turns + 10}

    def _check_id(self, run_id):
        require(type(run_id) is str and self._run_id is not None and run_id == self._run_id,
                "Unknown or discarded run; cannot resume")

    def _snapshot(self):
        if self._run_id is None:
            return None
        values = self._graph.get_state(self._config()).values
        return deepcopy(dict(values) if values else self._initial)

    def snapshot(self):
        require(self._lock.acquire(blocking=False), "Execution is running")
        try:
            return self._snapshot()
        finally:
            self._lock.release()

    def start(self, request):
        request = validate_request(request)  # Reject before model/tool invocation or old-state deletion.
        require(self._lock.acquire(blocking=False), "Execution is running")
        try:
            require(self._run_id is None, "Use generate_again to replace the current task")
            self._initial = initial_state(request, self._mode)
            self._run_id = self._initial["run_id"]
            return self._snapshot()
        finally:
            self._lock.release()

    def _discard(self):
        # Trusted lifecycle hooks do local cleanup only; never registered model actions.
        failed = False
        try:
            for adapter in (self._model, self._tools):
                cleanup = getattr(adapter, "reset_run", None)
                if callable(cleanup):
                    try:
                        cleanup()
                    except Exception:
                        failed = True
        finally:
            if self._run_id is not None:
                self._saver.delete_thread(self._run_id)
            self._run_id, self._initial = None, None
        require(not failed, "Local adapter cleanup failed; no active task remains")

    def generate_again(self, request):
        request = validate_request(request)
        require(self._lock.acquire(blocking=False), "Execution is running; replacement disabled")
        try:
            self._discard()
            self._initial = initial_state(request, self._mode)
            self._run_id = self._initial["run_id"]
            return self._snapshot()
        finally:
            self._lock.release()

    def reset(self):
        require(self._lock.acquire(blocking=False), "Execution is running; reset disabled")
        try:
            self._discard()
        finally:
            self._lock.release()

    def run(self, run_id):
        return self._execute(run_id)

    def resume(self, run_id, reply):
        require(type(reply) is str and reply.strip() and len(reply) <= 2000,
                "Clarification reply must contain 1–2000 characters")
        return self._execute(run_id, reply=reply)

    def _execute(self, run_id, reply=None):
        require(self._lock.acquire(blocking=False), "Execution is already running")
        try:
            self._check_id(run_id)
            state = self._snapshot()
            if reply is None and state["status"] != "created":
                return state  # Rerender/replay never invokes or resumes the graph.
            require(reply is None or state["status"] == "needs_clarification",
                    "This run is not awaiting clarification")
            inputs = Command(resume=reply) if reply is not None else {**state, "status": "running"}
            with tracing_context(enabled=False):
                try:
                    self._graph.invoke(inputs, self._config())
                except Exception:
                    # No exception bodies, source text or credentials in events.
                    self._graph.update_state(self._config(), {"status": "failed",
                        "events": [*self._snapshot()["events"],
                                   {"action": "execution", "outcome": "failed_safely"}]})
            self._initial = None
            return self._snapshot()
        finally:
            self._lock.release()

    @staticmethod
    def _event(state, action, outcome, started, **fields):
        state["events"].append({"sequence": len(state["events"]) + 1,
            "action": action, "outcome": outcome,
            "elapsed_seconds": round(time.monotonic() - started, 6), **fields})

    def _decide(self, state):
        state = deepcopy(state)
        if state["turns"] >= self._max_turns:
            state["status"] = "failed"
            state["events"].append({"action": "budget", "outcome": "turn_limit"})
            return state
        view = deepcopy(state)
        view.pop("pending", None)
        view["allowed_actions"] = action_registry()
        view["remaining_limits"] = {"model_turns": self._max_turns - state["turns"],
                                    "product_searches": self._max_searches - state["searches"]}
        state["turns"] += 1
        state["pending"] = None
        started = time.monotonic()
        try:
            proposal = deepcopy(self._model(view))
            # Bounded, JSON-only action boundary. Never merge a model state patch.
            require(len(json.dumps(proposal, allow_nan=False)) <= 8000, "Action exceeds size bound")
            state["pending"] = deepcopy(validate_action(proposal))
        except (HarnessError, TypeError, ValueError, OverflowError):
            self._event(state, "model_proposal", "rejected", started)
        except Exception:
            state["status"] = "failed"
            self._event(state, "model_adapter", "failed_safely", started)
        return state

    @staticmethod
    def _validate_evidence(value, authority):
        require(type(value) is dict and value.get("product_id") == PRODUCT and
                value.get("requested_authority") == authority and
                value.get("status") in {"evidence_found", "incomplete"} and
                type(value.get("records")) is list and len(value["records"]) <= 10,
                "Invalid evidence result")
        seen = set()
        for record in value["records"]:
            require(type(record) is dict and type(record.get("chunk_id")) is str and
                    record["chunk_id"] not in seen, "Duplicate or malformed evidence record")
            seen.add(record["chunk_id"])
            payload = record["evidence_payload"]
            metadata = storage_fields(payload)
            require(record["chunk_id"] == payload["chunk_id"] and
                    record.get("unit_id") == payload["unit_id"] and
                    record["authority"] == payload["authority"] and
                    record["evidence_sha256"] == metadata["evidence_sha256"], "Evidence identity/digest differs")
            checked_packet({"id": record["chunk_id"], "metadata": metadata}, record["authority"])
            require(record["authority"] == authority or
                    (authority == "synthetic_product_intent" and record["authority"] == "public_product_facts"),
                    "Evidence authority transition not allowed")
            require(type(record.get("usable_as_complete_evidence")) is bool, "Missing evidence completeness flag")
            require(record.get("reference_status") in {"resolved", "not_expanded", "incomplete", "invalid"},
                    "Missing reference completeness status")
            require(not record["usable_as_complete_evidence"] or
                    record["reference_status"] in {"resolved", "not_expanded"},
                    "Contradictory evidence completeness")
        return value

    @staticmethod
    def _objective_gaps(state):
        supported = {row["evidence_payload"]["unit_id"]
                     for result in state["evidence"] for row in result["records"]
                     if row["authority"] == "public_product_facts" and
                     row["usable_as_complete_evidence"] and
                     row["evidence_payload"].get("chunk_kind") == "product_claim" and
                     row["evidence_payload"].get("claim_source_mappings")}
        return [label for claim, label in objective_claims(state["request"]).items()
                if claim not in supported]

    def _dispatch(self, state):
        state = deepcopy(state)
        action = state["pending"]
        state["pending"] = None
        if action is None:
            return state
        name, args, action_id = action["name"], action["arguments"], action["id"]
        fingerprint = hashlib.sha256(json.dumps({"name": name, "arguments": args},
            sort_keys=True, allow_nan=False).encode()).hexdigest()
        started = time.monotonic()
        previous = state["ledger"].get(action_id)
        if previous is not None:
            if previous["fingerprint"] != fingerprint or previous["status"] != "completed":
                state["status"] = "failed"
                self._event(state, name, "replay_conflict", started, action_id=action_id)
            else:
                self._event(state, name, "replayed", started, action_id=action_id)
            return state
        state["ledger"][action_id] = {"action": deepcopy(action), "fingerprint": fingerprint,
                                      "status": "pending", "result": None}
        try:
            if name == "read_pmm_brief":
                value = deepcopy(self._tools.read_pmm(deepcopy(state["request"])))
                require(type(value) is dict and value.get("status") == "ok" and
                        value.get("page_id") == PMM_PAGE and value.get("authority") == "synthetic_pmm_guidance" and
                        type(value.get("blocks")) is list and value["blocks"], "Complete PMM guidance required")
                state["pmm"] = value
            elif name == "check_launch":
                context = deepcopy(self._tools.read_launch(deepcopy(state["request"])))
                require(type(context) is dict and context.get("market_id") == state["request"]["market_id"] and
                        context.get("product_id") == PRODUCT, "Wrong operational scope")
                value = evaluate_launch(context, state["request"]["evaluation_date"])
                state["launch"] = value
                if value["decision"] == "Hold":
                    state["status"] = "held"
            elif name == "search_product_evidence":
                require(state["searches"] < self._max_searches, "Search limit reached")
                state["searches"] += 1
                value = self._validate_evidence(deepcopy(self._tools.search(**args)), args["authority"])
                state["evidence"].append(value)
                state["research_gaps"] = self._objective_gaps(state)
            elif name == "request_clarification":
                value = {"question": args["question"]}
                state["clarification"] = args["question"]
                state["status"] = "needs_clarification"
            else:  # finish cannot supply status/approval; code determines the outcome.
                launch = state["launch"]
                require(launch is not None, "Launch eligibility must be checked")
                if launch["decision"] == "Clarify":
                    state["status"] = "needs_clarification"
                    state["clarification"] = "; ".join(c["message"] for c in launch["conditions"])
                else:
                    require(launch["promotional_draft_allowed"] and state["pmm"] is not None,
                            "Research prerequisites remain incomplete")
                    state["research_gaps"] = self._objective_gaps(state)
                    if not state["research_gaps"]:
                        state["status"] = "research_complete"
                value = {"status": "research_incomplete" if state["research_gaps"] and
                         state["status"] == "running" else state["status"],
                         "mode": state["mode"], "missing_requirements": list(state["research_gaps"])}
            state["ledger"][action_id].update(status="completed", result=deepcopy(value))
            self._event(state, name, "completed", started, action_id=action_id,
                        decision=state["launch"]["decision"] if name == "check_launch" else None)
        except Exception:
            state["ledger"][action_id]["status"] = "failed"
            state["status"] = "failed"
            self._event(state, name, "failed_safely", started, action_id=action_id)
        return state

    def _clarify(self, state):
        # Interrupt node has no side effects before interrupt: resume reexecutes it.
        reply = interrupt({"run_id": state["run_id"], "question": state["clarification"],
                           "notice": "Reply is guidance, never operational approval"})
        require(type(reply) is str and reply.strip() and len(reply) <= 2000, "Invalid clarification reply")
        return {"feedback": reply, "status": "running", "clarification": ""}
