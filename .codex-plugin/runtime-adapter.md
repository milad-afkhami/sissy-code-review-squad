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

Before workflow subagents start, verify every model tier required by the workflow. Use the runtime model catalog when available. Otherwise, start one no-tools readiness subagent for each distinct required model and wait for all readiness checks before continuing. A readiness subagent must only reply `READY`; it must not read files, call tools, or write external content. If an explicit model is unavailable, stop before posting GitLab content. Do not silently substitute, downgrade, or choose another model.

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

Do not change the canonical data supplied to an agent or the response shape expected from it.

## Model Tiers

Map canonical Claude model tiers exactly:

| Claude tier | Codex model | Reasoning effort |
| --- | --- | --- |
| Haiku | `gpt-5.6-luna` | `medium` |
| Sonnet | `gpt-5.6-terra` | `high` |
| Opus | `gpt-5.6` | `xhigh` |

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
