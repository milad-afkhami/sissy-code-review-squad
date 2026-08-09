# Release Guide

This is the release process for Sissy Code Review Squad across Claude Code and
Codex CLI.

## Prerequisites

- You have write access to the GitHub repository.
- Git and GitHub CLI authentication are configured.
- The intended release changes are complete and locally verified.
- No commit has been created before the repository-required complete-diff
  approval gate.

## Version Files

Keep the version synchronized in all four files:

1. `package.json`
2. `.claude-plugin/plugin.json`
3. `.claude-plugin/marketplace.json`
4. `.codex-plugin/plugin.json`

Use semantic versioning: patch for compatible fixes, minor for compatible
features, and major for breaking changes.

## Release Process

### 1. Update All Four Versions

Change only the `version` value in each version file, then verify equality:

```bash
python3 - <<'PY'
import json
from pathlib import Path

paths = (
    Path("package.json"),
    Path(".claude-plugin/plugin.json"),
    Path(".claude-plugin/marketplace.json"),
    Path(".codex-plugin/plugin.json"),
)
versions = {str(path): json.loads(path.read_text())["version"] for path in paths}
print(versions)
if len(set(versions.values())) != 1:
    raise SystemExit("version mismatch")
PY
```

### 2. Run Release Verification

```bash
python3 scripts/test_classify_discussions.py
python3 -m unittest scripts.test_codex_compatibility -v
python3 -m py_compile scripts/classify_discussions.py scripts/test_classify_discussions.py scripts/test_codex_compatibility.py
python3 -m json.tool package.json >/dev/null
python3 -m json.tool .claude-plugin/plugin.json >/dev/null
python3 -m json.tool .claude-plugin/marketplace.json >/dev/null
python3 -m json.tool .codex-plugin/plugin.json >/dev/null
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
claude --plugin-dir ./claude-plugin plugin details sissy-code-review-squad
npm pack --dry-run --json
git diff --check
```

Confirm Claude reports exactly three skills (`clear-mr-comments`,
`follow-up-review`, and `sissy-squad`) with no duplicate names. Confirm the npm
file list contains the canonical Claude command, agent, and rule files while
excluding `.codex-plugin/` and `skills/`; Codex is distributed from the Git
marketplace rather than the Claude-oriented npm artifact.

### 3. Show the Complete Diff and Get Approval

Show `git status --short`, the complete tracked and untracked release diff, and
the verification results. Wait for explicit approval before staging or
committing. If anything changes after approval, show the new complete diff and
obtain approval again.

### 4. Commit the Approved Release

Stage only the approved files and inspect the staged diff:

```bash
git add <approved-release-files>
git diff --cached --check
git diff --cached
git commit -m "<approved-release-commit-message>"
```

### 5. Create and Verify the Annotated Tag

```bash
git tag -a "v<new-version>" -m "Release v<new-version>"
git tag -n99 -l "v<new-version>"
```

### 6. Push Main and the Tag

```bash
git push origin main
git push origin "v<new-version>"
```

### 7. Publish the GitHub Release

Write release notes to a Markdown file and publish them without shell-embedded
multiline text:

```bash
gh release create "v<new-version>" \
  --title "v<new-version>" \
  --notes-file "/absolute/path/to/release-notes.md"
gh release view "v<new-version>"
```

Release notes should describe user-visible features, configuration migrations,
compatibility, and the full changelog link.

### 8. Update Claude Code Locally

Use the command spelling supported by the installed Claude CLI:

```bash
claude plugin update sissy-code-review-squad@sissy-code-review-squad
claude plugin details sissy-code-review-squad@sissy-code-review-squad
```

If the local CLI uses `plugins` rather than `plugin`, follow `claude --help`.
The details output must list exactly the three canonical Claude commands, with
no duplicate `sissy-squad` or `follow-up-review` entry.

### 9. Install the Released Codex Plugin

For the first install, add the released repository tag as a marketplace and
install the plugin:

```bash
codex plugin marketplace add milad-afkhami/sissy-code-review-squad --ref "v<new-version>" --json
codex plugin add sissy-code-review-squad@sissy-code-review-squad --json
```

If the marketplace already exists, inspect it and use the supported marketplace
upgrade flow rather than adding a duplicate:

```bash
codex plugin marketplace list --json
codex plugin marketplace upgrade sissy-code-review-squad --json
codex plugin add sissy-code-review-squad@sissy-code-review-squad --json
```

### 10. Verify Local State and Restart

```bash
codex plugin marketplace list --json
codex plugin list --json
```

Confirm the released version is installed and enabled, the cached manifest is
valid, `$sissy-squad` and `$follow-up-review` exist, and no Codex
`$clear-mr-comments` skill exists. Restart Claude Code after its update and
restart Codex after its install so each runtime discovers the release.

## Release Notes Template

```markdown
## What's Changed

### Features
- ...

### Configuration
- ...

### Compatibility
- ...

**Full Changelog**: https://github.com/milad-afkhami/sissy-code-review-squad/compare/v<previous-version>...v<new-version>
```

## Verification Checklist

- [ ] All four version files match.
- [ ] Automated tests, JSON validation, package dry run, and diff check pass.
- [ ] The complete diff was explicitly approved before commit.
- [ ] The annotated tag exists locally and on GitHub.
- [ ] The GitHub release is published with the intended notes.
- [ ] The local Claude plugin update completed.
- [ ] The Codex marketplace points to the released tag.
- [ ] The Codex plugin is installed and enabled.
- [ ] The affected runtime was restarted and exposes the expected commands or skills.

## Rollback

Do not delete a published release or remote tag as a routine recovery step. Those
actions affect other users and require explicit approval after confirming the
exact tag and release. Prefer a forward fix or a reviewed revert release when
the published artifact has already been consumed.
