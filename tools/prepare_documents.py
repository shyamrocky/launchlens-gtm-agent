#!/usr/bin/env python3
"""Prepare only LaunchLens's two approved PDFs. No network or model calls."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import re
import sys
import tempfile
import warnings
from pathlib import Path

import pypdf
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("data/generated/m15b-document-preparation")
FORMAT_VERSION = "1.0"
PARSER_VERSION = "6.21.4"
MANIFEST_CSV = "data/public_sources/product_source_manifest.csv"
CSV_SHA = "b2f7021e263b579fa209bbd8b8c04dbd9f6e549c1e0cb8a75ce11a7077c75f8e"
DOCUMENTS = (
    {
        "document_id": "cherry-float-product-brief",
        "document_version": "0.2",
        "authority": "public_product_facts",
        "path": "data/public_sources/coca_cola_cherry_float_product_brief.pdf",
        "sha256": "57d0cbf0e5064dddeab6dfdf73825e58a71b8cc1d4a5c183973b29a8c580cbfc",
        "markdown": "data/public_sources/coca_cola_cherry_float_product_brief.md",
        "markdown_sha256": "22444a67072f60a37d2a15359f17f8a5be6d53af1cd6e30dcebec99dbf05780f",
        "source_url": "https://drive.google.com/file/d/1pJhRHdp5Oe6sk6aG5D_aP2MQY7gdHT3x/view",
        "pages": 3,
        "blocks": 59,
        "header": "LaunchLens | Product evidence | Draft v0.2\nResearch snapshot 2026-11-04 | Owner review pending\n",
    },
    {
        "document_id": "cherry-float-synthetic-prd",
        "document_version": "0.3",
        "authority": "synthetic_product_intent",
        "path": "data/synthetic/coca_cola_cherry_float_prd.pdf",
        "sha256": "95a0392d9c120a3001f20ab5d601a0345c9cbf170d5f2fd7f75b37f3c73cfcff",
        "markdown": "data/synthetic/coca_cola_cherry_float_prd.md",
        "markdown_sha256": "c217232461ca7932fc6aecaa37fb3438fbdad6c9ccd20e3a282add493d6b6e19",
        "source_url": "https://drive.google.com/file/d/1ThKUJxAmUn2Qf-rVmyVbDu2M5ZSqyCgS/view",
        "pages": 2,
        "blocks": 37,
        "header": "LaunchLens | Synthetic educational scenario | v0.3 draft\n",
    },
)


class PreparationError(ValueError):
    """The approved source or preservation contract was not satisfied."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PreparationError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_bytes(root: Path, relative: str, expected: str) -> bytes:
    path = root / relative
    require(path.is_file() and not path.is_symlink(), f"Missing/unsafe input: {relative}")
    data = path.read_bytes()
    require(sha256(data) == expected, f"SHA-256 mismatch: {relative}")
    return data


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def normalize_text(text: str) -> tuple[str, dict[str, int]]:
    """Preserve every line boundary; do not infer paragraphs or repair words."""
    counts = {
        "crlf_to_lf": text.count("\r\n"),
        "cr_to_lf": text.replace("\r\n", "").count("\r"),
        "nbsp_to_space": text.count("\u00a0"),
        "trailing_whitespace_removed": 0,
        "extra_blank_lines_removed": 0,
    }
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    lines = []
    for line in text.split("\n"):
        cleaned = line.rstrip(" \t")
        counts["trailing_whitespace_removed"] += len(line) - len(cleaned)
        lines.append(cleaned)
    text = "\n".join(lines)
    reduced = re.sub(r"\n{3,}", "\n\n", text)
    counts["extra_blank_lines_removed"] = text.count("\n") - reduced.count("\n")
    return reduced, counts


LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
ID = re.compile(r"\b(?:PROD|REQ)-\d{3}\b")


def markdown_blocks(markdown: str, brief: bool) -> list[list[dict]]:
    """Read the two known authoring formats for validation, never ingestion text."""
    pages = []
    for page in markdown.split("<!-- page-break -->"):
        blocks = []
        for block in re.split(r"\n\s*\n", page.strip()):
            display = re.sub(r"^#{1,3} ", "", block)
            if brief:
                display = re.sub(r"^- ", "", display)
            links = [{"label": m[1], "uri": m[2]} for m in LINK.finditer(display)]
            display = LINK.sub(lambda m: m[1], display)
            blocks.append({"text": display, "links": links})
        pages.append(blocks)
    return pages


def find_span(text: str, expected: str, start: int = 0) -> tuple[int, int]:
    # Whitespace equivalence is for comparison only; stored line boundaries survive.
    pattern = r"\s+".join(re.escape(token) for token in expected.split())
    match = re.compile(pattern).search(text, start)
    require(match is not None, f"Missing/reordered statement or qualification: {expected[:100]}")
    return match.span()


def extract_pages(pdf: bytes) -> list[dict]:
    """Hash-gated callers supply trusted, small, text-based PDFs only."""
    diagnostics: list[str] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            diagnostics.append(record.getMessage())

    logger = logging.getLogger("pypdf")
    handler = Capture()
    logger.addHandler(handler)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            reader = PdfReader(io.BytesIO(pdf), strict=True)
            require(not reader.is_encrypted, "Encrypted PDF is outside scope")
            pages = []
            for page in reader.pages:
                raw = page.extract_text(extraction_mode="plain") or ""
                require(bool(raw.strip()), "Empty page text; OCR is outside scope")
                require("\ufffd" not in raw and "\x00" not in raw, "Unresolved extraction characters")
                normalized, changes = normalize_text(raw)
                links = []
                for reference in page.get("/Annots", []):
                    annotation = reference.get_object()
                    action = annotation.get("/A")
                    if action is not None:
                        action = action.get_object()
                    if action and action.get("/S") == "/URI":
                        uri = str(action.get("/URI", ""))
                        require(uri.startswith("https://"), "Unexpected non-HTTPS source link")
                        links.append({"uri": uri, "rect": [float(v) for v in annotation["/Rect"]]})
                pages.append({"raw_text": raw, "normalized_text": normalized, "normalization_changes": changes, "hyperlinks": links})
            diagnostics.extend(str(w.message) for w in caught)
        require(not diagnostics, "PDF parser emitted warnings; review required")
        return pages
    finally:
        logger.removeHandler(handler)


def validate_page(page: dict, spec: dict, number: int, blocks: list[dict]) -> None:
    """Check complete display blocks, their order, links and no unexplained text."""
    text = page["normalized_text"]
    header = spec["header"] + str(number) + "\n"
    require(text.startswith(header), f"Unexpected page header: {spec['document_id']} page {number}")
    cursor = len(header)
    evidence = []
    validation_blocks = []
    for block in blocks:
        start, end = find_span(text, block["text"], cursor)
        require(not text[cursor:start].strip(), "Unexpected text between approved blocks")
        validation_blocks.append({"start": start, "end": end})
        for link in block["links"]:
            require(link["uri"] in [a["uri"] for a in page["hyperlinks"]], "Source link destination missing/changed")
        evidence_id = re.match(r"^(PROD|REQ)-\d{3}\b", block["text"])
        if evidence_id:
            evidence.append({
                "id": evidence_id[0], "start": start, "end": end,
                "references": sorted(set(re.findall(r"\bS[1-5]\b|\bPROD-\d{3}\b", block["text"])) - {evidence_id[0]}),
            })
        cursor = end
    require(not text[cursor:].strip(), "Unexpected text after approved blocks")
    page["evidence_spans"] = evidence
    page["validated_block_spans"] = validation_blocks
    page["warnings"] = []


def validate_claim_relationships(records: list[dict], manifest_csv: bytes) -> dict:
    """Validate complete statements and 21 source mappings, not just ID counts."""
    rows = list(csv.DictReader(io.StringIO(manifest_csv.decode("utf-8"))))
    require(len(rows) == 21, "Expected 21 claim-source mappings")
    expected_ids = {f"PROD-{i:03d}" for i in range(1, 16)}
    require({r['claim_id'] for r in rows} == expected_ids, "Unexpected manifest claim set")
    brief_pages = [r for r in records if r["authority"] == "public_product_facts"]
    claims = {span["id"]: (r, span) for r in brief_pages for span in r["evidence_spans"]}
    require(set(claims) == expected_ids, "Expected 15 complete claim statements")
    for claim_id, (page, span) in claims.items():
        mappings = [r for r in rows if r["claim_id"] == claim_id]
        actual = page["normalized_text"][span["start"]:span["end"]]
        statements = {r["claim_statement"] for r in mappings}
        statuses = {r["verification_status"] for r in mappings}
        require(len(statements) == len(statuses) == 1, "Inconsistent manifest statements/statuses")
        statement, status = next(iter(statements)), next(iter(statuses))
        sources = sorted({r["source_id"] for r in mappings})
        expected = f"{claim_id} | {status} | {', '.join(sources)}. {statement}"
        require(" ".join(actual.split()) == " ".join(expected.split()), f"Claim statement/status/source mismatch: {claim_id}")
        require(span["references"] == sources, f"Source association changed: {claim_id}")
        for mapping in mappings:
            ref_page = brief_pages[2]
            require(mapping["source_url"] in {a["uri"] for a in ref_page["hyperlinks"]}, "Unresolved claim-source URL")
            find_span(ref_page["normalized_text"], f"{mapping['source_id']}. {mapping['source_title']}")
            find_span(ref_page["normalized_text"], mapping["source_url"])
    requirements = [(r, s) for r in records for s in r["evidence_spans"] if s["id"].startswith("REQ-")]
    require({s["id"] for _, s in requirements} == {f"REQ-{i:03d}" for i in range(1, 8)} and len(requirements) == 7, "Expected seven complete requirements")
    for _, span in requirements:
        require(set(span["references"]) <= expected_ids, "Requirement references an unknown product claim")
    return {"complete_claims": len(claims), "complete_requirements": len(requirements), "claim_source_mappings": len(rows)}


def validate_records(records: list[dict], root: Path) -> dict:
    """Explicit validation for the fixed two-document format; no generic framework."""
    schema = json.loads((root / "data/schemas/parsed_page.schema.json").read_text())
    require(len(records) == 5, "Expected exactly five page records")
    require(len({r["record_id"] for r in records}) == 5, "Duplicate page record IDs")
    for spec in DOCUMENTS:
        md = checked_bytes(root, spec["markdown"], spec["markdown_sha256"]).decode("utf-8")
        blocks = markdown_blocks(md, spec["authority"] == "public_product_facts")
        pages = [r for r in records if r["document_id"] == spec["document_id"]]
        require([r["page_number"] for r in pages] == list(range(1, spec["pages"] + 1)), "Missing/reordered pages")
        require(sum(map(len, blocks)) == spec["blocks"], "Unexpected authoring block count")
        for number, (page, page_blocks) in enumerate(zip(pages, blocks, strict=True), 1):
            require(set(page) == set(schema["required"]), "Unexpected page record fields")
            for field, value in {
                "format_version": FORMAT_VERSION, "document_version": spec["document_version"],
                "authority": spec["authority"], "source_path": spec["path"],
                "source_url": spec["source_url"], "source_sha256": spec["sha256"],
                "parser_version": PARSER_VERSION,
                "record_id": f"{spec['document_id']}:v{spec['document_version']}:{spec['sha256']}:p{number}",
            }.items():
                require(page[field] == value, f"Invalid provenance or authority: {field}")
            require(isinstance(page["raw_text"], str) and isinstance(page["normalized_text"], str), "Text must be strings")
            normalized, changes = normalize_text(page["raw_text"])
            require(page["normalized_text"] == normalized and page["normalization_changes"] == changes, "Normalization not reproducible")
            require(page["identifiers"] == sorted(set(ID.findall(normalized))), "Identifier catalog mismatch")
            require(not page["warnings"], "Unresolved parser warning")
            # Recompute preservation evidence; do not trust stored PASS/spans.
            checked = dict(page)
            validate_page(checked, spec, number, page_blocks)
            require(checked["evidence_spans"] == page["evidence_spans"], "Statement/reference spans changed")
            require(checked["validated_block_spans"] == page["validated_block_spans"], "Block spans changed")
            expected_links = [a["uri"] for b in page_blocks for a in b["links"]]
            if spec["authority"] == "public_product_facts" and number == 3:
                expected_links = re.findall(r"^https://\S+$", "\n".join(b["text"] for b in page_blocks), re.M)
            require([a["uri"] for a in page["hyperlinks"]] == expected_links, "Annotation links changed or reordered")
            require(all(len(a["rect"]) == 4 and all(isinstance(v, (int, float)) for v in a["rect"]) for a in page["hyperlinks"]), "Invalid PDF link rectangle")
    csv_bytes = checked_bytes(root, MANIFEST_CSV, CSV_SHA)
    return validate_claim_relationships(records, csv_bytes)


def prepare(root: Path = ROOT) -> tuple[bytes, bytes]:
    require(pypdf.__version__ == PARSER_VERSION, "Use the locked pypdf version via uv run --locked")
    records = []
    for spec in DOCUMENTS:
        pdf = checked_bytes(root, spec["path"], spec["sha256"])
        md = checked_bytes(root, spec["markdown"], spec["markdown_sha256"]).decode("utf-8")
        blocks = markdown_blocks(md, spec["authority"] == "public_product_facts")
        pages = extract_pages(pdf)
        require(len(pages) == spec["pages"] == len(blocks), "Unexpected page count")
        for number, (page, page_blocks) in enumerate(zip(pages, blocks, strict=True), 1):
            validate_page(page, spec, number, page_blocks)
            records.append({
                "format_version": FORMAT_VERSION,
                "record_id": f"{spec['document_id']}:v{spec['document_version']}:{spec['sha256']}:p{number}",
                "document_id": spec["document_id"], "document_version": spec["document_version"],
                "authority": spec["authority"], "source_path": spec["path"],
                "source_url": spec["source_url"], "source_sha256": spec["sha256"],
                "page_number": number, "parser_version": PARSER_VERSION,
                "identifiers": sorted(set(ID.findall(page["normalized_text"]))), **page,
            })
    counts = validate_records(records, root)
    content = b"".join(canonical_json(record) for record in records)
    dependencies = ["tools/prepare_documents.py", "data/schemas/parsed_page.schema.json", "pyproject.toml", "uv.lock", MANIFEST_CSV]
    dependencies += [spec[key] for spec in DOCUMENTS for key in ("path", "markdown")]
    manifest = {
        "format_version": FORMAT_VERSION, "checkpoint": "M1.5b.1", "validation": "PASS",
        "parser": {"name": "pypdf", "version": PARSER_VERSION, "extraction_mode": "plain"},
        "normalization_policy": "line-preserving-v1; no paragraph joining, dehyphenation, Unicode folding or case changes",
        "page_records": len(records), "approved_display_blocks": 96, **counts,
        "page_summary": [{"record_id": r["record_id"], "raw_characters": len(r["raw_text"]), "normalized_characters": len(r["normalized_text"]), "evidence_statements": len(r["evidence_spans"]), "hyperlinks": len(r["hyperlinks"]), "normalization_changes": r["normalization_changes"]} for r in records],
        "input_sha256": {f: sha256((root / f).read_bytes()) for f in dependencies},
        "outputs": {"pages.jsonl": {"sha256": sha256(content), "bytes": len(content)}},
        "warnings": [],
        "downstream_obligations": [
            "Page records are not retrieval chunks; do not index them as approved chunks.",
            "Brief page 2 shared Mandatory qualification applies to claims; retain page 1 scope and page 3 unknowns/source references.",
            "Per-source CSV locators and limitations remain authoritative references; they are validated but not ingested into page text.",
            "PRD synthetic intent never overrides product evidence; its contextual public citations do not turn requirements into product facts.",
        ],
    }
    # No time, absolute path or host data: the manifest bytes/hash are repeatable too.
    return content, canonical_json(manifest)


def main() -> int:
    try:
        content, manifest = prepare()
        destination = ROOT / OUTPUT
        require(not destination.is_symlink(), "Output directory must not be a symlink")
        destination.mkdir(parents=True, exist_ok=True)
        payloads = {"pages.jsonl": content, "manifest.json": manifest}
        # Validate everything before touching previous outputs; refuse unrelated files.
        require({p.name for p in destination.iterdir()} <= set(payloads), "Unexpected files in generated destination")
        for name in payloads:
            require(not (destination / name).is_symlink(), "Output must not be a symlink")
        with tempfile.TemporaryDirectory(prefix=".prepare-", dir=destination) as temporary:
            for name, data in payloads.items():
                (Path(temporary) / name).write_bytes(data)
            for name in payloads:
                (Path(temporary) / name).replace(destination / name)
        print(json.dumps({"status": "PASS", "pages": 5, "output": OUTPUT.as_posix(), "pages_sha256": sha256(content), "manifest_sha256": sha256(manifest)}, indent=2))
        return 0
    except (PreparationError, OSError, pypdf.errors.PdfReadError) as error:
        print(f"Preparation FAILED; no successful preparation claimed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
