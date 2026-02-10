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

- **Patch** (1.0.x) - Bug fixes, small improvements
- **Minor** (1.x.0) - New features, backward compatible
- **Major** (x.0.0) - Breaking changes

Example: If current version is `1.0.6` and you're adding a bug fix, the next version is `1.0.7`.

### Step 2: Update All Version Files

**CRITICAL:** Update the version in ALL THREE files to the same value.

```bash
# Example: Updating to version 1.0.7

# 1. Update package.json
# Change: "version": "1.0.6" → "version": "1.0.7"

# 2. Update .claude-plugin/plugin.json
# Change: "version": "1.0.6" → "version": "1.0.7"

# 3. Update .claude-plugin/marketplace.json
# Change: "version": "1.0.6" → "version": "1.0.7"
```

### Step 3: Commit Version Bump

```bash
git add package.json .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: bump version to 1.0.7"
```

### Step 4: Create Git Tag

```bash
# Create annotated tag with version
git tag -a v1.0.7 -m "Release v1.0.7"

# Verify tag was created
git tag -l "v1.0.7"
```

### Step 5: Push to Remote

```bash
# Push commits
git push origin main

# Push tags
git push origin v1.0.7
```

### Step 6: Create GitHub Release

1. Go to: https://github.com/milad-afkhami/sissy-code-review-squad/releases/new
2. Select the tag you just pushed (v1.0.7)
3. Title: `v1.0.7`
4. Description: Write release notes (see template below)
5. Click "Publish release"

## Release Notes Template

```markdown
## What's Changed

### 🐛 Bug Fixes
- Fixed comment formatting to follow correct standards (#issue)

### ✨ Features
- Added clear-mr-comments command for cleaning up MR comments
- Show plugin version in review summary notes

### 📝 Documentation
- Updated release process documentation

### 🔧 Internal
- Improved agent prompt structure
- Removed unnecessary orchestrator steps

**Full Changelog**: https://github.com/milad-afkhami/sissy-code-review-squad/compare/v1.0.6...v1.0.7
```

## Verification Checklist

After releasing, verify:

- [ ] All three version files show the same version number
- [ ] Git tag exists: `git tag -l`
- [ ] Tag is pushed to GitHub: Check tags page on GitHub
- [ ] GitHub release is published
- [ ] Users can install the new version: `claude-code plugin install sissy-code-review-squad`

## Rollback Procedure

If something goes wrong:

```bash
# Delete local tag
git tag -d v1.0.7

# Delete remote tag
git push origin :refs/tags/v1.0.7

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
  echo "Example: ./release.sh 1.0.7"
  exit 1
fi

VERSION=$1
TAG="v$VERSION"

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

echo "✅ Release $VERSION complete!"
echo "📦 Create GitHub release at: https://github.com/milad-afkhami/sissy-code-review-squad/releases/new?tag=$TAG"
```

Usage:
```bash
chmod +x release.sh
./release.sh 1.0.7
```

## Post-Release

After releasing:

1. Update the [README.md](README.md) if there are new features to document
2. Announce the release (if applicable)
3. Monitor for any issues reported by users
4. Start planning the next release

## Questions?

If you have questions about the release process, open an issue or refer to the [CONTRIBUTING.md](CONTRIBUTING.md) guide.
