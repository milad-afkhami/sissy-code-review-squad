# Claude Code — Project Guidelines

## Commit Rules

**Never commit without showing the full diff and getting explicit approval first.**

Before any commit:
1. Run `git diff` (or `git diff --staged`) and show the output to the user
2. Wait for explicit approval ("yes", "go ahead", "approved", etc.)
3. Only then commit

This applies to version bumps, bug fixes, and any other change — no exceptions.

## Release Process

The full release process is documented in [RELEASE.md](RELEASE.md).

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

