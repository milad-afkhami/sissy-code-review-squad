---
model: sonnet
description: Follow-up review for a GitLab MR — provisions an isolated worktree, evaluates addressed threads, and resolves or replies
---

# Follow-Up Review

Evaluate developer fixes on merge request `$ARGUMENTS` by checking which review threads have been acknowledged by the developer.

## How It Works

This is a single self-contained command — there is no separate setup step:

1. Fetches all unresolved discussion threads on the MR
2. Checks each thread for developer replies to classify them
3. Categorizes threads into: addressed (developer's reply signals they tried to fix it), disagreement (developer's reply pushes back on the concern), or untouched
4. For addressed threads, provisions an isolated worktree of the MR's **source branch** and spawns evaluator agents to verify each fix against the current code in that worktree
5. Resolves verified threads; replies with feedback on inadequate fixes
6. Posts a summary note and removes the worktree

Your default checkout — including uncommitted, unstaged changes — is never
modified. The worktree is a detached mirror of `origin/<source_branch>`, built
from the MR's own branch (so it can never evaluate against the wrong code) and
removed when the review finishes. If there are **no addressed threads**, no
worktree is created at all.

### Developer Workflow

After a review, developers should reply to each thread:

- If they've addressed it: reply with something positive like "done", "fixed", "ok", "addressed", etc.
- If they disagree: reply explaining why they disagree with the concern

## Instructions

### Step 1: Parse MR Metadata

**Spawn the MR Metadata Parser Agent** to extract project info and MR IID from the URL.

Read and execute the parser agent instructions from `@agents/parse-mr-metadata.md` with the MR URL as input: `{$ARGUMENTS}`

**Wait for the Parser Agent to complete** and parse its JSON output to get:

- `project_id`
- `mr_iid`
- `project_path`

### Step 2: Fetch and Classify Discussions

Spawn the Discussion Classifier Agent:

Read and execute the classifier agent instructions from `@agents/classify-mr-discussions.md` with:
- `project_id`: from Step 1
- `mr_iid`: from Step 1

Wait for the agent to complete. Parse its JSON output to get:
- `addressed`: array of addressed threads with full note data and file positions
- `addressed_count`, `disagreement_count`, `untouched_count`

If `addressed_count == 0`, skip directly to Step 7 (post summary). **No worktree is created and no cleanup is needed** in that case.

### Step 3: Fetch MR Data

**Only proceed with Steps 3–6 if `{addressed_count} > 0`.**

Spawn the MR Diff Fetcher Agent:

Read and execute the fetcher agent instructions from `@agents/fetch-mr-diffs.md` with:
- `project_id`: from Step 1
- `mr_iid`: from Step 1
- `file_filter`: array of unique `new_path` values from the `addressed` threads classified in Step 2 (exclude nulls)

Wait for the agent to complete. Parse its JSON output to get:
- `source_branch`: the MR's source branch (needed to provision the worktree)
- `description`: MR description (for discovery context)
- `changed_files`: array of `{new_path}` — the file paths referenced by addressed threads

### Step 3b: Provision the Isolated Worktree

Create a detached worktree mirroring the MR's `source_branch`, re-fetched so it
holds the developer's latest pushed code. This never touches your working tree.
Substitute `{source_branch}` with the value from Step 3:

```bash
# Remove orphaned review worktrees from prior crashed runs.
# Safe because only one review runs at a time — any existing sissy worktree is a
# leftover, since this run has not created its own yet.
git worktree list --porcelain | sed -n 's/^worktree //p' | grep -F '/sissy-review-wt-' | while read -r wt; do
  git worktree remove --force "$wt" 2>/dev/null
done
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
- `WORKTREE_PATH=<path>` → store `<path>` as `{worktree_path}` for Steps 4, 5, and 8.

### Step 4: Architecture Discovery

**Spawn the Architecture Discovery Agent** to gather project context.

Read and execute the discovery agent instructions from `@agents/discovery.md` with:

- **Project Root**: {worktree_path from Step 3b}
- **Changed Files**: List all `new_path` values from `changed_files`, one per line
- **MR Description**: {description from Step 3 if available}

**Wait for the Discovery Agent to complete** and store its output as `{architecture_context}`.

### Step 5: Spawn Thread Evaluator Agents (Parallel, Batched by File)

**Group addressed threads by file before spawning agents.**

Build a map of buckets keyed by `new_path` (use the string `"__general__"` for threads where `new_path` is null):

```
buckets = {}
for each thread in addressed:
  key = thread.new_path ?? "__general__"
  buckets[key].push(thread)
```

Launch **one Thread Evaluator Agent per bucket**, all in a single message with multiple Task tool calls (parallel execution). Each agent handles all threads for one file (or all general comments) in a single pass.

Each agent prompt should include:

```
## File Under Review

**Project Root:** {worktree_path from Step 3b}
**File Path:** {bucket_key or "General comment (no file)" if bucket_key == "__general__"}

## Threads to Evaluate

{For each thread in this bucket:}
---

**Discussion ID:** {thread.id}
**Original Line:** {thread.new_line or "N/A" if null}

### Original Review Thread

{For each note in thread.notes (where system == false):}
**[{note.author}]:**
{note.body}

---

{End for each note}

{End for each thread}

---

## Architecture Context

{architecture_context}

---

{Content from @agents/thread-evaluator.md}
```

**Task Tool Parameters for ALL thread evaluator agents:**

- `subagent_type: "general-purpose"`

### Step 6: Process Verdicts

Wait for all Thread Evaluator Agents to complete. Each agent returns a JSON **array** — flatten all arrays into a single list of verdict objects, each with `discussion_id`, `verdict`, `explanation`, and `confidence`.

Process each verdict **serially** (to avoid race conditions on GitLab's discussion state):

**For `verdict == "resolved"`:**

Resolve the thread silently (no reply needed):

```
mcp__gitlab-mcp__resolve_merge_request_thread(
  project_id: "{project_id}",
  merge_request_iid: "{mr_iid}",
  discussion_id: "{discussion_id}",
  resolved: true
)
```

**For `verdict == "insufficient"`:**

Post a follow-up reply to the thread explaining what is still missing:

```
mcp__gitlab-mcp__create_merge_request_discussion_note(
  project_id: "{project_id}",
  merge_request_iid: "{mr_iid}",
  discussion_id: "{discussion_id}",
  body: "> SubAgent: 👮 Police Sissy (Follow-Up Review)\n> **🔄 [needs-work]** Not fully addressed\n\n{explanation}\n\n_Please revisit this concern and reply when ready for another follow-up._"
)
```

Store counts: `{resolved_count}`, `{insufficient_count}`

### Step 7: Post Summary Note

**First, read the plugin version:**

```
Read file: ${CLAUDE_PLUGIN_ROOT}/package.json
```

Extract the `version` field and store as `{plugin_version}`.

Create a summary note on the MR using `mcp__gitlab-mcp__create_merge_request_note`:

```markdown
![Police Sissy](https://milad-afkhami.com/images/blog/sissy/police-sissy.jpg){width=300 height=300}

## Follow-Up Review Summary

> **Reviewed by:** Sissy Code Review Squad v{plugin_version} — 👮 Police Sissy (Follow-Up)

### Thread Status

| Outcome                                               | Count                |
| ----------------------------------------------------- | -------------------- |
| ✅ Verified and resolved                              | {resolved_count}     |
| 🔄 Needs more work                                    | {insufficient_count} |
| 💬 Developer disagreed — skipped (needs human review) | {disagreement_count} |
| 👀 Untouched — skipped (awaiting developer)           | {untouched_count}    |

{If resolved_count > 0:}

### Resolved Threads

{For each resolved thread, list: brief description of the original concern and confirmation}

{If insufficient_count > 0:}

### Threads Needing More Work

{For each insufficient thread, list: brief description and what remains unaddressed}

{If disagreement_count > 0:}

### Threads Awaiting Human Review

{List threads where the developer disagreed. A human reviewer should evaluate these.}

---

{If all addressed threads are resolved AND disagreement_count == 0 AND untouched_count == 0:}
✅ **All review threads are addressed.** This MR may be ready to merge pending final human approval.

{Else if untouched_count > 0:}
👀 **{untouched_count} thread(s) still awaiting developer action.** The developer should reply to addressed threads and run follow-up again.

{Else if insufficient_count > 0:}
🔄 **{insufficient_count} thread(s) need further attention.** Please address the remaining concerns and run follow-up again.
```

After the summary note is posted, run:

```bash
(result=$(notify-send "👮 Follow-Up Review Complete" "✅ {resolved_count} resolved · 🔄 {insufficient_count} needs work · 💬 {disagreement_count} disagreed · 👀 {untouched_count} untouched" --action="default=Open MR" --wait --icon=dialog-information); [ "$result" = "default" ] && xdg-open "$ARGUMENTS") &
```

Where each count comes from the verdict tallies collected in Step 6. Clicking "Open MR" in the notification opens the MR URL (`$ARGUMENTS`) in the browser.

### Step 8: Clean Up the Worktree

If a worktree was provisioned in Step 3b (i.e. `addressed_count > 0`), remove it.
Substitute `{worktree_path}` with the path captured in Step 3b:

```bash
git worktree remove --force "{worktree_path}" 2>/dev/null
git worktree prune
```

Run this even if earlier steps reported issues, so no worktree is left behind. If
`addressed_count == 0`, there is no worktree to remove — skip this step.

## Pipeline Overview

1. **PARSE MR METADATA** → Task(parse-mr-metadata)
   - Output: `{project_id, mr_iid, project_path}` JSON

2. **FETCH DISCUSSIONS + CLASSIFY THREADS** → Task(classify-mr-discussions)
   - Fetches, paginates, filters, and classifies all unresolved threads
   - Output: `{addressed, addressed_count, disagreement_count, untouched_count}` JSON
   - If 0 addressed → skip to summary (no worktree)

3. **FETCH MR DATA** → Task(fetch-mr-diffs, file_filter)
   - Output: `{source_branch, description, changed_files}` JSON

3b. **PROVISION WORKTREE** → prune orphans → fetch → `git worktree add --detach origin/<source_branch>` → `{worktree_path}`

4. **ARCHITECTURE DISCOVERY** → Task(discovery, Project Root = worktree)

5. **SPAWN THREAD EVALUATORS** (parallel, single message) → Task(thread-evaluator) × file_buckets
   - Threads grouped by `new_path` (null threads → `__general__` bucket)
   - One agent per bucket, each reads its file once from the worktree
   - Each returns: array of `{verdict, explanation, confidence}` JSON objects

6. **PROCESS VERDICTS** (serial)
   - resolved → resolve thread silently via MCP
   - insufficient → reply with explanation via MCP

7. **POST SUMMARY NOTE** → GitLab MCP

8. **CLEAN UP WORKTREE** → `git worktree remove` + `prune` (only if one was created)

## Important Notes

1. **Self-contained**: There is no `sissy-setup`. This command provisions the worktree of the MR's source branch itself, evaluates, and cleans up in one run.
2. **Isolation**: Evaluators read the detached worktree, never the reviewer's working tree. Because the worktree is built from the MR's own `source_branch`, it can never evaluate fixes against the wrong branch.
3. **Discussion Classifier**: Owns the entire fetch + paginate + filter + classify pipeline. Returns compact JSON — discussions never touch main context.
4. **Last reply wins**: A thread is classified by the intent of its last non-system reply.
5. **Discovery Agent**: Only spawned if there are addressed threads (uses Sonnet). Explores the worktree via its `Project Root` input.
6. **Parallel Evaluation**: All thread evaluator agents MUST be spawned in a single message (use Opus).
7. **Serial Processing**: Verdicts are processed serially to avoid race conditions on GitLab state.
8. **No new issues**: Police Sissy only evaluates existing concerns. It does NOT raise new issues.
9. **Benefit of the doubt**: When evidence is ambiguous, resolve in the developer's favor.
10. **Skip policy**: Threads where the developer disagreed and untouched threads are always skipped.
11. **File reads**: Evaluators read source files from the worktree at `{worktree_path}/{File Path}` (the `Project Root` passed in each prompt). If a file is absent (e.g., deleted in the MR), the evaluator falls back to the diff text.
12. **One review at a time per repo**: the orphan-worktree sweep in Step 3b assumes this.
```
