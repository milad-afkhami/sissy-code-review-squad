#!/usr/bin/env python3
"""Freeze complete initial-review inputs from pinned git objects (Codex only)."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile


def git(repo, *args):
    return subprocess.check_output(
        ["git", "-C", str(repo), "--literal-pathspecs", *args], stderr=subprocess.PIPE,
    ).decode("utf-8", errors="surrogateescape")


def snapshot(repo, source, output_parent):
    original = source.read_bytes()
    context = json.loads(original)
    refs = context["diff_refs"]
    for key in ("base_sha", "head_sha", "start_sha"):
        if not isinstance(refs.get(key), str) or not re.fullmatch(r"[0-9a-f]{40}", refs[key]):
            raise ValueError(f"{key}: expected full commit SHA")
    base, head, start = refs["base_sha"], refs["head_sha"], refs["start_sha"]
    if git(repo, "rev-parse", "HEAD").strip() != head:
        raise ValueError("worktree HEAD does not match the MR head; refetch MR inputs")
    if git(repo, "status", "--porcelain"):
        raise ValueError("worktree has local changes; source must match the pinned HEAD")
    for sha in (base, head, start):
        git(repo, "cat-file", "-e", sha + "^{commit}")

    # Match the canonical fetcher's non-merge-commit path filter, using the
    # recorded target tip instead of a remote branch that may have moved.
    authored = sorted(set(filter(None, git(
        repo, "log", "--no-merges", "--format=", "--name-only", "-z", start + ".." + head,
    ).split("\0"))))
    scope = ["--no-color", "--find-renames", base, head, "--", *authored]
    # With an empty authored list, canonical git diff receives no pathspecs.
    fields = iter(git(repo, "diff", "--name-status", "-z", *scope).split("\0")[:-1])
    changes = []
    for status in fields:
        old_path = new_path = next(fields)
        if status.startswith("R"):
            new_path = next(fields)
        changes.append({
            "old_path": old_path, "new_path": new_path,
            "new_file": status == "A", "deleted_file": status == "D",
            "_status": status,
        })
    supplied = context["changed_files"]
    paths = [item["old_path"] if item.get("deleted_file") or item["new_path"] == "/dev/null"
             else item["new_path"] for item in supplied]
    expected = {item["new_path"] for item in changes}
    if len(paths) != len(set(paths)) or set(paths) != expected:
        raise ValueError("changed file inventory differs from pinned git diff: " + json.dumps({
            "missing": sorted(expected - set(paths)), "unexpected": sorted(set(paths) - expected),
            "duplicate_paths": len(paths) != len(set(paths)),
        }))
    full_diff = git(repo, "diff", "--no-ext-diff", "--no-textconv", "--binary", "--full-index", *scope)
    # Patch order matches name-status order. Hunk lines have a +/-/space prefix,
    # so a bare diff --git marks a new section even with unusual filenames.
    patches = [part for part in re.split(r"(?m)(?=^diff --git )", full_diff) if part]
    if len(patches) != sum(2 if item["_status"] == "T" else 1 for item in changes):
        raise ValueError("git patch sections do not match the changed file inventory")
    cursor = 0
    for item in changes:
        sections = 2 if item.pop("_status") == "T" else 1
        item["diff"] = "".join(patches[cursor:cursor + sections])
        cursor += sections
    context["changed_files"] = changes
    encoded = (json.dumps(context, indent=2) + "\n").encode()
    run_dir = Path(tempfile.mkdtemp(prefix="sissy-codex-", dir=output_parent))
    (run_dir / "source.json").write_bytes(original)
    frozen = run_dir / "context.json"
    frozen.write_bytes(encoded)
    manifest = {
        "base_sha": base, "head_sha": head, "start_sha": start, "changed_paths": sorted(expected),
        "source_sha256": hashlib.sha256(original).hexdigest(),
        "snapshot_sha256": hashlib.sha256(encoded).hexdigest(),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return {"snapshot_path": str(frozen.resolve()), "run_dir": str(run_dir.resolve()),
            "head_sha": head, "file_count": len(changes)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True, help="Complete saved fetcher JSON")
    parser.add_argument("--output-parent", type=Path, default=None)
    args = parser.parse_args()
    try:
        result = snapshot(args.repo, args.input, args.output_parent)
    except (ValueError, KeyError, TypeError, OSError, StopIteration, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Review input incomplete: {error}\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
