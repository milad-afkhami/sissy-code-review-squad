#!/usr/bin/env python3
"""Tests for classify_discussions.assemble — disagreement payload enrichment."""
import json
import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(__file__), "classify_discussions.py")


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
    print("OK")
