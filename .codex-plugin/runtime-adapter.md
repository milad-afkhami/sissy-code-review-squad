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
