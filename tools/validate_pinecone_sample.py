#!/usr/bin/env python3
"""Bounded three-record hosted evidence test. Default is offline preflight.

Never retries writes or reuses an existing index. No full-corpus upload or search.
"""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import prepare_embedding_projection as projection

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from launchlens.evidence_payload import encode_packet, storage_fields, metadata_bytes, restore_evidence

INDEX = "launchlens-e5-sample-v1"
NAMESPACE = "m15b4-three-record-fidelity"
VERSION = "2025-10"
UNITS = ("PROD-008", "PROD-011", "REQ-007")
OUTPUT = ROOT / "data/generated/m15b4-pinecone-sample"
EXPECTED_SHA = "ededee8bf3679af87f87b2f191632797f960b02c26ffcb1d68e9707550bf2093"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_sample():
    path = ROOT / "data/generated/m15b-embedding-projection/projection.jsonl"
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == EXPECTED_SHA, "Accepted projection hash mismatch")
    rows = [json.loads(line) for line in raw.splitlines()]
    profile = json.loads((ROOT / projection.PROFILE).read_text())
    projection.validate_projection(rows, projection.load_packets(ROOT), profile, projection.load_tokenizer(profile, ROOT))
    selected = []
    for unit in UNITS:
        matches = [row for row in rows if row["unit_id"] == unit]
        require(len(matches) == 1, "Sample ID missing or ambiguous")
        row = matches[0]
        require(metadata_bytes(storage_fields(row["evidence_payload"])) <= 40000, "Evidence too large; do not trim")
        selected.append(row)
    return selected


def verify_record(row, record):
    require(record["id"] == row["chunk_id"], "Fetched ID mismatch")
    fields = record["metadata"]
    require(fields == storage_fields(row["evidence_payload"]), "Hosted metadata mismatch; stop without dropping fields")
    packet = restore_evidence(fields, expected_chunk_id=row["chunk_id"], expected_authority=row["authority"])
    require(encode_packet(packet) == encode_packet(row["evidence_payload"]), "Hosted evidence byte mismatch")
    require(len(record["values"]) == 1024, "Fetched vector dimensions mismatch")
    return {"unit_id": row["unit_id"], "chunk_id": row["chunk_id"], "authority": row["authority"],
            "evidence_sha256": fields["evidence_sha256"], "evidence_utf8_bytes": len(fields["evidence_json"].encode()),
            "metadata_bytes": metadata_bytes(fields), "local_passage_tokens": row["local_token_fit"]["passage_tokens"],
            "exact_evidence_and_all_fields": True, "source_references": packet["source_references"],
            "qualifications_and_citations_unchanged": True}


def read_key():
    # Read only the required local variable; never evaluate shell syntax or log it.
    entries = []
    for line in (ROOT / ".env").read_text().splitlines():
        if re.match(r"^\s*(?:export\s+)?PINECONE_API_KEY\s*=", line):
            entries.append(line.split("=", 1)[1].strip().strip("\"'"))
    require(len(entries) == 1 and bool(entries[0]) and not any(c.isspace() for c in entries[0]), "Missing or ambiguous Pinecone key")
    require((ROOT / ".env").stat().st_mode & 0o077 == 0, "Environment file must be private")
    return entries[0]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def execute(rows):
    require(not OUTPUT.exists(), "Execution receipt already exists; do not rerun hosted writes")
    key = read_key()
    OUTPUT.mkdir(parents=True)
    receipt = {"status": "IN_PROGRESS", "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "api_version": VERSION, "index": INDEX, "namespace": NAMESPACE,
               "model": "multilingual-e5-large", "parameters": {"input_type": "passage", "truncate": "NONE"},
               "projection_sha256": EXPECTED_SHA, "events": []}
    def save():
        (OUTPUT / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    save()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                                         urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    allowed_hosts = {"api.pinecone.io"}
    def call(method, url, body=None):
        parsed = urllib.parse.urlparse(url)
        require(parsed.scheme == "https" and parsed.hostname in allowed_hosts, "Untrusted API destination")
        event = {"method": method, "path": parsed.path, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        receipt["events"].append(event)
        save()
        data = None if body is None else json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
        request = urllib.request.Request(url, data=data, method=method,
            headers={"Api-Key": key, "X-Pinecone-Api-Version": VERSION, "Content-Type": "application/json", "Accept": "application/json"})
        try:
            with opener.open(request, timeout=45) as response:
                event["http_status"] = response.status
                result = json.load(response)
        except urllib.error.HTTPError as error:
            event["http_status"] = error.code
            # Store bounded provider explanation, redact even accidental key echoes.
            event["provider_error"] = error.read(2000).decode(errors="replace").replace(key, "[REDACTED]")
            save()
            raise ValueError(f"Pinecone rejected {method} {parsed.path}: HTTP {error.code}; stop") from None
        save()
        return result
    try:
        existing = call("GET", "https://api.pinecone.io/indexes")
        require(not any(x["name"] == INDEX for x in existing["indexes"]), "Dedicated sample index already exists; refusing overwrite")
        require(not existing.get("pagination", {}).get("next"), "Unexpected index pagination; inspect before writes")
        index = call("POST", "https://api.pinecone.io/indexes", {
            "name": INDEX, "vector_type": "dense", "dimension": 1024, "metric": "cosine",
            "spec": {"serverless": {"cloud": "aws", "region": "us-east-1"}},
            "deletion_protection": "disabled", "tags": {"project": "launchlens", "purpose": "three-record-fidelity"}})
        receipt["created_index"] = index
        save()
        for attempt in range(20):
            if index.get("status", {}).get("ready"):
                break
            time.sleep(3)
            index = call("GET", f"https://api.pinecone.io/indexes/{INDEX}")
        require(index.get("status", {}).get("ready"), "Index not ready; stop")
        require(index["dimension"] == 1024 and index["metric"] == "cosine", "Index configuration mismatch")
        host = index["host"]
        require(re.fullmatch(r"[a-z0-9.-]+\.pinecone\.io", host) is not None, "Unexpected data-plane host")
        allowed_hosts.add(host)
        receipt["host"] = host
        response = call("POST", "https://api.pinecone.io/embed", {
            "model": "multilingual-e5-large", "parameters": receipt["parameters"],
            "inputs": [{"text": row["embedding_text"]} for row in rows]})
        require(response["model"] == "multilingual-e5-large" and len(response["data"]) == 3, "Embedding response mismatch")
        receipt["embedding_usage"] = response.get("usage", {})
        vectors = []
        for row, item in zip(rows, response["data"], strict=True):
            values = item["values"]
            require(len(values) == 1024 and all(isinstance(v, (float, int)) and math.isfinite(v) for v in values), "Invalid embedding vector")
            require(any(values), "Unexpected zero embedding")
            vectors.append({"id": row["chunk_id"], "values": values, "metadata": storage_fields(row["evidence_payload"])})
        upsert = call("POST", f"https://{host}/vectors/upsert", {"namespace": NAMESPACE, "vectors": vectors})
        require(upsert.get("upsertedCount") == 3, "Upsert count mismatch; stop")
        receipt["upsert"] = upsert
        query = urllib.parse.urlencode([("namespace", NAMESPACE)] + [("ids", row["chunk_id"]) for row in rows])
        for attempt in range(20):
            fetched = call("GET", f"https://{host}/vectors/fetch?{query}")
            records = fetched.get("vectors", {})
            require(set(records) <= {row["chunk_id"] for row in rows}, "Unexpected fetched ID")
            # Verify every present record immediately; only missing data permits polling.
            checks = [verify_record(row, records[row["chunk_id"]]) for row in rows if row["chunk_id"] in records]
            if len(checks) == 3:
                break
            time.sleep(3)
        require(len(checks) == 3, "Three records not visible before timeout; stop")
        require(fetched.get("namespace") == NAMESPACE, "Fetched namespace mismatch")
        (OUTPUT / "fetched.json").write_text(json.dumps(fetched, ensure_ascii=False, indent=2) + "\n")
        receipt["checks"] = checks
        receipt["fetch_usage"] = fetched.get("usage", {})
        receipt["status"] = "PASS"
        receipt["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
        print(json.dumps({k: receipt[k] for k in ["status", "index", "namespace", "embedding_usage", "checks"]}, ensure_ascii=False, indent=2))
    except Exception as error:
        receipt["status"] = "STOPPED"
        receipt["failure"] = str(error).replace(key, "[REDACTED]")
        save()
        raise ValueError(receipt["failure"]) from None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Create one dedicated index, embed/upload exactly three records, fetch and verify; requires owner authorization")
    args = parser.parse_args()
    sample = load_sample()
    if args.execute:
        execute(sample)
    else:
        print(json.dumps({"status": "OFFLINE_PREFLIGHT_PASS", "units": list(UNITS),
                          "metadata_bytes": {r["unit_id"]: r["runtime_metadata_bytes"] for r in sample}}, indent=2))
