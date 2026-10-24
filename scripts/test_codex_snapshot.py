"""Exercise the Codex input boundary against real git objects."""

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


HELPER = Path(__file__).resolve().parents[1] / ".codex-plugin/snapshot.py"


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "snapshot-test@example.invalid")
        self.git("config", "user.name", "Snapshot test")
        self.git("config", "commit.gpgsign", "false")
        for name in ("changed.txt", "removed.txt", "rename me.txt", "stable.txt"):
            (self.repo / name).write_text(name + "\n" + "unchanged\n" * 20)
        self.commit()
        self.base = self.git("rev-parse", "HEAD").strip()
        # Both rename paths occur in the canonical authored-commit inventory.
        with (self.repo / "rename me.txt").open("a") as source:
            source.write("feature edit before rename\n")
        self.commit()
        (self.repo / "changed.txt").write_text("middle-marker\n" + "large diff\n" * 15000 + "last-marker\n")
        (self.repo / "removed.txt").unlink()
        self.git("mv", "rename me.txt", "renamed file.txt")
        (self.repo / "added.txt").write_text("new file\n")
        self.commit()
        self.head = self.git("rev-parse", "HEAD").strip()
        self.context = {
            "title": "Snapshot fixture", "description": "Requirements\n" + "context\n" * 20000 + "required-tail",
            "source_branch": "feature", "target_branch": "main",
            "diff_refs": {"base_sha": self.base, "start_sha": self.base, "head_sha": self.head},
            "changed_files": [
                {"old_path": "added.txt", "new_path": "added.txt", "new_file": True},
                {"old_path": "changed.txt", "new_path": "changed.txt"},
                {"old_path": "removed.txt", "new_path": "/dev/null", "deleted_file": True},
                {"old_path": "rename me.txt", "new_path": "renamed file.txt"},
            ],
        }
        self.input = self.root / "input.json"

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, text=True).stdout

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "fixture")

    def run_snapshot(self):
        self.input.write_text(json.dumps(self.context))
        return subprocess.run([
            "python3", str(HELPER), "--repo", str(self.repo), "--input", str(self.input),
            "--output-parent", str(self.root),
        ], capture_output=True, text=True)

    def test_complete_snapshot_recovers_full_diff_and_keeps_large_requirements(self):
        self.context["changed_files"][1]["diff"] = "...truncated..."
        result = self.run_snapshot()
        self.assertEqual(0, result.returncode, result.stderr)
        output = json.loads(result.stdout)
        frozen = json.loads(Path(output["snapshot_path"]).read_text())
        self.assertEqual(self.context["description"], frozen["description"])
        changes = {x["new_path"]: x for x in frozen["changed_files"]}
        self.assertEqual(4, len(changes))
        self.assertIn("+middle-marker", changes["changed.txt"]["diff"])
        self.assertIn("+last-marker", changes["changed.txt"]["diff"])
        self.assertGreater(len(changes["changed.txt"]["diff"]), 150000)
        self.assertTrue(changes["added.txt"]["new_file"])
        self.assertTrue(changes["removed.txt"]["deleted_file"])
        self.assertEqual("rename me.txt", changes["renamed file.txt"]["old_path"])
        run = Path(output["run_dir"])
        self.assertEqual(self.input.read_bytes(), (run / "source.json").read_bytes())
        manifest = json.loads((run / "manifest.json").read_text())
        self.assertEqual(self.head, manifest["head_sha"])
        self.assertEqual(hashlib.sha256(Path(output["snapshot_path"]).read_bytes()).hexdigest(), manifest["snapshot_sha256"])

    def test_incomplete_file_inventory_is_rejected_before_snapshot(self):
        self.context["changed_files"] = self.context["changed_files"][:1]
        result = self.run_snapshot()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("changed file inventory", result.stderr)
        self.assertFalse(list(self.root.glob("sissy-codex-*")))

    def test_duplicate_paths_cannot_hide_an_omitted_file(self):
        self.context["changed_files"][1] = self.context["changed_files"][0]
        result = self.run_snapshot()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("changed file inventory", result.stderr)

    def test_stale_worktree_is_rejected(self):
        self.git("checkout", "-q", self.base)
        result = self.run_snapshot()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("worktree HEAD", result.stderr)

    def test_dirty_worktree_cannot_supply_source_for_a_clean_snapshot(self):
        (self.repo / "changed.txt").write_text("different code than the recorded head\n")
        result = self.run_snapshot()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("worktree has local changes", result.stderr)

    def test_merge_only_changes_remain_outside_canonical_authored_scope(self):
        self.git("checkout", "-qb", "side", self.base)
        (self.repo / "stable.txt").write_text("side-branch edit\n")
        self.commit()
        self.git("checkout", "-q", "--detach", self.head)
        self.git("merge", "--no-ff", "--no-commit", "side")
        (self.repo / "merge-only.txt").write_text("created only during the merge\n")
        self.commit()
        self.context["diff_refs"]["head_sha"] = self.git("rev-parse", "HEAD").strip()
        self.context["changed_files"].append({"old_path": "stable.txt", "new_path": "stable.txt"})
        result = self.run_snapshot()
        self.assertEqual(0, result.returncode, result.stderr)
        frozen = json.loads(Path(json.loads(result.stdout)["snapshot_path"]).read_text())
        self.assertEqual(5, len(frozen["changed_files"]))
        self.assertNotIn("merge-only.txt", [item["new_path"] for item in frozen["changed_files"]])

    def test_invalid_refs_are_rejected_without_git_revision_injection(self):
        self.context["diff_refs"]["base_sha"] = "HEAD~1"
        result = self.run_snapshot()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("full commit SHA", result.stderr)

    def test_empty_authored_filter_preserves_canonical_git_diff_fallback(self):
        self.git("checkout", "-qb", "target", self.base)
        (self.repo / "stable.txt").write_text("already on target\n")
        self.commit()
        target = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-q", "--detach", self.base)
        self.git("merge", "--no-ff", "--no-commit", "target")
        (self.repo / "merge-only.txt").write_text("merge resolution\n")
        self.commit()
        self.context["diff_refs"] = {"base_sha": target, "start_sha": target,
                                     "head_sha": self.git("rev-parse", "HEAD").strip()}
        self.context["changed_files"] = [{"old_path": "merge-only.txt", "new_path": "merge-only.txt"}]
        result = self.run_snapshot()
        self.assertEqual(0, result.returncode, result.stderr)
        frozen = json.loads(Path(json.loads(result.stdout)["snapshot_path"]).read_text())
        self.assertEqual(["merge-only.txt"], [item["new_path"] for item in frozen["changed_files"]])

    def test_file_to_directory_conversion_has_no_duplicated_child_patch(self):
        (self.repo / "stable.txt").unlink()
        (self.repo / "stable.txt").mkdir()
        (self.repo / "stable.txt/settings").write_text("setting=value\n")
        self.commit()
        self.context["diff_refs"]["head_sha"] = self.git("rev-parse", "HEAD").strip()
        self.context["changed_files"].extend([
            {"old_path": "stable.txt", "new_path": "stable.txt", "deleted_file": True},
            {"old_path": "stable.txt/settings", "new_path": "stable.txt/settings", "new_file": True},
        ])
        result = self.run_snapshot()
        self.assertEqual(0, result.returncode, result.stderr)
        frozen = json.loads(Path(json.loads(result.stdout)["snapshot_path"]).read_text())
        changes = {x["new_path"]: x for x in frozen["changed_files"]}
        self.assertNotIn("diff --git a/stable.txt/settings", changes["stable.txt"]["diff"])
        self.assertEqual(1, changes["stable.txt/settings"]["diff"].count("diff --git "))

    def test_type_change_keeps_both_git_patch_sections_under_one_file(self):
        (self.repo / "stable.txt").unlink()
        (self.repo / "stable.txt").symlink_to("added.txt")
        self.commit()
        self.context["diff_refs"]["head_sha"] = self.git("rev-parse", "HEAD").strip()
        self.context["changed_files"].append({"old_path": "stable.txt", "new_path": "stable.txt"})
        result = self.run_snapshot()
        self.assertEqual(0, result.returncode, result.stderr)
        frozen = json.loads(Path(json.loads(result.stdout)["snapshot_path"]).read_text())
        change = next(x for x in frozen["changed_files"] if x["new_path"] == "stable.txt")
        self.assertIn("120000", change["diff"])
        self.assertEqual(2, change["diff"].count("diff --git "))

    def test_repeated_runs_do_not_overwrite_the_previous_snapshot(self):
        first = self.run_snapshot()
        self.assertEqual(0, first.returncode, first.stderr)
        first_path = Path(json.loads(first.stdout)["snapshot_path"])
        original = first_path.read_bytes()
        second = self.run_snapshot()
        self.assertEqual(0, second.returncode, second.stderr)
        self.assertNotEqual(str(first_path), json.loads(second.stdout)["snapshot_path"])
        self.assertEqual(original, first_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
