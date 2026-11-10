"""Deterministic model-facing view; full evidence remains in harness-owned state.

No retrieval, model, environment or file access. Exact shared objects are pooled;
roles and per-passage bindings remain explicit. Unknown packet fields are retained.
"""
from copy import deepcopy
import hashlib
import json

VERSION = "deduplicated-state-v1"
DOCUMENT_FIELDS = ("format_version", "policy_version", "product_id", "document_id",
    "document_version", "source_path", "source_url", "source_sha256",
    "source_acceptance", "preparation_acceptance", "chunk_status")
CSV_TEXT_FIELDS = ("claim_id", "source_id", "verification_status", "market_scope",
                   "temporal_scope", "source_locator", "notes_or_limitations")


class ContextError(RuntimeError):
    """Invalid context must stop rather than silently dropping evidence."""


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def structured_packet_text(packet):
    """Recognize the accepted redundant text representation; unknown forms stay intact."""
    try:
        text = "\n\n".join(s["text"] for s in packet["segments"])
        mappings = packet["claim_source_mappings"]
        if mappings:
            text += "\n\nSource-specific CSV evidence (separate from PDF text):\n"
            text += "\n\n".join("\n".join(f"{f}: {row[f]}" for f in CSV_TEXT_FIELDS) for row in mappings)
        if packet.get("links"):
            text += "\n\nPDF hyperlink destinations:\n" + "\n".join(link["uri"] for link in packet["links"])
        return text
    except (KeyError, TypeError):
        return None


def normalize_content(value):
    """Remove duplicate rich-text/API styling, preserve actual text and links."""
    if isinstance(value, list):
        return [normalize_content(v) for v in value]
    if isinstance(value, dict):
        if value.get("type") == "text" and isinstance(value.get("text"), dict):
            original = value["text"].get("content", "")
            result = {"text": value.get("plain_text", original)}
            if original != result["text"]:
                result["source_text"] = original
            urls = list(dict.fromkeys(url for url in
                [value.get("href"), (value["text"].get("link") or {}).get("url")] if url))
            if urls:
                result["urls"] = urls
            # Keep non-default styling: strikethrough/code/emphasis can carry meaning.
            annotations = {k: deepcopy(v) for k, v in value.get("annotations", {}).items()
                           if not ((k in {"bold", "italic", "strikethrough", "underline", "code"} and v is False)
                                   or (k == "color" and v == "default"))}
            if annotations:
                result["annotations"] = annotations
            extras = {k: normalize_content(v) for k, v in value.items()
                      if k not in {"type", "text", "plain_text", "href", "annotations"}}
            if extras:
                result["additional_fields"] = extras
            return result
        return {k: normalize_content(v) for k, v in value.items()}
    return deepcopy(value)


def build_context(state):
    """Pure projection: no token truncation, semantic selection or LLM summarization."""
    pool, index, packets, packet_index = {}, {}, {}, {}
    def intern(kind, value):
        key = kind + ":" + canonical(value)
        if key not in index:
            alias = "s" + str(len(pool) + 1)
            index[key] = alias
            pool[alias] = {"kind": kind, "value": deepcopy(value)}
        return index[key]
    result = {"policy": VERSION, "lower_trust_data_only": True, "shared": pool,
              "packets": packets, "retrieval_results": [],
              "pmm": normalize_content(state["pmm"]), "launch": deepcopy(state["launch"])}
    for retrieval in state["evidence"]:
        summary = {k: deepcopy(v) for k, v in retrieval.items() if k != "records"}
        # Search ranking is already explicit; retain ranks/metadata, never reorder hits.
        summary["records"] = []
        for row in retrieval["records"]:
            packet = row["evidence_payload"]
            chunk_id = packet["chunk_id"]
            serialized = canonical(packet)
            if chunk_id in packet_index:
                alias, previous = packet_index[chunk_id]
                if previous != serialized:
                    raise ContextError("Same evidence ID has conflicting packets")
            else:
                alias = "p" + str(len(packets) + 1)
                packet_index[chunk_id] = (alias, serialized)
                document = {k: packet[k] for k in DOCUMENT_FIELDS if k in packet}
                omitted = set(document) | {"text", "segments", "source_references", "claim_source_mappings"}
                focused = {k: deepcopy(v) for k, v in packet.items() if k not in omitted}
                focused.update(document_ref=intern("document", document),
                    segment_refs=[intern("segment", v) for v in packet["segments"]],
                    source_reference_refs=[intern("source_reference", v) for v in packet["source_references"]],
                    claim_source_mapping_refs=[intern("claim_source_mapping", v) for v in packet["claim_source_mappings"]])
                if structured_packet_text(packet) == packet["text"]:
                    focused["text_representation"] = "segments_and_mappings"
                else:
                    # Preserve unmatched text instead of assuming it is redundant.
                    focused["additional_text_ref"] = intern("additional_text", packet["text"])
                packets[alias] = focused
            summary["records"].append({**{k: deepcopy(v) for k, v in row.items()
                                         if k != "evidence_payload"}, "packet_ref": alias})
        result["retrieval_results"].append(summary)
    return result


def expand_packet(context, alias):
    """Exact inversion for fidelity audits; the LLM uses the compact view directly."""
    focused = deepcopy(context["packets"][alias]);pool = context["shared"]
    packet = pool[focused.pop("document_ref")]["value"].copy()
    for destination, field in [("segments", "segment_refs"),
                               ("source_references", "source_reference_refs"),
                               ("claim_source_mappings", "claim_source_mapping_refs")]:
        packet[destination] = [deepcopy(pool[ref]["value"]) for ref in focused.pop(field)]
    extra = focused.pop("additional_text_ref", None)
    focused.pop("text_representation", None)
    packet.update(focused)
    packet["text"] = pool[extra]["value"] if extra else structured_packet_text(packet)
    return deepcopy(packet)


def native_history(state):
    """Rebuild concise native action/result pairs from the current authoritative ledger."""
    history = []
    for action_id, entry in state["ledger"].items():
        action = entry["action"]
        expected = hashlib.sha256(json.dumps({"name": action["name"], "arguments": action["arguments"]},
            sort_keys=True, allow_nan=False).encode()).hexdigest()
        recovered = (entry['status']=='failed' and action['name']=='generate_package'
            and state.get('mode') in {'offline_package','live_package'} and state.get('retry_attempts')==1
            and state.get('package') is not None and len(state.get('failure_history',[]))==1
            and state['failure_history'][0].get('stage')=='draft_validation')
        if (entry["status"] != "completed" and not recovered) or entry["fingerprint"] != expected or action["id"] != action_id:
            raise ContextError("Uncompleted or mismatched action cannot become model history")
        if recovered:
            history.extend([{'role':'assistant','tool_calls':[{'id':action_id,'type':'function',
                'function':{'name':action['name'],'arguments':canonical(action['arguments'])}}]},
                {'role':'tool','tool_call_id':action_id,'content':canonical({'lower_trust_data_only':True,
                    'result':{'status':'rejected','diagnostic':state['failure_history'][0]}})}])
            continue
        history.append({"role": "assistant", "tool_calls": [{"id": action_id, "type": "function",
            "function": {"name": action["name"], "arguments": canonical(action["arguments"])}}]})
        name = action["name"]
        if name in {"read_pmm_brief", "check_launch", "search_product_evidence"}:
            reference = {"read_pmm_brief": "pmm", "check_launch": "launch",
                         "search_product_evidence": "retrieval_results"}[name]
            result = {"context_ref": "research_context." + reference,
                      "status": entry["result"].get("status", "computed")}
        else:
            result = deepcopy(entry["result"])
        history.append({"role": "tool", "tool_call_id": action_id,
                        "content": canonical({"lower_trust_data_only": True, "result": result})})
    return history
