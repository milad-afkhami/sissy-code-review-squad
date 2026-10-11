#!/usr/bin/env python3
"""Exercise the completion gate through its CLI, without a model or GitLab writes."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("validate_review_coverage.py")
SHA = "a" * 40
SCOPE = {
    "head_sha": SHA,
    "changed_files": ["src/read.ts", "src/drawer.tsx"],
    "enabled_agents": ["performance", "qa"],
}


def report(agent):
    return {
        "agent": agent,
        "head_sha": SHA,
        "files": [
            {"path": "src/read.ts", "status": "reviewed", "evidence": "src/read.ts:8 cancellation and retry branches inspected"},
            {"path": "src/drawer.tsx", "status": "reviewed", "evidence": "src/drawer.tsx:12 consumes the shared query and disables Continue"},
        ],
        "checks": {
            "domain_checklist": {"status": "reviewed", "evidence": "src/read.ts:8 cache, cancellation and timeout checks; src/drawer.tsx:12 render subscriptions"},
            "integration_paths": {"status": "reviewed", "evidence": "src/page.tsx:4 -> src/drawer.tsx:12 -> src/read.ts:8"},
            "failure_paths": {"status": "reviewed", "evidence": "src/read.ts:20 rejects interrupted responses; src/drawer.tsx:30 keeps retry available"},
        },
        "candidates": [],
    }


class ReviewCoverageTests(unittest.TestCase):
    def run_gate(self, reports=None, scope=None):
        reports = [report("performance"), report("qa")] if reports is None else reports
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scope_path = root / "scope.json"
            scope_path.write_text(json.dumps(SCOPE if scope is None else scope))
            paths = []
            for index, value in enumerate(reports):
                path = root / f"report-{index}.json"
                path.write_text(json.dumps(value))
                paths.append(str(path))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--scope", str(scope_path), "--reports", *paths],
                capture_output=True, text=True,
            )
        return result.returncode, json.loads(result.stdout)

    def test_complete_zero_finding_review_passes_without_a_comment_quota(self):
        code, result = self.run_gate()
        self.assertEqual(0, code)
        self.assertEqual({"complete": True, "gaps": []}, result)

    def test_missing_enabled_agent_cannot_be_approved(self):
        code, result = self.run_gate([report("performance")])
        self.assertEqual(1, code)
        self.assertIn("missing report: qa", result["gaps"])

    def test_missing_changed_file_is_reported_by_agent_and_path(self):
        qa = report("qa")
        qa["files"].pop()
        code, result = self.run_gate([report("performance"), qa])
        self.assertEqual(1, code)
        self.assertIn("qa: missing file: src/drawer.tsx", result["gaps"])

    def test_stale_report_cannot_satisfy_new_head(self):
        qa = report("qa")
        qa["head_sha"] = "b" * 40
        code, result = self.run_gate([report("performance"), qa])
        self.assertEqual(1, code)
        self.assertIn("qa: report head does not match scope", result["gaps"])

    def test_deleted_files_keep_distinct_old_paths_in_scope(self):
        scope = copy.deepcopy(SCOPE)
        scope["changed_files"] = ["src/removed-a.ts", "src/removed-b.ts"]
        reports = [report("performance"), report("qa")]
        for value in reports:
            for item, path in zip(value["files"], scope["changed_files"]):
                item.update(path=path, evidence=f"Base revision {path}:1 and remaining callers inspected")
        self.assertEqual(0, self.run_gate(reports, scope)[0])
        scope["changed_files"] = ["/dev/null"]
        code, result = self.run_gate(reports, scope)
        self.assertEqual(2, code)
        self.assertIn("scope: use old_path for deleted files, not /dev/null", result["gaps"])

    def test_unreviewed_file_and_unchecked_integration_block_completion(self):
        qa = report("qa")
        qa["files"][0]["status"] = "unreviewed"
        qa["checks"]["integration_paths"]["status"] = "unreviewed"
        code, result = self.run_gate([report("performance"), qa])
        self.assertEqual(1, code)
        self.assertIn("qa: file src/read.ts: unreviewed", result["gaps"])
        self.assertIn("qa: check integration_paths: unreviewed", result["gaps"])

    def test_not_applicable_requires_a_reason_but_does_not_force_irrelevant_work(self):
        qa = report("qa")
        qa["files"][0].update(status="not_applicable", evidence="Generated declarations only; no runtime change")
        self.assertEqual(0, self.run_gate([report("performance"), qa])[0])
        qa["files"][0]["evidence"] = " "
        code, result = self.run_gate([report("performance"), qa])
        self.assertEqual(1, code)
        self.assertIn("qa: file src/read.ts: missing evidence", result["gaps"])

    def test_unresolved_candidate_cannot_disappear_into_approval(self):
        qa = report("qa")
        qa["candidates"] = [{"title": "Stale selection", "disposition": "unresolved", "evidence": "Need to trace the Continue handler after retry"}]
        code, result = self.run_gate([report("performance"), qa])
        self.assertEqual(1, code)
        self.assertIn("qa: unresolved candidate: Stale selection", result["gaps"])
        for disposition in ("posted", "dismissed", "deferred"):
            with self.subTest(disposition=disposition):
                qa["candidates"][0].update(disposition=disposition, evidence="src/drawer.tsx:30 membership is checked synchronously; disposition documented")
                self.assertEqual(0, self.run_gate([report("performance"), qa])[0])

    def test_missing_checks_and_candidate_dispositions_fail_closed(self):
        qa = report("qa")
        del qa["checks"]["failure_paths"]
        qa["candidates"] = [{"title": "Ordering", "disposition": "unknown", "evidence": "src/read.ts:20"}]
        code, result = self.run_gate([report("performance"), qa])
        self.assertEqual(1, code)
        self.assertIn("qa: check failure_paths: missing record", result["gaps"])
        self.assertIn("qa: candidate Ordering: invalid disposition", result["gaps"])

    def test_duplicate_or_disabled_agents_cannot_substitute_for_missing_work(self):
        code, result = self.run_gate([report("qa"), report("qa"), report("seo")])
        self.assertEqual(1, code)
        self.assertIn("duplicate report: qa", result["gaps"])
        self.assertIn("unexpected agent: seo", result["gaps"])
        self.assertIn("missing report: performance", result["gaps"])

    def test_unexpected_and_duplicate_paths_are_not_coverage(self):
        qa = report("qa")
        qa["files"].append(copy.deepcopy(qa["files"][0]))
        qa["files"][1]["path"] = "src/unrelated.ts"
        code, result = self.run_gate([report("performance"), qa])
        self.assertEqual(1, code)
        self.assertIn("qa: duplicate file: src/read.ts", result["gaps"])
        self.assertIn("qa: unexpected file: src/unrelated.ts", result["gaps"])
        self.assertIn("qa: missing file: src/drawer.tsx", result["gaps"])

    def test_malformed_scope_and_report_return_machine_readable_failure(self):
        for scope, reports in (({}, []), (SCOPE, [None]), (SCOPE, [{"agent": "qa", "files": None}])):
            with self.subTest(scope=scope, reports=reports):
                code, result = self.run_gate(reports, scope)
                self.assertNotEqual(0, code)
                self.assertFalse(result["complete"])
                self.assertTrue(result["gaps"])


if __name__ == "__main__":
    unittest.main()
