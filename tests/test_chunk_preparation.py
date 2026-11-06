"""Evidence completeness and authority checks for M1.5b.2; no remote services."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import prepare_chunks as chunks


class ChunkPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = chunks.load_inputs(ROOT)
        cls.chunks = chunks.build_chunks(cls.inputs)
        cls.by_unit = {c["unit_id"]: c for c in cls.chunks}

    def test_coverage_and_no_primary_block_duplication(self):
        counts = chunks.validate_chunks(self.chunks, self.inputs)
        self.assertEqual(counts, {"chunks": 45, "product_claim_chunks": 15,
                                  "requirement_chunks": 7, "primary_blocks": 96,
                                  "claim_source_mappings": 21})
        self.assertEqual(len({c["chunk_id"] for c in self.chunks}), 45)

    def test_canada_claim_packet_is_self_contained_and_sources_not_conflated(self):
        claim = self.by_unit["PROD-011"]
        self.assertIn("This is not an isolated Canadian Cherry Float date.", claim["primary_text"])
        text = " ".join(claim["text"].split())
        self.assertIn("S4 separately specifies March 2026 for Cherry Float", text)
        self.assertIn("No fictional readiness or approval is established.", text)
        self.assertIn("Actual shelf arrival and simulation readiness remain unverified.", text)
        self.assertEqual(claim["page_numbers"], [1, 2, 3])
        self.assertEqual([m["source_id"] for m in claim["claim_source_mappings"]], ["S1"])
        references = {r["source_id"]: r for r in claim["source_references"]}
        self.assertIn("claim_support", references["S1"]["roles"])
        self.assertEqual(references["S4"]["roles"], ["shared_qualification"])
        for source in references.values():
            self.assertIn(source["url"], claim["text"])

    def test_every_claim_keeps_csv_scope_and_global_limitations(self):
        for c in self.chunks:
            if c["chunk_kind"] != "product_claim":
                continue
            for mapping in c["claim_source_mappings"]:
                for field in ["market_scope", "temporal_scope", "source_locator", "notes_or_limitations"]:
                    self.assertIn(mapping[field], c["text"])
            self.assertIn("Mandatory qualification:", c["text"])
            self.assertIn("absence", c["text"])
            self.assertIn("No global availability duration is established.", c["text"])

    def test_req007_conditions_and_synthetic_authority(self):
        c = self.by_unit["REQ-007"]
        text = " ".join(c["primary_text"].split())
        self.assertIn("both the fictional Launch Calendar and Readiness Tracker support the claim", text)
        self.assertIn("the system must withhold the claim", text)
        self.assertIn("current inventory or launch authorization", text)
        self.assertEqual(c["authority"], "synthetic_product_intent")
        self.assertIn("they do not establish delivered capabilities or approved claims", " ".join(c["text"].split()))

    def test_cross_document_references_do_not_merge_authority(self):
        c = self.by_unit["REQ-001"]
        self.assertEqual(c["related_claim_ids"], ["PROD-001", "PROD-002"])
        expected = [self.by_unit[i]["chunk_id"] for i in ["PROD-001", "PROD-002"]]
        self.assertEqual(c["related_chunk_ids"], expected)
        self.assertTrue(all(p["page_record_id"].startswith(chunks.PRD + ":") for p in c["segments"]))
        self.assertEqual(c["claim_source_mappings"], [])
        self.assertEqual(c["claim_ids"], [])

    def test_historical_pending_labels_do_not_determine_acceptance(self):
        claim = self.by_unit["PROD-011"]
        self.assertIn("owner acceptance is pending", claim["text"])
        self.assertEqual(claim["claim_source_mappings"][0]["owner_review_status"], "PENDING")
        self.assertEqual(claim["source_acceptance"]["status"], "OWNER_ACCEPTED")
        self.assertEqual(claim["preparation_acceptance"]["status"], "OWNER_ACCEPTED")
        self.assertEqual(claim["chunk_status"], "PREPARED_PENDING_OWNER_ACCEPTANCE")
        self.assertEqual(claim["source_acceptance"]["source_sha256"], claim["source_sha256"])

    def test_all_source_reference_chunks_identify_their_own_source(self):
        for source_id in ["S1", "S2", "S3", "S4", "S5"]:
            c = self.by_unit[source_id]
            own = next(s for s in c["source_references"] if s["source_id"] == source_id)
            self.assertIn("document_reference", own["roles"])
            self.assertIn(own["url"], c["primary_text"])

    def test_competitor_urls_survive_labels_only_in_prd_text(self):
        c = self.by_unit["competitive-context"]
        self.assertEqual(len(c["links"]), 2)
        self.assertIn("PepsiCo release, 2025-01-14", c["primary_text"])
        for link in c["links"]:
            self.assertIn(link["uri"], c["text"])
        self.assertEqual(c["authority"], "synthetic_product_intent")

    def test_range_references_are_expanded(self):
        overview = next(c for c in self.chunks if c["document_id"] == chunks.BRIEF and c["unit_id"] == "overview")
        self.assertEqual(overview["related_claim_ids"], ["PROD-001", "PROD-002", "PROD-003"])

    def assert_rejected(self, unit, mutate):
        records = copy.deepcopy(self.chunks)
        record = next(c for c in records if c["unit_id"] == unit)
        mutate(record)
        with self.assertRaises(chunks.prep.PreparationError):
            chunks.validate_chunks(records, self.inputs)

    def test_missing_cross_page_source_rejected(self):
        self.assert_rejected("PROD-011", lambda c: c.update(segments=[s for s in c["segments"] if s["page_number"] != 3]))

    def test_mandatory_qualification_removal_rejected(self):
        self.assert_rejected("PROD-011", lambda c: c.update(text=c["text"].replace("Mandatory qualification:", "")))

    def test_csv_limitations_removed_rejected(self):
        self.assert_rejected("PROD-008", lambda c: c["claim_source_mappings"][0].update(notes_or_limitations=""))

    def test_source_swap_rejected(self):
        self.assert_rejected("PROD-011", lambda c: c["source_references"][0].update(url="https://example.invalid"))

    def test_authority_promotion_rejected(self):
        self.assert_rejected("REQ-007", lambda c: c.update(authority="public_product_facts"))

    def test_acceptance_promotion_of_chunks_rejected(self):
        self.assert_rejected("REQ-007", lambda c: c.update(chunk_status="OWNER_ACCEPTED"))

    def test_changed_canonical_acceptance_binding_rejected(self):
        self.assert_rejected("PROD-011", lambda c: c["source_acceptance"].update(record_sha256="0" * 64))

    def test_broken_related_chunk_link_rejected(self):
        self.assert_rejected("REQ-001", lambda c: c.update(related_chunk_ids=[]))

    def test_text_truncation_rejected(self):
        self.assert_rejected("REQ-007", lambda c: c.update(primary_text=c["primary_text"][:100]))

    def test_missing_duplicate_or_reordered_chunks_rejected(self):
        for records in [self.chunks[:-1], [self.chunks[0], *self.chunks[:-1]], list(reversed(self.chunks))]:
            with self.assertRaises(chunks.prep.PreparationError):
                chunks.validate_chunks(records, self.inputs)

    def test_tampered_input_pages_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dest = root / chunks.prep.OUTPUT
            dest.mkdir(parents=True)
            (dest / "pages.jsonl").write_bytes((ROOT / chunks.prep.OUTPUT / "pages.jsonl").read_bytes() + b" ")
            with self.assertRaisesRegex(chunks.prep.PreparationError, "SHA-256 mismatch"):
                chunks.load_inputs(root)

    def test_absent_current_source_approval_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = chunks.APPROVALS[chunks.BRIEF][0]
            dest = root / path
            dest.parent.mkdir(parents=True)
            dest.write_text((ROOT / path).read_text().replace("Status: OWNER ACCEPTED.", "Status: PENDING.", 1))
            with self.assertRaisesRegex(chunks.prep.PreparationError, "SHA-256 mismatch"):
                chunks.approval(root, chunks.BRIEF, chunks.prep.DOCUMENTS[0]["sha256"])

    def test_changed_approval_record_requires_review_even_if_label_stays_accepted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            relative = chunks.APPROVALS[chunks.BRIEF][0]
            target = root / relative
            target.parent.mkdir(parents=True)
            target.write_text((ROOT / relative).read_text() + "\nLater approval-state change.\n")
            with self.assertRaisesRegex(chunks.prep.PreparationError, "SHA-256 mismatch"):
                chunks.approval(root, chunks.BRIEF, chunks.prep.DOCUMENTS[0]["sha256"])

    def test_repeated_generation_has_identical_content_and_manifest(self):
        first = chunks.prepare(ROOT)
        second = chunks.prepare(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(json.loads(first[1])["outputs"]["chunks.jsonl"]["sha256"], chunks.prep.sha256(first[0]))

    def test_failure_preserves_previous_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = root / chunks.OUTPUT
            out.mkdir(parents=True)
            old = out / "chunks.jsonl"
            old.write_text("previous output\n")
            with patch.object(chunks, "ROOT", root), patch.object(chunks, "prepare", side_effect=chunks.prep.PreparationError("test rejection")):
                self.assertEqual(chunks.main(), 1)
            self.assertEqual(old.read_text(), "previous output\n")


if __name__ == "__main__":
    unittest.main()
