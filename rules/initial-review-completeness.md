# Initial Review Completeness

These instructions apply to initial `sissy-squad` reviews in both runtimes, in
addition to the domain agent and Code Review Standards. They do not change the
follow-up review workflow or its disposition rules.

## Review the scope before concluding

- Account for every changed file from the supplied scope. Read the full relevant
  source and trace callers, shared helpers, consumers, and contracts when behavior
  depends on them. For deletions, inspect the base revision and remaining callers;
  for renames, compare the old and new paths. Do not mistake a missing source file
  for an irrelevant change.
- Apply the domain agent's entire relevant checklist. Inspect normal behavior,
  alternative entry/exit paths, failures, retries, cancellation, cleanup and state
  transitions where applicable. Record a specific reason when a file or check is
  outside your domain; a disabled neighboring agent does not expand your domain.
- MR descriptions, reported verification, and previous review conclusions are
  claims to check against the code, not proof of correctness. Preserve explicit
  requester deferrals, but verify that their scope covers the observed behavior;
  they do not exempt surrounding code or new consequences from review.
- Evaluate severity separately from whether a concern deserves reporting. Use
  suggestions, nits and questions for actionable improvements, conventions, and
  concrete unresolved contract questions as the domain rules permit. Runtime
  reproduction is not a prerequisite for a finding established by source and a
  reachable scenario. Do not promote speculation to a blocker or manufacture
  comments to hit a quota. A complete review may legitimately find zero issues.
- Before returning, make a second pass over your coverage gaps and candidate
  concerns. Investigate them or explicitly record the limitation. Neither a low
  nor a high finding count is a stopping criterion.

## Return a coverage report

Alongside the canonical counts, findings and GitLab write references, write one
JSON report to the supplied `coverage_report_path` outside the reviewed worktree.
Use the exact `agent_key` and `head_sha` from the supplied scope. The orchestrator
provides the scope; never shrink or rewrite it to make your report pass.

The report has these fields:

- `agent`: the enabled config key, e.g. `qa`.
- `head_sha`: the full reviewed commit SHA.
- `files`: one object for every path in `scope.changed_files`, with `path`,
  `status` (`reviewed`, `not_applicable`, or `unreviewed`), and `evidence`.
  Evidence is a concise, verifiable source reference and what was checked, or
  the reason it is not applicable/unreviewed. Group related explanations by
  reusing a concise reference rather than writing an essay per file.
- `checks`: an object containing `domain_checklist`, `integration_paths`, and
  `failure_paths`. Each has the same `status` and `evidence` fields. Identify
  checklist categories checked, actual caller/consumer paths, and relevant
  failure/lifecycle scenarios. State when checks were static versus executed.
- `candidates`: an array of concerns investigated (may be empty). Each has
  `title`, `disposition` (`posted`, `dismissed`, `deferred`, or `unresolved`), and
  `evidence`. For posted concerns, include the thread reference; for dismissals,
  cite the code that disproves the concern; for deferrals, cite the explicit
  requester decision and its scope. Merely failing to reproduce a concern is not
  disproof. A concrete external contract question can be posted as a question;
  work still needed to investigate your own hypothesis stays `unresolved`.

Do not claim checks you did not perform. These are short audit facts, not private
reasoning transcripts. A report documents review coverage; it cannot prove that
all bugs have been found.

If asked to fill a gap, continue the same review and reuse existing GitLab thread
references. Post only newly established findings; update your existing domain
summary if counts change instead of duplicating comments.
