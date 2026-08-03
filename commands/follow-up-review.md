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
4. For addressed **and disagreed** threads, provisions an isolated worktree of the MR's **source branch** and spawns evaluator agents against the current code in that worktree
5. Resolves verified fixes; replies with feedback on inadequate fixes; and posts a position on each disagreement (agree / counter / your-call) — **never resolving a disagreement**, so you keep the final call
6. Posts a summary note and removes the worktree

Your default checkout — including uncommitted, unstaged changes — is never
modified. The worktree is a detached mirror of `origin/<source_branch>`, built
from the MR's own branch (so it can never evaluate against the wrong code) and
removed when the review finishes. If there are **no addressed threads**, no
worktree is created at all.

### Developer Workflow

After a review, developers should reply to each thread:

- If they've addressed it: reply with "done"/"fixed"/etc., or simply describe the change they made ("extracted a shared component", "deleted the unused export") — a plain description counts just as well.
- If they disagree: reply explaining why. A reply that declines or defers the change is treated as a disagreement — Police Sissy will post a position on it (agree / counter / your-call) but never resolve it, leaving the final call to a human. Tone doesn't change the classification; the conclusion does.

## Instructions

### Step 1: Parse MR Metadata

**Spawn the MR Metadata Parser Agent** to extract project info and MR IID from the URL.

Read and execute the parser agent instructions from `@agents/parse-mr-metadata.md` with the MR URL as input: `{$ARGUMENTS}`

**Wait for the Parser Agent to complete** and parse its JSON output to get:

- `project_id`
- `mr_iid`
- `project_path`

### Step 2: Fetch and Classify Discussions

First, resolve the plugin root so it can be passed to the classifier as a
literal absolute path (the classifier's helper script lives under it, and
`${CLAUDE_PLUGIN_ROOT}` is not guaranteed to be set inside a spawned subagent's
shell — resolving it here, where it is available, removes that dependency):

```bash
echo "PLUGIN_ROOT=${CLAUDE_PLUGIN_ROOT}"
```

Store the printed path as `{plugin_root}`.

Spawn the Discussion Classifier Agent:

Read and execute the classifier agent instructions from `@agents/classify-mr-discussions.md` with:
- `project_id`: from Step 1
- `mr_iid`: from Step 1
- `plugin_root`: `{plugin_root}` from the command above

Wait for the agent to complete. Parse its JSON output to get:
- `addressed`: array of addressed threads with full note data and file positions
- `disagreements`: array of `{discussion_id, new_path, reason}` for threads where the developer pushed back
- `total_unresolved`, `addressed_count`, `disagreement_count`, `untouched_count`

**Consistency guardrail (do this before proceeding):** the classifier decides
`untouched` mechanically (a thread with a developer reply can never be
`untouched`), so the counts must reconcile. Verify:

- `addressed_count == len(addressed)`
- `disagreement_count == len(disagreements)`
- `addressed_count + disagreement_count + untouched_count == total_unresolved`

If any check fails, or the output contains a `warnings` array, **do not silently
proceed** — print a short warning noting the discrepancy (and any `warnings`
entries) so the run is auditable, then continue with the numbers as returned.

If `addressed_count == 0` **and** `disagreement_count == 0`, skip directly to Step 7 (post summary). **No worktree is created and no cleanup is needed** in that case. If either count is > 0, continue.

### Step 3: Fetch MR Data

**Only proceed with Steps 3–6 if `{addressed_count} > 0` OR `{disagreement_count} > 0`.**

Spawn the MR Diff Fetcher Agent:

Read and execute the fetcher agent instructions from `@agents/fetch-mr-diffs.md` with:
- `project_id`: from Step 1
- `mr_iid`: from Step 1
- `file_filter`: array of unique `new_path` values from **both** the `addressed` and `disagreements` threads classified in Step 2 (union; exclude nulls)

Wait for the agent to complete. Parse its JSON output to get:
- `source_branch`: the MR's source branch (needed to provision the worktree)
- `description`: MR description (for discovery context)
- `changed_files`: array of `{new_path}` — the file paths referenced by addressed or disagreed threads

### Step 3b: Provision the Isolated Worktree

Create a detached worktree mirroring the MR's `source_branch`, re-fetched so it
holds the developer's latest pushed code. This never touches your working tree.
Substitute `{source_branch}` with the value from Step 3:

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
- `WORKTREE_PATH=<path>` → store `<path>` as `{worktree_path}` for Steps 4, 5, and 8. A disagreement-only MR (no addressed threads) still reaches this step, so the worktree is available to judge pushbacks against.

### Step 4: Architecture Discovery

**Spawn the Architecture Discovery Agent** to gather project context.

Read and execute the discovery agent instructions from `@agents/discovery.md` with:

- **Project Root**: {worktree_path from Step 3b}
- **Changed Files**: List all `new_path` values from `changed_files`, one per line
- **MR Description**: {description from Step 3 if available}

**Wait for the Discovery Agent to complete** and store its output as `{architecture_context}`.

### Step 5: Spawn Thread Evaluator Agents (Parallel, Batched by File)

**Group addressed and disagreement threads by file before spawning agents.**

Build a map of buckets keyed by `new_path` (use the string `"__general__"` for threads where `new_path` is null):

```
buckets = {}
for each thread in addressed:
  key = thread.new_path ?? "__general__"
  buckets[key].push({ ...thread, kind: "addressed" })
for each thread in disagreements:
  key = thread.new_path ?? "__general__"
  buckets[key].push({ ...thread, kind: "disagreement" })
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
**Kind:** {thread.kind}

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

Wait for all Thread Evaluator Agents to complete. Each agent returns a JSON **array** — flatten all arrays into a single list of verdict objects. `resolved`/`insufficient` (addressed) verdicts carry `discussion_id`, `verdict`, `explanation`, `confidence`; `conceded`/`countered`/`unsure` (disagreement) verdicts carry `discussion_id`, `verdict`, `reply`, `confidence`.

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

**For `verdict == "conceded" | "countered" | "unsure"` (Kind: disagreement):**

Post the evaluator's `reply` to the thread and **do NOT resolve it** — the human decides. Pick the badge/headline by verdict:

| verdict | badge | headline |
| --- | --- | --- |
| `conceded` | `✅ [agrees]` | Your pushback holds |
| `countered` | `↩️ [counter]` | Concern may still stand |
| `unsure` | `🤔 [your-call]` | Judgment call |

```
mcp__gitlab-mcp__create_merge_request_discussion_note(
  project_id: "{project_id}",
  merge_request_iid: "{mr_iid}",
  discussion_id: "{discussion_id}",
  body: "> SubAgent: 👮 Police Sissy (Follow-Up Review)\n> **{badge}** {headline}\n\n{reply}\n\n_You have the final call on this thread — resolve it or reply if you disagree._"
)
```

Never call `resolve_merge_request_thread` for a disagreement verdict.

Store counts: `{resolved_count}`, `{insufficient_count}`, `{conceded_count}`, `{countered_count}`, `{unsure_count}`. The three disagreement counts must sum to `{disagreement_count}`.

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
| 💬 Developer disagreed — replied, your decision (✅ {conceded_count} agree · ↩️ {countered_count} counter · 🤔 {unsure_count} your-call) | {disagreement_count} |
| 👀 Untouched — skipped (awaiting developer)           | {untouched_count}    |

{If resolved_count > 0:}

### Resolved Threads

{For each resolved thread, list: brief description of the original concern and confirmation}

{If insufficient_count > 0:}

### Threads Needing More Work

{For each insufficient thread, list: brief description and what remains unaddressed}

{If disagreement_count > 0:}

### Disagreements — Police Sissy Replied, Your Decision

{For each disagreement, list its `new_path` (or "general comment" if null), Police Sissy's stance (✅ agrees / ↩️ counter / 🤔 your-call), and a one-line gist of the reply. Police Sissy has posted a position in each thread but resolved none — you make the final call.}

---

{If all addressed threads are resolved AND disagreement_count == 0 AND untouched_count == 0:}
✅ **All review threads are addressed.** This MR may be ready to merge pending final human approval.

{Else if untouched_count > 0:}
👀 **{untouched_count} thread(s) still awaiting developer action.** The developer should reply to addressed threads and run follow-up again.

{Else if insufficient_count > 0:}
🔄 **{insufficient_count} thread(s) need further attention.** Please address the remaining concerns and run follow-up again.

{Else if disagreement_count > 0:}
💬 **{disagreement_count} disagreement(s) replied — awaiting your decision.** Review Police Sissy's position in each thread and resolve it or reply.
```

After the summary note is posted, run:

```bash
(result=$(notify-send "👮 Follow-Up Review Complete" "✅ {resolved_count} resolved · 🔄 {insufficient_count} needs work · 💬 {disagreement_count} replied · 👀 {untouched_count} untouched" --action="default=Open MR" --wait --icon=dialog-information); [ "$result" = "default" ] && xdg-open "$ARGUMENTS") &
```

Where each count comes from the verdict tallies collected in Step 6. Clicking "Open MR" in the notification opens the MR URL (`$ARGUMENTS`) in the browser.

### Step 8: Clean Up the Worktree

If a worktree was provisioned in Step 3b (i.e. `addressed_count > 0` OR `disagreement_count > 0`), remove it.
Substitute `{worktree_path}` with the path captured in Step 3b:

```bash
git worktree remove --force "{worktree_path}" 2>/dev/null
git worktree prune
```

Run this even if earlier steps reported issues, so no worktree is left behind. If
`addressed_count == 0` and `disagreement_count == 0`, there is no worktree to remove — skip this step.

## Pipeline Overview

1. **PARSE MR METADATA** → Task(parse-mr-metadata)
   - Output: `{project_id, mr_iid, project_path}` JSON

2. **FETCH DISCUSSIONS + CLASSIFY THREADS** → Task(classify-mr-discussions)
   - Fetches, paginates, filters, splits `untouched` mechanically, and classifies
     the has-reply threads (`addressed` vs `disagreement`) via judgment
   - Output: `{addressed, disagreements, total_unresolved, addressed_count, disagreement_count, untouched_count}` JSON
   - Guardrail: counts must reconcile against `total_unresolved` (see Step 2)
   - If 0 addressed AND 0 disagreements → skip to summary (no worktree)

3. **FETCH MR DATA** → Task(fetch-mr-diffs, file_filter)
   - Output: `{source_branch, description, changed_files}` JSON

3b. **PROVISION WORKTREE** → prune orphans → fetch → `git worktree add --detach origin/<source_branch>` → `{worktree_path}`

4. **ARCHITECTURE DISCOVERY** → Task(discovery, Project Root = worktree)

5. **SPAWN THREAD EVALUATORS** (parallel, single message) → Task(thread-evaluator) × file_buckets
   - Threads grouped by `new_path` (null threads → `__general__` bucket)
   - One agent per bucket, each reads its file once from the worktree
   - Each returns per-thread verdicts: addressed → `resolved|insufficient` + `explanation`; disagreement → `conceded|countered|unsure` + `reply`

6. **PROCESS VERDICTS** (serial)
   - resolved → resolve thread silently via MCP
   - insufficient → reply with explanation via MCP
   - conceded|countered|unsure → post reply, never resolve

7. **POST SUMMARY NOTE** → GitLab MCP

8. **CLEAN UP WORKTREE** → `git worktree remove` + `prune` (only if one was created)

## Important Notes

1. **Self-contained**: There is no `sissy-setup`. This command provisions the worktree of the MR's source branch itself, evaluates, and cleans up in one run.
2. **Isolation**: Evaluators read the detached worktree, never the reviewer's working tree. Because the worktree is built from the MR's own `source_branch`, it can never evaluate fixes against the wrong branch.
3. **Discussion Classifier**: Owns the entire fetch + paginate + filter + classify pipeline. Returns compact JSON — discussions never touch main context. `untouched` (threads with no developer reply) is decided mechanically by a helper script, so a replied-to thread can never be misfiled as untouched; the model only judges `addressed` vs `disagreement` on threads that have a reply. Note bodies for `addressed` threads are extracted deterministically, not transcribed by the model.
4. **Last reply wins**: A thread is classified by the intent of its last non-system reply. A long or polite reply that declines the change is a `disagreement`, not `addressed` — the conclusion is judged, not the tone.
5. **Discovery Agent**: Only spawned if there are addressed **or disagreed** threads (uses Sonnet). Explores the worktree via its `Project Root` input.
6. **Parallel Evaluation**: All thread evaluator agents MUST be spawned in a single message (use Opus).
7. **Serial Processing**: Verdicts are processed serially to avoid race conditions on GitLab state.
8. **No new issues**: Police Sissy only evaluates existing concerns. It does NOT raise new issues.
9. **Benefit of the doubt**: When evidence is ambiguous, resolve in the developer's favor.
10. **Skip policy**: Untouched threads are always skipped (awaiting the developer). Disagreements are NOT skipped — Police Sissy posts a position in each, but never auto-resolves; the human decides.
11. **File reads**: Evaluators read source files from the worktree at `{worktree_path}/{File Path}` (the `Project Root` passed in each prompt). If a file is absent (e.g., deleted in the MR), the evaluator falls back to the diff text.
12. **Concurrent reviews are safe**: each run uses a uniquely-named worktree and removes only its own, so multiple reviews can run against the same repo at once.
```
