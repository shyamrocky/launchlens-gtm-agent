#!/usr/bin/env python3
"""Populate exactly 45 approved records in an isolated validation namespace.

Default is offline validation. --execute embeds/upserts once, then verifies IDs,
evidence and stored vectors. No semantic queries, chat models or agent calls.
"""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import ssl
import struct
import time
import urllib.error
import urllib.parse
import urllib.request

import validate_pinecone_sample as sample

ROOT = Path(__file__).resolve().parents[1]
INDEX = sample.INDEX
NAMESPACE = "m15b4-corpus-validation-v1"
OUTPUT = ROOT / "data/generated/m15b4-full-corpus"
require = sample.require


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def load_records():
    sample.load_sample()  # Reuses full accepted projection/upstream validation.
    path = ROOT / "data/generated/m15b-embedding-projection/projection.jsonl"
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == sample.EXPECTED_SHA, "Projection changed")
    rows = [json.loads(line) for line in raw.splitlines()]
    require(len(rows) == len({r["chunk_id"] for r in rows}) == 45, "Expected 45 unique records")
    return rows


def vector_hash(values):
    require(len(values) == 1024 and all(isinstance(v, (int, float)) and math.isfinite(v) for v in values), "Invalid vector")
    require(any(values), "Unexpected zero vector")
    return hashlib.sha256(struct.pack("<1024f", *values)).hexdigest()


def execute(rows):
    require(not OUTPUT.exists(), "Existing execution output; refusing automatic hosted rerun")
    key = sample.read_key()
    OUTPUT.mkdir(parents=True)
    receipt = {"status": "IN_PROGRESS", "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "index": INDEX, "namespace": NAMESPACE, "api_version": sample.VERSION,
               "projection_sha256": sample.EXPECTED_SHA, "model": "multilingual-e5-large",
               "parameters": {"input_type": "passage", "truncate": "NONE"}, "events": []}

    def save():
        (OUTPUT / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), sample.NoRedirect(),
                                         urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    allowed_hosts = {"api.pinecone.io"}

    def call(method, url, body=None):
        parts = urllib.parse.urlparse(url)
        require(parts.scheme == "https" and parts.hostname in allowed_hosts, "Untrusted API destination")
        data = None if body is None else encoded(body)
        if parts.path == "/vectors/upsert":
            require(method == "POST" and body["namespace"] == NAMESPACE and len(body["vectors"]) == 45, "Write outside authorized scope")
            require(len(data) < 2_000_000, "Upsert exceeds conservative request budget; stop without trimming")
            receipt["upsert_request_bytes"] = len(data)
        event = {"method": method, "path": parts.path}
        if parts.hostname != "api.pinecone.io":
            event["namespace"] = body.get("namespace") if body else urllib.parse.parse_qs(parts.query).get("namespace", [None])[0]
        receipt["events"].append(event)
        save()
        req = urllib.request.Request(url, method=method, data=data, headers={
            "Api-Key": key, "X-Pinecone-Api-Version": sample.VERSION,
            "Content-Type": "application/json", "Accept": "application/json"})
        try:
            with opener.open(req, timeout=45) as response:
                event["http_status"] = response.status
                result = json.load(response)
        except urllib.error.HTTPError as error:
            event["http_status"] = error.code
            event["provider_error"] = error.read(2000).decode(errors="replace").replace(key, "[REDACTED]")
            save()
            raise ValueError(f"Pinecone rejected {method} {parts.path}: HTTP {error.code}; no retries") from None
        if "usage" in result:
            event["usage"] = result["usage"]
        save()
        return result

    def list_ids(host, namespace):
        ids, token, seen_tokens = [], None, set()
        for _ in range(10):
            params = {"namespace": namespace, "limit": 20}
            if token:
                params["paginationToken"] = token
            result = call("GET", f"https://{host}/vectors/list?" + urllib.parse.urlencode(params))
            require(result.get("namespace") == namespace, "Wrong namespace in listing")
            ids.extend(v["id"] for v in result.get("vectors", []))
            require(len(ids) == len(set(ids)), "Duplicate listed ID")
            token = result.get("pagination", {}).get("next")
            if not token:
                return set(ids)
            require(token not in seen_tokens, "Repeated pagination token")
            seen_tokens.add(token)
        raise ValueError("Listing exceeded bounded pagination")

    def fetch(host, namespace, ids):
        params = [("namespace", namespace)] + [("ids", i) for i in sorted(ids)]
        result = call("GET", f"https://{host}/vectors/fetch?" + urllib.parse.urlencode(params))
        require(result.get("namespace") == namespace, "Wrong fetched namespace")
        return result

    save()
    try:
        description = call("GET", f"https://api.pinecone.io/indexes/{INDEX}")
        require(description["name"] == INDEX and description["dimension"] == 1024 and description["metric"] == "cosine", "Existing index configuration mismatch")
        require(description["status"]["ready"], "Existing index not ready")
        host = description["host"]
        require(re.fullmatch(r"[a-z0-9.-]+\.pinecone\.io", host) is not None, "Unexpected index host")
        allowed_hosts.add(host)
        receipt["host"] = host
        require(not list_ids(host, NAMESPACE), "Validation namespace not empty; refusing overwrite")
        old_rows = [r for r in rows if r["unit_id"] in sample.UNITS]
        old_ids = {r["chunk_id"] for r in old_rows}
        require(list_ids(host, sample.NAMESPACE) == old_ids, "Original sample ID set changed")
        old = fetch(host, sample.NAMESPACE, old_ids)["vectors"]
        require(set(old) == old_ids, "Original sample incomplete")
        for row in old_rows:
            sample.verify_record(row, old[row["chunk_id"]])
        receipt["sample_before_sha256"] = hashlib.sha256(encoded(old)).hexdigest()
        response = call("POST", "https://api.pinecone.io/embed", {
            "model": receipt["model"], "parameters": receipt["parameters"],
            "inputs": [{"text": r["embedding_text"]} for r in rows]})
        require(response["model"] == receipt["model"] and len(response["data"]) == 45, "Embedding response mismatch")
        receipt["embedding_usage"] = response.get("usage", {})
        vectors, hashes = [], {}
        for i, (row, item) in enumerate(zip(rows, response["data"], strict=True)):
            require(item.get("index", i) == i, "Embedding order mismatch")
            hashes[row["chunk_id"]] = vector_hash(item["values"])
            vectors.append({"id": row["chunk_id"], "values": item["values"], "metadata": sample.storage_fields(row["evidence_payload"])})
        result = call("POST", f"https://{host}/vectors/upsert", {"namespace": NAMESPACE, "vectors": vectors})
        require(result.get("upsertedCount") == 45, "Unexpected upsert count; stop")
        receipt["upserted_count"] = 45
        expected = {r["chunk_id"] for r in rows}
        for attempt in range(15):
            fetched = fetch(host, NAMESPACE, expected)
            records = fetched.get("vectors", {})
            require(set(records) <= expected, "Unexpected fetched ID")
            checks = []
            for row in rows:
                if row["chunk_id"] not in records:
                    continue
                record = records[row["chunk_id"]]
                checked = sample.verify_record(row, record)
                require(vector_hash(record["values"]) == hashes[row["chunk_id"]], "Stored vector differs at float32 precision")
                checked["vector_float32_sha256"] = hashes[row["chunk_id"]]
                checks.append(checked)
            if len(checks) == 45:
                break
            time.sleep(2)  # Read-only visibility polling; never retry a write.
        require(len(checks) == 45, "Missing records after visibility wait")
        for attempt in range(15):
            listed = list_ids(host, NAMESPACE)
            require(listed <= expected, "Unintended record found in validation namespace")
            if listed == expected:
                break
            time.sleep(2)
        require(listed == expected, "Listed corpus incomplete")
        require(list_ids(host, sample.NAMESPACE) == old_ids, "Original sample ID set changed during test")
        after = fetch(host, sample.NAMESPACE, old_ids)["vectors"]
        require(encoded(after) == encoded(old), "Original sample records changed during test")
        receipt["sample_after_sha256"] = hashlib.sha256(encoded(after)).hexdigest()
        receipt["checks"] = checks
        receipt["listed_ids"] = sorted(listed)
        receipt["sample_unchanged"] = True
        receipt["fetch_usage"] = fetched.get("usage", {})
        (OUTPUT / "fetched.json").write_text(json.dumps(fetched, ensure_ascii=False, indent=2) + "\n")
        receipt.update(status="PASS", finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        save()
        print(json.dumps({k: receipt[k] for k in ["status", "index", "namespace", "upserted_count", "embedding_usage", "upsert_request_bytes", "sample_unchanged"]}, indent=2))
    except Exception as error:
        receipt.update(status="STOPPED", failure=str(error).replace(key, "[REDACTED]"))
        save()
        raise ValueError(receipt["failure"]) from None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    rows = load_records()
    if args.execute:
        execute(rows)
    else:
        print(json.dumps({"status": "OFFLINE_PREFLIGHT_PASS", "records": len(rows),
            "local_passage_tokens": sum(r["local_token_fit"]["passage_tokens"] for r in rows),
            "largest_metadata_bytes": max(r["runtime_metadata_bytes"] for r in rows),
            "index": INDEX, "namespace": NAMESPACE}, indent=2))
