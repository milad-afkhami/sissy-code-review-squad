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

### Step 2: Git — Fetch Origin

Run:

```bash
git fetch origin
```

If the command exits non-zero, **stop immediately** and print:

```
❌ git fetch failed. Check your network connection and remote configuration.
```

Otherwise continue silently.

### Step 3: Git — Check for Dirty Working Tree

Run:

```bash
git status --porcelain
```

If the output is non-empty, print this warning and list the dirty files, then **continue** (do not stop):

```
⚠️  Warning: You have uncommitted changes:
<list each dirty file on its own line>

Continuing with checkout — your changes may be overwritten by the hard reset.
```

If the output is empty, continue silently.

### Step 4: Git — Checkout Branch

Run:

```bash
git checkout "$ARGUMENTS"
```

If the command fails (non-zero exit), **stop immediately** and print:

```
❌ Branch '$ARGUMENTS' not found. Make sure the branch exists on origin and that `git fetch` succeeded.
```

Do not attempt to create the branch.

### Step 5: Git — Hard Reset to Origin

Run:

```bash
git reset --hard "origin/$ARGUMENTS"
```

If the command fails (non-zero exit), **stop immediately** and print:

```
❌ Failed to reset to origin/$ARGUMENTS. The branch may not have been pushed to origin.
```

Otherwise print:

```
✅ Checked out and reset to origin/$ARGUMENTS
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

If the user closes the dialog without confirming (zenity exits non-zero), **stop immediately** and print:

```
❌ Setup cancelled.
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

Print the final agent state as a table, then the run prompt on its own line:

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

/sissy-squad <MR_URL>
```

Show the actual enabled/disabled state from the selection. `/sissy-squad <MR_URL>` must appear on its own line with a blank line above it.

## Important Notes

1. The hard reset will silently discard any local commits not on origin. This is intentional — the goal is an exact mirror of origin.
2. Always write all 10 agent keys to `.claude/review-config.yml`, even if some are disabled.
3. `zenity` is required for the agent selector dialog. It is pre-installed on most Ubuntu/GNOME desktops (`sudo apt install zenity` if missing).
