# Performance Refactor Plan — Sissy Code Review Squad

**Repo:** `/home/milad/Desktop/projects/sissy-code-review-squad`

---

## Problem Statement

The `follow-up-review` command took ~1 hour on a 60-thread MR. Root causes are structural:

1. **Main orchestrator chunk-reads large MCP payloads** — discussions and diffs fetched into main context grow with MR size. Claude re-sends all context bytes on every turn (even if cached), so large payloads penalize every subsequent step.
2. **Classifier subagent broke its JSON contract** — returned prose instead of JSON, forcing the orchestrator to redo extraction inline with sequential chunk-reads + an ad-hoc Python script.
3. **Diff payload in main context** — both `sissy-squad` and `follow-up-review` call `get_merge_request_diffs` in the orchestrator. On large MRs the raw diff payload lives in main context for the entire rest of the run.

Both commands share the same Step 3 anti-pattern. Both benefit from the same fixes.

---

## Current Version: 1.8.0

---

## Agent File Reference Syntax (critical — do not confuse these)

Two distinct patterns are used in command and agent files:

| Syntax | Meaning | Used for |
|--------|---------|----------|
| `@agents/foo.md` | Invoke `foo` as a **subagent** at runtime | `classify-mr-discussions`, `fetch-mr-diffs`, `discovery`, `parse-mr-metadata` |
| `${CLAUDE_PLUGIN_ROOT}/rules/foo.md` | **Read file contents** and embed verbatim in the prompt | `code-review-standards` |

Using `${CLAUDE_PLUGIN_ROOT}/...` on an agent file embeds its raw markdown text into the prompt instead of running it as a subagent — a silent correctness bug that produces no error but completely changes behavior.

---

## Decisions Made (do not re-debate these)

- **Fix A and Fix B are Phase 1** — purely structural, zero accuracy risk.
- **Architecture discovery is kept** in `follow-up-review` — removing it risks evaluators marking fixes as "resolved" when the developer fixed the surface symptom but used an inconsistent pattern.
- **Per-thread evaluators are kept** (not batched per-file) — multi-file review comments would be silently mis-evaluated if batched. Per-thread is safer. Batching deferred to Phase 2.2.
- **`fetch-mr-diffs` is shared** between `sissy-squad` and `follow-up-review`.
- **`follow-up-review` uses `file_filter`** when calling `fetch-mr-diffs` — only fetch diffs for files referenced by addressed threads.
- **Evaluators read source files from disk** (Phase 2.1, implemented in v1.5.0) — the source branch must be checked out locally when running follow-up-review.

---

## What Has Been Implemented

### ✅ Phase 1 — Fix A: `agents/classify-mr-discussions.md` (v1.6.0)

Haiku subagent that owns the full discussions pipeline: fetch, paginate, filter, classify, extract. Main orchestrator receives one compact JSON blob. `commands/follow-up-review.md` Step 2 delegates to this agent.

**Known bug fixed in v1.6.2:** The Python one-liner for handling oversized MCP output had the wrong format assumption. The actual persisted file format from `mcp__gitlab-mcp__mr_discussions` is plain JSON `{"items": [...]}` — not the wrapped `[{type:"text", text:"..."}]` format the original one-liner assumed.

Current correct one-liner in `agents/classify-mr-discussions.md`:
```bash
cat /path/to/file.json | python3 -c "import json,sys; data=json.load(sys.stdin); items=data.get('items', data) if isinstance(data, dict) else data; print(json.dumps(items))"
```

### ✅ Phase 1 — Fix B: `agents/fetch-mr-diffs.md` (v1.6.0)

Haiku subagent that fetches MR metadata and diffs, with optional `file_filter`. Both `sissy-squad` Step 3 and `follow-up-review` Step 3 delegate to this agent.

**Known bug fixed in v1.6.2:** Same wrong format assumption in the fallback one-liner. Current correct fallback in `agents/fetch-mr-diffs.md`:
```bash
cat /path/to/file.json | python3 -c "import json,sys; print(sys.stdin.read())"
```

### ✅ Phase 2.1 — Evaluators read source files from disk (v1.5.0)

`agents/thread-evaluator.md` now reads the file at `File Path` directly from the local working directory instead of receiving diff text in the prompt. Falls back to diff text if the file doesn't exist (deleted files) or `File Path` is `"General comment (no file)"`.

`commands/follow-up-review.md` Step 5 now passes `File Path` (one line) instead of embedding a full diff block per evaluator.

### ✅ Phase 2.0 — Fix agent file reference syntax in sissy-squad Step 5 (v1.8.0)

Replaced the ambiguous `{Content from the agent's specific command file}` prose placeholder with explicit `{Content from @agents/<agent-file>.md}` syntax and added a hard prohibition in the Important Notes section against reading agent files before spawning.

**What was observed before the fix (v1.7.x runs):** The orchestrator read all 9 review agent files (~1,000 lines total) into main context sequentially before spawning any subagent. The LLM inferred this from the prose placeholder even though no explicit Read instructions existed.

**What the fix does:** The `@agents/foo.md` syntax instructs the runtime to resolve each agent file inside the subagent's own context. The orchestrator never reads these files. The "Agent File" column in the agent table provides the exact path per agent.

**Validation status:** Validated on MR !2035. No `Read(agents/*.md)` calls appeared anywhere in the orchestrator. Pipeline went directly: parse-mr-metadata → fetch-mr-diffs → discovery → spawn agents. Fix confirmed working.

---

## Validation Protocol

After each change, ask the user to run the plugin on a real MR and share the Claude Code output log. The output should show the agent pipeline in sequence — look for:

1. **For `classify-mr-discussions` agent changes:** Does the agent return clean JSON? Does it handle the `mr_discussions` MCP call and correctly paginate? If the MCP output was large (saved to file), did the agent successfully extract the items array?

2. **For `fetch-mr-diffs` agent changes:** Did the Haiku agent run, fetch MR metadata and diffs, and return structured JSON? Were the correct files included (or filtered correctly for follow-up)?

3. **For evaluator changes:** Did each evaluator agent read a file from disk (look for `Read` tool calls in the output)? Did it fall back correctly for general comments?

4. **For Phase 2.0 (sissy-squad agent pre-read fix):** Are there any `Read(agents/*.md)` calls in the orchestrator before the review agents spawn? There should be none. The pipeline should go: parse-mr-metadata → fetch-mr-diffs → discovery → spawn all agents.

**How to share a run log:** Copy and paste the full Claude Code conversation output from `/sissy-squad <MR_URL>` or `/follow-up-review <MR_URL>` directly into the chat. Include:
- The agent spawn messages
- Any tool call outputs (MCP responses, Read calls, Bash calls)
- The final summary note content
- Any errors or fallback messages

---

## v1.8.0 Validation Status

**v1.8.0 validated on MR !2035.**

All three success criteria confirmed:
1. No `Read(agents/*.md)` calls appeared anywhere in the orchestrator log
2. Pipeline went directly: parse-mr-metadata → fetch-mr-diffs → discovery → spawn agents
3. All enabled agents (performance, git, qa) completed and posted comments normally

Phase 2.0 is complete and stable. Next: Phase 2.2 (batch thread evaluators by file).

---

## Phase 2 — Remaining Work

### 2.2 — Batch thread evaluators by file (per-file instead of per-thread)

**Status: Deferred — do not implement until v1.8.0 is validated**

**Rationale:** 60 threads → 60 parallel Opus subagents. At this scale, Task scheduling overhead dominates. Most threads are on distinct files — batching by file means each evaluator reads the file once and evaluates all threads on it in one pass.

**Concern:** Multi-file review comments (a note that references one file but mentions another in the body) must not be silently dropped. Threads with `new_path == null` (general comments) go into a dedicated "general" batch. The orchestrator must explicitly handle this bucketing.

**Files to modify:** `commands/follow-up-review.md` Step 5 (bucketing logic + batched agent prompts), `agents/thread-evaluator.md` (handle multiple threads per invocation)

**Before implementing:** Validate v1.8.0 first. Then revisit after confirming Phase 1 fixes are stable.

---

## Expected Impact

| Metric | Before Phase 1 | After Phase 1 (v1.6.x) | After Phase 2.0 (v1.8.0) |
|--------|---------------|------------------------|--------------------------|
| Wall time on large MRs | ~1 hour | significantly reduced | further reduced |
| Chunk-reads of discussions in main context | many sequential passes | 0 | 0 |
| Diff payload in main context | full MR diff | 0 | 0 |
| Classifier contract failures | possible (prose returned) | 0 (strict JSON output) | 0 |
| Diff payload passed to follow-up evaluators | 100% of MR files | only addressed-thread files | only addressed-thread files |
| Agent files read into orchestrator context | ~1,000 lines (9 files) | ~1,000 lines (9 files) | 0 |
| Shared infra between commands | none | `fetch-mr-diffs` agent | `fetch-mr-diffs` agent |

---

## Version History

| Version | Change |
|---------|--------|
| 1.4.0 | Baseline — MCP calls in main orchestrator |
| 1.5.0 | Phase 2.1: Evaluators read source files from disk |
| 1.6.0 | Phase 1: `classify-mr-discussions` + `fetch-mr-diffs` agents wired in |
| 1.6.1 | Fix: Detect and read oversized MCP output in both agents (partial — wrong format) |
| 1.6.2 | Fix: Correct persisted MCP output extraction — plain JSON format, not wrapped |
| 1.7.0 | Feature: Add `/sissy-setup` pre-review command |
| 1.7.1–1.7.3 | Fix: Inquirer TUI → zenity OS dialog for agent selection in sissy-setup |
| 1.7.4 | Fix: Correct sissy-squad command name in setup summary |
| 1.8.0 | Phase 2.0: Eliminate orchestrator pre-read of review agent files in sissy-squad |
