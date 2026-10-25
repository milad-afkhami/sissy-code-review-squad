"""Exercise the Codex follow-up artifact boundary without network or MR writes."""
import copy
import json
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / ".codex-plugin/followup.py"


class FollowupArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.classify = self.root / "classify"
        self.classify.mkdir()
        self.body = "## Test Checklist\n" + "- [ ] Keep complete Unicode evidence 🧪\n" * 150
        self.records = [
            {"discussion_id": "qa", "new_path": None, "new_line": None, "has_reply": True,
             "notes": [{"author": "reviewer", "body": self.body}, {"author": "dev", "body": "Done"}]},
            {"discussion_id": "issue", "new_path": "src/a.ts", "new_line": 4, "has_reply": True,
             "notes": [{"author": "reviewer", "body": "Original concern"}, {"author": "dev", "body": "Intentional"}]},
        ]
        self.write(self.classify / "filtered.json", self.records)
        self.write(self.classify / "classification.json", {"qa": "addressed", "issue": "disagreement"})
        # A model-shortened return must never become the evaluator's source.
        self.write(self.classify / "result.json", {"addressed": [{"discussion_id": "qa", "notes": []}]})
        self.architecture = self.root / "architecture.md"
        self.architecture.write_text("Complete architecture context\n")

    def write(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False))

    def call(self, *args):
        return subprocess.run([sys.executable, str(HELPER), *map(str, args)],
                              text=True, capture_output=True)

    def prepare(self):
        result = self.call("prepare", "--classification-dir", self.classify,
                           "--project-root", self.root, "--architecture", self.architecture)
        self.assertEqual(0, result.returncode, result.stderr)
        value = json.loads(result.stdout)
        self.addCleanup(shutil.rmtree, value["run_dir"])
        return value

    def verdicts(self):
        return [{"discussion_id": "qa", "verdict": "resolved", "explanation": "Accepted QA report on trust", "confidence": "medium"},
                {"discussion_id": "issue", "verdict": "unsure", "reply": "Product decision remains open", "confidence": "medium"}]

    def test_complete_notes_and_kinds_reach_separate_buckets(self):
        result = self.prepare()
        manifest = json.loads(Path(result["manifest_path"]).read_text())
        buckets = [json.loads(Path(b["path"]).read_text()) for b in manifest["buckets"]]
        general = next(b for b in buckets if b["file_path"] == "General comment (no file)")
        specific = next(b for b in buckets if b["file_path"] == "src/a.ts")
        self.assertEqual(self.body, general["threads"][0]["notes"][0]["body"])
        self.assertEqual("addressed", general["threads"][0]["kind"])
        self.assertEqual("disagreement", specific["threads"][0]["kind"])
        self.assertEqual("Complete architecture context\n", specific["architecture_context"])
        self.assertEqual(str(self.root), specific["project_root"])

    def test_valid_complete_verdicts_are_retained_without_rewriting(self):
        result = self.prepare()
        path = self.root / "verdicts.json"
        self.write(path, self.verdicts())
        checked = self.call("check", "--manifest", result["manifest_path"], "--verdicts", path)
        self.assertEqual(0, checked.returncode, checked.stderr)
        validated = json.loads(checked.stdout)
        self.assertEqual(self.verdicts(), json.loads(Path(validated["verdicts_path"]).read_text()))

    def test_missing_duplicate_foreign_and_wrong_kind_verdicts_are_rejected(self):
        result = self.prepare()
        original = self.verdicts()
        wrong = copy.deepcopy(original)
        wrong[1] = {"discussion_id": "issue", "verdict": "resolved", "explanation": "Wrong kind", "confidence": "high"}
        for label, values in [("missing", original[:1]), ("duplicate", original + original[:1]),
                              ("foreign", original + [{**original[0], "discussion_id": "other"}]),
                              ("wrong kind", wrong),
                              ("missing reply", [original[0], {k: v for k, v in original[1].items() if k != "reply"}])]:
            with self.subTest(label=label):
                path = self.root / "bad.json"
                self.write(path, values)
                checked = self.call("check", "--manifest", result["manifest_path"], "--verdicts", path)
                self.assertNotEqual(0, checked.returncode)

    def test_edited_bucket_is_rejected_before_any_verdict_can_be_used(self):
        result = self.prepare()
        manifest = json.loads(Path(result["manifest_path"]).read_text())
        bucket_path = Path(manifest["buckets"][0]["path"])
        bucket = json.loads(bucket_path.read_text())
        bucket["threads"][0]["notes"][0]["body"] = "## Test Checklist"
        self.write(bucket_path, bucket)
        verdicts = self.root / "verdicts.json"
        self.write(verdicts, self.verdicts())
        checked = self.call("check", "--manifest", result["manifest_path"], "--verdicts", verdicts)
        self.assertNotEqual(0, checked.returncode)
        self.assertIn("changed", checked.stderr)

    def test_runs_are_isolated_and_zero_selected_threads_are_valid(self):
        first = self.prepare()
        second = self.prepare()
        self.assertNotEqual(first["manifest_path"], second["manifest_path"])
        self.write(self.classify / "filtered.json", [])
        self.write(self.classify / "classification.json", {})
        result = self.prepare()
        manifest = json.loads(Path(result["manifest_path"]).read_text())
        self.assertEqual([], manifest["buckets"])


if __name__ == "__main__":
    unittest.main()
