---
model: sonnet
description: Prepare a branch for review — fetch, checkout, hard-reset to origin, and configure review agents
---

# Pre-Review Setup

Prepare branch `$ARGUMENTS` for review and configure which agents should run.

## Instructions

### Step 1: Validate Input

If `$ARGUMENTS` is empty, stop immediately and print:

```
Usage: /sissy-setup <branch-name>

Example: /sissy-setup feature/my-branch
```

If `$ARGUMENTS` contains `://`, `gitlab.`, or `github.`, stop immediately and print:

```
❌ Expected a branch name, not a URL. Usage: /sissy-setup <branch-name>
```

> **Isolation guarantee:** This command NEVER modifies your main working tree.
> The review runs in a separate git worktree, so your uncommitted, unstaged
> changes in the default checkout are always safe — even though the worktree is a
> detached mirror of origin. There is no `checkout` or `reset` of your working
> directory anywhere in this command.

### Step 2: Git — Prune Stale Worktree and Fetch

First remove any leftover review worktree from a previous run (e.g. a review that
crashed before it could clean up), then fetch. This whole block is self-contained
— it recomputes its paths from git, so it does not rely on variables from other
steps.

```bash
GIT_COMMON_DIR=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
STATE_FILE="$GIT_COMMON_DIR/sissy-review-worktree"

# Tear down an orphaned worktree recorded by a prior run, if any
if [ -f "$STATE_FILE" ]; then
  OLD_WT=$(sed -n 's/^worktree_path=//p' "$STATE_FILE")
  [ -n "$OLD_WT" ] && git worktree remove --force "$OLD_WT" 2>/dev/null
  rm -f "$STATE_FILE"
fi

# Reclaim administrative entries for worktrees whose directories are gone
git worktree prune

git fetch origin
```

If `git fetch origin` exits non-zero, **stop immediately** and print:

```
❌ git fetch failed. Check your network connection and remote configuration.
```

Otherwise continue silently.

### Step 3: Git — Verify Branch Exists on Origin

Run:

```bash
git rev-parse --verify --quiet "origin/$ARGUMENTS"
```

If the command fails (non-zero exit), **stop immediately** and print:

```
❌ Branch 'origin/$ARGUMENTS' not found. Make sure the branch exists on origin and that `git fetch` succeeded.
```

Do not attempt to create the branch.

### Step 4: Git — Create Isolated Review Worktree and Record State

Create a fresh, uniquely-named worktree checked out as a **detached mirror** of
`origin/$ARGUMENTS`, then record its location so `sissy-squad` and
`follow-up-review` can find it. Detaching avoids any "branch already checked out"
conflict with your main tree and needs no reset. Creating the worktree and
writing the state file happen in **one block** so the generated path stays in
scope.

```bash
GIT_COMMON_DIR=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
STATE_FILE="$GIT_COMMON_DIR/sissy-review-worktree"

WORKTREE_PATH=$(mktemp -u --tmpdir "sissy-review-wt-XXXXXX")
git worktree add --detach "$WORKTREE_PATH" "origin/$ARGUMENTS" || exit 1

# Record state inside .git (per-clone, never tracked, never committed)
cat > "$STATE_FILE" <<EOF
worktree_path=$WORKTREE_PATH
branch=$ARGUMENTS
EOF

echo "✅ Isolated review worktree ready at $WORKTREE_PATH (origin/$ARGUMENTS)"
echo "   Your main working tree is untouched."
```

If `git worktree add` fails (the block exits non-zero), **stop immediately** and
print:

```
❌ Failed to create review worktree for origin/$ARGUMENTS. If you're in a restricted or sandboxed environment, creation may have been denied — check that $TMPDIR (or /tmp) is writable and that the worktree path is accessible.
```

### Step 6: Config — Read Existing Agent State

Read the file `.claude/review-config.yml` from the current working directory.

If the file does not exist, treat all 10 agents as enabled:
- `accessibility`: true
- `security`: true
- `performance`: true
- `seo`: true
- `styling`: true
- `code-quality`: true
- `react`: true
- `typescript`: true
- `git`: true
- `qa`: true

Parse the file to build a map of `agentKey → boolean` for all 10 keys:
`accessibility`, `security`, `performance`, `seo`, `styling`, `code-quality`, `react`, `typescript`, `git`, `qa`.

Any key absent from the file defaults to `true`.

### Step 7: Config — Launch Interactive Toggle UI

First, check that `zenity` is available:

```bash
zenity --version
```

If the command fails, **stop immediately** and print:

```
❌ zenity is required for the agent selector UI. Install it with: sudo apt install zenity
```

Run the following command, substituting each `{{KEY}}` placeholder with `TRUE` or `FALSE` based on the enabled state parsed in Step 6 (e.g., if `accessibility` is enabled use `TRUE`, if disabled use `FALSE`):

```bash
zenity --list \
  --checklist \
  --title="Sissy Code Review Squad" \
  --text="Select agents to enable for this review:" \
  --column="✓" --column="Agent" --column="Focus" \
  --width=520 --height=420 \
  {{ACCESSIBILITY}}  "accessibility"  "🦯  Colorblind Sissy — WCAG, ARIA, semantic HTML" \
  {{SECURITY}}       "security"       "🔒  SecuSissy — XSS, secrets, auth" \
  {{PERFORMANCE}}    "performance"    "⚡  TurboSissy — Re-renders, bundle, CWV" \
  {{SEO}}            "seo"            "🌐  Canonical Sissy — Crawlability, meta, SSR" \
  {{STYLING}}        "styling"        "🎨  ChicSissy — Tailwind, design system, RTL" \
  {{CODE_QUALITY}}   "code-quality"   "🧹  KISS Sissy — Readability, DRY, naming" \
  {{REACT}}          "react"          "⚛️  Hooked Sissy — Hooks, components, state" \
  {{TYPESCRIPT}}     "typescript"     "📝  Unknown Sissy — Type safety, inference" \
  {{GIT}}            "git"            "📚  Detached-HEAD Sissy — Commits, PR structure" \
  {{QA}}             "qa"             "✅  BugSlayer Sissy — Requirements, bugs, tests" \
  --separator=","
```

Capture the output of this command as `SELECTED_AGENTS`. It will be a comma-separated string of the agent keys the user checked (e.g., `accessibility,security,performance`).

If the user closes the dialog without confirming (zenity exits non-zero), **skip Step 8 entirely** (do not write the config file) and proceed directly to Step 9 using the existing agent state from Step 6. Print:

```
⚠️ Agent selection skipped — keeping existing configuration.
```

### Step 8: Config — Write Updated review-config.yml

Use the `SELECTED_AGENTS` comma-separated string from Step 7 to determine which agents are enabled.

Run:

```bash
mkdir -p .claude
```

Write `.claude/review-config.yml` with the following structure. Set `enabled: true` for every key present in the array and `enabled: false` for every key absent. All 10 keys must always be present in the output file:

```yaml
# Sissy Code Review Squad Configuration
# Copy this file to your project's .claude/review-config.yml
#
# Enable or disable agents based on your project's needs.
# All agents are enabled by default.

agents:
  # Colorblind Sissy - WCAG compliance, ARIA, semantic HTML
  accessibility:
    enabled: <true|false>

  # SecuSissy - XSS, secrets, auth vulnerabilities
  security:
    enabled: <true|false>

  # TurboSissy - Re-renders, bundle size, Core Web Vitals
  performance:
    enabled: <true|false>

  # Canonical Sissy - Crawlability, meta tags, SSR
  # Disable for non-web projects or internal tools
  seo:
    enabled: <true|false>

  # ChicSissy - Tailwind, design system, responsive design
  styling:
    enabled: <true|false>

  # KISS Sissy - Readability, DRY, naming conventions
  code-quality:
    enabled: <true|false>

  # Hooked Sissy - React patterns, hooks, components
  # Disable for non-React projects
  react:
    enabled: <true|false>

  # Unknown Sissy - Type safety, TypeScript best practices
  # Disable for JavaScript-only projects
  typescript:
    enabled: <true|false>

  # Detached-HEAD Sissy - Commit messages, PR structure
  git:
    enabled: <true|false>

  # BugSlayer Sissy - Requirements, bugs, test checklists
  qa:
    enabled: <true|false>
```

Replace each `<true|false>` with the actual boolean from the selection.

### Step 9: Summary

Print the final agent state as a table, then the run prompt on its own line.

- If Step 8 ran (user confirmed the dialog), use header: `✅ Config saved to .claude/review-config.yml`
- If Step 8 was skipped (user cancelled), use header: `✅ Worktree ready. Using existing .claude/review-config.yml`

Example output:

```
✅ Config saved to .claude/review-config.yml

Agent              Status
─────────────────────────────
accessibility      ✅ enabled
security           ✅ enabled
performance        ✅ enabled
seo                ❌ disabled
styling            ✅ enabled
code-quality       ✅ enabled
react              ✅ enabled
typescript         ✅ enabled
git                ✅ enabled
qa                 ✅ enabled

Run your review:

/sissy-code-review-squad:sissy-squad <MR_URL>
```

Show the actual enabled/disabled state. `/sissy-code-review-squad:sissy-squad <MR_URL>` must appear on its own line with a blank line above it.

### Step 10: Desktop Notification

Run:

```bash
notify-send "✅ Sissy Setup Complete" "Branch: $ARGUMENTS\nAgents configured. Ready to run sissy-squad." --icon=dialog-information
```

## Important Notes

1. The review runs in an **isolated git worktree** — a detached mirror of `origin/$ARGUMENTS` created in a unique temp directory. Your main working tree, including uncommitted and unstaged changes, is never touched. `sissy-squad` / `follow-up-review` remove the worktree when they finish, so re-run `/sissy-setup` before each review pass to get a fresh checkout.
2. The worktree location is recorded in `<git-common-dir>/sissy-review-worktree` (inside `.git/`, never committed). `sissy-squad` and `follow-up-review` read it from there; if it is missing they will tell you to run this setup first.
3. `review-config.yml` is written to your **main repo** at `.claude/review-config.yml` — it is your per-project preference, independent of the branch under review.
4. Always write all 10 agent keys to `.claude/review-config.yml`, even if some are disabled.
5. `zenity` is required for the agent selector dialog. It is pre-installed on most Ubuntu/GNOME desktops (`sudo apt install zenity` if missing).
