#!/usr/bin/env python3
"""Project existing evidence into focused text and lossless payload; no inference."""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import tempfile
import urllib.request
from pathlib import Path

import tokenizers
from tokenizers import Tokenizer

import prepare_chunks as chunks

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from launchlens.evidence_payload import encode_packet, storage_fields, metadata_bytes, restore_evidence

PROFILE = Path("tools/embedding_preparation/profile.json")
OUTPUT = Path("data/generated/m15b-embedding-projection")
CHUNKS_SHA = "89d02d88a75864eec963bc0662fcf4dcde799882c8c1f334343d081815bbcbb0"
CHUNK_MANIFEST_SHA = "91c844f3c125811cc0ef27c61074a37339f12d3f05b4433a5490206e4713cfed"


def load_profile(root: Path = ROOT) -> dict:
    profile = json.loads((root / PROFILE).read_text())
    chunks.prep.require(profile["model"] == "multilingual-e5-large", "Unexpected model profile")
    chunks.prep.require(profile["provider_input_limit"] == 507, "Review a changed provider limit")
    chunks.prep.require(tokenizers.__version__ == profile["tokenizer"]["library_version"], "Use the isolated locked tokenizer environment")
    return profile


def provision(root: Path = ROOT) -> None:
    """Explicit public tokenizer-only download; no .env, credentials or weights."""
    profile = load_profile(root)
    target = root / profile["tokenizer"]["cache_path"]
    chunks.prep.require(not target.is_symlink(), "Unsafe tokenizer cache")
    target.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    files = profile["tokenizer"]["files"]
    chunks.prep.require(set(files) == {"tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "README.md"}, "Only reviewed tokenizer files may be downloaded")
    for name, spec in files.items():
        path = target / name
        if path.is_file() and not path.is_symlink() and chunks.prep.sha256(path.read_bytes()) == spec["sha256"]:
            continue
        prefix = f"https://huggingface.co/{profile['tokenizer']['repo']}/resolve/{profile['tokenizer']['revision']}/"
        chunks.prep.require(spec["url"] == prefix + name, "Unexpected tokenizer source")
        with opener.open(urllib.request.Request(spec["url"], headers={"User-Agent": "LaunchLens-tokenizer-only"}), timeout=40) as response:
            data = response.read(30_000_001)
        chunks.prep.require(len(data) == spec["bytes"] and chunks.prep.sha256(data) == spec["sha256"], "Tokenizer download hash/size mismatch")
        chunks.prep.require(not path.is_symlink(), "Unsafe tokenizer output")
        with tempfile.NamedTemporaryFile(dir=target, delete=False) as temporary:
            temporary.write(data)
            temp_path = Path(temporary.name)
        temp_path.replace(path)


def load_tokenizer(profile: dict, root: Path = ROOT) -> Tokenizer:
    folder = root / profile["tokenizer"]["cache_path"]
    for name, spec in profile["tokenizer"]["files"].items():
        chunks.prep.checked_bytes(root, (folder / name).relative_to(root).as_posix(), spec["sha256"])
    tokenizer = Tokenizer.from_file(str(folder / "tokenizer.json"))
    tokenizer.no_truncation()
    tokenizer.no_padding()
    chunks.prep.require(tokenizer.num_special_tokens_to_add(False) == 2, "Review changed tokenizer framing")
    return tokenizer


def focused_text(packet: dict) -> str:
    """Remove register syntax only; preserve all words and inline qualifiers."""
    text = packet["primary_text"]
    if packet["chunk_kind"] == "product_claim":
        pattern = r"^PROD-\d{3} \| (?:SOURCE_SUPPORTED|QUALIFIED_SOURCE_STATEMENT) \| S[1-5](?:, S[1-5])*\. "
        text, count = re.subn(pattern, "", text, count=1)
        chunks.prep.require(count == 1, "Unrecognized claim register prefix")
    elif packet["chunk_kind"] == "requirement":
        text = re.sub(r"^E\. Proposed product requirements \((?:synthetic intent|continued)\)\n\n", "", text)
        text, count = re.subn(r"^REQ-\d{3} - ", "", text, count=1)
        chunks.prep.require(count == 1, "Unrecognized requirement prefix")
    text = " ".join(text.split())
    role = "Public product facts" if packet["authority"] == "public_product_facts" else "Synthetic product intent"
    return f"Product: Coca-Cola Cherry Float\nDocument role: {role}\n{text}"


def passage_tokens(tokenizer: Tokenizer, text: str) -> int:
    return len(tokenizer.encode("passage: " + text, add_special_tokens=True).ids)


def project(packet: dict, profile: dict, tokenizer: Tokenizer) -> dict:
    text = focused_text(packet)
    count = passage_tokens(tokenizer, text)
    chunks.prep.require(count <= profile["provider_input_limit"], f"Projection exceeds token budget: {packet['unit_id']}")
    fields = storage_fields(packet)
    size = metadata_bytes(fields)
    chunks.prep.require(size <= profile["runtime_evidence"]["metadata_byte_ceiling"], "Full evidence exceeds reviewed storage budget; do not truncate")
    restored = restore_evidence(json.loads(json.dumps(fields)), expected_chunk_id=packet["chunk_id"], expected_authority=packet["authority"])
    chunks.prep.require(encode_packet(restored) == encode_packet(packet), "Evidence round trip changed the original packet")
    return {"profile_version": profile["profile_version"], "projection_status": "PREPARED_PENDING_OWNER_ACCEPTANCE",
            "chunk_id": packet["chunk_id"], "unit_id": packet["unit_id"], "document_id": packet["document_id"],
            "authority": packet["authority"], "embedding_model": profile["model"], "embedding_text": text,
            "evidence_payload": packet, "evidence_sha256": fields["evidence_sha256"],
            "local_token_fit": {"passage_tokens": count, "before_packet_tokens": passage_tokens(tokenizer, packet["text"]),
                                "limit": profile["provider_input_limit"], "truncated": False,
                                "framing": "passage prefix plus special tokens; hosted parity unverified"},
            "runtime_metadata_bytes": size}


def load_packets(root: Path = ROOT) -> list[dict]:
    raw = chunks.prep.checked_bytes(root, (chunks.OUTPUT / "chunks.jsonl").as_posix(), CHUNKS_SHA)
    manifest_raw = chunks.prep.checked_bytes(root, (chunks.OUTPUT / "manifest.json").as_posix(), CHUNK_MANIFEST_SHA)
    manifest = json.loads(manifest_raw)
    for path, expected in manifest["input_sha256"].items():
        chunks.prep.checked_bytes(root, path, expected)
    packets = [json.loads(line) for line in raw.splitlines()]
    chunks.validate_chunks(packets, chunks.load_inputs(root))
    return packets


def validate_projection(rows: list[dict], packets: list[dict], profile: dict, tokenizer: Tokenizer) -> None:
    chunks.prep.require(len(rows) == len(packets) == 45, "Expected all 45 unchanged chunk IDs")
    for row, packet in zip(rows, packets, strict=True):
        chunks.prep.require(row == project(packet, profile, tokenizer), f"Projection/evidence mismatch: {packet['unit_id']}")


def audit_data(rows: list[dict]) -> list[dict]:
    result = []
    for row in rows:
        p = row["evidence_payload"]
        result.append({"unit": row["unit_id"], "document": "Product Brief" if p["authority"] == "public_product_facts" else "Synthetic PRD",
                       "authority": p["authority"], "before": p["text"], "after": row["embedding_text"],
                       "before_tokens": row["local_token_fit"]["before_packet_tokens"], "after_tokens": row["local_token_fit"]["passage_tokens"],
                       "sources": p["source_references"], "mappings": p["claim_source_mappings"], "links": p["links"],
                       "pages": p["page_numbers"], "primary_pages": sorted({s["page_number"] for s in p["segments"] if s["role"] == "primary"}),
                       "chunk_id": p["chunk_id"], "evidence_digest": row["evidence_sha256"], "metadata_bytes": row["runtime_metadata_bytes"],
                       "source_status": p["source_acceptance"]["status"], "chunk_status": p["chunk_status"]})
    return result


def render_audit(rows: list[dict], root: Path = ROOT) -> bytes:
    template = (root / "tools/embedding_preparation/audit_template.html").read_text()
    data = json.dumps(audit_data(rows), ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")
    chunks.prep.require(template.count("__AUDIT_DATA__") == 1, "Audit template placeholder mismatch")
    return template.replace("__AUDIT_DATA__", data).encode("utf-8")


def prepare(root: Path = ROOT) -> dict[str, bytes]:
    profile = load_profile(root)
    tokenizer = load_tokenizer(profile, root)
    packets = load_packets(root)
    rows = [project(p, profile, tokenizer) for p in packets]
    validate_projection(rows, packets, profile, tokenizer)
    outputs = {"projection.jsonl": b"".join(chunks.prep.canonical_json(r) for r in rows), "audit.html": render_audit(rows, root)}
    summary = {"checkpoint": "M1.5b.3", "technical_validation": "LOCAL_PASS", "owner_acceptance": "PENDING",
               "profile_version": profile["profile_version"], "model": profile["model"], "records": len(rows),
               "source_chunk_sha256": CHUNKS_SHA, "source_manifest_sha256": CHUNK_MANIFEST_SHA,
               "tokenizer_revision": profile["tokenizer"]["revision"], "token_limit": profile["provider_input_limit"],
               "before_tokens_total": sum(r["local_token_fit"]["before_packet_tokens"] for r in rows),
               "after_tokens_total": sum(r["local_token_fit"]["passage_tokens"] for r in rows),
               "before_tokens_max": max(r["local_token_fit"]["before_packet_tokens"] for r in rows),
               "after_tokens_max": max(r["local_token_fit"]["passage_tokens"] for r in rows),
               "before_over_limit": sum(r["local_token_fit"]["before_packet_tokens"] > profile["provider_input_limit"] for r in rows),
               "after_over_limit": sum(r["local_token_fit"]["passage_tokens"] > profile["provider_input_limit"] for r in rows),
               "runtime_metadata_bytes_max": max(r["runtime_metadata_bytes"] for r in rows),
               "evidence_round_trips": len(rows), "external_embedding_calls": 0,
               "query_token_checks": [{"query": q, "tokens": len(tokenizer.encode("query: " + q, add_special_tokens=True).ids)} for q in
                                      ["What nutrition information is supported for the original U.S. can?", "When was Cherry Float announced for Canada?", "What should happen if marketing authorization is pending?"]],
               "limitations": profile["limitations"]}
    outputs["summary.json"] = chunks.prep.canonical_json(summary)
    dependencies = ["tools/prepare_embedding_projection.py", str(PROFILE), "tools/embedding_preparation/pyproject.toml", "tools/embedding_preparation/uv.lock",
                    "tools/embedding_preparation/audit_template.html", "src/launchlens/evidence_payload.py"]
    manifest = {"checkpoint": "M1.5b.3", "status": "PREPARED_PENDING_OWNER_ACCEPTANCE",
                "input_sha256": {p: chunks.prep.sha256((root / p).read_bytes()) for p in dependencies},
                "upstream_chunks_sha256": CHUNKS_SHA, "upstream_manifest_sha256": CHUNK_MANIFEST_SHA,
                "outputs": {name: {"bytes": len(data), "sha256": chunks.prep.sha256(data)} for name, data in outputs.items()}}
    outputs["manifest.json"] = chunks.prep.canonical_json(manifest)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provision-tokenizer", action="store_true", help="Download only the four hash-pinned public tokenizer files, then stop")
    args = parser.parse_args()
    try:
        if args.provision_tokenizer:
            provision()
            print("Tokenizer-only provisioning PASS; no model weights, document uploads or inference.")
            return 0
        outputs = prepare()
        destination = ROOT / OUTPUT
        chunks.prep.require(not destination.is_symlink(), "Unsafe output directory")
        destination.mkdir(parents=True, exist_ok=True)
        chunks.prep.require({p.name for p in destination.iterdir()} <= set(outputs), "Unexpected generated files")
        for name in outputs:
            chunks.prep.require(not (destination / name).is_symlink(), "Unsafe output file")
        with tempfile.TemporaryDirectory(prefix=".projection-", dir=destination) as temporary:
            for name, data in outputs.items():
                (Path(temporary) / name).write_bytes(data)
            for name in outputs:
                (Path(temporary) / name).replace(destination / name)
        print(json.dumps(json.loads(outputs["summary.json"]), indent=2))
        return 0
    except (chunks.prep.PreparationError, OSError, ValueError, KeyError) as error:
        print(f"Projection FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
