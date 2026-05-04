# Release Guide

This document describes the exact process for releasing a new version of the Sissy Code Review Squad plugin.

## Prerequisites

- All changes are committed and tested
- You have write access to the repository
- Git is configured with your credentials

## Version Files to Update

The plugin version is stored in **3 files** that must be kept in sync:

1. `package.json` - Root package file
2. `.claude-plugin/plugin.json` - Claude Code plugin metadata
3. `.claude-plugin/marketplace.json` - Marketplace listing metadata

## Release Process

### Step 1: Decide Version Number

Follow [Semantic Versioning](https://semver.org/):

- **Patch** (x.y.Z) - Bug fixes, small improvements
- **Minor** (x.Y.0) - New features, backward compatible
- **Major** (X.0.0) - Breaking changes

### Step 2: Update All Version Files

**CRITICAL:** Update the version in ALL THREE files to the same value.

```bash
# 1. Update package.json
# Change: "version": "<old>" → "version": "<new>"

# 2. Update .claude-plugin/plugin.json
# Change: "version": "<old>" → "version": "<new>"

# 3. Update .claude-plugin/marketplace.json
# Change: "version": "<old>" → "version": "<new>"
```

### Step 3: Commit Version Bump

```bash
git add package.json .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: bump version to <new-version>"
```

### Step 4: Create Git Tag

```bash
# Create annotated tag with version
git tag -a v<new-version> -m "Release v<new-version>"

# Verify tag was created
git tag -l "v<new-version>"
```

### Step 5: Push to Remote

```bash
# Push commits
git push origin main

# Push tags
git push origin v<new-version>
```

### Step 6: Create GitHub Release

Use the `gh` CLI to create the release directly (no browser needed):

```bash
gh release create v<new-version> --title "v<new-version>" --notes "## What's Changed

### ✨ Features
- ...

**Full Changelog**: https://github.com/milad-afkhami/sissy-code-review-squad/compare/v<prev-version>...v<new-version>"
```

The release will appear immediately on the GitHub releases page.

### Step 7: Update Local Plugin

After the GitHub release is published, update the plugin in your Claude Code instance:

```bash
claude plugin update sissy-code-review-squad
```

Then **reload your Claude Code window** for the new commands to take effect.

## Release Notes Template

```markdown
## What's Changed

### 🐛 Bug Fixes
- ...

### ✨ Features
- ...

### 📝 Documentation
- ...

### 🔧 Internal
- ...

**Full Changelog**: https://github.com/milad-afkhami/sissy-code-review-squad/compare/v<prev-version>...v<new-version>
```

## Verification Checklist

After releasing, verify:

- [ ] All three version files show the same version number
- [ ] Git tag exists: `git tag -l`
- [ ] Tag is pushed to GitHub: Check tags page on GitHub
- [ ] GitHub release is published: `gh release view v<new-version>`
- [ ] Local plugin updated: `claude plugin update sissy-code-review-squad`
- [ ] Claude Code window reloaded — new commands available

## Rollback Procedure

If something goes wrong:

```bash
# Delete local tag
git tag -d v<new-version>

# Delete remote tag
git push origin :refs/tags/v<new-version>

# Revert version bump commit
git revert HEAD

# Push revert
git push origin main
```

## Common Mistakes to Avoid

1. ❌ **Forgetting to update all 3 version files** - This causes version mismatch
2. ❌ **Not creating a git tag** - Releases should always be tagged
3. ❌ **Not pushing tags separately** - Tags require `git push origin <tag>`
4. ❌ **Typo in version numbers** - Double-check all version strings match exactly
5. ❌ **Skipping the GitHub release** - Users need release notes to understand changes

## Quick Release Script

For convenience, you can use this script to automate the process:

```bash
#!/bin/bash
# release.sh - Automated release script

set -e  # Exit on error

# Check if version is provided
if [ -z "$1" ]; then
  echo "Usage: ./release.sh <version>"
  echo "Example: ./release.sh 1.2.0"
  exit 1
fi

VERSION=$1
TAG="v$VERSION"
PREV_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
PREV_VERSION=${PREV_TAG#v}

echo "🚀 Releasing version $VERSION..."

# Update version in all files
echo "📝 Updating version files..."
sed -i "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" package.json
sed -i "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" .claude-plugin/plugin.json
sed -i "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" .claude-plugin/marketplace.json

# Commit changes
echo "💾 Committing version bump..."
git add package.json .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: bump version to $VERSION"

# Create tag
echo "🏷️  Creating tag $TAG..."
git tag -a "$TAG" -m "Release $TAG"

# Push everything
echo "⬆️  Pushing to remote..."
git push origin main
git push origin "$TAG"

# Create GitHub release
echo "📦 Creating GitHub release..."
CHANGELOG_URL="https://github.com/milad-afkhami/sissy-code-review-squad/compare/${PREV_TAG}...${TAG}"
gh release create "$TAG" --title "$TAG" --notes "## What's Changed

**Full Changelog**: $CHANGELOG_URL"

# Update local plugin
echo "🔌 Updating local plugin..."
claude plugin update sissy-code-review-squad

echo "✅ Release $VERSION complete! Reload your Claude Code window."
```

Usage:
```bash
chmod +x release.sh
./release.sh 1.2.0
```

## Post-Release

After releasing:

1. Update the [README.md](README.md) if there are new features to document
2. Announce the release (if applicable)
3. Monitor for any issues reported by users
4. Start planning the next release

## Questions?

If you have questions about the release process, open an issue or refer to the [CONTRIBUTING.md](CONTRIBUTING.md) guide.
