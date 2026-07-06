---
model: sonnet
description: Follow-up review for a GitLab MR — evaluates addressed threads and resolves or replies
---

# Follow-Up Review

Evaluate developer fixes on merge request `$ARGUMENTS` by checking which review threads have been acknowledged by the developer.

## How It Works

This command:

1. Fetches all unresolved discussion threads on the MR
2. Checks each thread for developer replies to classify them
3. Categorizes threads into: addressed (developer's reply signals they tried to fix it), disagreement (developer's reply pushes back on the concern), or untouched
4. For addressed threads, spawns evaluator agents to verify the fix against current code
5. Resolves verified threads; replies with feedback on inadequate fixes
6. Posts a summary note

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

### Step 1b: Locate the Review Worktree

`/sissy-setup` prepared an isolated worktree (a detached mirror of the MR branch,
re-fetched so it holds the developer's latest pushed code) that the evaluators
read from. Find it:

```bash
GIT_COMMON_DIR=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
STATE_FILE="$GIT_COMMON_DIR/sissy-review-worktree"
if [ ! -f "$STATE_FILE" ]; then
  echo "NO_STATE"
else
  WORKTREE_PATH=$(sed -n 's/^worktree_path=//p' "$STATE_FILE")
  if [ -z "$WORKTREE_PATH" ] || [ ! -d "$WORKTREE_PATH" ]; then
    echo "MISSING_WORKTREE"
  else
    echo "WORKTREE_PATH=$WORKTREE_PATH"
  fi
fi
```

Interpret the output:

- `NO_STATE` → **stop immediately** and print: `❌ No prepared review worktree. Run /sissy-setup <branch> first.`
- `MISSING_WORKTREE` → **stop immediately** and print: `❌ The review worktree is missing (removed or lost on reboot). Re-run /sissy-setup <branch>.`
- `WORKTREE_PATH=<path>` → store `<path>` as `{worktree_path}` for use in Steps 4, 5, and 8.

### Step 2: Fetch and Classify Discussions

Spawn the Discussion Classifier Agent:

Read and execute the classifier agent instructions from `@agents/classify-mr-discussions.md` with:
- `project_id`: from Step 1
- `mr_iid`: from Step 1

Wait for the agent to complete. Parse its JSON output to get:
- `addressed`: array of addressed threads with full note data and file positions
- `addressed_count`, `disagreement_count`, `untouched_count`

If `addressed_count == 0`, skip to Step 7 (post summary).

### Step 3: Fetch MR Data

**Only proceed with Steps 3-5 if `{addressed_count} > 0`. If zero addressed threads, skip directly to Step 7.**

Spawn the MR Diff Fetcher Agent:

Read and execute the fetcher agent instructions from `@agents/fetch-mr-diffs.md` with:
- `project_id`: from Step 1
- `mr_iid`: from Step 1
- `file_filter`: array of unique `new_path` values from the `addressed` threads classified in Step 2 (exclude nulls)

Wait for the agent to complete. Parse its JSON output to get:
- `description`: MR description (for discovery context)
- `changed_files`: array of `{new_path}` — the file paths referenced by addressed threads

### Step 4: Architecture Discovery

**Spawn the Architecture Discovery Agent** to gather project context.

Read and execute the discovery agent instructions from `@agents/discovery.md` with:

- **Project Root**: {worktree_path from Step 1b}
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

**Project Root:** {worktree_path from Step 1b}
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

### Step 8: Clean Up the Review Worktree

The follow-up is complete — remove the isolated worktree and its state file. **Run
this on every path**, including when Step 2 found zero addressed threads and you
skipped ahead to Step 7. The block is self-contained (it re-reads the path from
the state file):

```bash
GIT_COMMON_DIR=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
STATE_FILE="$GIT_COMMON_DIR/sissy-review-worktree"
WORKTREE_PATH=$(sed -n 's/^worktree_path=//p' "$STATE_FILE" 2>/dev/null)
[ -n "$WORKTREE_PATH" ] && git worktree remove --force "$WORKTREE_PATH" 2>/dev/null
git worktree prune
rm -f "$STATE_FILE"
```

To run another review afterward, re-run `/sissy-setup <branch>` first.

## Pipeline Overview

1. **PARSE MR METADATA** → Task(parse-mr-metadata)
   - Output: `{project_id, mr_iid, project_path}` JSON

2. **FETCH DISCUSSIONS + CLASSIFY THREADS** → Task(classify-mr-discussions)
   - Fetches, paginates, filters, and classifies all unresolved threads
   - Output: `{addressed, addressed_count, disagreement_count, untouched_count}` JSON

3. **FETCH MR DATA** → Task(fetch-mr-diffs, file_filter) (skip if 0 addressed)
   - Fetches only files referenced by addressed threads
   - Output: `{description, changed_files}` JSON

4. **ARCHITECTURE DISCOVERY** → Task(discovery agent)
   - Output: Architecture context markdown

5. **SPAWN THREAD EVALUATORS** (parallel, single message) → Task(thread-evaluator) × file_buckets
   - Threads are grouped by `new_path` before spawning (null threads → `__general__` bucket)
   - One agent per bucket (file), each evaluates all threads on that file in one pass
   - All spawned in parallel (single message)
   - Each reads its file once from disk (falls back to diff if file absent)
   - Each returns: array of `{verdict, explanation, confidence}` JSON objects, one per thread

6. **PROCESS VERDICTS** (serial)
   - resolved → resolve thread silently via MCP
   - insufficient → reply with explanation via MCP

7. **POST SUMMARY NOTE** → GitLab MCP
   - Police Sissy summary with counts and verdicts

## Important Notes

1. **MR Metadata Parser**: MUST complete first to get project_id and mr_iid
2. **Discussion Classifier**: Owns the entire fetch + paginate + filter + classify pipeline. Returns compact JSON — discussions never touch main context.
3. **Last reply wins**: A thread is classified by the intent of its last non-system reply
4. **Discovery Agent**: Only spawned if there are addressed threads to evaluate (uses Sonnet)
5. **Parallel Evaluation**: All thread evaluator agents MUST be spawned in a single message (use Opus)
6. **Serial Processing**: Verdicts are processed serially to avoid race conditions on GitLab state
7. **No new issues**: Police Sissy only evaluates existing concerns. It does NOT raise new issues.
8. **Benefit of the doubt**: When evidence is ambiguous, resolve in the developer's favor
9. **Skip policy**: Threads where the developer disagreed and untouched threads are always skipped
10. **File reads**: Evaluators read source files from the isolated review worktree at `{worktree_path}/{File Path}` (the `Project Root` passed in each prompt), not the reviewer's own working tree. `/sissy-setup` must have prepared the worktree before running this command. If a file is absent (e.g., deleted in the MR), the evaluator falls back to the diff text.
