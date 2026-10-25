#!/usr/bin/env python3
"""Tests for classify_discussions.assemble — disagreement payload enrichment."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), "classify_discussions.py")


class ReplyIdentityTests(unittest.TestCase):
    def prepare(self, replies, developer_author=None):
        original = {"author": {"username": "reviewer"}, "body": "Original concern",
                    "system": False, "resolvable": True, "resolved": False}
        notes = [original] + [dict(system=False, **n) for n in replies]
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "page.json")
            with open(source, "w") as file:
                json.dump([{"id": "d1", "individual_note": False, "notes": notes}], file)
            command = [sys.executable, SCRIPT, "prep", source, "--out-dir", directory]
            if developer_author:
                command += ["--developer-author", developer_author]
            completed = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(0, completed.returncode, completed.stderr)
            result = completed.stdout
            with open(os.path.join(directory, "filtered.json")) as file:
                filtered = json.load(file)
        return json.loads(result), filtered

    def test_reviewer_clarification_is_untouched(self):
        result, _ = self.prepare([{"author": {"username": "reviewer"}, "body": "Clarification"}])
        self.assertEqual(1, result["untouched_count"])
        self.assertEqual([], result["worksheet"])

    def test_police_reply_does_not_reprocess_old_developer_action(self):
        result, filtered = self.prepare([
            {"author": {"username": "developer"}, "body": "Fixed"},
            {"author": {"username": "reviewer"}, "body": "> SubAgent: 👮 Police Sissy (Follow-Up Review)\nStill missing"},
        ])
        self.assertEqual(1, result["untouched_count"])
        self.assertEqual(3, len(filtered[0]["notes"]))

    def test_new_developer_reply_wins_and_full_context_is_preserved(self):
        result, filtered = self.prepare([
            {"author": "developer", "body": "Intentional"},
            {"author": "reviewer", "body": "Please fix the second consumer"},
            {"author": "developer", "body": "Fixed both consumers"},
        ])
        self.assertEqual(0, result["untouched_count"])
        self.assertEqual([{"author": "developer", "body": "Fixed both consumers"}],
                         result["worksheet"][0]["replies"])
        self.assertEqual(4, len(filtered[0]["notes"]))

    def test_bot_and_other_squad_account_are_not_developer_replies(self):
        for author, body in [
            ({"username": "ci", "bot": True}, "Pipeline succeeded"),
            ({"username": "automation"}, "> SubAgent: 👮 Police Sissy (Follow-Up Review)\nNeeds work"),
        ]:
            with self.subTest(author=author):
                result, _ = self.prepare([{"author": author, "body": body}])
                self.assertEqual(1, result["untouched_count"])

    def test_mr_author_can_reply_using_the_same_account_as_sissy(self):
        notes = [{"author": "reviewer", "body": "Fixed and tested"}]
        result, _ = self.prepare(notes, developer_author="reviewer")
        self.assertEqual(1, result["to_classify_count"])
        notes += [{"author": "reviewer", "body": "> SubAgent: 👮 Police Sissy (Follow-Up Review)\nNeeds work"}]
        result, _ = self.prepare(notes, developer_author="reviewer")
        self.assertEqual(1, result["untouched_count"])
        notes += [{"author": "reviewer", "body": "Fixed the remaining case"}]
        result, _ = self.prepare(notes, developer_author="reviewer")
        self.assertEqual([{"author": "reviewer", "body": "Fixed the remaining case"}],
                         result["worksheet"][0]["replies"])

    def test_assemble_saves_the_same_complete_result_it_prints(self):
        with tempfile.TemporaryDirectory() as directory:
            body = "## Test Checklist\n" + "- [ ] Preserve this case 🧪\n" * 180
            filtered = [{"discussion_id": "d1", "new_path": None, "new_line": None,
                         "notes": [{"author": "reviewer", "body": body},
                                   {"author": "developer", "body": "Done"}], "has_reply": True}]
            with open(os.path.join(directory, "filtered.json"), "w") as file:
                json.dump(filtered, file)
            classification = os.path.join(directory, "classification.json")
            with open(classification, "w") as file:
                json.dump({"d1": "addressed"}, file)
            output = subprocess.check_output([sys.executable, SCRIPT, "assemble", "--dir", directory,
                                              "--classification", classification], text=True)
            artifact = os.path.join(directory, "result.json")
            self.assertTrue(os.path.isfile(artifact), "complete classifier artifact was not saved")
            with open(artifact) as file:
                saved = json.load(file)
            self.assertEqual(json.loads(output), saved)
            self.assertEqual(body, saved["addressed"][0]["notes"][0]["body"])


def _run_assemble(filtered, classification):
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "filtered.json"), "w") as fh:
            json.dump(filtered, fh)
        cls_path = os.path.join(d, "classification.json")
        with open(cls_path, "w") as fh:
            json.dump(classification, fh)
        out = subprocess.check_output(
            [sys.executable, SCRIPT, "assemble", "--dir", d, "--classification", cls_path],
            text=True,
        )
        return json.loads(out)


def test_disagreement_carries_notes_and_position():
    filtered = [
        {"discussion_id": "d1", "new_path": "src/a.css", "new_line": 12,
         "notes": [{"author": "milad", "body": "This causes reflow."},
                   {"author": "dev", "body": "Intentional; scrollbar breaks otherwise."}],
         "has_reply": True},
    ]
    classification = {"d1": {"bucket": "disagreement", "reason": "declined; scrollbar"}}
    result = _run_assemble(filtered, classification)

    assert result["disagreement_count"] == 1
    dis = result["disagreements"][0]
    assert dis["discussion_id"] == "d1"
    assert dis["new_path"] == "src/a.css"
    assert dis["new_line"] == 12                      # NEW: position preserved
    assert dis["reason"] == "declined; scrollbar"     # existing field kept
    assert dis["notes"] == filtered[0]["notes"]        # NEW: full notes preserved


def test_counts_still_reconcile():
    filtered = [
        {"discussion_id": "a1", "new_path": "src/x.tsx", "new_line": 3,
         "notes": [{"author": "milad", "body": "n+1"}, {"author": "dev", "body": "fixed"}],
         "has_reply": True},
        {"discussion_id": "d1", "new_path": "src/y.tsx", "new_line": 9,
         "notes": [{"author": "milad", "body": "unsafe"}, {"author": "dev", "body": "no, it's fine"}],
         "has_reply": True},
        {"discussion_id": "u1", "new_path": "src/z.tsx", "new_line": 1,
         "notes": [{"author": "milad", "body": "typo"}], "has_reply": False},
    ]
    classification = {"a1": {"bucket": "addressed", "reason": ""},
                      "d1": {"bucket": "disagreement", "reason": "disputes premise"}}
    result = _run_assemble(filtered, classification)

    assert result["addressed_count"] == 1
    assert result["disagreement_count"] == 1
    assert result["untouched_count"] == 1
    assert (result["addressed_count"] + result["disagreement_count"]
            + result["untouched_count"] == result["total_unresolved"] == 3)


if __name__ == "__main__":
    test_disagreement_carries_notes_and_position()
    test_counts_still_reconcile()
    unittest.main()
