# Codex CLI Compatibility — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Release Sissy Code Review Squad 2.4.1 with Claude Code behavior preserved and two Codex CLI skills that run the same canonical initial-review and follow-up-review workflows through the user's configured GitLab MCP server. Tasks 1–11 produced v2.4.0; Tasks 12–16 are the forward patch for the runtime-discovery conflict found during local installation.

**Architecture:** Keep the existing Claude command, agent, and standards files in place as the canonical workflow sources. Add a skills-only Codex plugin whose two thin entrypoints load a shared runtime adapter and then execute the matching canonical command. The adapter translates host mechanics—arguments, plugin-root resolution, subagents, models, and MCP tool names—without copying or rewriting reviewer prompts. Move only the project review configuration to the runtime-neutral `.sissy/` path, with one-way migration from `.claude/`.

**Tech Stack:** Markdown command/skill files, JSON plugin manifests, Python 3 standard-library contract tests, npm package metadata, Codex CLI plugin marketplace commands, Claude Code CLI plugin update, Git/GitHub CLI release tooling.

## Global Constraints

- Treat commit `96a3fd3` as the byte-level baseline for every file under `agents/`, `rules/code-review-standards.md`, `commands/follow-up-review.md`, and `commands/clear-mr-comments.md`.
- Do not move, rewrite, reformat, or normalize protected files. The only existing prompt file allowed to change is `commands/sissy-squad.md`, and only its review-config path/migration mechanics may change.
- Expose exactly two Codex skills: `sissy-squad` and `follow-up-review`. Do not create a Codex `clear-mr-comments` skill.
- Keep Codex entrypoints thin: they reference canonical files; they do not duplicate command, agent, rules, comment-format, or summary bodies.
- Assume GitLab MCP is already configured by the user. Do not add MCP credentials, an MCP server definition, or a new dependency.
- Fail Codex preflight before worktree creation or GitLab content writes when required MCP operations or explicitly mapped models are unavailable.
- Preserve canonical ordering: parse before fetch, discovery before reviews, enabled reviewers in parallel, follow-up evaluator buckets in parallel, verdict writes serially, cleanup after any created worktree.
- Keep `.claude/review-config.yml` as read-only legacy input. New and migrated settings live at `.sissy/review-config.yml`.
- Keep all four release manifests synchronized. Tasks 1–11 used `2.4.0`;
  the final forward patch uses `2.4.1`.
- Do not make intermediate commits. Repository instructions require showing the complete diff and receiving explicit approval before every commit. Make one release commit only after that gate.
- Do not run a live MR smoke test without a disposable MR URL because both workflows write to GitLab.

## File Map

### Create

- `.codex-plugin/plugin.json` — Codex plugin manifest.
- `skills/sissy-squad/SKILL.md` — initial-review Codex entrypoint.
- `skills/follow-up-review/SKILL.md` — follow-up Codex entrypoint.
- `.codex-plugin/runtime-adapter.md` — shared host translation and preflight contract.
- `scripts/test_codex_compatibility.py` — package-safe compatibility and integrity suite.
- `scripts/.npmignore` — exclude generated Python bytecode from npm packages.
- `docs/superpowers/specs/2026-08-09-codex-cli-compatibility-design.md` — approved design.
- `docs/superpowers/plans/2026-08-09-codex-cli-compatibility.md` — this plan.

### Modify

- `commands/sissy-squad.md` — neutral config path plus one-way legacy migration only.
- `templates/review-config.yml` — neutral destination comment.
- `package.json` — publish Codex files and release version.
- `.claude-plugin/plugin.json` — release version only.
- `.claude-plugin/marketplace.json` — Claude's legacy-compatible catalog,
  routed to the nested Claude projection in v2.4.1.
- `.agents/plugins/marketplace.json` — Codex-native catalog routed to the
  repository-root Codex plugin.
- `claude-plugin/` — symlink-only projection of canonical Claude components.
- `README.md` — dual-runtime positioning, install, invocation, configuration, and prerequisites.
- `CONTRIBUTING.md` — dual-runtime development and verification.
- `docs/installation.md` — separate Claude Code and Codex CLI installation paths.
- `docs/configuration.md` — neutral config path and migration note.
- `docs/troubleshooting.md` — runtime-specific install/MCP/config diagnostics.
- `RELEASE.md` — four-version release process plus both local runtime updates.

---

### Task 1: Add the prompt-integrity characterization suite

**Files:**

- Create: `scripts/test_codex_compatibility.py`

**Interfaces:**

- Runs with `python3 -m unittest scripts.test_codex_compatibility -v`.
- Uses only the Python standard library.
- Embeds baseline hashes so it also works in npm tarballs and installed plugin caches that lack `.git/`.

- [ ] **Step 1: Create the test module with the immutable baseline**

Start the file with these imports, constants, and helper:

```python
#!/usr/bin/env python3
"""Contract tests for Claude Code and Codex CLI plugin compatibility."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]

PROTECTED_SHA256 = {
    "agents/accessibility.md": "15789520880f5a45feaabe3a7eaf8644396154894c16332577042848c22ea239",
    "agents/classify-mr-discussions.md": "9c2beeb062e4866783bbdd5d14429f6e86d90bc4ae14b2a5d62702a4b1968f1a",
    "agents/code-quality.md": "9b44fd9b30af018c5e0f475dca5cf477a9e3e0926350e25bbc5e57ae6d566329",
    "agents/discovery.md": "ce63359040ec65eed5eb4ac671854b8e0686360a7aae120b3845198745293356",
    "agents/fetch-mr-diffs.md": "fa8095a799bbe1b9f5a4dec1d978936f83f2ea55d9be5fbc59fa110940d2922a",
    "agents/git.md": "f5f26c8269e9d8356300eb755cdbd4e57a560ebf5b2e35d4a1b6f5589d92931b",
    "agents/parse-mr-metadata.md": "1f8098081cfc01c0828014ab7b9d06e8b9fac1550df2ff9d185874bf59787a40",
    "agents/performance.md": "35b9f45c2cee001bacac3a59c3682afef9b160afb733b8a021a88c55a245724f",
    "agents/qa.md": "28a74449d885d0a6ecc7b0d3553cc9cd3110d80bf6ee7e7ae80244279e8c6213",
    "agents/react.md": "3675cfb25c168d9486371a94735ea2b11e728a0ce2c731b4c7f87978a4d5c790",
    "agents/security.md": "1cfd5c692b5894138908bdc5dca723135964dfca60d03af92ec7d3dcd652404f",
    "agents/seo.md": "cb626806e78fd25a3818e8a16473bf31a112a23593f3b519a82808c34d0ace83",
    "agents/styling.md": "c981357b5c6bfdc9d871eca555d2a7b4681ba3bb87a44774260e54a7b8113169",
    "agents/thread-evaluator.md": "e9fdf2039c663ab9e540bf1d69b4d36b7614805e8cb407f554450542eded5866",
    "agents/typescript.md": "056f4dd3c82172693325504133fd0c900ee905e2759ef70ac6820a2ceea5a18e",
    "commands/clear-mr-comments.md": "b7b9904bcbe6a79bcc64d3602b24efafb38a41b0f7abfa94475003338f093838",
    "commands/follow-up-review.md": "4add04c2970c909462bfa1d89b9df1ddbdf838a58c0278174c634b5da7f04602",
    "rules/code-review-standards.md": "141022b7be6457761bed648e2925b5ddaf765205d8801c9e6001e269179635b4",
}


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class CodexCompatibilityTests(unittest.TestCase):
    def test_protected_prompt_hashes_match_2_3_0_baseline(self) -> None:
        for relative_path, expected in PROTECTED_SHA256.items():
            with self.subTest(path=relative_path):
                actual = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
                self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the characterization test**

Run:

```bash
python3 -m unittest scripts.test_codex_compatibility.CodexCompatibilityTests.test_protected_prompt_hashes_match_2_3_0_baseline -v
```

Expected: `OK`. A failure at this stage means the baseline or current protected bytes are wrong; resolve that before continuing.

- [ ] **Step 3: Prove Git history independence**

Inspect the test and confirm it contains no subprocess call to `git`, no `.git` path, and no `git show` logic:

```bash
rg -n "subprocess|git show|\.git" scripts/test_codex_compatibility.py
```

Expected: no matches.

---

### Task 2: Add the Codex manifest and thin skill entrypoints

**Files:**

- Modify: `scripts/test_codex_compatibility.py`
- Create: `.codex-plugin/plugin.json`
- Create: `skills/sissy-squad/SKILL.md`
- Create: `skills/follow-up-review/SKILL.md`

**Interfaces:**

- Codex manifest points to `./skills/`.
- Skill frontmatter names are exactly `sissy-squad` and `follow-up-review`.
- Each skill loads `.codex-plugin/runtime-adapter.md` and one canonical command.
- The initial development version remains `2.3.0`; all four versions move together in Task 7.

- [ ] **Step 1: Add failing manifest and entrypoint tests**

Add these methods inside `CodexCompatibilityTests`:

```python
    def test_codex_manifest_and_skill_set(self) -> None:
        manifest = json.loads(read_text(".codex-plugin/plugin.json"))
        self.assertEqual("sissy-code-review-squad", manifest["name"])
        self.assertEqual("./skills/", manifest["skills"])
        self.assertEqual("Sissy Code Review Squad", manifest["interface"]["displayName"])
        self.assertEqual("Productivity", manifest["interface"]["category"])

        skills = sorted(
            path.parent.name
            for path in (ROOT / "skills").glob("*/SKILL.md")
        )
        self.assertEqual(["follow-up-review", "sissy-squad"], skills)
        self.assertFalse((ROOT / "skills/clear-mr-comments/SKILL.md").exists())

    def test_skill_frontmatter_and_canonical_references(self) -> None:
        expected = {
            "sissy-squad": "commands/sissy-squad.md",
            "follow-up-review": "commands/follow-up-review.md",
        }
        for skill_name, command_path in expected.items():
            with self.subTest(skill=skill_name):
                body = read_text(f"skills/{skill_name}/SKILL.md")
                self.assertRegex(body, rf"(?m)^name: {re.escape(skill_name)}$")
                self.assertRegex(body, r"(?m)^description: \S.+$")
                self.assertIn(".codex-plugin/runtime-adapter.md", body)
                self.assertIn(command_path, body)
```

- [ ] **Step 2: Run the two tests and confirm the expected failure**

Run:

```bash
python3 -m unittest \
  scripts.test_codex_compatibility.CodexCompatibilityTests.test_codex_manifest_declares_skills_plugin \
  scripts.test_codex_compatibility.CodexCompatibilityTests.test_sissy_skill_references_canonical_sources \
  scripts.test_codex_compatibility.CodexCompatibilityTests.test_every_skills_child_is_an_actual_skill \
  scripts.test_codex_compatibility.CodexCompatibilityTests.test_codex_exposes_only_approved_skills \
  -v
```

Expected: errors because `.codex-plugin/plugin.json` and the skills do not exist yet.

- [ ] **Step 3: Create the Codex manifest**

Create `.codex-plugin/plugin.json`:

```json
{
  "name": "sissy-code-review-squad",
  "version": "2.3.0",
  "description": "Multi-agent code review plugin for GitLab merge requests. 10 specialized AI agents review accessibility, security, performance, SEO, styling, code quality, React, TypeScript, Git hygiene, and QA.",
  "author": {
    "name": "Milad Afkhami",
    "url": "https://github.com/milad-afkhami"
  },
  "homepage": "https://github.com/milad-afkhami/sissy-code-review-squad#readme",
  "repository": "https://github.com/milad-afkhami/sissy-code-review-squad",
  "license": "MIT",
  "keywords": [
    "code-review",
    "gitlab",
    "merge-request",
    "accessibility",
    "security",
    "performance",
    "react",
    "typescript"
  ],
  "skills": "./skills/",
  "interface": {
    "displayName": "Sissy Code Review Squad",
    "shortDescription": "Review GitLab merge requests with a specialized agent squad.",
    "longDescription": "Run the canonical Sissy initial and follow-up GitLab merge request review workflows from Codex CLI.",
    "developerName": "Milad Afkhami",
    "category": "Productivity",
    "capabilities": [
      "Review GitLab merge requests",
      "Verify fixes in review threads"
    ],
    "defaultPrompt": [
      "$sissy-squad https://gitlab.com/your-org/your-project/-/merge_requests/123",
      "$follow-up-review https://gitlab.com/your-org/your-project/-/merge_requests/123"
    ]
  }
}
```

- [ ] **Step 4: Create the two thin skills**

Create `skills/sissy-squad/SKILL.md`:

```markdown
---
name: sissy-squad
description: Use when the user explicitly invokes the Codex Sissy initial-review skill with a GitLab merge request URL.
---

# Sissy Squad

Treat the text supplied after this skill invocation as the skill arguments.

1. Resolve the plugin root as two directories above this `SKILL.md`.
2. Read `.codex-plugin/runtime-adapter.md` from that root completely.
3. Read `commands/sissy-squad.md` from that root completely.
4. Execute the canonical command once, applying only the host translations in the shared adapter and substituting the skill arguments for the command arguments.
```

Create `skills/follow-up-review/SKILL.md`:

```markdown
---
name: follow-up-review
description: Use when the user explicitly invokes the Codex Sissy follow-up skill with a GitLab merge request URL.
---

# Follow-Up Review

Treat the text supplied after this skill invocation as the skill arguments.

1. Resolve the plugin root as two directories above this `SKILL.md`.
2. Read `.codex-plugin/runtime-adapter.md` from that root completely.
3. Read `commands/follow-up-review.md` from that root completely.
4. Execute the canonical command once, applying only the host translations in the shared adapter and substituting the skill arguments for the command arguments.
```

- [ ] **Step 5: Run the focused tests**

Run the command from Step 2 again.

Expected: both tests pass. At this stage the skills contain the required adapter path as a reference; Task 3 creates and validates the referenced file.

---

### Task 3: Implement the shared Codex runtime adapter

**Files:**

- Modify: `scripts/test_codex_compatibility.py`
- Create: `.codex-plugin/runtime-adapter.md`

**Interfaces:**

- Initial-review MCP operations: `search_repositories`, `get_merge_request`, `get_merge_request_diffs`, `create_merge_request_thread`, `create_merge_request_note`.
- Follow-up adds: `mr_discussions`, `create_merge_request_discussion_note`, `resolve_merge_request_thread`.
- Model mapping: Haiku → `gpt-5.6-luna`/`medium`; Sonnet → `gpt-5.6-terra`/`high`; Opus → `gpt-5.6-sol`/`xhigh`.
- Agent-file model metadata is mirrored only as a filename-to-tier table; no prompt body is copied.

- [ ] **Step 1: Add failing adapter-contract tests**

Add these methods inside `CodexCompatibilityTests`:

```python
    def test_runtime_adapter_contract(self) -> None:
        body = read_text(".codex-plugin/runtime-adapter.md")

        for token in (
            "$ARGUMENTS",
            "${CLAUDE_PLUGIN_ROOT}",
            "@agents/<name>.md",
            "spawn_agent",
            "wait_agent",
            "mcp__gitlab-mcp__<operation>",
            "mcp__gitlab_mcp__<operation>",
        ):
            self.assertIn(token, body)

        for operation in (
            "search_repositories",
            "get_merge_request",
            "get_merge_request_diffs",
            "mr_discussions",
            "create_merge_request_thread",
            "create_merge_request_note",
            "create_merge_request_discussion_note",
            "resolve_merge_request_thread",
        ):
            self.assertIn(operation, body)

        for model, effort in (
            ("gpt-5.6-luna", "medium"),
            ("gpt-5.6-terra", "high"),
            ("gpt-5.6-sol", "xhigh"),
        ):
            self.assertRegex(
                body,
                rf"(?s){re.escape(model)}.*?{re.escape(effort)}",
            )

        self.assertIn("before creating a worktree", body)
        self.assertIn("before posting GitLab content", body)
        self.assertIn("Do not silently substitute", body)

    def test_codex_host_files_do_not_copy_canonical_bodies(self) -> None:
        host = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((ROOT / "skills").rglob("*.md"))
        )
        canonical_paths = [
            ROOT / "commands/sissy-squad.md",
            ROOT / "commands/follow-up-review.md",
            ROOT / "rules/code-review-standards.md",
            *sorted((ROOT / "agents").glob("*.md")),
        ]
        for path in canonical_paths:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn(path.read_text(encoding="utf-8"), host)
```

- [ ] **Step 2: Run the new tests and confirm the expected failure**

Run:

```bash
python3 -m unittest \
  scripts.test_codex_compatibility.CodexCompatibilityTests.test_initial_review_runtime_adapter_contract \
  scripts.test_codex_compatibility.CodexCompatibilityTests.test_codex_initial_host_does_not_copy_canonical_bodies \
  scripts.test_codex_compatibility.CodexCompatibilityTests.test_follow_up_skill_references_canonical_sources \
  scripts.test_codex_compatibility.CodexCompatibilityTests.test_follow_up_runtime_adapter_contract \
  -v
```

Expected: failure because the shared adapter does not exist.

- [ ] **Step 3: Create `.codex-plugin/runtime-adapter.md`**

Write a concise adapter with these exact sections and contracts:

```markdown
# Claude Command to Codex Runtime Adapter

Apply this adapter only to host-specific mechanics. The selected canonical command and every canonical agent/rule file remain authoritative. Do not paraphrase, modernize, reorder, or otherwise change their review instructions, comment formats, summaries, control flow, or cleanup rules.

## Resolve Inputs and Paths

- `$ARGUMENTS` and `{$ARGUMENTS}` mean the complete text supplied after the explicit Codex skill invocation.
- Resolve the absolute plugin root as two directories above the selected `SKILL.md`.
- `${CLAUDE_PLUGIN_ROOT}` means that resolved absolute plugin root.
- Resolve every canonical relative path from the plugin root, never from the reviewed repository or temporary worktree.

## Preflight Before Side Effects

After canonical input validation and before creating a worktree or posting GitLab content, complete both preflights below. GitLab reads are allowed during the canonical workflow only after the MCP operation preflight passes.

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

If any operation is absent, stop before creating a worktree or posting GitLab content. Print the missing operation names and tell the user to inspect `codex mcp list` and the configured GitLab MCP server.

Before workflow subagents start, verify availability of every model tier required by that workflow. Use the runtime model catalog when available; otherwise use a no-tools readiness subagent for each required model and wait for all readiness checks before continuing. A readiness subagent must only reply `READY` and must not read files, call tools, or write external content. If any explicit model is unavailable, stop before posting GitLab content. Do not silently substitute, downgrade, or choose another model.

## Spawn Canonical Agents

`@agents/<name>.md` means: spawn a Codex subagent whose first instruction is to resolve and read that canonical agent file completely, then follow it with the supplied workflow inputs. The parent must not preload or embed the agent file. Preserve the command's sequential and parallel boundaries with `spawn_agent` and `wait_agent`:

- metadata parsing completes before MR fetching;
- discovery completes before review/evaluator agents start;
- enabled initial-review agents start in parallel;
- follow-up evaluator buckets start in parallel;
- follow-up verdict writes occur serially;
- cleanup follows the canonical command after a worktree exists, including downstream failure paths.

Translate Claude Task/TaskOutput mechanics only; do not change the canonical data passed to an agent or the expected response shape.

## Model Tiers

Map canonical Claude model tiers exactly:

| Claude tier | Codex model | Reasoning effort |
| --- | --- | --- |
| Haiku | `gpt-5.6-luna` | `medium` |
| Sonnet | `gpt-5.6-terra` | `high` |
| Opus | `gpt-5.6-sol` | `xhigh` |

Use this filename-to-tier metadata when selecting a model before the child reads its canonical file:

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

For each canonical `mcp__gitlab-mcp__<operation>` instruction, call the configured Codex GitLab MCP tool with the same operation suffix and the same arguments. Do not modify canonical files to encode the Codex namespace. Preserve read/write order, thread-vs-note selection, reply bodies, resolution rules, and summary bodies.

## Completion

Follow canonical error messages, notifications, and cleanup instructions. Report a host translation error separately from a review result. Never claim GitLab content was posted, a thread was resolved, or a worktree was removed unless the corresponding operation succeeded.
```

- [ ] **Step 4: Run the full compatibility suite**

Run:

```bash
python3 -m unittest scripts.test_codex_compatibility -v
```

Expected: all tests created so far pass.

---

### Task 4: Move project review configuration to `.sissy/` with one-way migration

**Files:**

- Modify: `scripts/test_codex_compatibility.py`
- Modify: `commands/sissy-squad.md:38-114`
- Modify: `templates/review-config.yml:1-3`

**Interfaces:**

- Preferred config: `.sissy/review-config.yml`.
- Legacy input: `.claude/review-config.yml`.
- Migration occurs only when preferred config is absent and legacy config exists.
- Migration copies bytes unchanged and never deletes or rewrites legacy input.
- Picker writes only `.sissy/review-config.yml`.

- [ ] **Step 1: Add failing migration contract tests**

Add these methods inside `CodexCompatibilityTests`:

```python
    def test_sissy_command_uses_neutral_config_with_legacy_copy(self) -> None:
        body = read_text("commands/sissy-squad.md")
        self.assertIn('REVIEW_CONFIG=".sissy/review-config.yml"', body)
        self.assertIn('LEGACY_REVIEW_CONFIG=".claude/review-config.yml"', body)
        self.assertIn('[ ! -f "$REVIEW_CONFIG" ]', body)
        self.assertIn('[ -f "$LEGACY_REVIEW_CONFIG" ]', body)
        self.assertIn('mkdir -p .sissy', body)
        self.assertIn('cp -- "$LEGACY_REVIEW_CONFIG" "$REVIEW_CONFIG"', body)
        self.assertIn('> .sissy/review-config.yml', body)
        self.assertNotIn('> .claude/review-config.yml', body)
        self.assertNotRegex(body, r"\brm\b[^\n]*LEGACY_REVIEW_CONFIG")

    def test_review_config_template_points_to_neutral_path(self) -> None:
        body = read_text("templates/review-config.yml")
        self.assertIn(".sissy/review-config.yml", body)
        self.assertNotIn(".claude/review-config.yml", body)
```

- [ ] **Step 2: Run the focused tests and confirm the expected failure**

Run:

```bash
python3 -m unittest \
  scripts.test_codex_compatibility.CodexCompatibilityTests.test_legacy_config_is_copied_once_without_modifying_source \
  scripts.test_codex_compatibility.CodexCompatibilityTests.test_existing_neutral_config_is_never_overwritten_by_legacy \
  scripts.test_codex_compatibility.CodexCompatibilityTests.test_picker_targets_only_neutral_config \
  scripts.test_codex_compatibility.CodexCompatibilityTests.test_review_config_template_points_to_neutral_path \
  -v
```

Expected: failures because the command and template still use `.claude/review-config.yml`.

- [ ] **Step 3: Change only the config setup in `commands/sissy-squad.md`**

Replace the Step 3 introduction and Step 3a path text so they name `.sissy/review-config.yml`, then insert this bash block before the command reads the config:

```bash
REVIEW_CONFIG=".sissy/review-config.yml"
LEGACY_REVIEW_CONFIG=".claude/review-config.yml"

if [ ! -f "$REVIEW_CONFIG" ] && [ -f "$LEGACY_REVIEW_CONFIG" ]; then
  mkdir -p .sissy &&
    cp -- "$LEGACY_REVIEW_CONFIG" "$REVIEW_CONFIG" &&
    echo "MIGRATED:$LEGACY_REVIEW_CONFIG->$REVIEW_CONFIG"
fi
```

Then make these narrowly scoped edits in the existing picker block:

```bash
mkdir -p .sissy
```

and:

```bash
} > .sissy/review-config.yml
```

Update the picker comment to say the file is written by `/sissy-squad` at `.sissy/review-config.yml`. Do not alter the agent list, defaults, Zenity behavior, cancellation handling, or any later review step.

- [ ] **Step 4: Update the template destination comment**

Change only the second line of `templates/review-config.yml` to:

```yaml
# Copy this file to your project's .sissy/review-config.yml
```

- [ ] **Step 5: Run focused tests and inspect the prompt diff**

Run:

```bash
python3 -m unittest \
  scripts.test_codex_compatibility.CodexCompatibilityTests.test_legacy_config_is_copied_once_without_modifying_source \
  scripts.test_codex_compatibility.CodexCompatibilityTests.test_existing_neutral_config_is_never_overwritten_by_legacy \
  scripts.test_codex_compatibility.CodexCompatibilityTests.test_picker_targets_only_neutral_config \
  scripts.test_codex_compatibility.CodexCompatibilityTests.test_review_config_template_points_to_neutral_path \
  -v
git diff -- commands/sissy-squad.md templates/review-config.yml
```

Expected: tests pass. The prompt diff contains only `.sissy` path text, the one-way copy block, and the picker destination change.

- [ ] **Step 6: Re-run protected hashes**

Run:

```bash
python3 -m unittest scripts.test_codex_compatibility.CodexCompatibilityTests.test_protected_prompt_hashes_match_2_3_0_baseline -v
```

Expected: `OK`.

---

### Task 5: Publish Codex files and document both runtimes

**Files:**

- Modify: `scripts/test_codex_compatibility.py`
- Create: `scripts/.npmignore`
- Modify: `package.json:44-55`
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`
- Modify: `docs/installation.md`
- Modify: `docs/configuration.md`
- Modify: `docs/troubleshooting.md`

**Interfaces:**

- npm package includes `.codex-plugin/` and `skills/`, without Python cache artifacts.
- Claude Code commands remain documented, including `clear-mr-comments`.
- Codex CLI documents only the two supported skills.
- Both runtimes document preconfigured GitLab MCP as a prerequisite.
- All active config instructions use `.sissy/review-config.yml`; legacy `.claude/` appears only in migration/troubleshooting text.

- [ ] **Step 1: Add a failing package-behavior test**

Add these methods inside `CodexCompatibilityTests`:

```python
    def test_npm_package_contains_codex_runtime_files(self) -> None:
        completed = subprocess.run(
            ["npm", "pack", "--dry-run", "--json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        packaged = {entry["path"] for entry in payload[0]["files"]}
        required = {
            ".codex-plugin/plugin.json",
            ".codex-plugin/runtime-adapter.md",
            "skills/sissy-squad/SKILL.md",
            "skills/follow-up-review/SKILL.md",
        }
        self.assertLessEqual(required, packaged)
        cache_artifacts = {
            path
            for path in packaged
            if "__pycache__" in Path(path).parts or path.endswith((".pyc", ".pyo"))
        }
        self.assertEqual(set(), cache_artifacts)
```

- [ ] **Step 2: Run the focused tests and confirm the expected failure**

Run:

```bash
python3 -m unittest scripts.test_codex_compatibility.CodexCompatibilityTests.test_npm_package_contains_codex_runtime_files -v
```

Expected: failure because Codex files are absent from the package; after Python
tests have run, it also exposes any packaged `__pycache__` artifact.

- [ ] **Step 3: Add Codex directories to npm packaging**

Add these entries to `package.json`'s `files` array without removing any existing entry:

```json
".codex-plugin/",
"skills/",
```

Create `scripts/.npmignore` with:

```text
__pycache__/
**/*.pyc
**/*.pyo
```

- [ ] **Step 4: Update README and installation guide**

Document these exact user-visible workflows while retaining the current Claude commands:

```bash
codex plugin marketplace add milad-afkhami/sissy-code-review-squad --ref v2.4.0
codex plugin add sissy-code-review-squad@sissy-code-review-squad
```

Codex invocations:

```text
$sissy-squad https://gitlab.com/your-org/your-project/-/merge_requests/123
$follow-up-review https://gitlab.com/your-org/your-project/-/merge_requests/123
```

State plainly that `clear-mr-comments` remains Claude-only. Do not add a Codex alias or adapter for it.

Describe GitLab MCP as separately configured in each runtime. For Codex diagnostics, use:

```bash
codex mcp list
```

Do not provide or install a new server configuration; existing users keep their own configured server and credentials.

- [ ] **Step 5: Update configuration and troubleshooting docs**

Replace active `.claude/review-config.yml` paths with `.sissy/review-config.yml`. Add one migration paragraph:

```text
On the first `sissy-squad` run after upgrading, if `.sissy/review-config.yml` is absent and `.claude/review-config.yml` exists, the plugin copies the legacy file unchanged to `.sissy/review-config.yml`. The legacy file is left untouched; future picker saves update only `.sissy/review-config.yml`.
```

Split install-not-found and MCP diagnostics by runtime. Preserve unrelated troubleshooting guidance and the existing `.claude/rules/` recommendations because reviewer prompts still consume those canonical project-context files.

- [ ] **Step 6: Update contributing instructions**

Add the Codex plugin layout, the compatibility test command, the protected-file constraint, and local Codex marketplace validation. Keep the Claude link/test workflow.

- [ ] **Step 7: Run focused tests and search for stale active config guidance**

Run:

```bash
python3 -m unittest scripts.test_codex_compatibility.CodexCompatibilityTests.test_npm_package_contains_codex_runtime_files -v
rg -n "\.claude/review-config\.yml" README.md CONTRIBUTING.md docs/installation.md docs/configuration.md docs/troubleshooting.md templates/review-config.yml
```

Expected: the package test passes. Review the documentation diff directly;
remaining `.claude/review-config.yml` matches explain legacy migration only,
not active configuration.

---

### Task 6: Make release instructions dual-runtime and four-version aware

**Files:**

- Modify: `scripts/test_codex_compatibility.py`
- Modify: `RELEASE.md`

**Interfaces:**

- Release guide names all four version files.
- Codex install uses the released Git tag as marketplace ref.
- Post-release checks cover Claude update, Codex installation/enabled state, and the required Codex restart.
- Rollback warns that deleting already-published tags/releases is destructive and requires explicit approval.

- [ ] **Step 1: Add a failing release-guide contract test**

Add this method inside `CodexCompatibilityTests`:

```python
    def test_release_guide_covers_four_versions_and_codex_install(self) -> None:
        body = read_text("RELEASE.md")
        for path in (
            "package.json",
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            ".codex-plugin/plugin.json",
        ):
            self.assertIn(path, body)
        self.assertIn("codex plugin marketplace add", body)
        self.assertIn("codex plugin add", body)
        self.assertIn("codex plugin list", body)
        self.assertIn("restart Codex", body)
```

- [ ] **Step 2: Run the test and confirm the expected failure**

Run:

```bash
python3 -m unittest scripts.test_codex_compatibility.CodexCompatibilityTests.test_release_guide_covers_four_versions_and_codex_install -v
```

Expected: failure because `RELEASE.md` still documents three version files and Claude-only local update.

- [ ] **Step 3: Update `RELEASE.md`**

Make all prose, examples, checklist counts, and the quick script use four synchronized manifests. Add `.codex-plugin/plugin.json` to the version-edit and staging commands.

After the Claude update command, add the released Codex flow:

```bash
codex plugin marketplace add milad-afkhami/sissy-code-review-squad --ref "v<new-version>"
codex plugin add sissy-code-review-squad@sissy-code-review-squad
codex plugin list --json
```

The guide must tell the releaser to verify the plugin is installed and enabled, then restart Codex. Keep the current Git push and GitHub release workflow. Replace the destructive rollback recipe with an approval warning before remote tag/release deletion.

- [ ] **Step 4: Run the focused test**

Run the command from Step 2 again.

Expected: `OK`.

---

### Task 7: Synchronize release version 2.4.0

**Files:**

- Modify: `scripts/test_codex_compatibility.py`
- Modify: `package.json:3`
- Modify: `.claude-plugin/plugin.json:3`
- Modify: `.claude-plugin/marketplace.json:4`
- Modify: `.codex-plugin/plugin.json:3`

**Interfaces:**

- Every manifest reports `2.4.0`.

- [ ] **Step 1: Add the failing version synchronization test**

Add this method inside `CodexCompatibilityTests`:

```python
    def test_all_release_versions_match(self) -> None:
        paths = (
            "package.json",
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            ".codex-plugin/plugin.json",
        )
        versions = {
            path: json.loads(read_text(path))["version"]
            for path in paths
        }
        self.assertEqual({"2.4.0"}, set(versions.values()), versions)
```

- [ ] **Step 2: Run the test and confirm the expected failure**

Run:

```bash
python3 -m unittest scripts.test_codex_compatibility.CodexCompatibilityTests.test_all_release_versions_match -v
```

Expected: failure because the manifests still report `2.3.0`.

- [ ] **Step 3: Change only the four version values to `2.4.0`**

Do not alter Claude manifest descriptions, commands, marketplace source, or other metadata.

- [ ] **Step 4: Run the version and full compatibility suites**

Run:

```bash
python3 -m unittest scripts.test_codex_compatibility -v
```

Expected: all compatibility tests pass.

---

### Task 8: Perform full local verification

**Files:**

- Verify only; do not edit unless a check exposes an in-scope defect.

- [ ] **Step 1: Run both Python test paths**

Run:

```bash
python3 scripts/test_classify_discussions.py
python3 -m unittest scripts.test_codex_compatibility -v
```

Expected: `OK` from the existing helper tests and all compatibility tests pass.

- [ ] **Step 2: Run syntax, JSON, and whitespace checks**

Run:

```bash
python3 -m py_compile scripts/classify_discussions.py scripts/test_classify_discussions.py scripts/test_codex_compatibility.py
python3 -m json.tool package.json >/dev/null
python3 -m json.tool .claude-plugin/plugin.json >/dev/null
python3 -m json.tool .claude-plugin/marketplace.json >/dev/null
python3 -m json.tool .codex-plugin/plugin.json >/dev/null
git diff --check
```

Expected: all commands exit 0 with no diff-check output.

- [ ] **Step 3: Verify protected hashes independently**

Run:

```bash
sha256sum agents/*.md rules/code-review-standards.md commands/follow-up-review.md commands/clear-mr-comments.md
```

Compare every value to `PROTECTED_SHA256` in the test. Expected: exact match.

- [ ] **Step 4: Verify package contents**

Run:

```bash
npm pack --dry-run --json
```

Inspect the JSON file list. It must contain:

- `.codex-plugin/plugin.json`;
- `skills/sissy-squad/SKILL.md`;
- `skills/follow-up-review/SKILL.md`;
- `.codex-plugin/runtime-adapter.md`;
- both canonical commands;
- every canonical agent and `rules/code-review-standards.md`;
- `scripts/test_codex_compatibility.py` and user docs.

- [ ] **Step 5: Validate local Codex prerequisites without changing plugin state**

Run:

```bash
codex --version
codex mcp list
codex plugin marketplace list --json
codex plugin list --json
```

Expected: Codex CLI responds; the configured GitLab MCP server is visible; no local installation is attempted before the release exists.

- [ ] **Step 6: Review scope and protected prompt diff**

Run:

```bash
git status --short
git diff --stat
git diff -- agents rules/code-review-standards.md commands/follow-up-review.md commands/clear-mr-comments.md
git diff -- commands/sissy-squad.md
```

Expected: the protected-file diff is empty. `commands/sissy-squad.md` contains only approved config migration/path edits.

---

### Task 9: Mandatory complete-diff approval gate

**Files:**

- No edits.

- [ ] **Step 1: Show all changes before any commit**

Run and present the complete output to the user:

```bash
git diff --no-ext-diff -- . ':(exclude)docs/superpowers/specs/2026-08-09-codex-cli-compatibility-design.md' ':(exclude)docs/superpowers/plans/2026-08-09-codex-cli-compatibility.md'
git diff --no-index /dev/null docs/superpowers/specs/2026-08-09-codex-cli-compatibility-design.md || true
git diff --no-index /dev/null docs/superpowers/plans/2026-08-09-codex-cli-compatibility.md || true
```

Also provide `git status --short` and the fresh verification results from Task 8.

- [ ] **Step 2: Stop and request explicit commit/release approval**

Do not stage, commit, tag, push, publish, or install yet. Ask the user to approve the displayed complete diff. Examples of valid explicit responses are `approved` or `go ahead`.

This is the one unavoidable pause in the user's “do not stop” instruction because repository instructions prohibit a commit before explicit post-diff approval.

---

### Task 10: Commit, tag, push, and publish v2.4.0

**Files:**

- Create release-note scratchpad file outside the repository, as required by the user's copyable-output rule.
- No further repository edits unless verification catches an approved in-scope defect; any new diff requires returning to Task 9.

- [ ] **Step 1: Confirm approval and re-run the release-critical checks**

Run:

```bash
python3 scripts/test_classify_discussions.py
python3 -m unittest scripts.test_codex_compatibility -v
npm pack --dry-run --json
git diff --check
```

Expected: all pass immediately before commit.

- [ ] **Step 2: Stage the exact release scope and inspect it**

Run:

```bash
git add \
  .codex-plugin/plugin.json \
  .claude-plugin/plugin.json \
  .claude-plugin/marketplace.json \
  skills \
  scripts/.npmignore \
  scripts/test_codex_compatibility.py \
  commands/sissy-squad.md \
  templates/review-config.yml \
  package.json \
  README.md \
  CONTRIBUTING.md \
  docs/installation.md \
  docs/configuration.md \
  docs/troubleshooting.md \
  RELEASE.md \
  docs/superpowers/specs/2026-08-09-codex-cli-compatibility-design.md \
  docs/superpowers/plans/2026-08-09-codex-cli-compatibility.md
git diff --cached --check
git status --short
```

Expected: only the approved release files are staged.

- [ ] **Step 3: Create the approved release commit and annotated tag**

Run:

```bash
git commit -m "feat: add Codex CLI compatibility"
git tag -a v2.4.0 -m "Release v2.4.0"
```

- [ ] **Step 4: Verify commit and tag locally**

Run:

```bash
git status --short
git show --stat --oneline --decorate HEAD
git tag -n99 -l v2.4.0
```

Expected: clean worktree, one release commit, annotated `v2.4.0` tag.

- [ ] **Step 5: Push main and tag**

Run:

```bash
git push origin main
git push origin v2.4.0
```

- [ ] **Step 6: Write and publish release notes**

Write these sections to a scratchpad Markdown file, print its full absolute path after writing, and pass it to `gh release create --notes-file`:

```markdown
## What's Changed

### Features
- Added Codex CLI plugin support for the canonical `sissy-squad` and `follow-up-review` workflows.
- Added a shared runtime adapter for Codex subagents, model tiers, and configured GitLab MCP operations without duplicating reviewer prompts.

### Configuration
- Moved review-agent selection to `.sissy/review-config.yml`.
- Existing `.claude/review-config.yml` is copied unchanged on first use when the neutral file is absent; the legacy file is never overwritten or removed.

### Compatibility
- Claude Code commands and protected reviewer prompts remain unchanged.
- `clear-mr-comments` remains Claude Code-only.

**Full Changelog**: https://github.com/milad-afkhami/sissy-code-review-squad/compare/v2.3.0...v2.4.0
```

Then run `gh release create v2.4.0 --title "v2.4.0" --notes-file` with the exact absolute path printed after the scratchpad write, followed by:

```bash
gh release view v2.4.0
```

- [ ] **Step 7: Update Claude Code locally**

Run:

```bash
claude plugin update sissy-code-review-squad@sissy-code-review-squad
```

If the installed Claude CLI uses `plugins` rather than `plugin`, use the syntax reported by `claude --help`; do not alter repository files for a local CLI spelling difference.

---

### Task 11: Install the released plugin in Codex and hand off restart

**Files:**

- No repository edits.

- [ ] **Step 1: Add the released repository tag as a Codex marketplace**

Run:

```bash
codex plugin marketplace add milad-afkhami/sissy-code-review-squad --ref v2.4.0 --json
```

If the marketplace already exists, inspect `codex plugin marketplace list --json` and upgrade it to `v2.4.0` using the subcommand shown by `codex plugin marketplace --help`; do not create a duplicate marketplace.

- [ ] **Step 2: Install the released plugin**

Run:

```bash
codex plugin add sissy-code-review-squad@sissy-code-review-squad --json
```

If already installed, use the marketplace upgrade/install flow reported by `codex plugin --help` rather than deleting user configuration.

- [ ] **Step 3: Verify enabled state and cached release contents**

Run:

```bash
codex plugin marketplace list --json
codex plugin list --json
```

From the installed plugin record, resolve its cache path and verify:

```bash
SISSY_CODEX_CACHE_PATH=$(codex plugin list --json | python3 -c '
import json
import sys

plugins = json.load(sys.stdin)["installed"]
match = next(
    item for item in plugins
    if item["pluginId"] == "sissy-code-review-squad@sissy-code-review-squad"
)
print(match["source"]["path"])
')
python3 -m json.tool "$SISSY_CODEX_CACHE_PATH/.codex-plugin/plugin.json"
test -f "$SISSY_CODEX_CACHE_PATH/skills/sissy-squad/SKILL.md"
test -f "$SISSY_CODEX_CACHE_PATH/skills/follow-up-review/SKILL.md"
test ! -e "$SISSY_CODEX_CACHE_PATH/skills/clear-mr-comments/SKILL.md"
```

Expected: version `2.4.0`, installed `true`, enabled `true`, exactly the two approved skill entrypoints.

- [ ] **Step 4: Ask the user to restart Codex**

Report the published release, local Claude update result, Codex marketplace/plugin enabled state, and installed cache verification. Then ask the user to restart Codex so the newly installed skills are discovered. Do not claim the skills are visible in the current session before that restart.

The only intentionally unrun check may be a live GitLab MR smoke test when no disposable MR URL was supplied; state that clearly.

---

## v2.4.1 Forward Patch: Separate Runtime Discovery

Version 2.4.0 was committed, tagged, pushed, published, and installed into
Claude. Claude's component inventory then revealed five skills: its three
canonical commands plus duplicate Codex wrappers for `sissy-squad` and
`follow-up-review`. Do not rewrite or delete the published tag. Complete the
following patch release instead.

### Task 12: Reproduce and isolate the discovery conflict

**Files:** Verify only.

- [x] Run `claude --plugin-dir . plugin details sissy-code-review-squad` and
  confirm it reports five skills.
- [x] Confirm Claude always adds the root `skills/` directory while Codex's
  plugin validator requires `skills/` at its plugin root.
- [x] Test a nested Claude projection and a Codex-native marketplace in
  temporary local installations.
- [x] Confirm both caches materialize the protected canonical prompts with the
  v2.3.0 SHA-256 values and expose only the intended runtime entrypoints.

### Task 13: Add the split-marketplace regression tests

**Files:**

- Modify: `scripts/test_codex_compatibility.py`

- [x] Add a real Claude CLI inventory test for exactly the three canonical
  Claude commands.
- [x] Add catalog-routing tests for `.agents/plugins/marketplace.json` and the
  nested Claude projection.
- [x] Add symlink-integrity tests for the Claude projection.
- [x] Change the npm contract to require canonical Claude files and reject
  `.codex-plugin/` and `skills/` from the npm artifact.
- [x] Run the new tests before implementation and observe the expected
  duplicate-inventory, missing-catalog, missing-symlink, and package failures.

### Task 14: Implement and verify the v2.4.1 projection

**Files:**

- Create: `.agents/plugins/marketplace.json`
- Create: `claude-plugin/.claude-plugin/plugin.json` symlink
- Create: `claude-plugin/commands` symlink
- Create: `claude-plugin/agents` symlink
- Create: `claude-plugin/rules` symlink
- Create: `claude-plugin/scripts` symlink
- Create: `claude-plugin/package.json` symlink
- Modify: `.claude-plugin/marketplace.json`
- Modify: `package.json`
- Modify: `.claude-plugin/plugin.json`
- Modify: `.codex-plugin/plugin.json`
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`
- Modify: `docs/installation.md`
- Modify: `RELEASE.md`
- Modify: this plan and its design spec

- [x] Route Codex's native catalog to `./` and Claude's legacy catalog to
  `./claude-plugin`.
- [x] Create only relative symlinks in the Claude projection; do not copy or
  edit canonical prompt bodies.
- [x] Keep the npm artifact Claude-only by removing `.codex-plugin/` and
  `skills/` from `package.json`'s file list.
- [x] Set all four release versions to `2.4.1`.
- [x] Run the full Python suites, JSON and syntax checks, official plugin and
  skill validators, Claude inventory, npm dry run, protected hashes, and diff
  checks.

### Task 15: Obtain approval for the v2.4.1 diff

- [ ] Generate a complete tracked and untracked diff against v2.4.0.
- [ ] Confirm no protected prompt body changed and every new projection entry
  is a symlink.
- [ ] Present the complete diff and fresh verification results.
- [ ] Obtain explicit approval before staging or committing the forward patch.

### Task 16: Publish and install v2.4.1

- [ ] Commit with `fix: isolate Claude and Codex plugin discovery`.
- [ ] Create and push annotated tag `v2.4.1` without changing v2.4.0.
- [ ] Publish GitHub release v2.4.1 with a changelog link from v2.4.0.
- [ ] Refresh and update the installed Claude plugin; verify exactly three
  canonical commands in its component inventory.
- [ ] Add the v2.4.1 repository tag as the Codex marketplace and install
  `sissy-code-review-squad@sissy-code-review-squad`.
- [ ] Verify Codex version 2.4.1 is installed and enabled, both Codex skills are
  cached, `clear-mr-comments` is absent, and protected prompt hashes match.
- [ ] Stop only when restarting Codex is the sole remaining user action.
