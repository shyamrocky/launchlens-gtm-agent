#!/usr/bin/env python3
"""Fixed GTM semantic-search checks; read-only index access, one query-embedding batch.

No chat LLM, generated copy, reranking, record writes or adaptive query tuning.
Default preflight is offline; --execute requires scoped owner authorization.
"""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request

import validate_pinecone_corpus as corpus

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tools/gtm_retrieval_cases.json"
OUTPUT = ROOT / "data/generated/m15b4-semantic-retrieval"
require = corpus.require


def load_inputs():
    rows = corpus.load_records()
    spec = json.loads(CASES.read_text())
    require(len(spec["cases"]) == len({c["id"] for c in spec["cases"]}) == 8, "Expected eight fixed cases")
    require(spec["product_id"] == "CC-CHERRY-FLOAT" and spec["top_k"] == 5 and spec["acceptance_rank"] == 3, "Changed test policy")
    projection = corpus.sample.projection
    profile = projection.load_profile(ROOT)
    tokenizer = projection.load_tokenizer(profile, ROOT)
    for case in spec["cases"]:
        require(case["authority"] in {"public_product_facts", "synthetic_product_intent"}, "Unknown authority")
        require(case["expected_units"], "Missing expected evidence")
        units = {r["unit_id"] for r in rows if r["authority"] == case["authority"]}
        require(set(case["expected_units"]) <= units, "Expected unit absent from selected authority")
        require(not re.search(r"PROD-\d|REQ-\d", case["query"]), "Expected IDs must not leak into search text")
        count = len(tokenizer.encode("query: " + case["query"], add_special_tokens=True).ids)
        require(count <= 507, "Query exceeds accepted local token limit")
    return rows, spec


def evaluate(case, hits, acceptance_rank):
    ranks = {h["unit_id"]: h["rank"] for h in hits}
    expected_ranks = {unit: ranks.get(unit) for unit in case["expected_units"]}
    misses = [unit for unit, rank in expected_ranks.items() if rank is None or rank > acceptance_rank]
    return {"expected_ranks": expected_ranks, "misses_top_three": misses, "pass": not misses}


def execute(rows, spec):
    require(not OUTPUT.exists(), "Existing retrieval receipt; refusing unapproved rerun")
    key = corpus.sample.read_key()
    OUTPUT.mkdir(parents=True)
    by_id = {r["chunk_id"]: r for r in rows}
    receipt = {"status": "IN_PROGRESS", "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "index": corpus.INDEX, "namespace": corpus.NAMESPACE, "api_version": corpus.sample.VERSION,
        "model": "multilingual-e5-large", "parameters": {"input_type": "query", "truncate": "NONE"},
        "cases_sha256": hashlib.sha256(CASES.read_bytes()).hexdigest(), "fixed_cases": spec,
        "projection_sha256": corpus.sample.EXPECTED_SHA, "events": [], "results": []}

    def save():
        (OUTPUT / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), corpus.sample.NoRedirect(),
                                         urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    allowed_hosts = {"api.pinecone.io"}

    def call(method, url, body=None):
        parts = urllib.parse.urlparse(url)
        require(parts.scheme == "https" and parts.hostname in allowed_hosts, "Untrusted destination")
        if parts.hostname == "api.pinecone.io":
            require((method == "GET" and parts.path == f"/indexes/{corpus.INDEX}") or
                    (method == "POST" and parts.path == "/embed"), "Unapproved control/inference call")
        else:
            require((method == "GET" and parts.path == "/vectors/fetch") or
                    (method == "POST" and parts.path == "/query"), "Only index reads allowed")
            if body:
                require(body["namespace"] == corpus.NAMESPACE, "Wrong query namespace")
        event = {"method": method, "path": parts.path}
        receipt["events"].append(event)
        save()
        req = urllib.request.Request(url, method=method, data=None if body is None else corpus.encoded(body), headers={
            "Api-Key": key, "X-Pinecone-Api-Version": corpus.sample.VERSION,
            "Content-Type": "application/json", "Accept": "application/json"})
        try:
            with opener.open(req, timeout=45) as response:
                event["http_status"] = response.status
                data = json.load(response)
        except urllib.error.HTTPError as error:
            event["http_status"] = error.code
            event["provider_error"] = error.read(2000).decode(errors="replace").replace(key, "[REDACTED]")
            save()
            raise ValueError(f"Provider rejected {parts.path}: HTTP {error.code}; no retries") from None
        if "usage" in data:
            event["usage"] = data["usage"]
        save()
        return data

    def snapshot(host):
        query = urllib.parse.urlencode([("namespace", corpus.NAMESPACE)] + [("ids", i) for i in sorted(by_id)])
        response = call("GET", f"https://{host}/vectors/fetch?{query}")
        require(response.get("namespace") == corpus.NAMESPACE and set(response.get("vectors", {})) == set(by_id), "Incomplete/wrong corpus snapshot")
        for chunk_id, record in response["vectors"].items():
            corpus.sample.verify_record(by_id[chunk_id], record)
        return response["vectors"]

    save()
    try:
        description = call("GET", f"https://api.pinecone.io/indexes/{corpus.INDEX}")
        require(description["status"]["ready"] and description["dimension"] == 1024 and description["metric"] == "cosine", "Wrong index configuration")
        host = description["host"]
        require(re.fullmatch(r"[a-z0-9.-]+\.pinecone\.io", host) is not None, "Unexpected host")
        allowed_hosts.add(host)
        receipt["host"] = host
        before = snapshot(host)
        receipt["corpus_before_sha256"] = hashlib.sha256(corpus.encoded(before)).hexdigest()
        embedded = call("POST", "https://api.pinecone.io/embed", {
            "model": receipt["model"], "parameters": receipt["parameters"],
            "inputs": [{"text": c["query"]} for c in spec["cases"]]})
        require(embedded["model"] == receipt["model"] and len(embedded["data"]) == 8, "Query embedding mismatch")
        receipt["embedding_usage"] = embedded.get("usage", {})
        raw_responses = []
        for index, (case, vector) in enumerate(zip(spec["cases"], embedded["data"], strict=True)):
            require(vector.get("index", index) == index, "Embedding order mismatch")
            corpus.vector_hash(vector["values"])
            response = call("POST", f"https://{host}/query", {"namespace": corpus.NAMESPACE,
                "vector": vector["values"], "topK": spec["top_k"], "includeMetadata": True, "includeValues": False,
                "filter": {"product_id": {"$eq": spec["product_id"]}, "authority": {"$eq": case["authority"]}}})
            require(response.get("namespace") == corpus.NAMESPACE, "Wrong search namespace")
            matches = response.get("matches", [])
            require(len(matches) == 5 and len({h["id"] for h in matches}) == 5, "Expected five distinct hits")
            hits = []
            last_score = float("inf")
            for rank, hit in enumerate(matches, 1):
                require(hit["id"] in by_id, "Unexpected hit ID")
                packet = corpus.sample.restore_evidence(hit["metadata"], expected_chunk_id=hit["id"], expected_authority=case["authority"])
                require(packet["product_id"] == spec["product_id"], "Wrong product")
                require(corpus.sample.encode_packet(packet) == corpus.sample.encode_packet(by_id[hit["id"]]["evidence_payload"]), "Returned evidence changed")
                score = hit["score"]
                require(math.isfinite(score) and score <= last_score + 1e-6, "Invalid/reranked scores")
                last_score = score
                hits.append({"rank": rank, "chunk_id": hit["id"], "unit_id": packet["unit_id"], "score": score,
                    "authority": packet["authority"], "primary_text": packet["primary_text"],
                    "source_references": packet["source_references"], "evidence_sha256": hit["metadata"]["evidence_sha256"],
                    "evidence_verified": True})
            raw_responses.append({"case_id": case["id"], "response": response})
            receipt["results"].append({"case_id": case["id"], "query": case["query"], "purpose": case["purpose"],
                "authority": case["authority"], "hits": hits, **evaluate(case, hits, spec["acceptance_rank"])})
            save()
        after = snapshot(host)
        require(corpus.encoded(before) == corpus.encoded(after), "Corpus changed during read-only test")
        receipt["corpus_after_sha256"] = hashlib.sha256(corpus.encoded(after)).hexdigest()
        receipt["corpus_unchanged"] = True
        passed = sum(r["pass"] for r in receipt["results"])
        receipt.update(status="PASS" if passed == 8 else "RETRIEVAL_MISSES", passed=passed, total=8,
                       finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        (OUTPUT / "responses.jsonl").write_bytes(b"".join(corpus.encoded(r) + b"\n" for r in raw_responses))
        save()
        print(json.dumps({"status": receipt["status"], "passed": passed, "total": 8,
            "embedding_usage": receipt["embedding_usage"], "corpus_unchanged": True,
            "results": [{"case": r["case_id"], "pass": r["pass"], "expected_ranks": r["expected_ranks"],
                         "top_five": [{"unit": h["unit_id"], "score": round(h["score"], 4)} for h in r["hits"]]}
                        for r in receipt["results"]]}, indent=2))
    except Exception as error:
        receipt.update(status="STOPPED", failure=str(error).replace(key, "[REDACTED]"))
        save()
        raise ValueError(receipt["failure"]) from None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    rows, spec = load_inputs()
    if args.execute:
        execute(rows, spec)
    else:
        print(json.dumps({"status": "OFFLINE_PREFLIGHT_PASS", "cases": len(spec["cases"]),
            "top_k": spec["top_k"], "acceptance_rank": spec["acceptance_rank"],
            "cases_sha256": hashlib.sha256(CASES.read_bytes()).hexdigest()}, indent=2))
