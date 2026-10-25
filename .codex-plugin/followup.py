#!/usr/bin/env python3
"""Preserve complete follow-up inputs and validate verdicts before GitLab writes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def threads(result):
    selected = {}
    for field, kind in (("addressed", "addressed"), ("disagreements", "disagreement")):
        records = result[field]
        count = result["addressed_count" if kind == "addressed" else "disagreement_count"]
        if count != len(records):
            raise ValueError("classification count mismatch")
        for thread in records:
            identity = thread["discussion_id"]
            if not isinstance(identity, str) or not identity or identity in selected:
                raise ValueError("invalid or duplicate discussion ID")
            selected[identity] = dict(thread, kind=kind)
    if len(selected) + result["untouched_count"] != result["total_unresolved"]:
        raise ValueError("classification total mismatch")
    return selected


def prepare(args):
    directory = Path(args.classification_dir).resolve()
    # Reassemble from deterministic saved originals/decisions, never the model's
    # shortened final message or a previously edited result.json.
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/classify_discussions.py"), "assemble",
         "--dir", str(directory), "--classification", str(directory / "classification.json")],
        capture_output=True, text=True, check=True,
    )
    classified = json.loads(completed.stdout)
    selected = threads(classified)
    architecture = Path(args.architecture).read_text(encoding="utf-8")
    project_root = Path(args.project_root).resolve(strict=True)
    run = Path(tempfile.mkdtemp(prefix="sissy-followup-"))
    classification = run / "threads.json"
    write(classification, classified)
    grouped = {}
    for thread in selected.values():
        grouped.setdefault(thread["new_path"], []).append(thread)
    buckets = []
    for index, (path, records) in enumerate(grouped.items(), 1):
        bucket = run / f"bucket-{index:04d}.json"
        write(bucket, {"project_root": str(project_root),
                       "file_path": path if path is not None else "General comment (no file)",
                       "threads": records, "architecture_context": architecture})
        buckets.append({"path": str(bucket), "sha256": digest(bucket),
                        "discussion_ids": [t["discussion_id"] for t in records]})
    manifest = {"classification_path": str(classification), "classification_sha256": digest(classification),
                "buckets": buckets}
    manifest_path = run / "manifest.json"
    write(manifest_path, manifest)
    return {"manifest_path": str(manifest_path), "run_dir": str(run), "buckets": buckets,
            "counts": {k: v for k, v in classified.items() if k.endswith("count") or k == "total_unresolved"},
            "warnings": classified.get("warnings", [])}


def check(args):
    manifest_path = Path(args.manifest).resolve()
    manifest = read(manifest_path)
    classification = Path(manifest["classification_path"])
    if digest(classification) != manifest["classification_sha256"]:
        raise ValueError("classification artifact changed")
    selected = threads(read(classification))
    covered = []
    for bucket in manifest["buckets"]:
        if digest(bucket["path"]) != bucket["sha256"]:
            raise ValueError("evaluator bucket changed")
        data = read(bucket["path"])
        for thread in data["threads"]:
            if selected.get(thread["discussion_id"]) != thread:
                raise ValueError("evaluator thread differs from complete original")
            covered.append(thread["discussion_id"])
    if len(covered) != len(set(covered)) or set(covered) != set(selected):
        raise ValueError("evaluator bucket coverage mismatch")
    verdicts = read(args.verdicts)
    if not isinstance(verdicts, list):
        raise ValueError("verdicts must be a flattened JSON array")
    seen = set()
    for verdict in verdicts:
        identity = verdict["discussion_id"]
        if identity not in selected or identity in seen:
            raise ValueError("foreign or duplicate verdict ID")
        seen.add(identity)
        addressed = selected[identity]["kind"] == "addressed"
        allowed = {"resolved", "insufficient"} if addressed else {"conceded", "countered", "unsure"}
        field = "explanation" if addressed else "reply"
        if verdict.get("verdict") not in allowed:
            raise ValueError("verdict does not match thread kind")
        if not isinstance(verdict.get(field), str) or not verdict[field].strip():
            raise ValueError(f"missing {field}")
        if verdict.get("confidence") not in {"high", "medium"}:
            raise ValueError("invalid confidence")
    if seen != set(selected):
        raise ValueError("missing verdicts")
    destination = manifest_path.parent / "validated-verdicts.json"
    write(destination, verdicts)
    return {"verdicts_path": str(destination), "count": len(verdicts)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--classification-dir", required=True)
    prep.add_argument("--project-root", required=True)
    prep.add_argument("--architecture", required=True)
    verify = sub.add_parser("check")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--verdicts", required=True)
    args = parser.parse_args()
    try:
        result = prepare(args) if args.command == "prepare" else check(args)
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"follow-up artifact error: {error}\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
