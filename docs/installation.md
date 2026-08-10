# Installation Guide

Install Sissy Code Review Squad in Claude Code or Codex CLI. Both runtimes use
the same canonical review commands, agents, and GitLab comment formats.

## Prerequisites

Before installing, ensure you have:

1. **One supported runtime**
   - Claude Code CLI 1.0.0 or later, or
   - Codex CLI with plugin support.
2. **A GitLab MCP server already configured in that runtime**
   - The plugin does not install or own the server or its credentials.
   - Your GitLab token needs `api` scope to post and resolve review threads.
3. **Git with worktree support**
4. **Access to the GitLab project and merge request**
5. **Node.js 18+** only when using the npm-based Claude Code installation path

## Claude Code Installation

Install from the Claude marketplace:

```bash
claude plugins install sissy-code-review-squad
```

Or install from npm and link it:

```bash
npm install -g sissy-code-review-squad
claude plugins link sissy-code-review-squad
```

Verify the plugin with the command spelling supported by your Claude CLI:

```bash
claude plugins list
```

## Codex CLI Installation

Add the released repository tag as a marketplace, then install the plugin:

```bash
codex plugin marketplace add milad-afkhami/sissy-code-review-squad --ref v2.4.2
codex plugin add sissy-code-review-squad@sissy-code-review-squad
codex plugin list --json
```

Restart Codex after installation. The Codex plugin exposes exactly:

```text
$sissy-squad <MR_URL>
$follow-up-review <MR_URL>
```

`clear-mr-comments` remains a Claude Code-only command.

## Verify GitLab MCP

The server and credentials stay in the runtime's own configuration. In Codex,
confirm the existing server is visible:

```bash
codex mcp list
```

In Claude Code, use the runtime's MCP listing or settings view. For self-hosted
GitLab, keep the correct instance URL in that existing server configuration.

## Project Configuration

The picker creates `.sissy/review-config.yml` automatically. To prepare or edit
it manually:

```bash
mkdir -p .sissy
```

```yaml
# .sissy/review-config.yml
agents:
  accessibility:
    enabled: true
  security:
    enabled: true
  performance:
    enabled: true
  seo:
    enabled: true      # Set to false for non-web projects
  styling:
    enabled: true
  code-quality:
    enabled: true
  react:
    enabled: true      # Set to false for non-React projects
  typescript:
    enabled: true      # Set to false for JavaScript-only projects
  git:
    enabled: true
  qa:
    enabled: true
```

If `.sissy/review-config.yml` is absent and the older
`.claude/review-config.yml` exists, the next `sissy-squad` run copies the legacy
file unchanged to `.sissy/`. The legacy file is not deleted or overwritten.

## Your First Review

Navigate to the local checkout of the GitLab project, then invoke the command in
your runtime.

Claude Code:

```text
/sissy-code-review-squad:sissy-squad https://gitlab.com/your-org/your-repo/-/merge_requests/123
```

Codex CLI:

```text
$sissy-squad https://gitlab.com/your-org/your-repo/-/merge_requests/123
```

The workflow parses the MR, selects enabled agents, provisions an isolated
worktree from the MR source branch, runs discovery and reviews, posts GitLab
threads and a summary, then removes the worktree.

## Verification Checklist

After the first review, verify:

- [ ] all enabled agents completed;
- [ ] issues appear as GitLab discussion threads on the intended lines;
- [ ] the final summary has accurate counts;
- [ ] the temporary worktree was removed;
- [ ] no runtime, model-preflight, or MCP-operation error was reported.

## Updating

Claude Code:

```bash
claude plugins update sissy-code-review-squad
```

Codex CLI refreshes the configured Git marketplace, then reinstalls the selected
plugin version:

```bash
codex plugin marketplace upgrade sissy-code-review-squad
codex plugin add sissy-code-review-squad@sissy-code-review-squad
```

Restart the affected runtime after an update.

## Uninstalling

Claude Code:

```bash
claude plugins uninstall sissy-code-review-squad
```

Codex CLI:

```bash
codex plugin remove sissy-code-review-squad@sissy-code-review-squad
```

## Next Steps

- [Configuration Guide](./configuration.md)
- [Agents Reference](./agents.md)
- [Troubleshooting](./troubleshooting.md)
