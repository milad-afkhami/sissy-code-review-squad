# Git-Worktree Isolation for Sissy Reviews

**Date:** 2026-07-05
**Status:** Approved for implementation

## Problem

The reviewer runs Sissy against a developer's merge request while their own
uncommitted work sits in the same repository. Today `sissy-setup` does
`git checkout <branch>` + `git reset --hard origin/<branch>` **in the main
working directory**, which destroys those uncommitted, unstaged changes. The
reviewer wants to keep working on their feature in the default working tree
while Sissy reviews the MR in an isolated parallel checkout, cleaned up when the
review finishes.

## Diagnosis: what couples to the working tree

- **`sissy-setup`** — the destructive command. `checkout` + `reset --hard` in the
  main tree. Also runs the zenity agent-picker and writes `review-config.yml`
  (unrelated to git).
- **`sissy-squad`** — reviews almost entirely from the GitLab **diff text**
  embedded in agent prompts. The only local-disk reader is the **discovery**
  agent (reads `.claude/rules/*.md`, `package.json`, samples code).
- **`follow-up-review`** — genuinely needs the branch's real files on disk: the
  **thread-evaluator** agents read the developer's source to verify fixes.

Confirmed by inspection: of the review agents, only **`discovery`** and
**`thread-evaluator`** read local disk. `git.md` and the other eight work purely
off diff text and need no working tree.

## Why a worktree fits

`git worktree add` creates a second working directory backed by the same `.git`.
The main working tree — including uncommitted, unstaged changes — is physically
isolated: a `git reset --hard` inside the worktree cannot reach it. Using
`git worktree add --detach <path> origin/<branch>` checks out an exact mirror of
origin at a detached HEAD, which (a) needs no `reset`, and (b) sidesteps the
"branch already checked out elsewhere" error git would otherwise raise when the
same branch is checked out in the main tree.

## Lifecycle (setup owns creation; review owns teardown)

The worktree is created by `sissy-setup` and must outlive it so the later review
command reads the checkout setup produced. Because the reviewer runs squad and
follow-up roughly a day apart (never both against one live checkout), each review
command tears the worktree down on completion, and setup is re-run before the
next pass to fetch fresh code.

```
sissy-setup <branch>   → prune, fetch, create detached worktree, write state file
sissy-squad <MR_URL>   → locate worktree, review, remove worktree + state file
   … (developer pushes fixes; reviewer re-runs setup) …
sissy-setup <branch>   → fresh worktree mirroring the new origin state
follow-up-review <URL> → locate worktree, verify fixes, remove worktree + state file
```

## State file

Location: `<git-common-dir>/sissy-review-worktree` — inside `.git/`, so it is
per-clone and never tracked or committed. Resolved with
`git rev-parse --git-common-dir` (not `--git-dir`) so it points at the shared
`.git` even when invoked from within a worktree.

Format is jq-free `KEY=VALUE` lines (no `jq` dependency):

```
worktree_path=/tmp/sissy-review-wt-a1b2c3
branch=feature/foo
```

## Component changes

### `commands/sissy-setup.md`

Replace the git portion (current Steps 2–5) with:

1. `git worktree prune`; if a leftover state file exists, `git worktree remove
   --force` its path first (clears orphans from crashed runs).
2. `git fetch origin` — same failure message as today.
3. Verify `origin/<branch>` exists (`git rev-parse --verify`); clear error if not.
4. `WT=$(mktemp -u --tmpdir sissy-review-wt-XXXXXX)` — unique dir name per run,
   not created (git creates it).
5. `git worktree add --detach "$WT" "origin/<branch>"` — detached mirror, no reset.
6. Write the state file to `<git-common-dir>/sissy-review-worktree`.

- **Delete the dirty-working-tree warning (current Step 3).** A dirty main tree
  is now completely safe — this is the visible proof the problem is solved.
- Keep the zenity picker and `review-config.yml` write (current Steps 6–9)
  unchanged. `review-config.yml` continues to live in the **main repo**.
- Update the Step 9 summary and Step 10 notification text to mention the worktree.

### `commands/sissy-squad.md`

- **New first step:** read the state file. If absent →
  `Run /sissy-setup <branch> first.` and stop. If the path is gone →
  `Worktree missing — re-run /sissy-setup <branch>.` and stop. Store as `$WT`.
- **Step 4 (discovery):** inject `Project Root: $WT` into the discovery prompt.
- **New final step (after the summary note):**
  `git worktree remove --force "$WT"` → `git worktree prune` → delete the state
  file.
- `review-config.yml` is still read from the main-repo CWD (orchestrator does not
  move).

### `commands/follow-up-review.md`

- Same new first step (locate worktree, same errors) and same final teardown step.
- **Step 4 (discovery):** inject `Project Root: $WT`.
- **Step 5 (thread-evaluator):** inject `Project Root: $WT` into each bucket's
  prompt.

### `agents/discovery.md`

- Add a `Project Root` input (absolute path).
- Instruction: explore the project rooted at `{project_root}`; resolve all reads
  and globs under that path (`.claude/rules/*.md`, `package.json`, `CLAUDE.md`,
  code samples). If no `Project Root` is given, fall back to the current working
  directory (keeps the agent usable standalone).

### `agents/thread-evaluator.md`

- Add a `Project Root` input (absolute path).
- Read `{project_root}/{File Path}` instead of `{File Path}`. If no `Project
  Root` is given, fall back to `{File Path}` relative to CWD.

## What lives where (intentional asymmetry)

- **`review-config.yml`** → main repo, read by the orchestrator. It is the
  reviewer's per-project preference, independent of the branch.
- **`.claude/rules/*.md`, `package.json`, source** → read from the **worktree**
  by discovery/thread-evaluator. This is the actual code under review as it
  exists on origin, not the reviewer's locally-modified copies.

## Relationship to the `using-git-worktrees` skill

The Superpowers `using-git-worktrees` skill was reviewed. It targets a different
job — creating an isolated workspace **to author code in** (install deps, run a
baseline test suite, keep the worktree alive, save work to a branch at finish).
This design is a **throwaway, read-only review** that is destroyed after one run,
so several of that skill's rules are deliberately inverted here. Do not "fix"
this design toward the skill without re-reading this section.

- **Native worktree tools (`EnterWorktree`) over raw `git worktree add`:** not
  used. Native session-isolation moves Claude's own session into a worktree; we
  need a checkout that persists across two separate slash-command runs and is
  read by subagents through an injected path, while the orchestrator stays in the
  user's repo.
- **Project-local `.worktrees/` + `git check-ignore`:** not used. We place the
  worktree in `/tmp`, which is out-of-tree — its contents can never appear in
  `git status` or be committed, so there is nothing to gitignore.
- **Dependency install + baseline tests:** skipped. Agents only read source; no
  build or test run is needed.
- **On-create-failure fallback to working "in place":** rejected. In place would
  mean reviewing the user's own working tree — the wrong code — so creation
  failure **stops with an error** instead.
- **Detached-HEAD "create a branch at finish":** not applicable. Detached is
  desired and the worktree is discarded.

Two ideas were borrowed from the skill:

1. Canonicalize the git-common-dir with `cd "$(git rev-parse --git-common-dir)"
   && pwd -P` so the state-file path is absolute and independent of the launch
   CWD.
2. Name sandbox/permission denial as a likely cause in the worktree-creation
   failure message.

Using `--git-common-dir` (not `--git-dir`) also means running `/sissy-setup` from
inside another linked worktree still writes state to the shared `.git` and works
correctly.

## Assumptions & edge cases

- **One review at a time per repo** — the state file is a single slot. Matches
  the reviewer's ~1-day-apart workflow.
- **One review command per setup** — squad *or* follow-up removes the worktree;
  the reviewer re-runs setup before the next pass (which is needed anyway to pull
  fresh code).
- **Crashed review** leaves an orphan worktree, reclaimed by the next setup's
  `git worktree prune` / `git worktree remove` of the stale state path, and by
  the OS purging `/tmp`. No trap handlers are added to the command markdown.
- **Missing state file** on a review command → clear "run setup first" error.
- **Branch not on origin** → setup errors before creating anything.
- **Untouched agents:** `git`, `security`, and the other seven review agents work
  off diff text and need no worktree.
