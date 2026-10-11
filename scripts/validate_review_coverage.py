#!/usr/bin/env python3
"""Fail closed on missing initial-review coverage; never impose a finding quota.

This validates reported coverage, not the truth of a model's source analysis.
The orchestrator must inspect the evidence before selecting a verdict.
"""

import argparse
import json
from pathlib import Path
import re


AGENTS = {
    "accessibility", "security", "performance", "seo", "styling",
    "code-quality", "react", "typescript", "git", "qa",
}
CHECKS = ("domain_checklist", "integration_paths", "failure_paths")


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def unique_strings(value, label):
    if not isinstance(value, list) or not value or not all(nonempty(x) for x in value):
        raise ValueError(f"{label}: expected a nonempty list of strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{label}: duplicate entries")
    return set(value)


def validate(scope, reports):
    if not isinstance(scope, dict):
        raise ValueError("scope: expected an object")
    head = scope.get("head_sha")
    if not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("scope: expected a full head_sha")
    paths = unique_strings(scope.get("changed_files"), "scope changed_files")
    if "/dev/null" in paths:
        raise ValueError("scope: use old_path for deleted files, not /dev/null")
    enabled = unique_strings(scope.get("enabled_agents"), "scope enabled_agents")
    if not enabled <= AGENTS:
        raise ValueError("scope: unknown enabled agent")
    gaps = []
    seen_agents = set()

    def check_record(record, label):
        if not isinstance(record, dict):
            gaps.append(f"{label}: missing record")
            return
        status = record.get("status")
        if status not in ("reviewed", "not_applicable"):
            gaps.append(f"{label}: {status if status == 'unreviewed' else 'invalid status'}")
        if not nonempty(record.get("evidence")):
            gaps.append(f"{label}: missing evidence")

    for report in reports:
        if not isinstance(report, dict) or not nonempty(report.get("agent")):
            gaps.append("report: missing agent")
            continue
        agent = report["agent"]
        if agent not in enabled:
            gaps.append(f"unexpected agent: {agent}")
        if agent in seen_agents:
            gaps.append(f"duplicate report: {agent}")
        seen_agents.add(agent)
        if report.get("head_sha") != head:
            gaps.append(f"{agent}: report head does not match scope")
        files = report.get("files")
        if not isinstance(files, list):
            gaps.append(f"{agent}: files must be a list")
            files = []
        seen_paths = set()
        for item in files:
            if not isinstance(item, dict) or not nonempty(item.get("path")):
                gaps.append(f"{agent}: file missing path")
                continue
            path = item["path"]
            if path not in paths:
                gaps.append(f"{agent}: unexpected file: {path}")
            if path in seen_paths:
                gaps.append(f"{agent}: duplicate file: {path}")
            seen_paths.add(path)
            check_record(item, f"{agent}: file {path}")
        gaps.extend(f"{agent}: missing file: {path}" for path in sorted(paths - seen_paths))
        checks = report.get("checks")
        checks = checks if isinstance(checks, dict) else {}
        for name in CHECKS:
            check_record(checks.get(name), f"{agent}: check {name}")
        candidates = report.get("candidates")
        if not isinstance(candidates, list):
            gaps.append(f"{agent}: candidates must be a list (empty is allowed)")
            continue
        for item in candidates:
            if not isinstance(item, dict) or not nonempty(item.get("title")):
                gaps.append(f"{agent}: candidate missing title")
                continue
            title = item["title"]
            disposition = item.get("disposition")
            if disposition == "unresolved":
                gaps.append(f"{agent}: unresolved candidate: {title}")
            elif disposition not in ("posted", "dismissed", "deferred"):
                gaps.append(f"{agent}: candidate {title}: invalid disposition")
            if not nonempty(item.get("evidence")):
                gaps.append(f"{agent}: candidate {title}: missing evidence")
    gaps.extend(f"missing report: {agent}" for agent in sorted(enabled - seen_agents))
    return gaps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", required=True, type=Path)
    parser.add_argument("--reports", nargs="*", required=True, type=Path)
    args = parser.parse_args()
    try:
        scope = json.loads(args.scope.read_text(encoding="utf-8"))
        reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.reports]
        gaps = validate(scope, reports)
    except (OSError, ValueError) as error:
        print(json.dumps({"complete": False, "gaps": [str(error)]}))
        return 2
    print(json.dumps({"complete": not gaps, "gaps": gaps}))
    return 1 if gaps else 0


if __name__ == "__main__":
    raise SystemExit(main())
