#!/usr/bin/env python3
"""Local evidence preparation for the two approved Cherry Float documents only."""

from __future__ import annotations

import csv
import io
import json
import re
import sys
import tempfile
from pathlib import Path

import prepare_documents as prep

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("data/generated/m15b-chunks")
POLICY_VERSION = "evidence-blocks-v1"
PAGE_SHA = "af664f4ac9fa9e2a29a2184e95cc6bf0c87142b6daa46727b56d4856bacc37b6"
PAGE_MANIFEST_SHA = "54ef44b0b98eb621d4f7e81e3f50f70a5fb15ce33b33d612e7a4292485484ec1"
BRIEF, PRD = [spec["document_id"] for spec in prep.DOCUMENTS]
APPROVALS = {
    BRIEF: ("docs/planning/m1.1-product-brief-review.md", "Formal owner acceptance - 2026-11-04", "Product Brief v0.2"),
    PRD: ("docs/planning/m1.2-prd-review.md", "Formal milestone acceptance and GitHub sync authority - 2026-11-04", "PRD v0.3"),
}
PREPARATION_REVIEW = "docs/planning/m1.5b-document-preparation.md"
ACCEPTANCE_HASHES = {
    "docs/planning/m1.1-product-brief-review.md": "8e03e209a06d4c6bdaef1cd5338c7c726646ecd419b78d44417bf62225872718",
    "docs/planning/m1.2-prd-review.md": "17202f63e1e99631623a35870ca4decc76f90116a15e7c07bb62c84bb4f7e6b6",
    PREPARATION_REVIEW: "7cbf02013ca074e19209b213963cdd882c35d93b3046fdc00c2d8d4af68036bb",
}


def approval(root: Path, document_id: str, source_hash: str) -> dict:
    path, heading, label = APPROVALS[document_id]
    data = prep.checked_bytes(root, path, ACCEPTANCE_HASHES[path])
    content = data.decode("utf-8")
    sections = content.split("## ", 2)
    prep.require(len(sections) > 1, "Canonical source acceptance section missing")
    first_section = sections[1]
    flattened = " ".join(first_section.split())
    prep.require(first_section.startswith(heading), "Expected canonical owner-acceptance section")
    prep.require("OWNER ACCEPTED" in flattened and label in flattened, "Canonical source acceptance missing")
    prep.require(source_hash in content, "Source hash absent from canonical acceptance record")
    return {"status": "OWNER_ACCEPTED", "date": "2026-11-04", "record_path": path,
            "record_sha256": prep.sha256(data), "section": heading, "source_sha256": source_hash}


def load_inputs(root: Path = ROOT) -> dict:
    content = prep.checked_bytes(root, (prep.OUTPUT / "pages.jsonl").as_posix(), PAGE_SHA)
    manifest_bytes = prep.checked_bytes(root, (prep.OUTPUT / "manifest.json").as_posix(), PAGE_MANIFEST_SHA)
    manifest = json.loads(manifest_bytes)
    prep.require(manifest["validation"] == "PASS", "Page preparation not validated")
    prep.require(manifest["outputs"]["pages.jsonl"]["sha256"] == prep.sha256(content), "Page manifest binding mismatch")
    for path, expected in manifest["input_sha256"].items():
        prep.checked_bytes(root, path, expected)
    records = [json.loads(line) for line in content.splitlines()]
    prep.validate_records(records, root)
    review_bytes = prep.checked_bytes(root, PREPARATION_REVIEW, ACCEPTANCE_HASHES[PREPARATION_REVIEW])
    review = review_bytes.decode("utf-8")
    prep.require("Status: **OWNER ACCEPTED / CLOSED (2026-11-05)**" in review, "M1.5b.1 owner acceptance missing")
    prep.require(PAGE_SHA in review and PAGE_MANIFEST_SHA in review, "Accepted page artifact hashes missing")
    sources = list(csv.DictReader(io.StringIO(prep.checked_bytes(root, prep.MANIFEST_CSV, prep.CSV_SHA).decode("utf-8"))))
    return {
        "root": root, "records": records,
        "pages": {(r["document_id"], r["page_number"]): r for r in records},
        "mappings": sources,
        "acceptance": {s["document_id"]: approval(root, s["document_id"], s["sha256"]) for s in prep.DOCUMENTS},
        "preparation_acceptance": {"status": "OWNER_ACCEPTED", "date": "2026-11-05", "record_path": PREPARATION_REVIEW,
                                   "record_sha256": prep.sha256(review_bytes), "pages_sha256": PAGE_SHA, "manifest_sha256": PAGE_MANIFEST_SHA},
    }


def recipes() -> list[tuple[str, str, str, int, list[int]]]:
    """Reviewed authoring-block boundaries, not a generic paragraph algorithm."""
    units = []
    def add(doc, unit, kind, page, indexes):
        units.append((doc, unit, kind, page, list(indexes)))
    add(BRIEF, "metadata", "document_context", 1, range(0, 9))
    for unit, index in [("overview", 9), ("features", 11), ("consumer-context", 13), ("positioning", 15)]:
        add(BRIEF, unit, "context", 1, [index, index + 1])
    add(BRIEF, "claim-register-context", "document_context", 2, [0, 1])
    for i in range(1, 16):
        add(BRIEF, f"PROD-{i:03d}", "product_claim", 2, [i + 1])
    add(BRIEF, "shared-qualification", "qualification", 2, [17])
    add(BRIEF, "unknowns", "qualification", 3, range(0, 5))
    add(BRIEF, "source-context", "document_context", 3, [5, 6])
    for i in range(1, 6):
        add(BRIEF, f"S{i}", "source_reference", 3, range(7 + (i - 1) * 3, 10 + (i - 1) * 3))
    add(BRIEF, "disclaimer", "document_context", 3, [22, 23])
    add(PRD, "metadata", "document_context", 1, range(0, 6))
    for unit, indexes in [("opportunity", [6, 7]), ("competitive-context", range(8, 13)),
                          ("vision", [13, 14]), ("audience", [15, 16])]:
        add(PRD, unit, "context", 1, indexes)
    for i, indexes in [(1, [17, 18]), (2, [19]), (3, [20])]:
        add(PRD, f"REQ-{i:03d}", "requirement", 1, indexes)
    for i, indexes in [(4, [0, 1]), (5, [2]), (6, [3]), (7, [4])]:
        add(PRD, f"REQ-{i:03d}", "requirement", 2, indexes)
    add(PRD, "scope", "context", 2, [5, 6, 7])
    add(PRD, "success-criteria", "context", 2, range(8, 12))
    add(PRD, "dependencies", "context", 2, range(12, 16))
    return units


def selectors(document: str, page: int, primary: list[int], source_ids: list[str]) -> list[tuple[int, int, str]]:
    selected = [(page, i, "primary") for i in primary]
    if document == BRIEF:
        # Classification/temporal scope, status meanings, mandatory qualification,
        # all unknowns, date caveats and independent-use boundary accompany claims.
        context = [(1, i) for i in (6, 7, 8)] + [(2, 1), (2, 17)]
        context += [(3, i) for i in (1, 2, 3, 4, 6, 23)]
        selected += [(p, i, "required_context") for p, i in context]
        for source_id in source_ids:
            first = 7 + (int(source_id[1:]) - 1) * 3
            selected += [(3, i, "source_reference") for i in range(first, first + 3)]
    else:
        # Requirements never inherit public-fact authority from product references.
        selected += [(1, i, "required_context") for i in (2, 3, 4, 5)]
        selected += [(2, i, "required_context") for i in (6, 7, 13, 14, 15)]
    seen = set()
    unique = []
    for p, i, role in selected:
        if (p, i) not in seen:
            seen.add((p, i))
            unique.append((p, i, role))
    return unique


def segment(inputs: dict, document: str, page: int, block: int, role: str) -> dict:
    record = inputs["pages"][(document, page)]
    span = record["validated_block_spans"][block]
    return {"role": role, "page_record_id": record["record_id"], "page_number": page,
            "block_index": block, "start": span["start"], "end": span["end"],
            "text": record["normalized_text"][span["start"]:span["end"]]}


def related_claims(text: str) -> list[str]:
    ids = set(re.findall(r"\bPROD-\d{3}\b", text))
    for first, last in re.findall(r"PROD-(\d{3})\s+to\s+PROD-(\d{3})", text):
        ids.update(f"PROD-{i:03d}" for i in range(int(first), int(last) + 1))
    return sorted(ids)


def source_references(inputs: dict, mapping_ids: list[str], document: str, unit: str) -> list[dict]:
    if document != BRIEF:
        return []
    # Shared mandatory qualification cites S1 and S4; do not mislabel these as
    # extra claim-source mappings for claims supported by a different source.
    result = []
    own_source = {unit} if unit in {"S1", "S2", "S3", "S4", "S5"} else set()
    for source_id in sorted(set(mapping_ids) | {"S1", "S4"} | own_source):
        source = next(r for r in inputs["mappings"] if r["source_id"] == source_id)
        roles = (["claim_support"] if source_id in mapping_ids else [])
        if source_id in {"S1", "S4"}:
            roles.append("shared_qualification")
        if source_id == unit:
            roles.append("document_reference")
        result.append({"source_id": source_id, "title": source["source_title"], "url": source["source_url"], "roles": roles})
    return result


def full_text(segments: list[dict], mappings: list[dict], links: list[dict]) -> str:
    text = "\n\n".join(s["text"] for s in segments)
    # These are verbatim CSV fields, labeled separately from PDF-origin text.
    fields = ("claim_id", "source_id", "verification_status", "market_scope", "temporal_scope", "source_locator", "notes_or_limitations")
    if mappings:
        text += "\n\nSource-specific CSV evidence (separate from PDF text):\n"
        text += "\n\n".join("\n".join(f"{field}: {row[field]}" for field in fields) for row in mappings)
    if links:
        text += "\n\nPDF hyperlink destinations:\n" + "\n".join(link["uri"] for link in links)
    return text


def build_chunks(inputs: dict) -> list[dict]:
    result = []
    for document, unit, kind, page, primary in recipes():
        spec = next(s for s in prep.DOCUMENTS if s["document_id"] == document)
        mappings = [dict(row) for row in inputs["mappings"] if kind == "product_claim" and row["claim_id"] == unit]
        mapping_ids = sorted({r["source_id"] for r in mappings})
        sources = source_references(inputs, mapping_ids, document, unit)
        source_ids = [r["source_id"] for r in sources]
        segments = [segment(inputs, document, p, i, role) for p, i, role in selectors(document, page, primary, source_ids)]
        primary_text = "\n\n".join(s["text"] for s in segments if s["role"] == "primary")
        links = inputs["pages"][(PRD, 1)]["hyperlinks"] if document == PRD and unit == "competitive-context" else []
        chunk = {
            "format_version": "1.0", "policy_version": POLICY_VERSION,
            "product_id": "CC-CHERRY-FLOAT", "document_id": document,
            "document_version": spec["document_version"], "authority": spec["authority"],
            "unit_id": unit, "chunk_kind": kind, "source_path": spec["path"],
            "source_url": spec["source_url"], "source_sha256": spec["sha256"],
            "source_acceptance": inputs["acceptance"][document],
            "preparation_acceptance": inputs["preparation_acceptance"],
            "chunk_status": "PREPARED_PENDING_OWNER_ACCEPTANCE",
            "page_numbers": sorted({s["page_number"] for s in segments}),
            "primary_text": primary_text, "segments": segments,
            "claim_ids": [unit] if kind == "product_claim" else [],
            "requirement_ids": [unit] if kind == "requirement" else [],
            "related_claim_ids": [i for i in related_claims(primary_text) if i != unit],
            "source_references": sources, "claim_source_mappings": mappings,
            "links": links,
            "text": full_text(segments, mappings, links),
        }
        # Links to other chunks are resolved after IDs exist. The digest binds the
        # complete local payload above, including source acceptance and CSV scope.
        chunk["chunk_id"] = f"{document}:v{spec['document_version']}:{unit}:{prep.sha256(prep.canonical_json(chunk))[:24]}"
        result.append(chunk)
    claim_index = {r["unit_id"]: r["chunk_id"] for r in result if r["chunk_kind"] == "product_claim"}
    for chunk in result:
        chunk["related_chunk_ids"] = [claim_index[i] for i in chunk["related_claim_ids"]]
    return result


def validate_chunks(chunks: list[dict], inputs: dict) -> dict:
    expected = build_chunks(inputs)
    prep.require(len(chunks) == len(expected), "Missing or extra chunks")
    prep.require(len({c["chunk_id"] for c in chunks}) == len(chunks), "Duplicate chunk IDs")
    required = set(json.loads((inputs["root"] / "data/schemas/evidence_chunk.schema.json").read_text())["required"])
    # Compare complete regenerated evidence, not just a self-reported PASS/digest.
    for actual, correct in zip(chunks, expected, strict=True):
        prep.require(set(actual) == required, "Chunk fields violate fixed format")
        prep.require(actual == correct, f"Incomplete or changed evidence/authority/acceptance: {correct['unit_id']}")
    coverage = []
    mappings = []
    for chunk in chunks:
        for part in chunk["segments"]:
            page = inputs["pages"][(chunk["document_id"], part["page_number"])]
            prep.require(part["page_record_id"] == page["record_id"], "Cross-document segment contamination")
            prep.require(part["text"] == page["normalized_text"][part["start"]:part["end"]], "Broken text lineage")
            if part["role"] == "primary":
                coverage.append((page["record_id"], part["block_index"]))
        mappings.extend(chunk["claim_source_mappings"])
    all_blocks = {(p["record_id"], i) for p in inputs["records"] for i in range(len(p["validated_block_spans"]))}
    prep.require(set(coverage) == all_blocks and len(coverage) == len(all_blocks) == 96, "Authored blocks missing or duplicated as primary content")
    prep.require(mappings == inputs["mappings"], "Claim-source rows missing, reordered or reassigned")
    claims = sum(c["chunk_kind"] == "product_claim" for c in chunks)
    requirements = sum(c["chunk_kind"] == "requirement" for c in chunks)
    prep.require(claims == 15 and requirements == 7, "Incomplete primary claim/requirement set")
    return {"chunks": len(chunks), "product_claim_chunks": claims, "requirement_chunks": requirements, "primary_blocks": len(coverage), "claim_source_mappings": len(mappings)}


def prepare(root: Path = ROOT) -> tuple[bytes, bytes]:
    inputs = load_inputs(root)
    chunks = build_chunks(inputs)
    counts = validate_chunks(chunks, inputs)
    content = b"".join(prep.canonical_json(c) for c in chunks)
    dependencies = ["tools/prepare_chunks.py", "data/schemas/evidence_chunk.schema.json", PREPARATION_REVIEW,
                    (prep.OUTPUT / "pages.jsonl").as_posix(), (prep.OUTPUT / "manifest.json").as_posix()]
    dependencies += [value[0] for value in APPROVALS.values()]
    manifest = {"checkpoint": "M1.5b.2", "policy_version": POLICY_VERSION,
                "technical_validation": "PASS", "chunk_status": "PREPARED_PENDING_OWNER_ACCEPTANCE", **counts,
                "input_sha256": {name: prep.sha256((root / name).read_bytes()) for name in dependencies},
                "outputs": {"chunks.jsonl": {"sha256": prep.sha256(content), "bytes": len(content)}},
                "sizes": {"largest_primary_characters": max(len(c["primary_text"]) for c in chunks),
                          "largest_evidence_characters": max(len(c["text"]) for c in chunks)},
                "chunk_summary": [{"unit_id": c["unit_id"], "document_id": c["document_id"], "chunk_id": c["chunk_id"],
                                   "kind": c["chunk_kind"], "primary_characters": len(c["primary_text"]),
                                   "evidence_characters": len(c["text"]), "page_numbers": c["page_numbers"]} for c in chunks],
                "limits": ["No embedding model/tokenizer is selected or invoked here; model token fit is unverified.",
                           "No blind token/character splits, overlap windows, truncation, summaries or inferred paragraphs.",
                           "Exact source labels are preserved; source/preparation acceptance comes only from canonical review records.",
                           "These local nested records are not a finalized Pinecone API payload; metadata adaptation and model budgeting require later approval."]}
    return content, prep.canonical_json(manifest)


def main() -> int:
    try:
        content, manifest = prepare()
        destination = ROOT / OUTPUT
        prep.require(not destination.is_symlink(), "Unsafe output directory")
        destination.mkdir(parents=True, exist_ok=True)
        payloads = {"chunks.jsonl": content, "manifest.json": manifest}
        prep.require({p.name for p in destination.iterdir()} <= set(payloads), "Unexpected files in output directory")
        for name in payloads:
            prep.require(not (destination / name).is_symlink(), "Unsafe output file")
        with tempfile.TemporaryDirectory(prefix=".chunks-", dir=destination) as temporary:
            for name, data in payloads.items():
                (Path(temporary) / name).write_bytes(data)
            for name in payloads:
                (Path(temporary) / name).replace(destination / name)
        print(json.dumps({"status": "PASS", "chunks": len(content.splitlines()), "output": str(OUTPUT),
                          "chunks_sha256": prep.sha256(content), "manifest_sha256": prep.sha256(manifest)}, indent=2))
        return 0
    except (prep.PreparationError, OSError, KeyError, ValueError) as error:
        print(f"Chunk preparation FAILED; no successful preparation claimed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
