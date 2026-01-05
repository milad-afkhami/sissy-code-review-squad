# Installation Guide

Get started with the Sissy Code Review Squad plugin in under 5 minutes.

## Prerequisites

Before installing, ensure you have:

1. **Claude Code CLI** (v1.0.0 or later)
   - [Install Claude Code](https://docs.anthropic.com/claude-code)

2. **GitLab MCP Server** configured
   - The plugin uses GitLab MCP to interact with merge requests
   - Configure your GitLab personal access token in MCP settings

3. **Node.js** (v18.0.0 or later)
   - Required for npm package management

4. **GitLab Project Access**
   - You need access to the GitLab project you want to review
   - A personal access token with `api` scope

## Installation

### Step 1: Install the Plugin

```bash
claude plugins install sissy-code-review-squad
```

Or install from npm directly:

```bash
npm install -g sissy-code-review-squad
claude plugins link sissy-code-review-squad
```

### Step 2: Verify Installation

```bash
claude --help
```

You should see `/sissy-squad` in the available commands.

### Step 3: Configure GitLab MCP

If you haven't already, configure the GitLab MCP server with your credentials:

```json
{
  "mcpServers": {
    "gitlab-mcp": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/gitlab-mcp"],
      "env": {
        "GITLAB_URL": "https://gitlab.com",
        "GITLAB_TOKEN": "your-personal-access-token"
      }
    }
  }
}
```

For self-hosted GitLab instances, update `GITLAB_URL` accordingly.

### Step 4: Create Configuration File

Create `.claude/review-config.yml` in your project root:

```bash
mkdir -p .claude
```

Copy the template:

```yaml
# .claude/review-config.yml
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

## Your First Review

### Step 1: Navigate to Your Project

```bash
cd /path/to/your/gitlab-project
```

### Step 2: Run the Review

```bash
claude
```

Then in Claude Code:

```
/sissy-squad https://gitlab.com/your-org/your-repo/-/merge_requests/123
```

Or use the alias:

```
/sissy-code-review-squad https://gitlab.com/your-org/your-repo/-/merge_requests/123
```

### Step 3: Watch the Magic

The orchestrator will:
1. Parse the MR URL and fetch metadata
2. Run architecture discovery on changed files
3. Spawn all enabled agents in parallel
4. Post individual findings as MR discussion threads
5. Post a comprehensive summary note

## Verification Checklist

After your first review, verify:

- [ ] All enabled agents posted their summary notes
- [ ] Individual issues appear as discussion threads on specific lines
- [ ] The Puppet Master summary note shows aggregated counts
- [ ] No error messages in the Claude Code output

## Updating the Plugin

To update to the latest version:

```bash
claude plugins update sissy-code-review-squad
```

## Uninstalling

To remove the plugin:

```bash
claude plugins uninstall sissy-code-review-squad
```

## Next Steps

- [Configuration Guide](./configuration.md) - Customize agent behavior
- [Agents Reference](./agents.md) - Learn what each agent reviews
- [Troubleshooting](./troubleshooting.md) - Common issues and solutions
