# Codex CLI Compatibility Design

**Status:** Approved
**Target release:** 2.4.0
**Approved scope:** Claude Code plus Codex CLI, with shared review behavior

## Goal

Add Codex CLI support to Sissy Code Review Squad without rewriting or
duplicating the existing reviewer prompts. Claude Code remains supported. Codex
gets explicit `$sissy-squad` and `$follow-up-review` skills that execute the
same canonical workflows and use the user's already-configured GitLab MCP
server.

## Non-Goals

- ChatGPT Work, Codex IDE, and Codex cloud support.
- Bundling, installing, or maintaining a GitLab MCP server.
- A Codex version of `clear-mr-comments`.
- Deterministic equality of model-generated findings between Claude and Codex.
- Rewriting reviewer prompts for Codex.
- Moving existing Claude command or agent files.

## Compatibility Contract

Both runtimes must use the same:

- reviewer prompt bodies;
- code-review standards;
- MR metadata and diff inputs;
- agent enablement;
- worktree isolation and cleanup behavior;
- severity and blocking rules;
- GitLab thread, reply, resolution, and summary formats.

Generated wording and findings may differ because Claude and Codex use different
models. Source instructions and externally visible workflow contracts must not
drift.

## Protected Existing Content

The implementation must leave these files byte-for-byte unchanged relative to
commit `96a3fd3`:

- every file under `agents/`;
- `rules/code-review-standards.md`;
- `commands/follow-up-review.md`;
- `commands/clear-mr-comments.md`.

`commands/sissy-squad.md` is the only existing prompt file that may change.
Its permitted changes are limited to the neutral review-config path and legacy
config migration described below. No reviewer instructions, review flow,
comment formats, or summaries may change.

## User Workflows

### Claude Code

Existing commands remain available:

- `/sissy-code-review-squad:sissy-squad <MR_URL>`
- `/sissy-code-review-squad:follow-up-review <MR_URL>`
- `/sissy-code-review-squad:clear-mr-comments <MR_URL>`

### Codex CLI

The Codex plugin exposes exactly two explicit skills:

- `$sissy-squad <MR_URL>`
- `$follow-up-review <MR_URL>`

There is no Codex `$clear-mr-comments` skill.

## Architecture

The existing Claude files remain the canonical workflow and reviewer sources.
A small Codex host layer loads those sources and translates only runtime
mechanics.

### Existing canonical sources

- `commands/sissy-squad.md`: full initial-review workflow.
- `commands/follow-up-review.md`: full follow-up workflow.
- `agents/*.md`: parser, fetcher, discovery, reviewers, classifier, and
  evaluator prompts.
- `rules/code-review-standards.md`: shared output and severity rules.

### New Codex host files

- `.codex-plugin/plugin.json`: installable skills-only Codex plugin manifest.
- `skills/sissy-squad/SKILL.md`: initial-review entrypoint.
- `skills/follow-up-review/SKILL.md`: follow-up entrypoint.
- `.codex-plugin/runtime-adapter.md`: shared Claude-to-Codex runtime mapping.

The two `SKILL.md` files stay small. Each resolves the plugin root relative to
its own location, reads the shared runtime adapter, reads the matching canonical
command completely, and executes it with the user's MR URL.

The skills must not embed copies of command, agent, or standards bodies.

## Runtime Translation

The shared adapter defines these mappings:

| Canonical construct | Codex behavior |
| --- | --- |
| `$ARGUMENTS` / `{$ARGUMENTS}` | Use the text supplied after the explicit skill invocation. |
| `${CLAUDE_PLUGIN_ROOT}` | Use the absolute plugin root derived from the selected `SKILL.md` path. |
| `@agents/<name>.md` | Spawn a Codex subagent whose prompt instructs it to read that canonical file completely before processing the supplied inputs. The parent must not preload reviewer files. |
| Claude Task / TaskOutput | Use Codex subagent spawn and wait controls, preserving sequential and parallel boundaries from the command. |
| `mcp__gitlab-mcp__<operation>` | Call the equivalent operation exposed by the configured GitLab MCP server, whose Codex namespace is currently `mcp__gitlab_mcp__<operation>`. Resolve by operation name rather than editing canonical prompts. |
| Claude model frontmatter | Apply the Codex model-tier mapping below when spawning the subagent. |

### Model-tier mapping

| Claude tier | Codex model | Reasoning effort |
| --- | --- | --- |
| Haiku | `gpt-5.6-luna` | `medium` |
| Sonnet | `gpt-5.6-terra` | `high` |
| Opus | `gpt-5.6` | `xhigh` |

If an explicitly mapped Codex model is unavailable, stop before posting any
GitLab content and report the unavailable model. Do not silently downgrade or
substitute a different model.

## GitLab MCP Prerequisite and Preflight

Users configure GitLab MCP separately in Codex. The plugin neither installs nor
owns the server or its credentials.

Before creating a worktree or writing to GitLab, a Codex skill verifies that
the configured server exposes every operation required by that workflow.

The initial-review preflight covers repository search, MR metadata, MR diffs,
thread creation, and summary-note creation. The follow-up preflight additionally
covers discussion listing, discussion replies, and thread resolution.

When a required operation is missing:

1. stop before worktree creation and GitLab writes;
2. print the missing operation names;
3. instruct the user to inspect `codex mcp list` and their GitLab MCP
   configuration.

## Neutral Project Configuration

The canonical project config becomes:

`.sissy/review-config.yml`

`commands/sissy-squad.md` performs one-way migration:

1. If `.sissy/review-config.yml` exists, read it.
2. Otherwise, if `.claude/review-config.yml` exists, create `.sissy/`, copy
   the legacy file unchanged, and read the new copy.
3. Otherwise, default every agent to enabled.
4. Future picker saves write only `.sissy/review-config.yml`.

The legacy file is never deleted or rewritten. `follow-up-review` and
`clear-mr-comments` do not use the agent-selection config and remain unchanged.

The template and user documentation switch to the neutral path and explain the
one-way fallback.

## Error Handling and Cleanup

After Codex preflight succeeds, the canonical command remains authoritative for
input validation, fetch failures, missing remote branches, worktree creation,
agent failures, GitLab posting, and cleanup.

Codex must preserve these boundaries:

- metadata parsing completes before MR fetching;
- discovery completes before reviewer spawning;
- enabled reviewers start in parallel;
- follow-up evaluator buckets start in parallel;
- follow-up verdict writes occur serially;
- each run removes only the worktree it created;
- cleanup still runs after downstream failures when a worktree exists.

The optional Zenity picker and desktop notification behavior remain unchanged.
Headless Codex runs use the command's existing fallback behavior.

## File and Packaging Changes

### Create

- `.codex-plugin/plugin.json`
- `skills/sissy-squad/SKILL.md`
- `skills/follow-up-review/SKILL.md`
- `.codex-plugin/runtime-adapter.md`
- `scripts/test_codex_compatibility.py`
- `scripts/.npmignore` to exclude generated Python bytecode from packages
- this design spec
- the matching implementation plan

### Modify

- `commands/sissy-squad.md`: neutral config path and migration only.
- `templates/review-config.yml`: neutral path in comments.
- `package.json`: include Codex plugin files in the published package and bump
  the release version.
- `.claude-plugin/plugin.json`: release version only.
- `.claude-plugin/marketplace.json`: release version only; it also remains the
  marketplace catalog Codex can consume.
- `README.md`, `CONTRIBUTING.md`, `docs/installation.md`,
  `docs/configuration.md`, and `docs/troubleshooting.md`: dual-runtime usage,
  prerequisites, config path, install, and troubleshooting.
- `RELEASE.md`: four synchronized version files plus Codex marketplace install
  and verification steps.

No production dependency is added.

## Verification Strategy

### Protected-content integrity

`scripts/test_codex_compatibility.py` embeds the expected SHA-256 digests captured
from commit `96a3fd3` for every protected Markdown file and fails if their current
bytes differ. The test must not require Git history to be present in an installed
or packaged copy.

### Static plugin checks

The test verifies:

- `.codex-plugin/plugin.json` is valid JSON with the expected name, version,
  and `./skills/` path;
- exactly the two approved Codex skills are present;
- each skill has valid `name` and `description` frontmatter;
- each skill references the correct canonical command and the shared adapter;
- no skill or adapter contains a copied reviewer prompt body;
- every referenced path exists;
- all four release-version locations match.

### Config migration checks

Static assertions verify that `commands/sissy-squad.md`:

- prefers `.sissy/review-config.yml`;
- copies the legacy file only when the neutral file is absent;
- writes picker output only to the neutral path;
- never deletes or overwrites the legacy file.

### Existing tests

Continue running:

`python3 -m unittest scripts/test_classify_discussions.py -v`

Run the new compatibility suite separately and together with the existing suite.

### Packaging and install checks

Before release:

1. run `npm pack --dry-run` and confirm the Codex manifest, both skills, shared
   adapter, canonical command/agent/rule files, and docs are included;
2. validate the manifest, skill frontmatter, canonical references, and runtime
   adapter with the compatibility suite;
3. confirm the local Codex CLI can list its configured GitLab MCP server and
   plugin marketplaces without changing plugin state;
4. run a disposable GitLab MR smoke test when a safe MR URL is available.

The live MR smoke test is not a prerequisite for publishing when no disposable
MR is supplied, because both workflows write comments to GitLab.

Install the plugin from the released Git tag after publishing, then ask for the
single Codex restart needed to discover the new skills.

## Release and Local Installation

Release `2.4.0` as a backward-compatible minor version.

The release follows `RELEASE.md`, updated for these four synchronized files:

1. `package.json`
2. `.claude-plugin/plugin.json`
3. `.claude-plugin/marketplace.json`
4. `.codex-plugin/plugin.json`

After verification and the repository-mandated full-diff approval:

1. commit the complete release;
2. create annotated tag `v2.4.0`;
3. push `main` and the tag;
4. publish the GitHub release with notes covering Codex CLI support and neutral
   config migration;
5. update the local Claude plugin;
6. add the released GitHub repository/tag as a Codex marketplace;
7. install `sissy-code-review-squad` from that marketplace;
8. verify the installed cache and enabled state;
9. ask the user to restart Codex so the new skills are discovered.

## Success Criteria

- Claude's initial review and follow-up workflows retain their existing prompt
  and output contracts.
- Protected prompt files match commit `96a3fd3` byte-for-byte.
- Codex exposes exactly `$sissy-squad` and `$follow-up-review`.
- Both Codex workflows use the existing canonical commands and agents.
- GitLab MCP preflight fails safely before external writes.
- Existing `.claude/review-config.yml` settings migrate without data loss.
- All automated checks pass.
- Version `2.4.0` is tagged, pushed, and published on GitHub.
- The released plugin is installed and enabled in the local Codex configuration.
- The only remaining manual action is restarting Codex.

## Official Codex References

- Plugin packaging and marketplaces:
  https://developers.openai.com/plugins/build/plugins
- Building Codex skills:
  https://learn.chatgpt.com/docs/build-skills
- Codex subagents:
  https://learn.chatgpt.com/docs/agent-configuration/subagents
- Codex MCP configuration:
  https://learn.chatgpt.com/docs/extend/mcp
