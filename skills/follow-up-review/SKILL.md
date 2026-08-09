---
name: follow-up-review
description: Use when the user explicitly invokes the Codex Sissy follow-up skill with a GitLab merge request URL.
---

# Follow-Up Review

Treat the complete text supplied after this skill invocation as the skill arguments.

1. Resolve the plugin root as two directories above this `SKILL.md`.
2. Read `.codex-plugin/runtime-adapter.md` from the plugin root completely.
3. Read `commands/follow-up-review.md` from the plugin root completely.
4. Execute the canonical command once. Substitute the skill arguments for the command arguments and apply only the host translations in the shared adapter.

Keep the canonical command and its referenced agent and rule files authoritative.
