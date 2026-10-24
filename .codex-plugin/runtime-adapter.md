# Claude Command to Codex Runtime Adapter

Apply this adapter only to host-specific mechanics. Keep the selected canonical command and every canonical agent and rule file authoritative. Do not paraphrase, modernize, reorder, or change their review instructions, comment formats, summaries, control flow, or cleanup rules.

## Resolve Inputs and Paths

- `$ARGUMENTS` and `{$ARGUMENTS}` mean the complete text supplied after the explicit Codex skill invocation.
- Resolve the absolute plugin root as two directories above the selected `SKILL.md`.
- `${CLAUDE_PLUGIN_ROOT}` means that resolved absolute plugin root.
- Resolve canonical relative paths from the plugin root, never from the reviewed repository or temporary worktree.

## Preflight Before Side Effects

After canonical input validation and before creating a worktree or posting GitLab content, complete the operation and model preflights below. Do not create a worktree or call a GitLab write operation until both pass.

Inspect the MCP tools available in the current Codex session and match GitLab operations by their operation suffix. The configured server currently exposes `mcp__gitlab_mcp__<operation>` while canonical files spell calls as `mcp__gitlab-mcp__<operation>`. This is a runtime name translation only.

For `sissy-squad`, require:

- `search_repositories`
- `get_merge_request`
- `get_merge_request_diffs`
- `create_merge_request_thread`
- `create_merge_request_note`

For `follow-up-review`, require:

- `search_repositories`
- `get_merge_request`
- `get_merge_request_diffs`
- `mr_discussions`
- `create_merge_request_note`
- `create_merge_request_discussion_note`
- `resolve_merge_request_thread`

If an operation is absent, stop before creating a worktree or posting GitLab content. Print the missing operation names and tell the user to inspect `codex mcp list` and the configured GitLab MCP server.

Before workflow subagents start, resolve every model tier required by the workflow using the ordered candidates in Model Tiers below. Use the current session's runtime model catalog when available and select the first available candidate for each tier. Otherwise, try the candidates in order with no-tools readiness subagents; each must only reply `READY` and must not read files, call tools, or write external content. Advance to the next candidate only when a model is explicitly unavailable. Stop on other readiness errors rather than treating them as model unavailability.

Report the resolved model and reasoning effort for each tier to the user before continuing, including which preferred models were unavailable. Use that resolved pair for every workflow subagent in the tier. If no listed candidate is available for a required tier, stop before creating a worktree or posting GitLab content and name the unavailable candidates. Do not silently substitute, downgrade, or choose an unlisted model.

## Spawn Canonical Agents

`@agents/<name>.md` means: use `spawn_agent` to start a Codex subagent whose first instruction is to resolve and read that canonical agent file completely, then follow it with the supplied workflow inputs. The parent must not preload or embed the agent file.

Use `spawn_agent` and `wait_agent` to translate Claude Task and TaskOutput mechanics while preserving these boundaries:

- metadata parsing completes before MR fetching;
- discovery completes before review agents start;
- enabled review agents form one logical parallel stage;
- follow-up evaluator buckets form one logical parallel stage;
- follow-up verdict writes remain serial;
- cleanup follows the canonical command after a worktree exists, including downstream failure paths.

Submit every task in a logical parallel stage without introducing dependencies between its tasks. If the runtime enforces a smaller concurrency capacity, keep the remaining tasks queued in that same logical stage and start them as slots become available. Wait for the complete stage before aggregation or verdict processing.

Preserve canonical inputs, response shapes, and review policy throughout each
agent's run, including coordinator follow-up messages. Carry this review contract
verbatim into each initial-review agent's prompt:

- Apply every applicable canonical checklist category to the changed code and
  its relevant callers, consumers, and state transitions. Before summarizing,
  finish unexplored checklist areas and keep brief local dispositions for
  considered concerns, including why a concern was dismissed or remains open.
- Preserve blocking issues, suggestions, nits, and questions. An uncertain
  requirement can be a question; an optional improvement can be a suggestion or
  nit. Do not replace this taxonomy with a generic bugs-only review policy.
- Challenge each finding's reachability, requirement, framework assumptions,
  and change from the baseline before posting. Separate distinct locations from
  distinct causes; do not inflate severity or create findings to meet a quota.
- Check agreed scope and explicitly accepted or deferred tradeoffs before
  reporting a concern. Keep them closed unless new evidence changes the decision;
  completing the checklist does not authorize reopening accepted risks.
- Request evidence or missing required work without narrowing scope, raising
  the canonical reporting threshold, or introducing an earlier stopping point.
  Zero findings is valid after completing the applicable review.

### Initial Review Snapshot (sissy-squad only)

Preserve the complete fetcher JSON in a run-specific scratch file; do not rebuild
it from displayed or summarized tool output. After canonical worktree creation
and before discovery, run the host helper:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/.codex-plugin/snapshot.py" \
  --repo "{worktree_path}" --input "{saved_fetcher_json_path}"
```

Use its `snapshot_path` as the shared MR context for discovery and all reviewers.
It checks the clean worktree HEAD and complete canonical authored-path inventory
against pinned MR refs, rebuilds full diffs from git, and retains original JSON and
checksums in a unique `run_dir`. On failure, stop before discovery/review posts,
report the missing or stale input, and perform canonical worktree cleanup.
Recover missing input without shrinking the reviewed scope.

In that run directory, retain the plugin revision, enabled agents, resolved
models/efforts, and exact rendered spawn/follow-up messages before dispatch.
Reviewers must retain complete requirements responses there before paging;
share the first complete response for each issue across reviewers, reuse those
frozen responses within the run, and disclose any unavailable
required context. Missing context cannot justify a complete or clean review.
Keep these evidence files local; preserve canonical GitLab formats. This helper
does not apply to follow-up-review's intentionally filtered file payloads.

### Initial Review Requirements (sissy-squad only)

The coordinator owns requirements retrieval. After discovery and before launching
reviewers, resolve referenced Jira issues from the branch and MR description,
using project guidance or linked issues to resolve the Jira site. Do not guess a
host from an issue key or hardcode an organization's host.

1. Inspect the current tool inventory and try the available Jira connector first,
   including site discovery when needed. Retrieve the full issue description,
   acceptance criteria and all comments, following every comment page. A search
   snippet, site-discovery response, or partial comment page is not complete.
2. If the connector is absent/disabled, returns an error (including `Unknown
   tool`, authentication, or permission errors), or cannot supply complete issue
   content/comments, load and follow the available `browser-use` skill. Use its
   authenticated browser to retrieve the issue and all comments from the resolved
   site. A catalogued connector that fails dispatch is unavailable for this
   attempt; do not keep probing it or ask the user to enable it before trying the
   browser. Never change connector settings. If no site can be resolved, or the
   browser skill/access is unavailable, record the specific remaining gap.
3. Save the complete raw issue and comment responses, source URL, retrieval time,
   route and any failed attempts in the snapshot's `run_dir` before paging them.
   Check comment pagination/counts to establish completeness. Mark partial
   evidence as partial, preserving it when both routes fail; an empty GitLab
   issue search does not establish that Jira is unavailable.
4. Pass the frozen requirements paths and completeness status to every reviewer.
   Reviewers must read and reuse them instead of fetching the same issue again.
   If a reviewer discovers another required issue or a gap, it requests retrieval
   from the coordinator, who uses the same route and shares the frozen result
   with affected reviewers before they conclude requirements-dependent work.

Do not fail GitLab preflight merely because Jira is disabled. When neither route
can retrieve required context, disclose what was tried and what remains missing
to reviewers and in the final review; do not claim full requirements compliance,
a complete review, or a clean approval from partial evidence. If no issue is
referenced, record that fact without inventing an issue or Jira site.

### Initial Review Publication Reconciliation (sissy-squad only)

Include this section verbatim in each initial-review agent's prompt. Preserve
the canonical output bodies and tool choices. Alongside its canonical result,
each reviewer returns publication evidence from this run: the target project/MR,
output kind, operation, returned note/thread IDs and the saved successful tool
response. A local draft, issue count, or promise to post is not publication.

Before Step 9's comprehensive summary, the coordinator reconciles the enabled
reviewers' required outputs against successful responses. Each enabled reviewer
must have its canonical domain summary note. When QA is enabled, verify three
separate outputs even when there are zero findings or requirements are missing:

| Required QA output | Successful publication evidence |
| --- | --- |
| `QA Analysis` | `create_merge_request_note` response with a note ID |
| `Test Checklist` | `create_merge_request_thread` response with a thread ID and its note ID(s), with no `position` |
| `QA Review Summary` | `create_merge_request_note` response with a separate note ID |

Match evidence to the current project/MR, canonical body and output kind; do not
count a summary, inline issue, or local evidence file as the separate analysis
note. Retain responses in `run_dir`. Do not require QA outputs when QA is skipped.

If an output or its proof is missing, send a scoped follow-up to the same reviewer
to recover the successful response or publish only the missing output using its
existing review evidence. For a timeout or ambiguous write, read back the MR's
notes/discussions with available GitLab read operations before retrying, and
reuse the matching publication rather than creating a duplicate. If read-back
cannot establish whether it posted, report an execution failure instead of
blindly retrying. Wait for recovery and reconcile again before aggregation;
do not rerun discovery or the full review, change findings to satisfy the gate,
or add empty issue threads. If required publication cannot be completed, report
the incomplete output as a host execution failure and perform canonical cleanup;
do not present the review stage as successfully completed.

## Tool Output (Codex)

Pass this section verbatim to every workflow subagent. `functions.exec` has an
outer output cap: increasing a nested tool's `max_output_tokens` does not raise
it. Retain large results with `store()` or a scratch file, then inspect each source
in bounded pages; print MCP text content instead of JSON-stringifying the whole
result. Set the outer `// @exec: {"max_output_tokens": ...}` budget for each page.
If either layer reports truncation, recover and read the omitted content from
every affected source before concluding the review. If recovery fails, report
the missing context explicitly; do not treat a truncated read as a complete one.

## Model Tiers

Map canonical Claude model tiers to the first available Codex model in each ordered list. All candidates in a row use that row's reasoning effort:

| Claude tier | Ordered Codex models | Reasoning effort |
| --- | --- | --- |
| Haiku | `gpt-5.6-luna` → `gpt-6-luna` | `medium` |
| Sonnet | `gpt-5.6-sol` → `gpt-6-sol` | `high` |
| Opus | `gpt-5.6-sol` → `gpt-6-sol` | `xhigh` |

Use this filename-to-tier metadata before the child reads its canonical file:

| Canonical agent file | Tier |
| --- | --- |
| `agents/parse-mr-metadata.md` | Haiku |
| `agents/fetch-mr-diffs.md` | Haiku |
| `agents/security.md` | Opus |
| `agents/accessibility.md` | Sonnet |
| `agents/classify-mr-discussions.md` | Sonnet |
| `agents/code-quality.md` | Sonnet |
| `agents/discovery.md` | Sonnet |
| `agents/git.md` | Sonnet |
| `agents/performance.md` | Sonnet |
| `agents/qa.md` | Sonnet |
| `agents/react.md` | Sonnet |
| `agents/seo.md` | Sonnet |
| `agents/styling.md` | Sonnet |
| `agents/thread-evaluator.md` | Sonnet |
| `agents/typescript.md` | Sonnet |

## GitLab Calls

For each canonical `mcp__gitlab-mcp__<operation>` instruction, call the configured Codex GitLab MCP tool with the same operation suffix and arguments. Do not edit canonical files to encode the Codex namespace. Preserve read and write order, thread-versus-note selection, reply bodies, resolution rules, and summary bodies.

## Completion

Follow canonical errors, notifications, and cleanup instructions. Report a host translation error separately from a review result. Never claim GitLab content was posted, a thread was resolved, or a worktree was removed unless the corresponding operation succeeded.
