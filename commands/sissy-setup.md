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

First, check that `npx` is available:

```bash
npx --version
```

If the command fails, **stop immediately** and print:

```
❌ npx is required. Please install Node.js (with ESM support).
```

Write the following Node.js ESM script to `/tmp/sissy-setup.mjs`. Before writing, replace each `{{key_enabled}}` placeholder with the actual boolean (`true` or `false`) parsed from Step 6.

Note: YAML keys with hyphens map to underscores in placeholder names (e.g., `code-quality` → `{{code_quality_enabled}}`).

Create the directory `/tmp/sissy-setup-tui/` and write two files into it:

**`/tmp/sissy-setup-tui/package.json`:**

```json
{ "type": "module" }
```

**`/tmp/sissy-setup-tui/index.mjs`** (replace each `{{key_enabled}}` placeholder with the actual boolean from Step 6):

```javascript
import checkbox from '@inquirer/checkbox';
import { writeFileSync } from 'fs';

const ENABLED_STATE = {
  accessibility:  {{accessibility_enabled}},
  security:       {{security_enabled}},
  performance:    {{performance_enabled}},
  seo:            {{seo_enabled}},
  styling:        {{styling_enabled}},
  'code-quality': {{code_quality_enabled}},
  react:          {{react_enabled}},
  typescript:     {{typescript_enabled}},
  git:            {{git_enabled}},
  qa:             {{qa_enabled}},
};

const choices = [
  { value: 'accessibility',  name: '🦯  Colorblind Sissy    (Accessibility)' },
  { value: 'security',       name: '🔒  SecuSissy           (Security)'      },
  { value: 'performance',    name: '⚡  TurboSissy          (Performance)'   },
  { value: 'seo',            name: '🌐  Canonical Sissy     (SEO)'           },
  { value: 'styling',        name: '🎨  ChicSissy           (Styling)'       },
  { value: 'code-quality',   name: '🧹  KISS Sissy          (Code Quality)'  },
  { value: 'react',          name: '⚛️   Hooked Sissy        (React)'         },
  { value: 'typescript',     name: '📝  Unknown Sissy       (TypeScript)'    },
  { value: 'git',            name: '📚  Detached-HEAD Sissy (Git)'           },
  { value: 'qa',             name: '✅  BugSlayer Sissy     (QA)'            },
].map(agent => ({ ...agent, checked: ENABLED_STATE[agent.value] ?? true }));

const selected = await checkbox({
  message: 'Select agents to enable for this review (Space to toggle, Enter to confirm):',
  choices,
  pageSize: 12,
});

writeFileSync('/tmp/sissy-agents.json', JSON.stringify(selected));
```

Then install the dependency and run:

```bash
cd /tmp/sissy-setup-tui && npm install --save @inquirer/checkbox --quiet && node index.mjs
```

Wait for the process to complete. The user interacts with the TUI directly in the terminal.

### Step 8: Config — Write Updated review-config.yml

Read `/tmp/sissy-agents.json`. It contains a JSON array of the agent keys the user selected as enabled (e.g., `["accessibility","security","performance"]`).

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
2. The `/tmp/sissy-setup.mjs` and `/tmp/sissy-agents.json` files are ephemeral — created and read within this command's execution, never committed.
3. Always write all 10 agent keys to `.claude/review-config.yml`, even if some are disabled.
