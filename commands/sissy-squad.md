---
model: opus
description: Run comprehensive code review on a GitLab merge request using 10 specialized agents
---

# Comprehensive Code Review

Review merge request `$ARGUMENTS` using specialized parallel review agents.

## How It Works

This orchestrator:

1. Fetches MR data once
2. Spawns an Architecture Discovery agent to gather project context
3. Spawns 10 specialized review agents in parallel (with context)
4. Collects results and posts a summary

## Instructions

### Step 1: Parse MR Metadata

**Spawn the MR Metadata Parser Agent** to extract project info and MR IID from the URL.

Read and execute the parser agent instructions from `@agents/parse-mr-metadata.md` with the MR URL as input: `{$ARGUMENTS}`

**Wait for the Parser Agent to complete** and parse its JSON output to get:

- `project_id`
- `mr_iid`
- `project_path`

### Step 2: Load Review Configuration

Read the review configuration from the user's project: `.claude/review-config.yml`

If the file doesn't exist, use all agents enabled by default.

**Default Configuration:** All agents enabled unless explicitly disabled in config.

**Agent Keys:** `accessibility`, `security`, `performance`, `seo`, `styling`, `code-quality`, `react`, `typescript`, `git`, `qa`

### Step 3: Fetch MR Data (Once)

Use GitLab MCP to get all data needed by agents (use the dynamically resolved project_id):

```
mcp__gitlab-mcp__get_merge_request(project_id: "{resolved_project_id}", merge_request_iid: "{iid}")
mcp__gitlab-mcp__get_merge_request_diffs(project_id: "{resolved_project_id}", merge_request_iid: "{iid}")
```

Extract and store:

- `title`, `author`, `source_branch`, `target_branch`
- `diff_refs` (base_sha, head_sha, start_sha)
- Full diffs with file paths and changes
- `description`, `labels`

### Step 4: Architecture Discovery

**Before spawning review agents**, spawn the Architecture Discovery agent to gather project context.

Read and execute the discovery agent instructions from `@agents/discovery.md` with:

- **Changed Files**: List all file paths from the diff, one per line
- **MR Description**: {MR description if available}

**Wait for the Discovery Agent to complete** and store its output as `{architecture_context}`.

### Step 5: Spawn Enabled Review Agents in Parallel

Launch only the **enabled agents** simultaneously using a single message with multiple Task tool calls.

**Skip agents not in the `enabled_agents` list.** Log which agents are skipped for transparency.

Each agent prompt should include:

````
## MR Context

**Title:** {title}
**Author:** {author.name} (@{author.username})
**Branch:** {source_branch} → {target_branch}
**MR IID:** {iid}
**Project ID:** {resolved_project_id}

### Diff Refs (for GitLab comments)
- base_sha: {diff_refs.base_sha}
- head_sha: {diff_refs.head_sha}
- start_sha: {diff_refs.start_sha}

---

## Code Review Standards (MUST FOLLOW)

@rules/code-review-standards.md

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

{Content from the agent's specific command file}

````

### Review Agents to Spawn (The Squad)

**Only spawn agents that are in the `enabled_agents` list.**

| Config Key | Agent | Command Content | Focus |
|------------|-------|-----------------|-------|
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
- `model: "opus"` ← Use Opus for highest quality reviews

### Step 6: Collect Results

Wait for all agents to complete using TaskOutput.

Each agent returns:
- Number of blocking issues
- Number of suggestions
- Number of nits
- Key findings summary

### Step 7: Post Summary Note

Create a summary note on the MR using `mcp__gitlab-mcp__create_merge_request_note`:

```markdown
![Puppet Master](https://milad-afkhami.com/images/blog/sissy/puppet-master-sissy.jpg){width=300 height=300}

## Comprehensive Code Review Summary

{If any agents were skipped, show:}
> **Note:** Some agents were skipped for this review: {list of skipped agent names}

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

### Blocking Issues Summary

{List all blocking issues from all agents with file references}

### Key Recommendations

{Top 3-5 most important improvements across all categories}

### Verdict

{One of:}
- ✅ **APPROVED** - No blocking issues, ready to merge
- ⚠️ **CHANGES REQUESTED** - Blocking issues must be resolved
- 💬 **NEEDS DISCUSSION** - Questions need clarification before decision

---

*Reviewed by The Squad: Colorblind Sissy (Accessibility), SecuSissy (Security), TurboSissy (Performance), Canonical Sissy (SEO), ChicSissy (Styling), KISS Sissy (Code Quality), Hooked Sissy (React), Unknown Sissy (TypeScript), Detached-HEAD Sissy (Git), BugSlayer Sissy (QA)*
````

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CODE REVIEW PIPELINE                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. PARSE MR METADATA (Task: MR Parser agent - Haiku)       │
│     ├── Extract MR IID from URL                             │
│     ├── Extract project name from URL                       │
│     ├── Search GitLab for project                           │
│     └── Output: {project_id, mr_iid, project_path} JSON     │
│                                                             │
│  2. LOAD CONFIGURATION                                      │
│     └── Read .claude/review-config.yml (user's project)     │
│                                                             │
│  3. FETCH MR DATA                                           │
│     └── Get MR details + diffs from GitLab                  │
│                                                             │
│  4. ARCHITECTURE DISCOVERY (Task: Explore agent - Sonnet)   │
│     ├── Read .claude/rules/*.md documentation               │
│     ├── Identify affected apps/packages/domains             │
│     ├── Sample code patterns where docs missing             │
│     ├── Find existing abstractions to recommend             │
│     └── Output: Clean Architecture Context markdown         │
│                                                             │
│  5. SPAWN ENABLED REVIEW AGENTS (in parallel - Opus)        │
│     ├── Only spawn agents enabled in config                 │
│     ├── All receive: Diffs + Architecture Context +         │
│     │   Code Review Standards (@rules/ reference resolved)  │
│     ├── Each posts comments directly to GitLab              │
│     └── Each returns: Issue counts + findings               │
│                                                             │
│  6. COLLECT & SUMMARIZE                                     │
│     ├── Show skipped agents in summary                      │
│     └── Post summary note to MR                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Important Notes

1. **MR Metadata Parser**: MUST complete first to get project_id and mr_iid (uses Haiku for efficiency)
2. **Configuration**: Read `.claude/review-config.yml` from user's project to determine enabled agents
3. **Discovery Agent**: MUST complete before spawning review agents (uses Sonnet)
4. **Parallel Reviews**: All enabled review agents MUST be spawned in a single message (use Opus)
5. **Context Sharing**: All review agents receive the same Architecture Context
6. **Code Review Standards**: The `@rules/code-review-standards.md` reference in the prompt template will be resolved to include the full standards (comment format, summary format, cover images)
7. **Direct Comments**: Each agent posts its own comments directly to GitLab
8. **Orchestrator Summary**: Only creates the final summary note (shows skipped agents)

## User Project Setup

For best results, users should have these files in their project:

- `.claude/review-config.yml` - Agent enablement (copy from plugin's templates/)
- `.claude/rules/tech-stack.md` - Project technology stack
- `.claude/rules/component-boilerplate.md` - Component patterns
- `.claude/rules/services-guideline.md` - Service layer patterns
- `.claude/rules/data-flow.md` - Data architecture

If these files don't exist, agents will still work but provide more generic feedback.
