---
model: sonnet
description: Configure agents, provision an isolated git worktree, and run a comprehensive code review on a GitLab merge request
---

# Comprehensive Code Review

Review merge request `$ARGUMENTS` using specialized parallel review agents, in an
isolated git worktree that never touches your working tree.

## How It Works

This is a single self-contained command — there is no separate setup step:

1. Parses the MR URL
2. Asks which agents to run (zenity picker) and saves your choice
3. Provisions an isolated worktree checked out to the MR's **source branch**
4. Runs Architecture Discovery + the enabled review agents in parallel against that worktree
5. Posts a summary and removes the worktree

Your default checkout — including uncommitted, unstaged changes — is never
modified. The worktree is a detached mirror of `origin/<source_branch>`, created
fresh per run and removed when the review finishes. Because it is built from the
MR's own branch, it can never review the wrong code.

## Instructions

### Step 1: Validate Input

If `$ARGUMENTS` is empty, stop immediately and print:

```
Usage: /sissy-squad <MR_URL>

Example: /sissy-squad https://gitlab.com/your-org/your-project/-/merge_requests/123
```

### Step 2: Parse MR Metadata

Check `python3 --version` before proceeding. The initial-review completion gate
requires Python 3. If unavailable, stop before creating a worktree or posting
GitLab content and explain that requirement.

**Spawn the MR Metadata Parser Agent** to extract project info and MR IID from the URL.

Read and execute the parser agent instructions from `@agents/parse-mr-metadata.md` with the MR URL as input: `{$ARGUMENTS}`

**Wait for the Parser Agent to complete** and parse its JSON output to get:

- `project_id`
- `mr_iid`
- `project_path`

### Step 3: Configure Agents (Interactive)

Pick which of the 10 agents run and save the choice to `.sissy/review-config.yml`
in your **main repo** (not the worktree — this is your project preference, not
branch code). Do this now, up front, so the rest of the review runs unattended.

**3a. Migrate and read existing config.** Before reading the config, run this
one-way migration block:

```bash
REVIEW_CONFIG=".sissy/review-config.yml"
LEGACY_REVIEW_CONFIG=".claude/review-config.yml"

if [ ! -f "$REVIEW_CONFIG" ] && [ -f "$LEGACY_REVIEW_CONFIG" ]; then
  mkdir -p .sissy &&
    cp -- "$LEGACY_REVIEW_CONFIG" "$REVIEW_CONFIG" &&
    echo "MIGRATED:$LEGACY_REVIEW_CONFIG->$REVIEW_CONFIG"
fi
```

Read `.sissy/review-config.yml` from the current directory. Build a map of
`agentKey → enabled` for all 10 keys
(`accessibility`, `security`, `performance`, `seo`, `styling`, `code-quality`,
`react`, `typescript`, `git`, `qa`). Any absent key — or a missing file — defaults
to `true`.

**3b. Check zenity.** Run `zenity --version`. If it fails — or `$DISPLAY` and `$WAYLAND_DISPLAY` are both empty (a headless session) — print `⚠️ Agent picker unavailable — using existing agent config.` and skip to Step 4 using the map from 3a. Otherwise a display exists, so show the picker; do not skip it because the session "seems" background.

**3c. Show the picker and write the config in ONE bash block** (selection and file write share a shell). The dialog blocks until the user clicks — run it foreground with a long timeout (Bash `timeout: 600000`); do not background it, wrap it in `timeout`, or kill it. Substitute each `{{KEY}}` with `TRUE`/`FALSE` from 3a, and `{project_path}`/`{mr_iid}` with the values from Step 2 (so the picker shows which project and MR this overlay is for):

```bash
SELECTED_AGENTS=$(zenity --list --checklist \
  --title="Sissy Code Review Squad" \
  --text="Reviewing {project_path} — MR !{mr_iid}
Select agents to enable for this review:" \
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
  --separator=",")

if [ $? -ne 0 ]; then
  echo "CANCELLED"
else
  mkdir -p .sissy
  {
    echo "# Sissy Code Review Squad Configuration"
    echo "# Written by /sissy-squad's agent picker. Edit here or re-run to change."
    echo "agents:"
    for key in accessibility security performance seo styling code-quality react typescript git qa; do
      case ",$SELECTED_AGENTS," in
        *",$key,"*) enabled=true ;;
        *)          enabled=false ;;
      esac
      printf '  %s:\n    enabled: %s\n' "$key" "$enabled"
    done
  } > .sissy/review-config.yml
  echo "SAVED:$SELECTED_AGENTS"
fi
```

The config file is written entirely in bash (no Write tool), so the save is
deterministic. Interpret the output:

- `CANCELLED` → the user dismissed the dialog. Do **not** rewrite the file. Use the map from 3a as the enabled set. Print `⚠️ Selection cancelled — using existing agent config.`
- `SAVED:<list>` → the enabled set is the comma-separated `<list>` (possibly empty). The file has been written.

If the resulting enabled set is **empty**, stop and print `No agents enabled — nothing to review.` (No worktree has been created yet, so there is nothing to clean up.)

Store the enabled set as `{enabled_agents}`.

> **Future idea (not implemented yet):** based on the changed files / MR diff, suggest a
> recommended subset of agents to enable and pre-check those in the picker (instead of
> defaulting every absent key to `true`). Deferred for now — the picker only identifies the
> project and MR; it does not yet recommend which agents to activate.

### Step 4: Fetch MR Data (Once)

Spawn the MR Diff Fetcher Agent:

Read and execute the fetcher agent instructions from `@agents/fetch-mr-diffs.md` with:
- `project_id`: from Step 2
- `mr_iid`: from Step 2
- No `file_filter` (fetch all files — sissy-squad needs the full diff)

Wait for the agent to complete. Parse its JSON output to get:
- `title`, `author`, `source_branch`, `target_branch`, `description`, `labels`
- `diff_refs` (base_sha, head_sha, start_sha)
- `changed_files`: array of `{new_path, old_path, new_file, deleted_file, diff}`

### Step 5: Provision the Isolated Worktree

Create a detached worktree mirroring the MR's `source_branch`. This never touches
your working tree. Substitute `{source_branch}` with the value from Step 4:

```bash
# Reclaim registry entries whose worktree directory is already gone (e.g. cleared
# on reboot). This only removes dead entries — never a live worktree — so
# concurrent reviews on the same repo don't disturb each other.
git worktree prune

git fetch origin || { echo "FETCH_FAILED"; exit 1; }
git rev-parse --verify --quiet "origin/{source_branch}" >/dev/null || { echo "BRANCH_MISSING"; exit 1; }

WORKTREE_PATH=$(mktemp -u --tmpdir "sissy-review-wt-XXXXXX")
git worktree add --detach "$WORKTREE_PATH" "origin/{source_branch}" || { echo "WORKTREE_FAILED"; exit 1; }
echo "WORKTREE_PATH=$WORKTREE_PATH"
```

Interpret the output:

- `FETCH_FAILED` → **stop** and print `❌ git fetch failed. Check your network connection and remote configuration.`
- `BRANCH_MISSING` → **stop** and print `❌ origin/{source_branch} not found — has the MR's source branch been pushed?`
- `WORKTREE_FAILED` → **stop** and print `❌ Could not create the review worktree. If you're in a restricted or sandboxed environment, check that $TMPDIR (or /tmp) is writable.`
- `WORKTREE_PATH=<path>` → store `<path>` as `{worktree_path}` for Step 6 and Step 10.

### Step 6: Architecture Discovery

**Before spawning review agents**, spawn the Architecture Discovery agent to gather project context.

Read and execute the discovery agent instructions from `@agents/discovery.md` with:

- **Project Root**: {worktree_path from Step 5}
- **Changed Files**: List all file paths from the diff, one per line
- **MR Description**: {MR description if available}

**Wait for the Discovery Agent to complete** and store its output as `{architecture_context}`.

### Step 6b: Read Code Review Standards

**CRITICAL:** Before spawning review agents, read the code review standards file:

```
Read file: ${CLAUDE_PLUGIN_ROOT}/rules/code-review-standards.md
```

Store the **entire contents** as `{code_review_standards}`. This content MUST be embedded verbatim in every agent prompt.

### Step 6c: Establish the Review Completion Contract

Read `${CLAUDE_PLUGIN_ROOT}/rules/initial-review-completeness.md` completely and
store its entire contents as `{initial_review_completeness}`. Embed it verbatim
in every enabled review agent's prompt alongside the Code Review Standards.

Create a unique temporary artifact directory outside the review worktree. Write
`scope.json` there with `head_sha` from Step 4, `changed_files` containing every
diff's review path, and `enabled_agents` from Step 3. The review path is `old_path`
when `deleted_file` is true or `new_path` is `/dev/null`; otherwise it is
`new_path`. Never use `/dev/null` as a file identity. Preserve both original paths
in the supplied diffs so reviewers can inspect deletions and renames correctly.
Confirm that the worktree HEAD matches this SHA before starting reviews; if it
does not, stop, report the mismatch and clean up rather than review a mixed
snapshot. Keep this scope fixed throughout the review.

Assign each enabled agent a separate `{coverage_report_path}` in that directory,
such as `qa-coverage.json`. Preserve these reports after worktree cleanup and
include their location in the final user response.

### Step 7: Spawn Enabled Review Agents in Parallel

Launch only the **enabled agents** (from `{enabled_agents}`) simultaneously using a single message with multiple Task tool calls.

**Skip agents not in the `enabled_agents` list.** Log which agents are skipped for transparency.

Each agent prompt should include:

````
## Code Review Standards

{code_review_standards}

---

## Initial Review Completeness

{initial_review_completeness}

**Agent key:** {agent_key}
**Scope file:** {scope_path}
**Coverage report path:** {coverage_report_path}

---

## MR Context

**Title:** {title}
**Author:** {author.name} (@{author.username})
**Branch:** {source_branch} → {target_branch}
**MR IID:** {iid}
**Project ID:** {resolved_project_id}

### Project Root (isolated worktree, checked out to the MR's source branch)

{worktree_path from Step 5}

Read the full changed files and their neighbors here when the diff hunk alone is
ambiguous (server/client boundaries, existing image dimensions, whether a dynamic
import already exists). This is a detached mirror of `origin/{source_branch}` — read
only; do not write to it.

### Diff Refs (for GitLab comments)
- base_sha: {diff_refs.base_sha}
- head_sha: {diff_refs.head_sha}
- start_sha: {diff_refs.start_sha}

---

## Architecture Context

{architecture_context}

---

### Changed Files

{For each diff:}
**File:** {new_path}
**Status:** {new_file ? "Added" : deleted_file ? "Deleted" : "Modified"}

```diff
{diff content}
````

---

{Content from @agents/<agent-file>.md}

````

The `@agents/<agent-file>.md` placeholder above is replaced per agent row — use the exact `@agents/...` path from the table below. This syntax causes the runtime to resolve the agent file inside the subagent's context, NOT in the orchestrator's context. Do NOT read any agent file before spawning.

### Review Agents to Spawn (The Squad)

**Only spawn agents that are in the `enabled_agents` list.**

| Config Key | Agent | Agent File | Focus |
|------------|-------|------------|-------|
| `accessibility` | 🦯 Colorblind Sissy (Accessibility) | `@agents/accessibility.md` | WCAG, ARIA, semantic HTML |
| `security` | 🔒 SecuSissy (Security) | `@agents/security.md` | XSS, secrets, auth |
| `performance` | ⚡ TurboSissy (Performance) | `@agents/performance.md` | Re-renders, bundle, CWV |
| `seo` | 🌐 Canonical Sissy (SEO) | `@agents/seo.md` | Crawlability, SSR, meta |
| `styling` | 🎨 ChicSissy (Styling) | `@agents/styling.md` | Tailwind, Design system, RTL |
| `code-quality` | 🧹 KISS Sissy (Code Quality) | `@agents/code-quality.md` | Readability, DRY, naming |
| `react` | ⚛️ Hooked Sissy (React) | `@agents/react.md` | Hooks, components, state |
| `typescript` | 📝 Unknown Sissy (TypeScript) | `@agents/typescript.md` | Types, safety, inference |
| `git` | 📚 Detached-HEAD Sissy (Git) | `@agents/git.md` | Commits, PR structure |
| `qa` | ✅ BugSlayer Sissy (QA) | `@agents/qa.md` | Requirements, bugs, test checklists |

**Task Tool Parameters for ALL review agents:**
- `subagent_type: "general-purpose"`
- Use each agent's own model setting

### Step 8: Collect Results and Verify Completion

Wait for all agents to complete using TaskOutput.

Each agent returns:
- Number of blocking issues
- Number of suggestions
- Number of nits
- Number of questions
- Key findings summary
- Coverage report path and successful GitLab write references

Run the completion gate against the fixed scope and all returned report paths:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_review_coverage.py" \
  --scope "{scope_path}" --reports {quoted_coverage_report_paths}
```

Exit 0 means the reported coverage is structurally complete. It does not prove
the evidence is true: inspect the source references, checklist coverage, and
candidate dispositions. Reject generic claims such as "all checked", blanket
`not_applicable` entries without domain-specific reasons, and MR-description
claims substituted for source evidence.

For missing or weak coverage, send the specific gaps to the responsible agent
and let it finish the investigation. Re-run the gate after updated reports.
Preserve its canonical review instructions: do not impose a finding cap, tell it
there is "no need to seek extra findings", suppress non-blocking findings, or
pressure it to wrap up because of elapsed time or its current issue count.
Challenge a questionable finding by requesting evidence or counterevidence;
do not silently drop the investigation merely because blocking severity has not
been established. Zero findings with complete coverage is a valid result.

If a genuine external limitation prevents completion, record the exact gaps and
use **INCOMPLETE REVIEW**, never **APPROVED**. Do not retry an unchanged external
blocker indefinitely. Retain established findings and still perform Step 10.
An unresolved product/API question posted for the author follows the existing
**NEEDS DISCUSSION** verdict; it is distinct from unfinished reviewer work.

### Step 9: Post Summary Note

**First, read the plugin version:**
```
Read file: ${CLAUDE_PLUGIN_ROOT}/package.json
```
Extract the `version` field (e.g., "1.0.6") and store as `{plugin_version}`.

Create a summary note on the MR using `mcp__gitlab-mcp__create_merge_request_note`:

```markdown
![Puppet Master](https://milad-afkhami.com/images/blog/sissy/puppet-master-sissy.jpg){width=300 height=300}

## Comprehensive Code Review Summary

> **Reviewed by:** Sissy Code Review Squad v{plugin_version}

{If any agents were skipped, show:}
> **Note:** Some agents were skipped for this review: {list of skipped agent names}

### Review Coverage

{State whether all enabled agents passed the completion gate and the evidence
audit, which commit was reviewed, and whether validation was static or executed.
If incomplete, list the affected agents and concrete gaps. Summarize material
deferred risks with their requester dispositions; do not imply they were fixed.}

### Review Results by Agent

| Agent | ❗ Blocking | 💡 Suggestions | 💅 Nits |
|-------|------------|----------------|---------|
| 🦯 Colorblind Sissy (Accessibility) | X | X | X |
| 🔒 SecuSissy (Security) | X | X | X |
| ⚡ TurboSissy (Performance) | X | X | X |
| 🌐 Canonical Sissy (SEO) | X | X | X |
| 🎨 ChicSissy (Styling) | X | X | X |
| 🧹 KISS Sissy (Code Quality) | X | X | X |
| ⚛️ Hooked Sissy (React) | X | X | X |
| 📝 Unknown Sissy (TypeScript) | X | X | X |
| 📚 Detached-HEAD Sissy (Git) | X | X | X |
| ✅ BugSlayer Sissy (QA) | X | X | X |
| **Total** | **X** | **X** | **X** |

**Note:** For skipped agents, show "⏭️ Skipped" instead of counts. Only include enabled agents in totals.

### Issue Distribution

Include these two Mermaid diagrams (with real data from agent results):

**Severity breakdown:**

~~~
```mermaid
---
config:
  theme: default
---
pie title Issue Severity Distribution
    "❗ Blocking ({count})" : {blocking_total}
    "💡 Suggestions ({count})" : {suggestions_total}
    "💅 Nits ({count})" : {nits_total}
    "❓ Questions ({count})" : {questions_total}
```
~~~

**Issues per agent** (only include enabled agents that found issues):

~~~
```mermaid
---
config:
  theme: default
---
xychart-beta
    title "Issues by Agent"
    x-axis [{list of agent nick names, e.g. "Chick Sissy", "Kiss Sissy"}]
    y-axis "Issues" 0 --> {max_count + 2}
    bar [{total issues per agent}]
```
~~~

### Blocking Issues Summary

{List all blocking issues from all agents with file references}

### Key Recommendations

{Top 3-5 most important improvements across all categories}

### Verdict

{One of:}
- ✅ **APPROVED** - Review complete in the enabled domains; no blocking issues or decision-blocking questions
- ⚠️ **CHANGES REQUESTED** - Blocking issues must be resolved
- 💬 **NEEDS DISCUSSION** - Questions need clarification before decision
- ⏸️ **INCOMPLETE REVIEW** - Required coverage remains unfinished; list gaps even if blocking findings were also posted

---

*Reviewed by The Squad: Colorblind Sissy (Accessibility), SecuSissy (Security), TurboSissy (Performance), Canonical Sissy (SEO), ChicSissy (Styling), KISS Sissy (Code Quality), Hooked Sissy (React), Unknown Sissy (TypeScript), Detached-HEAD Sissy (Git), BugSlayer Sissy (QA)*
````

After the summary note is posted, run:

```bash
(result=$(notify-send "🎀 Sissy Squad Complete" "MR: {title}\nVerdict: {verdict} — {blocking_total} blocking, {suggestions_total} suggestions, {nits_total} nits" --action="default=Open MR" --wait --icon=dialog-information); [ "$result" = "default" ] && xdg-open "$ARGUMENTS") &
```

Where `{title}` is the MR title, `{verdict}` is one of `✅ APPROVED`, `⚠️ CHANGES REQUESTED`, `💬 NEEDS DISCUSSION`, or `⏸️ INCOMPLETE REVIEW`, and the counts are the totals from Step 8. Clicking "Open MR" in the notification opens the MR URL (`$ARGUMENTS`) in the browser.

### Step 10: Clean Up the Worktree

The review is complete — remove the isolated worktree. Substitute `{worktree_path}`
with the path captured in Step 5:

```bash
git worktree remove --force "{worktree_path}" 2>/dev/null
git worktree prune
```

Run this even if earlier steps (Steps 6–9) reported issues, so no worktree is left behind.

## Pipeline Overview

1. **VALIDATE INPUT** → non-empty MR URL

2. **PARSE MR METADATA** → Task(parse-mr-metadata)
   - Output: `{project_id, mr_iid, project_path}` JSON

3. **CONFIGURE AGENTS** → migrate/read `.sissy/review-config.yml` → zenity picker → write `.sissy/review-config.yml` (bash) → `{enabled_agents}`

4. **FETCH MR DATA** → Task(fetch-mr-diffs) → includes `source_branch`

5. **PROVISION WORKTREE** → prune orphans → fetch → `git worktree add --detach origin/<source_branch>` → `{worktree_path}`

6. **ARCHITECTURE DISCOVERY** → Task(discovery, Project Root = worktree)

6b. **READ CODE REVIEW STANDARDS** → Read `${CLAUDE_PLUGIN_ROOT}/rules/code-review-standards.md` (to embed)

6c. **ESTABLISH COMPLETION CONTRACT** → embed `rules/initial-review-completeness.md`, fix scope/head, allocate coverage reports

7. **SPAWN ENABLED REVIEW AGENTS** (parallel, single message) → Task × enabled_agents
   - Each receives embedded Code Review Standards + Initial Review Completeness + Diffs + Architecture Context + Project Root (worktree) + scope/report paths
   - Each posts comments directly to GitLab

8. **VERIFY COMPLETION & SUMMARIZE** → validate reports and audit evidence → finish gaps → post summary with scope/limitations (never approve incomplete work)

9. **CLEAN UP WORKTREE** → `git worktree remove` + `prune`

## Important Notes

1. **Self-contained**: There is no `sissy-setup`. This command handles config, worktree provisioning, review, and cleanup in one run.
2. **Isolation**: The review reads a detached worktree mirroring `origin/<source_branch>`. Your main working tree — including uncommitted, unstaged changes — is never touched.
3. **Config location**: `.sissy/review-config.yml` is read and written in your **main repo**, not the worktree. If it is absent, an existing `.claude/review-config.yml` is copied there once and left untouched. It is your per-project preference, independent of the branch.
4. **Deterministic config write**: The picker writes the YAML with a bash heredoc/loop, not the Write tool, so the save cannot silently fail.
5. **Concurrent reviews are safe**: each run uses a uniquely-named worktree and removes only its own, so multiple reviews can run against the same repo at once.
6. **MR Metadata Parser**: MUST complete before fetch (needs project_id and mr_iid).
7. **Discovery Agent**: MUST complete before spawning review agents (uses Sonnet). It explores the worktree via the `Project Root` input.
8. **Code Review Standards**: Orchestrator reads `${CLAUDE_PLUGIN_ROOT}/rules/code-review-standards.md` and embeds the full content in each agent's prompt.
9. **Parallel Reviews**: All enabled review agents MUST be spawned in a single message (use Opus).
10. **Direct Comments**: Each agent posts its own comments directly to GitLab; the orchestrator only posts the final summary note.
11. **Agent files**: Do NOT read agent files (security.md, react.md, etc.) before spawning. Use `@agents/foo.md` syntax in each agent's prompt — this resolves inside the subagent's context, not the orchestrator's.

## User Project Setup

For best results, users should have these files in their project:

- `.claude/rules/tech-stack.md` - Project technology stack
- `.claude/rules/component-boilerplate.md` - Component patterns
- `.claude/rules/services-guideline.md` - Service layer patterns
- `.claude/rules/data-flow.md` - Data architecture

`.sissy/review-config.yml` is created and maintained by this command's agent
picker — you don't need to create it by hand. If these rule files don't exist,
agents will still work but provide more generic feedback.
