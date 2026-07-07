# Single-Command Worktree Reviews (2.0.0)

**Date:** 2026-07-06
**Status:** Approved for implementation
**Supersedes:** most of [2026-07-05-worktree-isolation-design.md](2026-07-05-worktree-isolation-design.md)

## Problem

The 1.12.0 design put worktree creation in a separate `sissy-setup` command that
had to run before `sissy-squad` or `follow-up-review`. Two problems surfaced in
real use:

1. **Two commands per review is tedious.** Setup then review, every time.
2. **The agent-config picker (zenity) was welded to setup**, but it writes
   `review-config.yml`, which is **squad-only and branch-independent**.
   `follow-up-review` never reads it — yet preparing a worktree for a follow-up
   forced the user to dodge the dialog. (Observed: the user interrupts zenity on
   purpose during follow-up prep.)
3. **A worktree/MR branch mismatch was unguarded.** Setup took a branch, the
   review took an MR URL; nothing checked they agreed. Evaluating fixes against
   the wrong branch would fail silently.

Root cause: `sissy-setup` bundled three unrelated jobs — worktree prep (needed by
both reviews), agent config (squad-only), and a branch argument (redundant with
the MR).

## Resolution

Delete `sissy-setup`. Make each review command self-contained and take **only the
MR URL**; derive the branch from the MR itself.

- **`sissy-squad <MR_URL>`**: parse MR → zenity agent picker (writes
  `review-config.yml`) → fetch MR (get `source_branch`) → provision detached
  worktree → discovery → enabled review agents → summary → remove worktree.
- **`follow-up-review <MR_URL>`**: parse MR → classify threads → *(if any
  addressed)* fetch → provision worktree → discovery → evaluators → resolve →
  summary → remove worktree. Zero-addressed runs never build a worktree. No
  zenity (config is irrelevant to follow-up).

Because the worktree is always built from the MR's own `source_branch`, the
branch-mismatch bug is **structurally impossible** — no guard needed.

## Key design points

- **No state file.** The worktree lives and dies inside one command run; the
  orchestrator holds the path (captured from `echo WORKTREE_PATH=…`) and
  substitutes it into the discovery/evaluator prompts and the cleanup block.
- **Orphan cleanup** is a sweep at provisioning time: remove any existing
  `sissy-review-wt-*` worktree, then `git worktree prune`. Safe under the
  documented **one-review-at-a-time** assumption (any pre-existing sissy worktree
  is a leftover, since this run hasn't created its own yet).
- **Config written in bash, not the Write tool.** In 1.12.0, `Write(review-config.yml)`
  errored at runtime and only survived because the content happened to be
  unchanged. The picker now generates the YAML with a bash loop
  (`printf … > .claude/review-config.yml`), which cannot silently fail.
- **zenity early.** The picker runs right after metadata parse so the user
  interacts once, up front, and the rest runs unattended.
- **zenity absent → graceful fallback.** If `zenity --version` fails, the review
  continues using the existing `review-config.yml` (or all-enabled default)
  instead of aborting.
- **`review-config.yml` stays in the main repo**; discovery/thread-evaluator read
  the worktree via their `Project Root` input (unchanged from 1.12.0).

## Component changes

- **Delete** `commands/sissy-setup.md`; remove `sissy-setup` from
  `package.json` `claudeCode.commands`.
- **Rewrite** `commands/sissy-squad.md`: add validate-input, agent picker,
  worktree provisioning, and cleanup steps; remove the old state-file locate step.
- **Rewrite** `commands/follow-up-review.md`: add worktree provisioning (only when
  `addressed_count > 0`) and cleanup; remove the state-file locate step; capture
  `source_branch` from the fetch step.
- **`agents/discovery.md`, `agents/thread-evaluator.md`**: unchanged — they
  already accept a `Project Root`.
- **README**: Quick Start, Configuration, pipeline diagram, Prerequisites
  (zenity/notify-send), and Commands table updated.
- **Version → 2.0.0** in `package.json`, `.claude-plugin/plugin.json`,
  `.claude-plugin/marketplace.json`. Removing a command is a breaking change.

## Assumptions & edge cases

- **One review at a time per repo** — required by the orphan sweep.
- **Empty agent selection** in squad → stop before provisioning a worktree
  ("nothing to review").
- **Zero addressed threads** in follow-up → skip straight to the summary; no
  worktree, no cleanup.
- **Crashed run** leaves a `/tmp` worktree; the next run's sweep removes it, and
  the OS purges `/tmp` on reboot.
- **Branch not on origin / fetch fails / worktree add fails** → each stops with a
  distinct error before any review work begins.
