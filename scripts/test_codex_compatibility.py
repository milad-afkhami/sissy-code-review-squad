#!/usr/bin/env python3
"""Contract tests for Claude Code and Codex CLI plugin compatibility."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
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
    path = ROOT / relative_path
    assert path.is_file(), f"missing required file: {relative_path}"
    return path.read_text(encoding="utf-8")


def bash_block_after(relative_path: str, marker: str) -> str:
    body = read_text(relative_path)
    assert marker in body, f"missing marker in {relative_path}: {marker}"
    match = re.search(r"```bash\n(.*?)\n```", body.split(marker, 1)[1], re.DOTALL)
    assert match is not None, f"missing bash block after marker: {marker}"
    return match.group(1)


class CodexCompatibilityTests(unittest.TestCase):
    def test_protected_prompt_hashes_match_2_3_0_baseline(self) -> None:
        for relative_path, expected in PROTECTED_SHA256.items():
            with self.subTest(path=relative_path):
                actual = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
                self.assertEqual(expected, actual)

    def test_codex_manifest_declares_skills_plugin(self) -> None:
        manifest = json.loads(read_text(".codex-plugin/plugin.json"))
        self.assertEqual("sissy-code-review-squad", manifest["name"])
        self.assertEqual("2.4.2", manifest["version"])
        self.assertEqual("./skills/", manifest["skills"])
        self.assertEqual(
            "Sissy Code Review Squad",
            manifest["interface"]["displayName"],
        )
        self.assertEqual("Productivity", manifest["interface"]["category"])

    def test_codex_native_marketplace_routes_to_root_plugin(self) -> None:
        catalog_path = ROOT / ".agents/plugins/marketplace.json"
        self.assertTrue(catalog_path.is_file(), "missing Codex-native marketplace")
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        plugin = next(
            item
            for item in catalog["plugins"]
            if item["name"] == "sissy-code-review-squad"
        )
        self.assertEqual(
            {"source": "local", "path": "./"},
            plugin["source"],
        )

    def test_claude_marketplace_routes_to_projection(self) -> None:
        catalog = json.loads(read_text(".claude-plugin/marketplace.json"))
        plugin = next(
            item
            for item in catalog["plugins"]
            if item["name"] == "sissy-code-review-squad"
        )
        self.assertEqual("./claude-plugin", plugin["source"])

    def test_claude_projection_symlinks_to_canonical_sources(self) -> None:
        expected = {
            "claude-plugin/.claude-plugin/plugin.json": ".claude-plugin/plugin.json",
            "claude-plugin/commands": "commands",
            "claude-plugin/agents": "agents",
            "claude-plugin/rules": "rules",
            "claude-plugin/scripts": "scripts",
            "claude-plugin/package.json": "package.json",
        }
        for projection, canonical in expected.items():
            with self.subTest(path=projection):
                path = ROOT / projection
                self.assertTrue(path.is_symlink(), f"not a symlink: {projection}")
                self.assertEqual((ROOT / canonical).resolve(), path.resolve())

    @unittest.skipUnless(shutil.which("claude"), "Claude CLI is not installed")
    def test_claude_projection_exposes_only_canonical_commands(self) -> None:
        completed = subprocess.run(
            [
                "claude",
                "--plugin-dir",
                str(ROOT / "claude-plugin"),
                "plugin",
                "details",
                "sissy-code-review-squad",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr or completed.stdout)
        inventory = re.search(
            r"(?m)^  Skills \((\d+)\)\s+(.+)$",
            completed.stdout,
        )
        self.assertIsNotNone(inventory, completed.stdout)
        assert inventory is not None
        self.assertEqual("3", inventory.group(1))
        self.assertEqual(
            ["clear-mr-comments", "follow-up-review", "sissy-squad"],
            inventory.group(2).split(", "),
        )

    def test_sissy_skill_references_canonical_sources(self) -> None:
        body = read_text("skills/sissy-squad/SKILL.md")
        self.assertRegex(body, r"(?m)^name: sissy-squad$")
        self.assertRegex(body, r"(?m)^description: Use when \S.+$")
        self.assertIn(".codex-plugin/runtime-adapter.md", body)
        self.assertIn("commands/sissy-squad.md", body)

    def test_initial_review_runtime_adapter_contract(self) -> None:
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
            "create_merge_request_thread",
            "create_merge_request_note",
        ):
            self.assertIn(operation, body)

        for row in (
            "| Haiku | `gpt-5.6-luna` | `medium` |",
            "| Sonnet | `gpt-5.6-terra` | `high` |",
            "| Opus | `gpt-5.6-sol` | `xhigh` |",
        ):
            self.assertIn(row, body)

        self.assertNotIn("| Opus | `gpt-5.6` | `xhigh` |", body)

        self.assertIn("before creating a worktree", body)
        self.assertIn("before posting GitLab content", body)
        self.assertIn("Do not silently substitute", body)

    def test_codex_initial_host_does_not_copy_canonical_bodies(self) -> None:
        host_paths = (
            ROOT / "skills/sissy-squad/SKILL.md",
            ROOT / ".codex-plugin/runtime-adapter.md",
        )
        host = "\n".join(
            read_text(str(path.relative_to(ROOT))) for path in host_paths
        )
        canonical_paths = [
            ROOT / "commands/sissy-squad.md",
            ROOT / "rules/code-review-standards.md",
            *sorted((ROOT / "agents").glob("*.md")),
        ]
        for path in canonical_paths:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn(path.read_text(encoding="utf-8"), host)

    def test_every_skills_child_is_an_actual_skill(self) -> None:
        for path in sorted((ROOT / "skills").iterdir()):
            if path.is_dir() and not path.name.startswith("."):
                with self.subTest(path=path.name):
                    self.assertTrue(
                        (path / "SKILL.md").is_file(),
                        f"skills child is not a skill: {path.name}",
                    )

    def test_codex_exposes_only_approved_skills(self) -> None:
        skills = sorted(
            path.parent.name
            for path in (ROOT / "skills").glob("*/SKILL.md")
        )
        self.assertEqual(["follow-up-review", "sissy-squad"], skills)
        self.assertFalse((ROOT / "skills/clear-mr-comments/SKILL.md").exists())

    def test_follow_up_skill_references_canonical_sources(self) -> None:
        body = read_text("skills/follow-up-review/SKILL.md")
        self.assertRegex(body, r"(?m)^name: follow-up-review$")
        self.assertRegex(body, r"(?m)^description: Use when \S.+$")
        self.assertIn(".codex-plugin/runtime-adapter.md", body)
        self.assertIn("commands/follow-up-review.md", body)

    def test_follow_up_runtime_adapter_contract(self) -> None:
        body = read_text(".codex-plugin/runtime-adapter.md")
        for operation in (
            "mr_discussions",
            "create_merge_request_discussion_note",
            "resolve_merge_request_thread",
        ):
            self.assertIn(operation, body)

        self.assertIn("follow-up evaluator buckets form one logical parallel stage", body)
        self.assertIn("follow-up verdict writes remain serial", body)
        self.assertIn("agents/classify-mr-discussions.md", body)
        self.assertIn("agents/thread-evaluator.md", body)

    def test_legacy_config_is_copied_once_without_modifying_source(self) -> None:
        block = bash_block_after(
            "commands/sissy-squad.md",
            "**3a. Migrate and read existing config.**",
        )
        legacy_bytes = b"agents:\n  security:\n    enabled: false\n"

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / ".claude/review-config.yml"
            legacy.parent.mkdir()
            legacy.write_bytes(legacy_bytes)

            subprocess.run(
                ["bash", "-euo", "pipefail", "-c", block],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual(legacy_bytes, legacy.read_bytes())
            self.assertEqual(
                legacy_bytes,
                (root / ".sissy/review-config.yml").read_bytes(),
            )

    def test_existing_neutral_config_is_never_overwritten_by_legacy(self) -> None:
        block = bash_block_after(
            "commands/sissy-squad.md",
            "**3a. Migrate and read existing config.**",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / ".claude/review-config.yml"
            neutral = root / ".sissy/review-config.yml"
            legacy.parent.mkdir()
            neutral.parent.mkdir()
            legacy.write_bytes(b"legacy\n")
            neutral.write_bytes(b"neutral\n")

            subprocess.run(
                ["bash", "-euo", "pipefail", "-c", block],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual(b"legacy\n", legacy.read_bytes())
            self.assertEqual(b"neutral\n", neutral.read_bytes())

    def test_picker_targets_only_neutral_config(self) -> None:
        body = read_text("commands/sissy-squad.md")
        self.assertIn("} > .sissy/review-config.yml", body)
        self.assertNotIn("> .claude/review-config.yml", body)
        self.assertNotRegex(body, r"(?m)^\s*rm\s+.*review-config\.yml")

    def test_review_config_template_points_to_neutral_path(self) -> None:
        body = read_text("templates/review-config.yml")
        self.assertIn(".sissy/review-config.yml", body)
        self.assertNotIn(".claude/review-config.yml", body)

    def test_npm_package_contains_claude_runtime_files(self) -> None:
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
            "commands/sissy-squad.md",
            "commands/follow-up-review.md",
            "commands/clear-mr-comments.md",
            "agents/security.md",
            "rules/code-review-standards.md",
        }
        self.assertLessEqual(required, packaged)
        cache_artifacts = {
            path
            for path in packaged
            if "__pycache__" in Path(path).parts or path.endswith((".pyc", ".pyo"))
        }
        self.assertEqual(set(), cache_artifacts)

    def test_npm_package_excludes_codex_host_files_from_claude_artifact(self) -> None:
        completed = subprocess.run(
            ["npm", "pack", "--dry-run", "--json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        packaged = {entry["path"] for entry in payload[0]["files"]}
        codex_host_files = {
            path
            for path in packaged
            if path.startswith(".codex-plugin/") or path.startswith("skills/")
        }
        self.assertEqual(set(), codex_host_files)

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
        self.assertEqual({"2.4.2"}, set(versions.values()), versions)


if __name__ == "__main__":
    unittest.main()
