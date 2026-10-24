# Claude Code — Project Guidelines

## Commit and Release Authorization

Follow the user's authorization for commits and releases. When the user invokes
`RELEASE.md` to perform a release, complete its commits, PR creation and merge,
tagging, publication, and local plugin updates without requesting repeated
approval. Inspect the complete diff and run the required checks before committing.

## Release Process

The full release process is documented in [RELEASE.md](RELEASE.md).

## Current Review Reliability Work

Read [the Codex review handoff](docs/codex-review-handoff.md) for the released
baseline, validated findings, and the next agreed patch before implementation.

## Agent File Reference Syntax

Two distinct patterns are used in command and agent files — **do not confuse them**:

| Syntax | Meaning | Used for |
|--------|---------|----------|
| `@agents/foo.md` | Invoke `foo` as a subagent | `classify-mr-discussions`, `fetch-mr-diffs`, `discovery`, `parse-mr-metadata` |
| `${CLAUDE_PLUGIN_ROOT}/rules/foo.md` | Read file contents and embed verbatim in the prompt | `code-review-standards` |

Using `${CLAUDE_PLUGIN_ROOT}/...` on an agent file would embed its raw markdown text into the prompt instead of running it as a subagent — a silent correctness bug.

## Key Architecture Facts

- **`agents/classify-mr-discussions.md`** — Haiku subagent. Fetches, paginates, filters, and classifies all MR discussion threads. Returns compact JSON. Discussions never touch main orchestrator context.
- **`agents/fetch-mr-diffs.md`** — Haiku subagent. Fetches MR metadata + diffs, supports optional `file_filter`. Shared by `sissy-squad` and `follow-up-review`.
- **`agents/thread-evaluator.md`** — Sonnet subagent. Reads source files directly from local disk (not diff text). Source branch must be checked out before running `follow-up-review`.
- **Persisted MCP output** — When an MCP call returns >~50KB, Claude saves it to a file and passes the path. Both Haiku agents detect this and read the file via Bash. The actual format is plain JSON (`{"items": [...]}` for discussions, raw object for diffs) — NOT a wrapped `[{type:"text", text:"..."}]` format.

