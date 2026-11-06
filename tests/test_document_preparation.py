"""Preservation, failure and repeatability tests for the approved five pages."""

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfWriter

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prepare_documents", ROOT / "tools/prepare_documents.py")
prep = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prep)


class DocumentPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content, cls.manifest = prep.prepare(ROOT)
        cls.records = [json.loads(line) for line in cls.content.splitlines()]

    def test_complete_approved_content_and_authority(self):
        result = prep.validate_records(self.records, ROOT)
        self.assertEqual(result, {"complete_claims": 15, "complete_requirements": 7, "claim_source_mappings": 21})
        manifest = json.loads(self.manifest)
        self.assertEqual(manifest["approved_display_blocks"], 96)
        self.assertEqual(sum(len(r["validated_block_spans"]) for r in self.records), 96)
        self.assertEqual(sum(len(r["hyperlinks"]) for r in self.records), 7)
        self.assertEqual([r["authority"] for r in self.records], ["public_product_facts"] * 3 + ["synthetic_product_intent"] * 2)

    def test_repeated_runs_are_byte_identical(self):
        content, manifest = prep.prepare(ROOT)
        self.assertEqual(content, self.content)
        self.assertEqual(manifest, self.manifest)
        self.assertEqual(json.loads(manifest)["outputs"]["pages.jsonl"]["sha256"], prep.sha256(content))

    def test_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "changed.pdf").write_bytes(b"%PDF-1.4\nnot the approved file")
            with self.assertRaisesRegex(prep.PreparationError, "SHA-256 mismatch"):
                prep.checked_bytes(root, "changed.pdf", prep.DOCUMENTS[0]["sha256"])

    def test_blank_pdf_page_rejected_without_ocr(self):
        import io
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        stream = io.BytesIO()
        writer.write(stream)
        with self.assertRaisesRegex(prep.PreparationError, "Empty page"):
            prep.extract_pages(stream.getvalue())

    def test_unreadable_pdf_rejected(self):
        with self.assertRaises(prep.pypdf.errors.PdfReadError):
            prep.extract_pages(b"not a PDF")

    def test_normalization_preserves_words_case_and_line_boundaries(self):
        raw = "PROD-011\u00a0 Canada  \r\nnot verified\t\r\n\r\n\r\nMarch 2026\rnext-line\n"
        normalized, changes = prep.normalize_text(raw)
        self.assertEqual(normalized, "PROD-011  Canada\nnot verified\n\nMarch 2026\nnext-line\n")
        self.assertEqual(changes["nbsp_to_space"], 1)
        self.assertEqual(changes["extra_blank_lines_removed"], 1)
        self.assertEqual(changes["trailing_whitespace_removed"], 3)
        self.assertEqual(prep.normalize_text(normalized)[0], normalized)

    def assert_rejected(self, mutate):
        records = copy.deepcopy(self.records)
        mutate(records)
        with self.assertRaises(prep.PreparationError):
            prep.validate_records(records, ROOT)

    @staticmethod
    def change_text(records, page_index, old, new):
        page = records[page_index]
        assert old in page["raw_text"]
        page["raw_text"] = page["raw_text"].replace(old, new, 1)
        page["normalized_text"], page["normalization_changes"] = prep.normalize_text(page["raw_text"])
        page["identifiers"] = sorted(set(prep.ID.findall(page["normalized_text"])))

    def test_canada_qualification_loss_rejected_even_with_all_ids(self):
        self.assert_rejected(lambda r: self.change_text(r, 1, "This is not an isolated Canadian Cherry Float date.", ""))

    def test_shared_qualification_loss_rejected(self):
        self.assert_rejected(lambda r: self.change_text(r, 1, "No fictional readiness or\napproval is established.", "Fictional readiness is established."))

    def test_req007_withholding_condition_loss_rejected(self):
        self.assert_rejected(lambda r: self.change_text(r, 4, "the system must withhold the claim", "the system may publish the claim"))

    def test_claim_source_reassignment_rejected(self):
        self.assert_rejected(lambda r: self.change_text(r, 1, "PROD-011 | QUALIFIED_SOURCE_STATEMENT | S1.", "PROD-011 | QUALIFIED_SOURCE_STATEMENT | S4."))

    def test_requirement_product_reference_reassignment_rejected(self):
        self.assert_rejected(lambda r: self.change_text(r, 4, "consistent with PROD-003.", "consistent with PROD-008."))

    def test_link_destination_change_rejected(self):
        self.assert_rejected(lambda r: r[3]["hyperlinks"][0].update(uri="https://example.invalid/changed"))

    def test_synthetic_authority_cannot_be_promoted(self):
        self.assert_rejected(lambda r: r[3].update(authority="public_product_facts"))

    def test_missing_and_duplicate_pages_rejected(self):
        self.assert_rejected(lambda r: r.pop())
        self.assert_rejected(lambda r: r.__setitem__(1, copy.deepcopy(r[0])))

    def test_identifiers_alone_cannot_pass(self):
        self.assert_rejected(lambda r: self.change_text(r, 1, "150 calories", "999 calories"))

    def test_unexplained_inserted_text_rejected(self):
        self.assert_rejected(lambda r: self.change_text(r, 0, "B. Product overview", "B. Product overview\nAvailable everywhere now."))

    def test_stored_evidence_span_tampering_rejected(self):
        self.assert_rejected(lambda r: r[1]["evidence_spans"][0].update(end=9999))

    def test_failure_does_not_overwrite_previous_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / prep.OUTPUT
            output.mkdir(parents=True)
            old = output / "pages.jsonl"
            old.write_text("previous accepted bytes\n")
            with patch.object(prep, "ROOT", root), patch.object(prep, "prepare", side_effect=prep.PreparationError("test rejection")):
                self.assertEqual(prep.main(), 1)
            self.assertEqual(old.read_text(), "previous accepted bytes\n")


if __name__ == "__main__":
    unittest.main()
