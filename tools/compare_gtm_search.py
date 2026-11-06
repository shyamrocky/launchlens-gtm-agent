#!/usr/bin/env python3
"""One fixed semantic/BM25/RRF comparison, with read-only Pinecone access.

Keyword scoring and fusion run locally over the same focused text/candidates.
No packages, sparse index, new services, corpus writes or parameter tuning.
"""
import argparse
from collections import Counter
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

import validate_gtm_retrieval as baseline

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "tools/gtm_search_comparison_profile.json"
OUTPUT = ROOT / "data/generated/m15b4-search-comparison"
require = baseline.require


def load_inputs():
    rows, cases = baseline.load_inputs()
    profile = json.loads(PROFILE.read_text())
    require(hashlib.sha256(baseline.CASES.read_bytes()).hexdigest() == profile["query_source_sha256"], "Fixed queries changed")
    require(profile["text_field"] == "embedding_text", "Unexpected search field")
    require(profile["keyword"]["k1"] == 1.2 and profile["keyword"]["b"] == 0.75, "Changed BM25 settings")
    require(profile["hybrid"]["rank_constant"] == 60 and profile["evaluation"]["acceptance_rank"] == 3, "Changed fusion/evaluation")
    return rows, cases, profile


def bm25_rank(rows, query, profile):
    cfg = profile["keyword"]
    tokenize = lambda text: re.findall(cfg["token_pattern"], text.lower())
    counters = {r["chunk_id"]: Counter(tokenize(r["embedding_text"])) for r in rows}
    lengths = {i: sum(c.values()) for i, c in counters.items()}
    n = len(rows)
    require(n > 0 and all(lengths.values()), "Empty candidate text")
    average = sum(lengths.values()) / n
    dfs = Counter(term for counter in counters.values() for term in counter)
    terms = set(tokenize(query))
    scored = []
    for row in rows:
        i = row["chunk_id"]
        score = 0.0
        for term in sorted(terms):
            tf = counters[i][term]
            if not tf:
                continue
            idf = math.log1p((n - dfs[term] + 0.5) / (dfs[term] + 0.5))
            denominator = tf + cfg["k1"] * (1 - cfg["b"] + cfg["b"] * lengths[i] / average)
            score += idf * tf * (cfg["k1"] + 1) / denominator
        if score > 0:
            scored.append({"chunk_id": i, "unit_id": row["unit_id"], "score": score})
    return [{**hit, "rank": rank} for rank, hit in enumerate(sorted(scored, key=lambda h: (-h["score"], h["chunk_id"])), 1)]


def rrf_rank(semantic, keyword, profile, by_id):
    scores = Counter()
    ranks = {}
    for method, hits in (("semantic", semantic), ("keyword", keyword)):
        weight = profile["hybrid"][method + "_weight"]
        for hit in hits:
            i = hit["chunk_id"]
            scores[i] += weight / (profile["hybrid"]["rank_constant"] + hit["rank"])
            ranks.setdefault(i, {})[method] = hit["rank"]
    ordered = sorted(scores, key=lambda i: (-scores[i], i))
    return [{"rank": rank, "chunk_id": i, "unit_id": by_id[i]["unit_id"], "score": scores[i],
             "component_ranks": ranks[i]} for rank, i in enumerate(ordered, 1)]


def execute(rows, spec, profile):
    require(not OUTPUT.exists(), "Existing comparison receipt; no unapproved rerun")
    key = baseline.corpus.sample.read_key()
    OUTPUT.mkdir(parents=True)
    by_id = {r["chunk_id"]: r for r in rows}
    old_path = ROOT / "data/generated/m15b4-semantic-retrieval/receipt.json"
    old_raw = old_path.read_bytes()
    require(hashlib.sha256(old_raw).hexdigest() == "eb2ba542810496c1eab40da76c3d55eba03c7d905dd16b30e1ee6ed645fb50e3", "Historical baseline changed")
    old = json.loads(old_raw)
    receipt = {"status": "IN_PROGRESS", "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "index": baseline.corpus.INDEX, "namespace": baseline.corpus.NAMESPACE,
        "profile_sha256": hashlib.sha256(PROFILE.read_bytes()).hexdigest(), "fixed_profile": profile,
        "queries_sha256": profile["query_source_sha256"], "events": [], "results": []}

    def save():
        (OUTPUT / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), baseline.corpus.sample.NoRedirect(),
                                         urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    allowed_hosts = {"api.pinecone.io"}

    def call(method, url, body=None):
        parts = urllib.parse.urlparse(url)
        require(parts.scheme == "https" and parts.hostname in allowed_hosts, "Untrusted destination")
        require(len(receipt["events"]) < 12, "Request bound exceeded")
        if parts.hostname == "api.pinecone.io":
            require((method == "GET" and parts.path == f"/indexes/{baseline.corpus.INDEX}") or
                    (method == "POST" and parts.path == "/embed"), "Unapproved control/model operation")
        else:
            require((method == "GET" and parts.path == "/vectors/fetch") or
                    (method == "POST" and parts.path == "/query" and body["namespace"] == baseline.corpus.NAMESPACE), "Only validation-corpus reads allowed")
        event = {"method": method, "path": parts.path}
        receipt["events"].append(event)
        save()
        request = urllib.request.Request(url, method=method, data=None if body is None else baseline.corpus.encoded(body), headers={
            "Api-Key": key, "X-Pinecone-Api-Version": baseline.corpus.sample.VERSION,
            "Accept": "application/json", "Content-Type": "application/json"})
        try:
            with opener.open(request, timeout=45) as response:
                event["http_status"] = response.status
                result = json.load(response)
        except urllib.error.HTTPError as error:
            event["http_status"] = error.code
            event["error"] = error.read(2000).decode(errors="replace").replace(key, "[REDACTED]")
            save()
            raise ValueError(f"Provider HTTP {error.code}; no retries") from None
        event["usage"] = result.get("usage", {})
        save()
        return result

    def snapshot(host):
        params = [("namespace", baseline.corpus.NAMESPACE)] + [("ids", i) for i in sorted(by_id)]
        response = call("GET", f"https://{host}/vectors/fetch?" + urllib.parse.urlencode(params))
        require(response.get("namespace") == baseline.corpus.NAMESPACE and set(response.get("vectors", {})) == set(by_id), "Incomplete snapshot")
        for i, record in response["vectors"].items():
            baseline.corpus.sample.verify_record(by_id[i], record)
        return response["vectors"]

    save()
    try:
        desc = call("GET", f"https://api.pinecone.io/indexes/{baseline.corpus.INDEX}")
        require(desc["status"]["ready"] and desc["dimension"] == 1024 and desc["metric"] == "cosine", "Wrong index")
        host = desc["host"]
        require(re.fullmatch(r"[a-z0-9.-]+\.pinecone\.io", host) is not None, "Unexpected host")
        allowed_hosts.add(host)
        before = snapshot(host)
        receipt["corpus_before_sha256"] = hashlib.sha256(baseline.corpus.encoded(before)).hexdigest()
        embedded = call("POST", "https://api.pinecone.io/embed", {"model": profile["semantic"]["model"],
            "parameters": {"input_type": "query", "truncate": "NONE"}, "inputs": [{"text": c["query"]} for c in spec["cases"]]})
        require(embedded["model"] == profile["semantic"]["model"] and len(embedded["data"]) == 8, "Embedding mismatch")
        receipt["embedding_usage"] = embedded.get("usage", {})
        responses = []
        for index, (case, vector) in enumerate(zip(spec["cases"], embedded["data"], strict=True)):
            require(vector.get("index", index) == index, "Embedding order mismatch")
            baseline.corpus.vector_hash(vector["values"])
            eligible = [r for r in rows if r["authority"] == case["authority"] and r["evidence_payload"]["product_id"] == spec["product_id"]]
            require(0 < len(eligible) <= 30, "Unexpected candidate scope")
            response = call("POST", f"https://{host}/query", {"namespace": baseline.corpus.NAMESPACE,
                "vector": vector["values"], "topK": len(eligible), "includeMetadata": False, "includeValues": False,
                "filter": {"product_id": {"$eq": spec["product_id"]}, "authority": {"$eq": case["authority"]}}})
            matches = response.get("matches", [])
            require(response.get("namespace") == baseline.corpus.NAMESPACE, "Wrong result namespace")
            require(len(matches) == len({m["id"] for m in matches}) == len(eligible) and
                    {m["id"] for m in matches} == {r["chunk_id"] for r in eligible}, "Wrong filtered candidates")
            semantic = []
            last_score = float("inf")
            for rank, hit in enumerate(matches, 1):
                require(math.isfinite(hit["score"]) and hit["score"] <= last_score + 1e-6, "Invalid score order")
                last_score = hit["score"]
                semantic.append({"rank": rank, "chunk_id": hit["id"], "unit_id": by_id[hit["id"]]["unit_id"], "score": hit["score"]})
            keyword = bm25_rank(eligible, case["query"], profile)
            hybrid = rrf_rank(semantic, keyword, profile, by_id)
            methods = {name: {"ranking": hits, **baseline.evaluate(case, hits, 3)}
                       for name, hits in (("semantic", semantic), ("keyword", keyword), ("hybrid", hybrid))}
            old_case = next(c for c in old["results"] if c["case_id"] == case["id"])
            same = [h["chunk_id"] for h in semantic[:5]] == [h["chunk_id"] for h in old_case["hits"]]
            receipt["results"].append({"case_id": case["id"], "query": case["query"], "purpose": case["purpose"],
                "expected_units": case["expected_units"], "authority": case["authority"], "candidate_count": len(eligible),
                "semantic_top_five_matches_original": same, "methods": methods})
            responses.append({"case_id": case["id"], "response": response})
            save()
        after = snapshot(host)
        require(baseline.corpus.encoded(after) == baseline.corpus.encoded(before), "Corpus changed")
        receipt["corpus_after_sha256"] = hashlib.sha256(baseline.corpus.encoded(after)).hexdigest()
        summary = {}
        semantic_pass = {r["case_id"] for r in receipt["results"] if r["methods"]["semantic"]["pass"]}
        for method in ("semantic", "keyword", "hybrid"):
            passed = {r["case_id"] for r in receipt["results"] if r["methods"][method]["pass"]}
            summary[method] = {"passed": len(passed), "total": 8, "improvements_vs_semantic": sorted(passed - semantic_pass),
                               "regressions_vs_semantic": sorted(semantic_pass - passed)}
        receipt["summary"] = summary
        receipt["hybrid_meets_predeclared_adoption_rule"] = summary["hybrid"]["passed"] > summary["semantic"]["passed"] and not summary["hybrid"]["regressions_vs_semantic"]
        receipt.update(status="COMPLETED", corpus_unchanged=True, finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        (OUTPUT / "responses.jsonl").write_bytes(b"".join(baseline.corpus.encoded(r) + b"\n" for r in responses))
        save()
        print(json.dumps({"status": "COMPLETED", "summary": summary,
            "hybrid_meets_predeclared_adoption_rule": receipt["hybrid_meets_predeclared_adoption_rule"],
            "embedding_usage": receipt["embedding_usage"], "corpus_unchanged": True,
            "cases": [{"case": r["case_id"], "original_semantic_top5_same": r["semantic_top_five_matches_original"],
                "methods": {m: {"pass": x["pass"], "expected_ranks": x["expected_ranks"],
                    "top3": [h["unit_id"] for h in x["ranking"][:3]]} for m,x in r["methods"].items()}}
                for r in receipt["results"]]}, indent=2))
    except Exception as error:
        receipt.update(status="STOPPED", failure=str(error).replace(key, "[REDACTED]"))
        save()
        raise ValueError(receipt["failure"]) from None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    rows, spec, profile = load_inputs()
    if args.execute:
        execute(rows, spec, profile)
    else:
        print(json.dumps({"status": "OFFLINE_PREFLIGHT_PASS", "cases": len(spec["cases"]),
                          "profile_sha256": hashlib.sha256(PROFILE.read_bytes()).hexdigest()}, indent=2))
