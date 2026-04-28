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

### Step 2: Fetch Unresolved Discussions and Classify Threads

Fetch all MR discussions using MCP:

```
mcp__gitlab-mcp__mr_discussions(project_id: "{project_id}", merge_request_iid: "{mr_iid}", per_page: 100)
```

If there are more than 100 discussions, paginate by calling again with `page: 2`, `page: 3`, etc. until an empty page is returned.

**Filter** to keep only unresolved, resolvable discussion threads:

- `individual_note == false` (real thread, not a standalone note)
- `notes[0].resolvable == true`
- `notes[0].resolved == false`
- `notes[0].system == false`

**Classify** each unresolved thread into one of three categories by examining the non-system notes (`.notes[] | select(.system == false)`):

**Classification rules:**

1. **`addressed`**: The thread has a non-system reply (beyond the original review note) where the developer's **last** reply signals positive intent — they tried to address the concern. Examples: "done", "fixed", "ok", "addressed", "I disagree but did it anyway", "should be good now", etc. Use your judgment to determine if the reply indicates the developer attempted a fix.
2. **`disagreement`**: The thread has a non-system reply (beyond the original review note) where the developer's **last** reply pushes back on the concern itself — they're arguing the original review comment was wrong or unnecessary. Examples: "I don't think this is an issue because...", "This is intentional", "No, this pattern is correct because...", etc.
3. **`untouched`**: The thread has only one non-system note (the original review comment). No developer response yet.

**Note:** A thread is classified by the **intent of its last non-system reply**. If the developer first disagreed and later replied "done", the thread is `addressed`.

Store the classified threads and counts: `{addressed_count}`, `{disagreement_count}`, `{untouched_count}`

For `addressed` threads, extract and store:

- `discussion_id` (`.id` of the discussion)
- All non-system note bodies and authors
- File position info (`.notes[0].position.new_path`, `.notes[0].position.new_line`) if available

If there are **zero addressed threads**, skip to Step 7 (post summary) with a note that no threads have been addressed yet.

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

- **Changed Files**: List all `new_path` values from `changed_files`, one per line
- **MR Description**: {description from Step 3 if available}

**Wait for the Discovery Agent to complete** and store its output as `{architecture_context}`.

### Step 5: Spawn Thread Evaluator Agents (Parallel)

Launch one Thread Evaluator Agent per **addressed** thread, all in a single message with multiple Task tool calls (parallel execution).

Each agent prompt should include:

```
## Thread to Evaluate

**Discussion ID:** {discussion.id}
**File Path:** {discussion.new_path or "General comment (no file)" if null}
**Original Line:** {discussion.new_line or "N/A" if null}

### Original Review Thread

{For each note in discussion.notes (where system == false):}
**[{note.author}]:**
{note.body}

---

{End for each}

---

## Architecture Context

{architecture_context}

---

{Content from @agents/thread-evaluator.md}
```

**Task Tool Parameters for ALL thread evaluator agents:**

- `subagent_type: "general-purpose"`

### Step 6: Process Verdicts

Wait for all Thread Evaluator Agents to complete. Parse each agent's JSON output to get `discussion_id`, `verdict`, `explanation`, and `confidence`.

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

## Pipeline Overview

1. **PARSE MR METADATA** → Task(parse-mr-metadata)
   - Output: `{project_id, mr_iid, project_path}` JSON

2. **FETCH DISCUSSIONS + CLASSIFY THREADS** → MCP: mr_discussions (paginate if >100)
   - Fetch all unresolved discussion threads
   - Classify by developer's last reply intent
   - Buckets: `addressed / disagreement / untouched`

3. **FETCH MR DATA** → Task(fetch-mr-diffs, file_filter) (skip if 0 addressed)
   - Fetches only files referenced by addressed threads
   - Output: `{description, changed_files}` JSON

4. **ARCHITECTURE DISCOVERY** → Task(discovery agent)
   - Output: Architecture context markdown

5. **SPAWN THREAD EVALUATORS** (parallel, single message) → Task(thread-evaluator) × addressed_threads
   - One agent per addressed thread
   - All spawned in parallel (single message)
   - Each reads its file directly from disk (falls back to diff if file absent)
   - Each returns: `{verdict, explanation, confidence}` JSON

6. **PROCESS VERDICTS** (serial)
   - resolved → resolve thread silently via MCP
   - insufficient → reply with explanation via MCP

7. **POST SUMMARY NOTE** → GitLab MCP
   - Police Sissy summary with counts and verdicts

## Important Notes

1. **MR Metadata Parser**: MUST complete first to get project_id and mr_iid
2. **Reply-based detection**: Classification uses MCP only — no curl or REST API needed. The developer's last non-system reply is evaluated by intent: positive signals (done, fixed, ok, etc.) → `addressed`; pushback on the concern → `disagreement`
3. **Last reply wins**: A thread is classified by the intent of its last non-system reply
4. **Discovery Agent**: Only spawned if there are addressed threads to evaluate (uses Sonnet)
5. **Parallel Evaluation**: All thread evaluator agents MUST be spawned in a single message (use Opus)
6. **Serial Processing**: Verdicts are processed serially to avoid race conditions on GitLab state
7. **No new issues**: Police Sissy only evaluates existing concerns. It does NOT raise new issues.
8. **Benefit of the doubt**: When evidence is ambiguous, resolve in the developer's favor
9. **Skip policy**: Threads where the developer disagreed and untouched threads are always skipped
10. **File reads**: Evaluators read source files directly from the local working directory. The source branch must be checked out before running this command. If a file is absent (e.g., deleted in the MR), the evaluator falls back to the diff text.
