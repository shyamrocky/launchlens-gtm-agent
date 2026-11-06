#!/usr/bin/env python3
"""One-hop exact-ID follow-up of links in the saved GTM-01 overview.

No semantic rerun, keyword search, embeddings, chat model or index writes.
Default preflight is offline; --execute performs two read-only HTTP calls.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request

import validate_pinecone_corpus as corpus

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data/generated/m15b4-semantic-retrieval/responses.jsonl"
BASELINE_SHA = "4a831b133ce262693989ae7fcf17de135ee6cf847bda43e81146b17c91ba1fbe"
OUTPUT = ROOT / "data/generated/m15b4-claim-links"
require = corpus.require


def linked_ids(parent):
    ids = parent["related_chunk_ids"]
    require(isinstance(ids, list) and 0 < len(ids) <= 5, "Missing/excessive links; no crawl")
    require(all(isinstance(i, str) and i for i in ids), "Invalid link")
    require(len(ids) == len(set(ids)) and parent["chunk_id"] not in ids, "Duplicate/self link")
    return list(ids)  # Existing IDs only; no target guesses or unit-ID lookup.


def load_inputs():
    raw = BASELINE.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == BASELINE_SHA, "Original search response changed")
    cases = [json.loads(line) for line in raw.splitlines()]
    matches = [c for c in cases if c["case_id"] == "GTM-01"]
    require(len(matches) == 1, "Missing/duplicate baseline case")
    hits = matches[0]["response"]["matches"]
    first = hits[0]
    parent = corpus.sample.restore_evidence(first["metadata"], expected_chunk_id=first["id"], expected_authority="public_product_facts")
    require(parent["product_id"] == "CC-CHERRY-FLOAT", "Wrong parent product")
    rows = {r["chunk_id"]: r for r in corpus.load_records()}
    require(corpus.sample.encode_packet(parent) == corpus.sample.encode_packet(rows[first["id"]]["evidence_payload"]), "Parent differs from accepted packet")
    return parent, linked_ids(parent), hits, rows


def verify_targets(parent, ids, fetched, rows):
    require(set(fetched) == {parent["chunk_id"], *ids}, "Missing or unintended fetched record")
    corpus.sample.verify_record(rows[parent["chunk_id"]], fetched[parent["chunk_id"]])
    require(fetched[parent["chunk_id"]]["metadata"]["evidence_json"] == corpus.sample.encode_packet(parent), "Hosted parent changed")
    checks = []
    for chunk_id in ids:
        checked = corpus.sample.verify_record(rows[chunk_id], fetched[chunk_id])
        packet = corpus.sample.restore_evidence(fetched[chunk_id]["metadata"], expected_chunk_id=chunk_id, expected_authority=parent["authority"])
        for field in ("product_id", "document_id", "document_version", "source_sha256"):
            require(packet[field] == parent[field], "Linked source/product scope mismatch")
        require(packet["chunk_kind"] == "product_claim", "Linked record is not a product claim")
        checked["primary_text"] = packet["primary_text"]
        checked["claim_support_sources"] = sorted({m["source_id"] for m in packet["claim_source_mappings"]})
        checks.append(checked)
    require({c["unit_id"] for c in checks} == set(parent["related_claim_ids"]), "Claim links/labels disagree")
    return checks


def execute(parent, ids, hits, rows):
    require(not OUTPUT.exists(), "Existing receipt; no unapproved rerun")
    key = corpus.sample.read_key()
    OUTPUT.mkdir(parents=True)
    receipt = {"status": "IN_PROGRESS", "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "index": corpus.INDEX, "namespace": corpus.NAMESPACE, "api_version": corpus.sample.VERSION,
        "baseline_sha256": BASELINE_SHA, "parent_id": parent["chunk_id"], "links_from_parent": ids,
        "original_top_five_ids": [h["id"] for h in hits], "events": []}

    def save():
        (OUTPUT / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), corpus.sample.NoRedirect(),
                                         urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    allowed = {"api.pinecone.io"}

    def get(url):
        parts = urllib.parse.urlparse(url)
        require(parts.scheme == "https" and parts.hostname in allowed, "Untrusted destination")
        require((parts.hostname == "api.pinecone.io" and parts.path == f"/indexes/{corpus.INDEX}") or
                (parts.hostname != "api.pinecone.io" and parts.path == "/vectors/fetch"), "Only describe/fetch reads allowed")
        require(len(receipt["events"]) < 2, "Read-call bound exceeded")
        event = {"method": "GET", "path": parts.path}
        receipt["events"].append(event)
        save()
        request = urllib.request.Request(url, headers={"Api-Key": key, "X-Pinecone-Api-Version": corpus.sample.VERSION, "Accept": "application/json"})
        try:
            with opener.open(request, timeout=45) as response:
                event["http_status"] = response.status
                result = json.load(response)
        except urllib.error.HTTPError as error:
            event["http_status"] = error.code
            save()
            raise ValueError(f"Read rejected: HTTP {error.code}; no retries") from None
        event["usage"] = result.get("usage", {})
        save()
        return result

    save()
    try:
        index = get(f"https://api.pinecone.io/indexes/{corpus.INDEX}")
        require(index["status"]["ready"] and index["dimension"] == 1024 and index["metric"] == "cosine", "Wrong index configuration")
        host = index["host"]
        require(re.fullmatch(r"[a-z0-9.-]+\.pinecone\.io", host) is not None, "Unexpected data host")
        allowed.add(host)
        query = urllib.parse.urlencode([("namespace", corpus.NAMESPACE)] + [("ids", i) for i in [parent["chunk_id"], *ids]])
        response = get(f"https://{host}/vectors/fetch?{query}")
        require(response.get("namespace") == corpus.NAMESPACE, "Wrong namespace")
        checks = verify_targets(parent, ids, response.get("vectors", {}), rows)
        new_ids = sorted(set(ids) - {h["id"] for h in hits})
        receipt["checks"] = checks
        receipt["new_claim_ids"] = [rows[i]["unit_id"] for i in new_ids]
        receipt["semantic_ranks_changed"] = False
        receipt["keyword_search_tested"] = False
        receipt["embedding_or_chat_calls"] = 0
        receipt.update(status="PASS", finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        (OUTPUT / "fetched.json").write_text(json.dumps(response, ensure_ascii=False, indent=2) + "\n")
        save()
        print(json.dumps({"status": "PASS", "links_read_from_parent": len(ids),
            "fetched_records_including_parent": len(response["vectors"]), "new_claim_ids": receipt["new_claim_ids"],
            "verified_claims": [{"unit_id": c["unit_id"], "sources": c["claim_support_sources"]} for c in checks],
            "semantic_ranks_changed": False, "keyword_search_tested": False}, indent=2))
    except Exception as error:
        receipt.update(status="STOPPED", failure=str(error).replace(key, "[REDACTED]"))
        save()
        raise ValueError(receipt["failure"]) from None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    parent, ids, hits, rows = load_inputs()
    if args.execute:
        execute(parent, ids, hits, rows)
    else:
        print(json.dumps({"status": "OFFLINE_PREFLIGHT_PASS", "parent_unit": parent["unit_id"],
                          "linked_units_from_packet": parent["related_claim_ids"], "one_hop_only": True}, indent=2))
