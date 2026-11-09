"""Inventory gates and source/date authority using safe operational fixtures."""
from copy import deepcopy
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from test_launch_checks import context
from launchlens.inventory import (InventoryError, load_display, market_row, fetch_inventory,
    launch_window, read_notion_key, request_for_market)
from launchlens.gtm_registry import HarnessError


class Reader:
    def __init__(self): self.calls = []
    def get_launch_context(self, market):
        self.calls.append(market)
        return context(market)


class InventoryTests(unittest.TestCase):
    def test_real_registry_metadata_and_document_links(self):
        display = load_display()
        self.assertEqual(display["case"]["product_id"], "CC-CHERRY-FLOAT")
        self.assertEqual(len(display["documents"]), 5)
        self.assertEqual([d["app"] for d in display["documents"]].count("Google Drive"), 2)
        self.assertTrue(all(d["url"].startswith(("https://drive.google.com/file/d/", "https://www.notion.so/")) for d in display["documents"]))

    def test_dates_and_decisions_come_from_source_records(self):
        reader = Reader(); snapshot = fetch_inventory(load_display(), reader)
        self.assertEqual(len(reader.calls), 3)
        self.assertEqual(snapshot["status"], "ok")
        self.assertEqual(launch_window(snapshot), ("2026-12-14", "2027-01-18"))
        self.assertEqual([snapshot["markets"][m]["decision"]["decision"] for m in ("US", "UK", "IN")], ["Proceed", "Clarify", "Hold"])
        changed = context("US")
        for row in changed["readiness"]:
            if row["values"]["Readiness Area"] == "Marketing communication authorization":
                row["values"].update(Status="Pending", **{"Blocker / Missing Information": "SIMULATION pending"})
        self.assertEqual(market_row(changed, "US")["decision"]["decision"], "Hold")

    def test_changed_dates_are_read_not_hardcoded(self):
        changed = context("US")
        launch = changed["calendar"][-1]["values"]
        launch.update({"Date": "2026-12-21", "Planned Launch Date": "2026-12-21"})
        row = market_row(changed, "US")
        self.assertEqual(row["planned_launch_date"], "2026-12-21")
        self.assertEqual(row["decision"]["decision"], "Clarify")
        self.assertFalse(row["decision"]["promotional_draft_allowed"])

    def test_unavailable_missing_duplicate_and_wrong_scope_never_show_ready(self):
        cases = [{"status": "error"}, context()]
        cases[1]["calendar"].append(deepcopy(cases[1]["calendar"][-1]))
        wrong = context(); wrong["product_id"] = "NIKE"; cases.append(wrong)
        bad_date = context(); bad_date["calendar"][-1]["values"]["Date"] = "2026-12-15"; cases.append(bad_date)
        for value in cases:
            with self.subTest(value=value.get("status")):
                row = market_row(value, "US")
                self.assertEqual(row["source_status"], "unavailable")
                self.assertIsNone(row["planned_launch_date"])
                self.assertIsNone(row["decision"])

    def test_failed_read_is_not_a_csv_or_historical_snapshot_fallback(self):
        class Failed(Reader):
            def get_launch_context(self, market): return {"status": "error"}
        snapshot = fetch_inventory(load_display(), Failed())
        self.assertIsNone(launch_window(snapshot))
        self.assertEqual(snapshot["status"], "unavailable")
        self.assertTrue(all(r["label"] == "Readiness unavailable" for r in snapshot["markets"].values()))

    def test_brief_selection_validates_scope_and_has_no_reads(self):
        display = load_display(); reader = Reader(); snapshot = fetch_inventory(display, reader)
        before = list(reader.calls)
        request = request_for_market(display, snapshot, "UK")
        self.assertEqual(request["evaluation_date"], "2027-01-04")
        self.assertEqual(reader.calls, before)
        with self.assertRaises(InventoryError): request_for_market(display, snapshot, "NIKE")
        with self.assertRaises(HarnessError): request_for_market(display, snapshot, "US", "2026-02-30")

    def test_credentials_private_unambiguous_and_errors_do_not_echo_keys(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            path = Path(folder) / ".env"
            path.write_text("NOTION_API_KEY=safe-test-value\n"); path.chmod(0o600)
            self.assertEqual(read_notion_key(path), "safe-test-value")
            path.chmod(0o644)
            with self.assertRaises(InventoryError) as error: read_notion_key(path)
            self.assertNotIn("safe-test-value", str(error.exception))
            path.chmod(0o600); path.write_text("NOTION_API_KEY=first\nNOTION_API_KEY=second\n")
            with self.assertRaises(InventoryError): read_notion_key(path)

    def test_current_evaluation_cannot_borrow_future_snapshot_permission(self):
        row = market_row(context(), "US")
        from launchlens.launch_checks import evaluate_launch
        result = evaluate_launch(row["context"], "2026-11-08")
        self.assertEqual(result["decision"], "Clarify")
        self.assertFalse(result["promotional_draft_allowed"])


if __name__ == "__main__": unittest.main()
