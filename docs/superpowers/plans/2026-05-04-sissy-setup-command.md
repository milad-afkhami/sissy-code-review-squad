# `/sissy-setup` Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a single `commands/sissy-setup.md` slash-command that fetches + checks out a branch, hard-resets it to origin, and presents an Inquirer.js checkbox TUI for toggling `.claude/review-config.yml` agent settings.

**Architecture:** Pure markdown command file (identical pattern to existing `sissy-squad.md` / `clear-mr-comments.md`). No new agents or shell scripts. The Inquirer script is written to `/tmp/` at runtime by Claude and executed via `npx`.

**Tech Stack:** Markdown command file, Node.js ESM (`@inquirer/checkbox`), YAML, Bash

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `commands/sissy-setup.md` | The entire command — git flow + config TUI |

---

### Task 1: Create the command file with frontmatter and git flow

**Files:**
- Create: `commands/sissy-setup.md`

- [ ] **Step 1: Create the file with frontmatter, title, and Steps 1–4 (git flow)**

Create `commands/sissy-setup.md` with this exact content for the git section:

```markdown
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

### Step 2: Git — Fetch Origin

Run:

```bash
git fetch origin
```

Report the output to the user.

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
git checkout $ARGUMENTS
```

If the command fails (non-zero exit), **stop immediately** and print:

```
❌ Branch '$ARGUMENTS' not found. Make sure the branch exists on origin and that `git fetch` succeeded.
```

Do not attempt to create the branch.

### Step 5: Git — Hard Reset to Origin

Run:

```bash
git reset --hard origin/$ARGUMENTS
```

Print a confirmation:

```
✅ Checked out and reset to origin/$ARGUMENTS
```
```

- [ ] **Step 2: Verify the file exists and the git section looks correct**

Run:
```bash
head -60 /home/milad/Desktop/projects/sissy-code-review-squad/commands/sissy-setup.md
```

Expected: frontmatter with `model: sonnet`, Steps 1–5 present, no placeholder text.

- [ ] **Step 3: Commit**

```bash
git add commands/sissy-setup.md
git commit -m "feat: add sissy-setup command — git flow section"
```

---

### Task 2: Add the config read + Inquirer TUI section

**Files:**
- Modify: `commands/sissy-setup.md`

- [ ] **Step 1: Append Step 6 (read config) to the command file**

Append the following after Step 5 in `commands/sissy-setup.md`:

```markdown
### Step 6: Config — Read Existing Agent State

Read the file `.claude/review-config.yml` from the current working directory.

If the file does not exist, treat all 10 agents as enabled:

```yaml
agents:
  accessibility: { enabled: true }
  security: { enabled: true }
  performance: { enabled: true }
  seo: { enabled: true }
  styling: { enabled: true }
  code-quality: { enabled: true }
  react: { enabled: true }
  typescript: { enabled: true }
  git: { enabled: true }
  qa: { enabled: true }
```

Parse the file to build a map of `agentKey → boolean` for all 10 keys:
`accessibility`, `security`, `performance`, `seo`, `styling`, `code-quality`, `react`, `typescript`, `git`, `qa`.

Any key absent from the file defaults to `true`.

### Step 7: Config — Launch Interactive Toggle UI

Write the following Node.js script to `/tmp/sissy-setup.mjs`, substituting the actual current enabled state for each agent in the `checked` field (`true` or `false`):

```javascript
import { checkbox } from '@inquirer/checkbox';
import { writeFileSync } from 'fs';

const ALL_AGENTS = [
  { value: 'accessibility',  name: '🦯  Colorblind Sissy  (Accessibility)' },
  { value: 'security',       name: '🔒  SecuSissy         (Security)' },
  { value: 'performance',    name: '⚡  TurboSissy        (Performance)' },
  { value: 'seo',            name: '🌐  Canonical Sissy   (SEO)' },
  { value: 'styling',        name: '🎨  ChicSissy         (Styling)' },
  { value: 'code-quality',   name: '🧹  KISS Sissy        (Code Quality)' },
  { value: 'react',          name: '⚛️   Hooked Sissy      (React)' },
  { value: 'typescript',     name: '📝  Unknown Sissy     (TypeScript)' },
  { value: 'git',            name: '📚  Detached-HEAD Sissy (Git)' },
  { value: 'qa',             name: '✅  BugSlayer Sissy   (QA)' },
];

// Pre-check agents based on current config state
// REPLACE the checked values below with actual state from Step 6
const choices = ALL_AGENTS.map(agent => ({
  ...agent,
  checked: ENABLED_STATE[agent.value] ?? true,
}));

const ENABLED_STATE = {
  accessibility: {{accessibility_enabled}},
  security:      {{security_enabled}},
  performance:   {{performance_enabled}},
  seo:           {{seo_enabled}},
  styling:       {{styling_enabled}},
  'code-quality':{{code_quality_enabled}},
  react:         {{react_enabled}},
  typescript:    {{typescript_enabled}},
  git:           {{git_enabled}},
  qa:            {{qa_enabled}},
};

const selected = await checkbox({
  message: 'Select agents to enable for this review (Space to toggle, Enter to confirm):',
  choices,
  pageSize: 12,
});

writeFileSync('/tmp/sissy-agents.json', JSON.stringify(selected));
```

**Important:** Before writing the file, replace each `{{key_enabled}}` placeholder with the actual boolean value parsed in Step 6 (e.g., `true` or `false`). Also move the `ENABLED_STATE` declaration above the `choices` constant so the reference resolves correctly.

Then run:

```bash
npx --yes --package=@inquirer/checkbox node /tmp/sissy-setup.mjs
```

Wait for the process to complete. The user will interact with the TUI directly in the terminal.
```

- [ ] **Step 2: Verify Step 6 and 7 are present and correct**

```bash
grep -n "Step 6\|Step 7\|sissy-setup.mjs\|sissy-agents.json" commands/sissy-setup.md
```

Expected: lines for each of those strings present.

- [ ] **Step 3: Commit**

```bash
git add commands/sissy-setup.md
git commit -m "feat: sissy-setup — add config read and Inquirer TUI step"
```

---

### Task 3: Add config write + summary section

**Files:**
- Modify: `commands/sissy-setup.md`

- [ ] **Step 1: Append Steps 8 and 9 (write config + summary)**

Append the following after Step 7:

```markdown
### Step 8: Config — Write Updated review-config.yml

Read `/tmp/sissy-agents.json`. It contains a JSON array of the agent keys the user selected as enabled (e.g., `["accessibility","security","performance"]`).

Write `.claude/review-config.yml` with this exact structure, setting `enabled: true` for every key present in the array and `enabled: false` for every key absent:

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

Ensure the `.claude/` directory exists before writing (create it if needed).

### Step 9: Summary

Print the final agent state as a table:

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

Show the actual enabled/disabled state from the selection. `/sissy-squad <MR_URL>` must appear on its own line with a blank line above it so it is easy to copy.

## Important Notes

1. `$ARGUMENTS` must be a branch name — not an MR URL. If it looks like a URL, stop and clarify.
2. The hard reset (`git reset --hard origin/<branch>`) will discard any local commits on the branch that are not on origin. The dirty-tree warning covers uncommitted changes; committed-but-not-pushed changes are silently discarded. This is intentional — the goal is an exact mirror of origin.
3. If `npx` is not available, stop with: `npx is required (Node.js ≥18). Please install Node.js.`
4. The `/tmp/sissy-setup.mjs` and `/tmp/sissy-agents.json` files are ephemeral — created and read within this command's execution, never committed.
5. Always write all 10 agent keys to `.claude/review-config.yml`, even if some are disabled. This ensures the file is always a complete, valid config.
```

- [ ] **Step 2: Verify the full command structure**

```bash
grep -n "^### Step" commands/sissy-setup.md
```

Expected output:
```
### Step 1: Validate Input
### Step 2: Git — Fetch Origin
### Step 3: Git — Check for Dirty Working Tree
### Step 4: Git — Checkout Branch
### Step 5: Git — Hard Reset to Origin
### Step 6: Config — Read Existing Agent State
### Step 7: Config — Launch Interactive Toggle UI
### Step 8: Config — Write Updated review-config.yml
### Step 9: Summary
```

- [ ] **Step 3: Commit**

```bash
git add commands/sissy-setup.md
git commit -m "feat: sissy-setup — add config write and summary section"
```

---

### Task 4: Register the command in package.json

**Files:**
- Modify: `package.json`

- [ ] **Step 1: Read the current commands list in package.json**

```bash
grep -A5 '"commands"' package.json
```

Expected: something like `"commands": ["sissy-squad", "clear-mr-comments", "follow-up-review"]`

- [ ] **Step 2: Add `sissy-setup` to the commands array**

In `package.json`, update the `claudeCode.commands` array to include `"sissy-setup"`:

```json
"commands": ["sissy-squad", "clear-mr-comments", "follow-up-review", "sissy-setup"]
```

- [ ] **Step 3: Verify**

```bash
grep -A5 '"commands"' package.json
```

Expected: `"sissy-setup"` is present in the array.

- [ ] **Step 4: Commit**

```bash
git add package.json
git commit -m "chore: register sissy-setup in package.json commands"
```

---

### Task 5: Manual verification

- [ ] **Step 1: Verify the command file is syntactically well-formed**

```bash
wc -l commands/sissy-setup.md
```

Expected: > 100 lines.

```bash
head -5 commands/sissy-setup.md
```

Expected: frontmatter `model: sonnet` and `description` present.

- [ ] **Step 2: Verify no placeholder text remains**

```bash
grep -n "TODO\|TBD\|placeholder\|fill in\|implement later" commands/sissy-setup.md
```

Expected: no output (zero matches).

- [ ] **Step 3: Verify all 10 agent keys are present in the Inquirer script**

```bash
grep -c "value:" commands/sissy-setup.md
```

Expected: 10

- [ ] **Step 4: Verify the YAML template in Step 8 has all 10 keys**

```bash
grep -c "enabled:" commands/sissy-setup.md
```

Expected: ≥ 20 (10 in the default state block in Step 6, 10 in the YAML template in Step 8)

- [ ] **Step 5: End-to-end test (manual)**

From a project repo that uses sissy-code-review-squad:
1. Run `/sissy-setup <a-real-branch-name>`
2. Confirm `git fetch` output appears
3. If repo is dirty, confirm warning lists files
4. Confirm checkout and hard reset succeed
5. Confirm Inquirer TUI opens, shows 10 agents with current state pre-checked
6. Toggle a couple of agents, press Enter
7. Confirm `.claude/review-config.yml` is written with correct values
8. Confirm final output shows `/sissy-squad <MR_URL>` on its own line

- [ ] **Step 6: Error path test — bad branch name**

Run `/sissy-setup nonexistent-branch-xyz`

Expected: error message `❌ Branch 'nonexistent-branch-xyz' not found.` and command stops.
