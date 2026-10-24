# Codex review reliability — current handoff

Updated: 2026-10-24. **Next patch agreed; implementation has not started.**

## Resume point

Implement two narrow execution fixes. Prefer Codex-host changes that enforce
existing contracts rather than new shared review machinery:

1. Try the available Jira connector first. If disabled, unavailable, or failing,
   fall back to `browser-use`. Retrieve the full issue and comments, freeze the
   response, and share it with reviewers. Do not change the user's connector
   settings or hardcode an organization's Jira host into this public plugin.
2. Reconcile required review outputs before final aggregation. In particular,
   confirm successful publication of the separate QA Analysis note, QA checklist
   thread, and QA summary. Request missing work without rerunning the full review.

The user sometimes disables Jira in Codex for performance, and sometimes enables
it. **Jira-first, then browser fallback** is the latest decision. An earlier
suggestion to bypass connector checks entirely was explicitly corrected.

Use the invalid security finding from the audited run as a regression case for
the existing evidence-validation policy. Do not add a generic review phase,
finding quota, broad shared coverage schema, or model upgrade.

The user requested wrapup before implementation. No next-fix source changes,
tests, PR, version bump, or release have been made.

## Released baseline

- Runtime release: **v2.5.4**; all four version manifests match.
- [PR #6](https://github.com/milad-afkhami/sissy-code-review-squad/pull/6):
  implementation commit `dac82bcaff3d098a6500904b80498d1e5edbc3d7`,
  merged as `c2ff39a529ecd0c8f4786ee603dd31c50c0715e4`.
- Annotated v2.5.4 tag points to that merge. The
  [GitHub release](https://github.com/milad-afkhami/sissy-code-review-squad/releases/tag/v2.5.4)
  is published.
- [PR #7](https://github.com/milad-afkhami/sissy-code-review-squad/pull/7):
  direct Codex release instructions, merged as
  `4da0c275660ab5aff47f3194f78c298bde412cc3`. These documentation changes are on
  main after the release tag; the published tag was not rewritten.
- Both local plugins were verified at 2.5.4. Codex was enabled and its marketplace
  pinned to v2.5.4. A normal fresh Codex session exposed exactly the two Sissy
  skills; Claude's standard inventory exposed exactly three commands.
- Last release validation: 32 repository tests, classifier checks, Python/JSON
  validation, npm boundaries, materialized Claude inventory, and independent
  review. The documentation follow-up's release-guide contract also passed.

## What v2.5.4 changed

The Codex-only snapshot helper checks the clean worktree head and complete
canonical authored-file scope against pinned target/base/head refs, reconstructs
full diffs from Git, and preserves the original input and checksums in a unique
run directory. It handles the canonical empty-filter behavior and avoids
duplicating patches for file-to-directory or file-type changes.

The adapter carries the complete canonical checklist and severity taxonomy,
requires scoped evidence challenges, respects accepted/deferred risks, and
retains exact rendered prompts, model choices, and requirements responses.
Follow-up-review keeps its filtered payload workflow. Canonical reviewer
instructions and model preference were preserved.

Model mapping remains Sonnet=`gpt-5.6-sol/high` with `gpt-6-sol/high` fallback;
Security uses the Opus tier at xhigh. Do not silently substitute model policies.

## Investigation conclusions to preserve

The initial complaint was far fewer Codex review threads than historical Claude
reviews. Historical comparisons confirm lower counts, but do not establish an
eightfold loss of valid bug recall.

Older Codex runs had real context truncation and an admitted premature-stop
instruction. The earlier v2.5.2 coordinator correction and v2.5.3 paging guard
addressed those mechanisms without proving general recall parity. An earlier
479-line shared coverage-system proposal was rejected; do not recreate it.

Same-source reviews showed variable optional findings, grouping, and severity.
Some extra historical comments were unsupported. One apparent stale-state
concern was subsequently reproduced through a different passive-effect closure
race, despite the original framework-preservation explanation being wrong.

Controlled offline QA calibration used fixed original source/requirements, the
same model/effort, two repetitions per case, a known-bug control, and a clean
control. Final baseline/candidate each detected the bug 4/4 and left the clean
control unflagged 4/4. The reproduced lifecycle race appeared 1/2 versus 2/2
relevant runs. An initial candidate reopened four deferred risks; the accepted
scope clause fixed that observed regression in the final repeats. This is a
small calibration probe, not proof of broad recall parity.

## New-version live-run audit

The subsequent `review MR 242` chat (UUID
`01a16f2f-a33f-7c73-8e05-689877fd5894`, back-office project) used v2.5.4.

Confirmed successes:

- Four-file snapshot and checksums matched the pinned source.
- Security, Code Quality, Git, and QA all received/read the full standards,
  new review contract, and output guard; exact prompts are preserved.
- Six suggestions represented four topics, with two cross-domain duplicate
  pairs. Those were robustness, maintainability, and process concerns rather
  than six independently proven production bugs.
- Missing Jira criteria and absent authentication test coverage were disclosed;
  the final verdict was Needs discussion.
- Fifteen existing tests passed, but they did not cover authentication.

Confirmed gaps driving the agreed next patch:

- Jira retrieval stopped after an Atlassian site-discovery Unknown tool error.
  The audit subsequently retrieved the full issue/comments via the authenticated
  browser, with HTTP 200. The issue's update time preceded the review. The run
  never attempted that fallback.
- QA omitted the mandatory separate QA Analysis note required in
  `agents/qa.md`'s Output Format. Local evidence and the summary did not replace
  that required published output. The coordinator missed the omission.
- Security initially posted an invalid blocker after misreading a complete
  prefix predicate, then correctly retracted/resolved it after scoped challenge.
  Preserve that recovery; use the case for regression validation, not a new
  broad review-policy rewrite.

The audit made no review-comment or reviewed-code changes. Do not modify that
MR's comments merely because the plugin's next patch is being implemented.

## Release and execution preferences

`CLAUDE.md` and `RELEASE.md` now treat an instruction to execute RELEASE.md as
authorization for the full commit/PR/merge/tag/publish/local-update workflow.
The user explicitly removed repeated final-diff approval gates. Preserve review
and verification without requesting the same authorization again.

Codex marketplace upgrade refreshes an existing pin; it does not retarget an old
release tag. Follow the tested remove-old-marketplace / add-new-tag / install
sequence in RELEASE.md. Verify standard CLI inventory, manifest, and cached
skills. Do not invent custom model-discovery probes or strip user configuration;
that caused an unnecessary release detour. Tell the user to restart existing
sessions instead of terminating them.

Keep unchanged external contracts and Claude behavior. Do not reopen accepted
risks or equate thread volume with quality. Never read/write MEMORY.md or memory/
directories. Keep public commits free of private source, full internal issue
contents, credentials, or raw chat logs. Preserve the pre-existing untracked
`.sissy/` project preferences.

## Reading for the next implementation

Required:

1. This handoff, then `CLAUDE.md` and `RELEASE.md`.
2. `.codex-plugin/runtime-adapter.md`, `commands/sissy-squad.md`,
   `agents/qa.md`, and `rules/code-review-standards.md`.
3. `scripts/test_codex_compatibility.py` and the host-specific snapshot helper
   and tests when the change touches their contracts.

Local-only evidence, when needed (ephemeral; not required for ordinary releases):

- Initial investigation, calibration results, implementation/release evidence:
  `/tmp/sissy-thread-investigation-20261024/`.
- Detailed v2.5.4 live-run audit and recovered requirements:
  `/tmp/sissy-backoffice-242-audit-ct41s8__/review-assessment.md`.
- Independent reviewer audit: `/tmp/sissy-backoffice-242-reviewer-audit.md`.
- Original run artifacts:
  `/tmp/codex-scratchpad-sissy-mr242-J299ls/sissy-codex-hpn7bz8b/`.
- Removed experimental worktrees are not working source locations; use this
  repository and recorded Git objects instead.

No product decision or user answer blocks the next scoped implementation.
