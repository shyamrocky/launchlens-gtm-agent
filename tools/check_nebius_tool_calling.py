#!/usr/bin/env python3
"""One isolated model/tool/result cycle; no application integrations.

Default is offline preflight. --execute requires owner authorization and makes
at most two chat requests, with no retries or fallback models.
"""
import argparse
import datetime
import json
from pathlib import Path
import re
import secrets
import ssl
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MODEL = "Qwen/Qwen3-30B-A3B-Instruct-2507"
ENDPOINT = "https://api.tokenfactory.nebius.com/v1/chat/completions"
OUTPUT = ROOT / "data/generated/nebius-tool-smoke/receipt.json"
EXPECTED_ARGS = {"product_id": "TEST-LAUNCH", "market": "US", "evaluation_date": "2026-12-14"}
TOOL = {"type": "function", "function": {
    "name": "get_test_launch_status",
    "description": "Read a harmless local test fixture. No real product, calendar, approvals or external service. Returns fixture status and a verification code.",
    "parameters": {"type": "object", "properties": {
        "product_id": {"type": "string", "enum": ["TEST-LAUNCH"]},
        "market": {"type": "string", "enum": ["US"]},
        "evaluation_date": {"type": "string", "enum": ["2026-12-14"]}},
        "required": ["product_id", "market", "evaluation_date"], "additionalProperties": False}}}
MESSAGES = [
    {"role": "system", "content": "You are testing tool integration, not real launch readiness. Obtain the requested fixture status from the available tool; do not invent it. After receiving the tool result, return ONLY a JSON object with exactly status and verification_code copied from that result. No prose or Markdown."},
    {"role": "user", "content": "Look up the test launch status for product TEST-LAUNCH, market US, evaluation date 2026-12-14. Report its status and verification code."}]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def dispatch(call):
    require(call.get("type") == "function", "Unexpected tool type")
    require(isinstance(call.get("id"), str) and call["id"], "Missing tool-call ID")
    require(call["function"]["name"] == TOOL["function"]["name"], "Unapproved tool")
    args = json.loads(call["function"]["arguments"])
    require(args == EXPECTED_ARGS, "Arguments outside approved fixture scope")
    return {"status": "FIXTURE_ONLY_READY", "verification_code": secrets.token_hex(8)}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def execute():
    require(not OUTPUT.exists(), "Receipt already exists; refusing another hosted run")
    env = ROOT / ".env"
    require(env.stat().st_mode & 0o077 == 0, "Environment file must be private")
    values = []
    for line in env.read_text().splitlines():
        match = re.match(r"^\s*(?:export\s+)?NEBIUS_API_KEY\s*=(.*)$", line)
        if match:
            values.append(match[1].strip().strip("\"'"))
    require(len(values) == 1 and values[0] and not any(c.isspace() for c in values[0]), "Missing or ambiguous key")
    key = values[0]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    receipt = {"status": "IN_PROGRESS", "model": MODEL, "endpoint": ENDPOINT,
               "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "request_limit": 2, "max_output_tokens_per_request": 256,
               "tool_choice": "auto", "calls": []}

    def save():
        OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                                         urllib.request.HTTPSHandler(context=ssl.create_default_context()))

    def chat(messages):
        require(len(receipt["calls"]) < 2, "Inference limit reached")
        event = {"attempt": len(receipt["calls"]) + 1}
        receipt["calls"].append(event)
        save()  # Count an attempted request even if transport fails.
        payload = {"model": MODEL, "messages": messages, "tools": [TOOL],
                   "tool_choice": "auto", "temperature": 0, "max_tokens": 256,
                   "stream": False, "store": False}
        request = urllib.request.Request(ENDPOINT, data=json.dumps(payload).encode(), method="POST",
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "Accept": "application/json"})
        started = time.monotonic()
        try:
            with opener.open(request, timeout=45) as response:
                event["http_status"] = response.status
                result = json.load(response)
        except urllib.error.HTTPError as error:
            event["http_status"] = error.code
            event["error"] = error.read(2000).decode(errors="replace").replace(key, "[REDACTED]")
            save()
            raise ValueError(f"Nebius rejected inference: HTTP {error.code}; no retries") from None
        event["elapsed_seconds"] = round(time.monotonic() - started, 3)
        event["usage"] = result.get("usage", {})
        event["response_model"] = result.get("model")
        require(len(result.get("choices", [])) == 1, "Expected one response choice")
        choice = result["choices"][0]
        event["finish_reason"] = choice["finish_reason"]
        raw = choice["message"]
        # Persist only public assistant output/tool calls, not internal reasoning.
        message = {k: raw[k] for k in ("role", "content", "tool_calls") if k in raw and raw[k] is not None}
        event["assistant_message"] = message
        save()
        require(message.get("role") == "assistant", "Unexpected response role")
        require(choice["finish_reason"] != "length", "Output truncated; stop")
        return message

    save()
    try:
        first = chat(MESSAGES)
        calls = first.get("tool_calls", [])
        require(len(calls) == 1, "Model did not select exactly one test tool; stop")
        fixture = dispatch(calls[0])
        receipt["tool_result"] = fixture
        second = chat(MESSAGES + [first, {"role": "tool", "tool_call_id": calls[0]["id"], "content": json.dumps(fixture)}])
        require(not second.get("tool_calls"), "Model requested another tool; stop at two requests")
        answer = json.loads(second.get("content", ""))
        require(answer == fixture, "Final answer did not preserve exact tool result")
        require(all(isinstance(call["usage"].get("total_tokens"), int) for call in receipt["calls"]), "Usage unavailable")
        receipt["total_usage"] = {k: sum(c["usage"].get(k, 0) for c in receipt["calls"])
                                  for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
        receipt.update(status="PASS", finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       valid_tool_and_arguments=True, exact_tool_result_consumed=True)
        save()
        print(json.dumps(receipt, indent=2))
    except Exception as error:
        receipt.update(status="STOPPED", failure=str(error).replace(key, "[REDACTED]"))
        save()
        raise ValueError(receipt["failure"]) from None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.execute:
        execute()
    else:
        require(TOOL["function"]["parameters"]["required"] == list(EXPECTED_ARGS), "Fixture schema mismatch")
        print("Offline preflight PASS. --execute makes at most two hosted requests; stops on error. No real launch data or service tools.")
