#!/usr/bin/env python3
"""Deterministic helpers for the MR discussion classifier agent.

The agent (Sonnet) is responsible for exactly ONE judgment: for each thread
that has a developer reply, is it `addressed` or `disagreement`? Everything
else — fetching-format handling, the unresolved filter, the `untouched` split,
note-body extraction, and final assembly — is mechanical and lives here so it
cannot be gotten wrong by a model under load.

Two subcommands:

  prep     Read the fetched discussions, filter to unresolved threads, split
           off `untouched` (exactly one non-system note) deterministically, and
           print a compact worksheet of the has-reply threads for the model to
           judge. Persists the full filtered data to <out-dir>/filtered.json.

  assemble Read the model's classification ({discussion_id: {bucket, reason?}})
           plus <out-dir>/filtered.json and print the final contract JSON
           (addressed[], disagreements[], and reconciled counts).

Design notes
------------
* `untouched` is decided here, never by the model. A thread with a developer
  reply therefore cannot be misfiled as `untouched` — that was the dominant
  bug this rewrite eliminates.
* Note bodies for `addressed` threads are extracted here by id, so the model
  never transcribes text into its output (removes output-size pressure and
  transcription hallucination).
* The counts always reconcile by construction:
  addressed + disagreement + untouched == total_unresolved.
"""

import argparse
import json
import os
import sys


# --- fetched-payload loading -------------------------------------------------

def _coerce_to_list(payload):
    """A single fetched page may arrive as a bare array, as {"items": [...]}
    (how the GitLab MCP wrapper persists large output), or wrapped in
    {"data": [...]}. Normalize any of these to a list of discussion objects."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "data", "discussions"):
            if isinstance(payload.get(key), list):
                return payload[key]
    raise ValueError(
        "Unrecognized discussions payload shape: expected a JSON array or an "
        "object with an 'items'/'data'/'discussions' array"
    )


def load_discussions(paths):
    """Load and concatenate discussions from one or more page files."""
    discussions = []
    for path in paths:
        with open(path, "r", encoding="utf-8") as fh:
            discussions.extend(_coerce_to_list(json.load(fh)))
    return discussions


# --- field helpers -----------------------------------------------------------

def _author_name(note):
    author = note.get("author")
    if isinstance(author, dict):
        return author.get("username") or author.get("name") or "unknown"
    if isinstance(author, str):
        return author
    return "unknown"


def _non_system_notes(discussion):
    return [n for n in discussion.get("notes", []) if not n.get("system", False)]


def _is_unresolved(discussion):
    """The classifier's filter, verbatim: a resolvable, unresolved, non-system,
    threaded (not individual) discussion."""
    if discussion.get("individual_note", False):
        return False
    notes = discussion.get("notes") or []
    if not notes:
        return False
    first = notes[0]
    return (
        first.get("resolvable", False) is True
        and first.get("resolved", True) is False
        and first.get("system", True) is False
    )


def _position(discussion):
    notes = discussion.get("notes") or []
    pos = (notes[0].get("position") if notes else None) or {}
    return pos.get("new_path"), pos.get("new_line")


def _truncate(text, limit):
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + " …[truncated]"


# --- prep --------------------------------------------------------------------

def cmd_prep(args):
    discussions = load_discussions(args.inputs)

    unresolved = [d for d in discussions if _is_unresolved(d)]

    filtered = []          # persisted: everything downstream might need, by id
    worksheet = []         # printed: only what the model needs to judge
    untouched_count = 0

    for d in unresolved:
        ns_notes = _non_system_notes(d)
        new_path, new_line = _position(d)
        discussion_id = d.get("id")

        record = {
            "discussion_id": discussion_id,
            "new_path": new_path,
            "new_line": new_line,
            "notes": [{"author": _author_name(n), "body": n.get("body", "")}
                      for n in ns_notes],
            "has_reply": len(ns_notes) >= 2,
        }
        filtered.append(record)

        if len(ns_notes) < 2:
            # Only the original review comment exists → untouched, decided here.
            untouched_count += 1
            continue

        worksheet.append({
            "discussion_id": discussion_id,
            "new_path": new_path,
            "concern": _truncate(ns_notes[0].get("body", ""), args.concern_chars),
            "replies": [{"author": _author_name(n), "body": n.get("body", "")}
                        for n in ns_notes[1:]],
        })

    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "filtered.json"), "w", encoding="utf-8") as fh:
        json.dump(filtered, fh, ensure_ascii=False)

    print(json.dumps({
        "total_unresolved": len(unresolved),
        "untouched_count": untouched_count,
        "to_classify_count": len(worksheet),
        "worksheet": worksheet,
    }, ensure_ascii=False, indent=2))
    return 0


# --- assemble ----------------------------------------------------------------

_VALID_BUCKETS = {"addressed", "disagreement"}


def _normalize_classification(raw):
    """Accept either {id: "addressed"} or {id: {"bucket": ..., "reason": ...}}."""
    norm = {}
    for discussion_id, value in raw.items():
        if isinstance(value, str):
            norm[discussion_id] = {"bucket": value, "reason": ""}
        elif isinstance(value, dict):
            norm[discussion_id] = {
                "bucket": value.get("bucket", ""),
                "reason": value.get("reason", "") or "",
            }
        else:
            norm[discussion_id] = {"bucket": "", "reason": ""}
    return norm


def cmd_assemble(args):
    with open(os.path.join(args.dir, "filtered.json"), "r", encoding="utf-8") as fh:
        filtered = json.load(fh)
    with open(args.classification, "r", encoding="utf-8") as fh:
        classification = _normalize_classification(json.load(fh))

    total_unresolved = len(filtered)
    untouched_count = sum(1 for r in filtered if not r["has_reply"])

    addressed = []
    disagreements = []
    warnings = []

    for record in filtered:
        if not record["has_reply"]:
            continue  # untouched — decided in prep, never sent to the model

        discussion_id = record["discussion_id"]
        entry = classification.get(discussion_id)
        bucket = entry["bucket"] if entry else ""

        if bucket not in _VALID_BUCKETS:
            # Missing or invalid model output for a replied thread. Default to
            # `addressed` (benefit of the doubt) so it gets verified downstream
            # rather than silently dropped — and record it loudly.
            warnings.append({
                "discussion_id": discussion_id,
                "issue": f"missing/invalid bucket {bucket!r}; defaulted to addressed",
            })
            bucket = "addressed"

        if bucket == "addressed":
            addressed.append({
                "discussion_id": discussion_id,
                "new_path": record["new_path"],
                "new_line": record["new_line"],
                "notes": record["notes"],
            })
        else:  # disagreement
            disagreements.append({
                "discussion_id": discussion_id,
                "new_path": record["new_path"],
                "new_line": record["new_line"],
                "notes": record["notes"],
                "reason": (entry["reason"] if entry else "") or "",
            })

    result = {
        "addressed": addressed,
        "disagreements": disagreements,
        "total_unresolved": total_unresolved,
        "addressed_count": len(addressed),
        "disagreement_count": len(disagreements),
        "untouched_count": untouched_count,
    }
    if warnings:
        result["warnings"] = warnings

    # Reconciliation invariant — must always hold by construction.
    assert (result["addressed_count"] + result["disagreement_count"]
            + result["untouched_count"] == total_unresolved), \
        "count reconciliation failed"

    print(json.dumps(result, ensure_ascii=False))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_prep = sub.add_parser("prep", help="filter, split untouched, emit worksheet")
    p_prep.add_argument("inputs", nargs="+", help="one or more discussions JSON files")
    p_prep.add_argument("--out-dir", required=True, help="dir to persist filtered.json")
    p_prep.add_argument("--concern-chars", type=int, default=800,
                        help="truncate the concern text in the worksheet to N chars")
    p_prep.set_defaults(func=cmd_prep)

    p_asm = sub.add_parser("assemble", help="build final contract JSON")
    p_asm.add_argument("--dir", required=True, help="dir holding filtered.json")
    p_asm.add_argument("--classification", required=True,
                       help="model classification JSON: {id: {bucket, reason?}}")
    p_asm.set_defaults(func=cmd_assemble)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
