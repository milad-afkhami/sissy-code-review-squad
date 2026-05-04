# Design: `/sissy-setup` Command

**Date:** 2026-05-04
**Status:** Approved

---

## Context

Before running `/sissy-squad <MR_URL>`, the reviewer needs two things to be true:

1. The local repo is checked out to the source branch being reviewed, hard-reset to match `origin`
2. `.claude/review-config.yml` reflects which agents should run for this project

Currently both steps are manual and error-prone. This command automates them in a single slash-command that runs immediately before `/sissy-squad`.

---

## Architecture

A single new file: `commands/sissy-setup.md` using `model: sonnet`.

No new agents, no shell scripts, no additional dependencies beyond `npx` (which ships with Node.js ≥18, already required by this plugin).

---

## Step-by-Step Behavior

### Step 1: Git — Fetch

Run:
```bash
git fetch origin
```

### Step 2: Git — Dirty Tree Warning

Run:
```bash
git status --porcelain
```

If output is non-empty, print a warning listing the dirty files. Continue — do not abort. The user is informed, not blocked.

### Step 3: Git — Checkout

Run:
```bash
git checkout <branch>
```

`<branch>` comes from `$ARGUMENTS`.

If the checkout fails (branch does not exist locally or on origin), **stop immediately** with a clear error message. Do not attempt to create the branch.

### Step 4: Git — Hard Reset

Run:
```bash
git reset --hard origin/<branch>
```

This leaves the repo in a clean state identical to `origin/<branch>`.

### Step 5: Config — Read Existing State

Read `.claude/review-config.yml` from the current working directory (the reviewed project's root).

If the file does not exist, treat all 10 agents as enabled (matching plugin defaults).

### Step 6: Config — Interactive Toggle UI

Write a self-contained Node.js script to `/tmp/sissy-setup.mjs` that:
- Imports `@inquirer/checkbox` via dynamic import (npx provides it)
- Pre-checks agents that are currently enabled
- On confirm, writes the selected agents as JSON to `/tmp/sissy-agents.json`

Claude writes the script to `/tmp/sissy-setup.mjs` then runs:
```bash
npx --yes --package=@inquirer/checkbox node /tmp/sissy-setup.mjs
```

The Inquirer checkbox presents all 10 agents with their current enabled state pre-checked. The user uses arrow keys + Space to toggle, Enter to confirm.

### Step 7: Config — Write Updated YAML

Claude reads `/tmp/sissy-agents.json` (the selected agents list) and writes the updated `.claude/review-config.yml`.

The written file must:
- Include all 10 agent keys (not just the selected ones)
- Set `enabled: true` for selected agents, `enabled: false` for deselected
- Preserve the comment header from `templates/review-config.yml`

### Step 8: Summary

Print a confirmation showing which agents are enabled vs disabled, then on a new line:

```
Config saved. Run your review:

/sissy-squad <MR_URL>
```

`<MR_URL>` is a placeholder — the user pastes their actual MR URL.

---

## File to Create

| File | Description |
|------|-------------|
| `commands/sissy-setup.md` | The new slash-command (only file added) |

---

## Files Referenced (Read-Only)

| File | Purpose |
|------|---------|
| `config/review-config.schema.json` | Agent key names and defaults |
| `templates/review-config.yml` | Comment header to preserve in written config |
| `.claude/review-config.yml` (user project) | Existing config to read current state from |

---

## Error Cases

| Condition | Behavior |
|-----------|----------|
| Branch not found after `git fetch` | Stop with error: `Branch '<name>' not found on origin.` |
| Dirty working tree | Warn with file list, continue |
| `.claude/review-config.yml` missing | Treat all agents as enabled, create the file after toggle |
| `npx` unavailable | Stop with error: `npx is required (Node.js ≥18). Please install Node.js.` |

---

## Verification

1. Run `/sissy-setup <branch>` from a repo that has a valid branch on origin
2. Confirm `git fetch` runs, dirty state warning appears if applicable
3. Confirm checkout succeeds and `git reset --hard origin/<branch>` runs
4. Confirm Inquirer TUI opens with current config state pre-checked
5. Toggle a few agents, press Enter
6. Confirm `.claude/review-config.yml` is written correctly
7. Confirm final output shows the `/sissy-squad <MR_URL>` line on its own line
8. Run with a non-existent branch name — confirm it stops cleanly with an error
