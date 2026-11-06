"""Local projection, token-fit and lossless runtime evidence contract tests."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))
import prepare_embedding_projection as projection
from launchlens.evidence_payload import EvidenceError, encode_packet, storage_fields, restore_evidence, metadata_bytes


class EmbeddingProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = projection.load_profile(ROOT)
        cls.tokenizer = projection.load_tokenizer(cls.profile, ROOT)
        cls.packets = projection.load_packets(ROOT)
        cls.rows = [projection.project(p, cls.profile, cls.tokenizer) for p in cls.packets]
        cls.by_unit = {r["unit_id"]: r for r in cls.rows}

    def test_all_45_ids_and_complete_evidence_preserved(self):
        self.assertEqual([r["chunk_id"] for r in self.rows], [p["chunk_id"] for p in self.packets])
        for row, original in zip(self.rows, self.packets):
            self.assertEqual(encode_packet(row["evidence_payload"]), encode_packet(original))
            self.assertEqual(row["evidence_sha256"], storage_fields(original)["evidence_sha256"])
            self.assertEqual(row["authority"], original["authority"])

    def test_original_nutrition_claim_is_not_paraphrased(self):
        row = self.by_unit["PROD-008"]
        self.assertEqual(row["embedding_text"], "Product: Coca-Cola Cherry Float\nDocument role: Public product facts\nThe U.S. original-variant label lists 150 calories and 42 g total sugars per 12 fl oz can.")
        self.assertNotIn("Mandatory qualification", row["embedding_text"])
        self.assertNotIn("https://", row["embedding_text"])
        self.assertIn("Mandatory qualification", row["evidence_payload"]["text"])
        self.assertIn("Preserve market, variant and serving size.", row["evidence_payload"]["text"])

    def test_canada_qualification_stays_in_focused_and_full_text(self):
        row = self.by_unit["PROD-011"]
        self.assertIn("This is not an isolated Canadian Cherry Float date.", row["embedding_text"])
        self.assertIn("March 2026 for Cherry Float", row["evidence_payload"]["text"])
        self.assertEqual(row["evidence_payload"]["page_numbers"], [1, 2, 3])

    def test_req007_does_not_become_real_product_fact(self):
        row = self.by_unit["REQ-007"]
        self.assertIn("Document role: Synthetic product intent", row["embedding_text"])
        self.assertIn("the system must withhold the claim", row["embedding_text"])
        self.assertIn("both the fictional Launch Calendar and Readiness Tracker", row["embedding_text"])
        self.assertEqual(row["evidence_payload"]["authority"], "synthetic_product_intent")

    def test_passage_and_special_tokens_are_counted_without_truncation(self):
        text = self.rows[0]["embedding_text"]
        self.assertEqual(projection.passage_tokens(self.tokenizer, text), len(self.tokenizer.encode("passage: " + text, add_special_tokens=True).ids))
        self.assertIsNone(self.tokenizer.truncation)
        self.assertIsNone(self.tokenizer.padding)
        self.assertGreater(projection.passage_tokens(self.tokenizer, "evidence " * 2000), 507)
        self.assertFalse(text.startswith("passage:"))

    def test_all_focused_inputs_fit_local_limit(self):
        self.assertEqual(len(self.rows), 45)
        self.assertTrue(all(r["local_token_fit"]["passage_tokens"] <= 507 for r in self.rows))
        self.assertTrue(all(not r["local_token_fit"]["truncated"] for r in self.rows))
        self.assertLess(sum(r["local_token_fit"]["passage_tokens"] for r in self.rows), sum(r["local_token_fit"]["before_packet_tokens"] for r in self.rows))

    def test_oversized_search_text_rejected_without_cutting_it(self):
        packet = copy.deepcopy(self.packets[0])
        packet["primary_text"] += " evidence" * 2000
        with self.assertRaisesRegex(projection.chunks.prep.PreparationError, "token budget"):
            projection.project(packet, self.profile, self.tokenizer)
        self.assertTrue(packet["primary_text"].endswith(" evidence" * 2000))

    def test_flat_transport_fields_and_full_roundtrip_for_every_packet(self):
        for packet in self.packets:
            fields = storage_fields(packet)
            self.assertTrue(all(isinstance(v, str) for v in fields.values()))
            self.assertNotIn("embedding_text", fields)
            self.assertLessEqual(metadata_bytes(fields), 40000)
            wire = json.loads(json.dumps(fields))
            actual = restore_evidence(wire, expected_chunk_id=packet["chunk_id"], expected_authority=packet["authority"])
            self.assertEqual(encode_packet(actual), encode_packet(packet))

    def test_runtime_decoder_needs_no_files(self):
        packet = self.by_unit["PROD-011"]["evidence_payload"]
        fields = json.loads(json.dumps(storage_fields(packet)))
        with patch("builtins.open", side_effect=AssertionError("Unexpected runtime file access")), patch.object(Path, "read_bytes", side_effect=AssertionError("Unexpected runtime file access")):
            actual = restore_evidence(fields, expected_chunk_id=packet["chunk_id"], expected_authority="public_product_facts")
        self.assertEqual(actual, packet)

    def test_missing_evidence_fails_closed(self):
        packet = self.packets[0]
        fields = storage_fields(packet)
        del fields["evidence_json"]
        with self.assertRaises(EvidenceError):
            restore_evidence(fields, expected_chunk_id=packet["chunk_id"], expected_authority=packet["authority"])

    def test_corrupted_evidence_fails_closed(self):
        packet = self.packets[0]
        fields = storage_fields(packet)
        fields["evidence_json"] += " "
        with self.assertRaisesRegex(EvidenceError, "digest"):
            restore_evidence(fields, expected_chunk_id=packet["chunk_id"], expected_authority=packet["authority"])

    def test_wrong_hit_id_rejected(self):
        packet = self.packets[0]
        with self.assertRaisesRegex(EvidenceError, "hit ID"):
            restore_evidence(storage_fields(packet), expected_chunk_id="unrelated-hit", expected_authority=packet["authority"])

    def test_wrong_authority_rejected(self):
        packet = self.by_unit["REQ-007"]["evidence_payload"]
        with self.assertRaisesRegex(EvidenceError, "authority"):
            restore_evidence(storage_fields(packet), expected_chunk_id=packet["chunk_id"], expected_authority="public_product_facts")

    def test_metadata_cannot_promote_pending_chunk_to_accepted(self):
        packet = self.packets[0]
        fields = storage_fields(packet)
        fields["chunk_preparation_status"] = "OWNER_ACCEPTED"
        with self.assertRaisesRegex(EvidenceError, "disagree"):
            restore_evidence(fields, expected_chunk_id=packet["chunk_id"], expected_authority=packet["authority"])

    def test_missing_or_false_provenance_rejected(self):
        packet = self.packets[0]
        fields = storage_fields(packet)
        fields["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(EvidenceError, "disagree"):
            restore_evidence(fields, expected_chunk_id=packet["chunk_id"], expected_authority=packet["authority"])

    def test_storage_budget_rejects_oversized_payload(self):
        packet = copy.deepcopy(self.packets[0])
        packet["text"] += "x" * 40000
        with self.assertRaisesRegex(projection.chunks.prep.PreparationError, "storage budget"):
            projection.project(packet, self.profile, self.tokenizer)

    def test_modified_projection_or_evidence_rejected(self):
        for field in ["embedding_text", "authority", "projection_status"]:
            rows = copy.deepcopy(self.rows)
            rows[0][field] = "altered"
            with self.assertRaises(projection.chunks.prep.PreparationError):
                projection.validate_projection(rows, self.packets, self.profile, self.tokenizer)

    def test_missing_projection_row_rejected(self):
        with self.assertRaises(projection.chunks.prep.PreparationError):
            projection.validate_projection(self.rows[:-1], self.packets, self.profile, self.tokenizer)

    def test_projection_does_not_self_approve_source_chunks(self):
        self.assertTrue(all(r["projection_status"] == "PREPARED_PENDING_OWNER_ACCEPTANCE" for r in self.rows))
        self.assertTrue(all(r["evidence_payload"]["chunk_status"] == "PREPARED_PENDING_OWNER_ACCEPTANCE" for r in self.rows))

    def test_missing_tokenizer_has_explicit_provisioning_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(projection.chunks.prep.PreparationError, "Missing/unsafe input"):
                projection.load_tokenizer(self.profile, Path(folder))

    def test_projection_has_no_network_side_effect(self):
        with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("Unexpected network call")):
            outputs = projection.prepare(ROOT)
        self.assertIn("audit.html", outputs)
        self.assertEqual(json.loads(outputs["summary.json"])["external_embedding_calls"], 0)

    def test_regeneration_has_identical_outputs(self):
        first = projection.prepare(ROOT)
        second = projection.prepare(ROOT)
        self.assertEqual(first, second)
        summary = json.loads(first["summary.json"])
        self.assertEqual(summary["after_over_limit"], 0)
        self.assertEqual(summary["evidence_round_trips"], 45)

    def test_audit_has_all_records_and_safe_text_data(self):
        audit = projection.render_audit(self.rows, ROOT).decode()
        self.assertIn("Choose a passage to audit", audit)
        self.assertIn("PROD-008", audit)
        self.assertIn("REQ-007", audit)
        self.assertNotIn("__AUDIT_DATA__", audit)
        self.assertNotIn("fetch(", audit)
        self.assertNotIn("https://cdn", audit)


if __name__ == "__main__":
    unittest.main()
