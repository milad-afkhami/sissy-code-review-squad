# Sissy Code Review Squad

A multi-agent code review plugin for Claude Code and Codex CLI that reviews GitLab merge requests across 10 specialized domains.

## The Squad

| Agent | Focus Area | Blocking Criteria |
|-------|------------|-------------------|
| 🦯 **Colorblind Sissy** | Accessibility | WCAG A/AA violations |
| 🔒 **SecuSissy** | Security | XSS, exposed secrets, auth bypass |
| ⚡ **TurboSissy** | Performance | Memory leaks, N+1 queries |
| 🌐 **Canonical Sissy** | SEO | Hidden content, missing meta tags |
| 🎨 **ChicSissy** | Styling | Design system violations, broken layouts |
| 🧹 **KISS Sissy** | Code Quality | Massive functions, unmaintainable code |
| ⚛️ **Hooked Sissy** | React | Missing cleanup, missing keys |
| 📝 **Unknown Sissy** | TypeScript | `any` types, unsafe assertions |
| 📚 **Detached-HEAD Sissy** | Git | Secrets in commits |
| ✅ **BugSlayer Sissy** | QA | Missing requirements, critical bugs |

## Installation

### Claude Code

```bash
claude plugins install sissy-code-review-squad
```

### Codex CLI

```bash
codex plugin marketplace add milad-afkhami/sissy-code-review-squad --ref v2.4.0
codex plugin add sissy-code-review-squad@sissy-code-review-squad
```

Restart Codex after installation so it discovers the new skills.

## Quick Start

1. **Install the plugin** (see above)

2. **Run a review** on any GitLab MR from either runtime:

   Claude Code:

   ```text
   /sissy-code-review-squad:sissy-squad https://gitlab.com/your-org/your-project/-/merge_requests/123
   ```

   Codex CLI:

   ```text
   $sissy-squad https://gitlab.com/your-org/your-project/-/merge_requests/123
   ```

On each run, a zenity dialog asks which agents to enable (saved to
`.sissy/review-config.yml`). The squad then reviews the MR in an **isolated git
worktree** — your working tree, including uncommitted changes, is never touched —
and posts comments directly to GitLab.

When the developer replies to the threads, run the follow-up to verify the fixes:

```text
/sissy-code-review-squad:follow-up-review https://gitlab.com/your-org/your-project/-/merge_requests/123
$follow-up-review https://gitlab.com/your-org/your-project/-/merge_requests/123
```

Both commands are self-contained: they provision the worktree from the MR's own
source branch and remove it when done. There is no separate setup step.

## Configuration

`sissy-squad` shows a zenity picker each run and writes your selection to
`.sissy/review-config.yml`. You can also edit that file directly to enable/disable
agents:

```yaml
agents:
  accessibility:
    enabled: true
  security:
    enabled: true
  performance:
    enabled: true
  seo:
    enabled: false    # Disable for non-web projects
  styling:
    enabled: true
  code-quality:
    enabled: true
  react:
    enabled: true
  typescript:
    enabled: true
  git:
    enabled: true
  qa:
    enabled: true
```

When upgrading, if the neutral file is absent and `.claude/review-config.yml`
exists, the next `sissy-squad` run copies the legacy file unchanged to `.sissy/`.
The legacy file is left untouched; future picker saves use only `.sissy/`.

## Comment Format

All review comments use consistent severity prefixes:

| Prefix | Meaning | Blocking? |
|--------|---------|-----------|
| `❗ [blocking]` | Must fix before merge | Yes |
| `💡 [suggestion]` | Recommended improvement | No |
| `💅 [nit]` | Style preference | No |
| `❓ [question]` | Needs clarification | No |

## Recommended Project Files

For best results, create these files in your project's `.claude/rules/` directory:

| File | Purpose |
|------|---------|
| `tech-stack.md` | Your project's technology stack (React, Next.js, TypeScript, etc.) |
| `component-boilerplate.md` | Component patterns and conventions |
| `services-guideline.md` | Service layer patterns |
| `data-flow.md` | Data architecture and state management |

These files help the Discovery agent provide project-specific context to reviewers.

**Note:** Some agents (React, TypeScript, Code Quality, Styling) will check for these files and provide more targeted feedback when they exist. If files are missing, agents gracefully continue with generic best practices.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    CODE REVIEW PIPELINE                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. PARSE MR METADATA                                       │
│     └── Extract project ID and MR IID from URL              │
│                                                             │
│  2. CONFIGURE AGENTS                                        │
│     └── zenity picker → write .sissy/review-config.yml      │
│                                                             │
│  3. FETCH MR DATA                                           │
│     └── Get MR details + diffs (incl. source branch)        │
│                                                             │
│  4. PROVISION WORKTREE                                      │
│     └── Detached mirror of origin/<source_branch> in /tmp   │
│         (your working tree is never touched)                │
│                                                             │
│  5. ARCHITECTURE DISCOVERY                                  │
│     └── Gather project context from the worktree            │
│                                                             │
│  6. PARALLEL REVIEW                                         │
│     └── All enabled agents review simultaneously            │
│                                                             │
│  7. SUMMARY + CLEANUP                                       │
│     └── Post summary to MR, then remove the worktree        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- **Claude Code CLI** (v1.0.0 or later) or **Codex CLI** with plugin support
- **Git** (any version with worktree support — 2.5+)
- **GitLab MCP Server** configured with access token
- **GitLab Project** with merge requests
- **zenity** — for the agent-selection dialog (`sudo apt install zenity`; if absent, the review falls back to your existing `.sissy/review-config.yml`)
- **notify-send** (`libnotify`) — for the completion desktop notification (optional)

### GitLab MCP Setup

The plugin uses the GitLab MCP server already configured in the runtime; it does
not install or own the server or its credentials. For Codex, verify the existing
configuration with `codex mcp list`. For Claude Code, a configuration has this
shape:

```json
{
  "mcpServers": {
    "gitlab-mcp": {
      "command": "npx",
      "args": ["-y", "@anthropic/gitlab-mcp"],
      "env": {
        "GITLAB_TOKEN": "your-gitlab-token",
        "GITLAB_URL": "https://gitlab.com"
      }
    }
  }
}
```

## Commands

| Runtime | Command | Description |
|---------|---------|-------------|
| Claude Code | `/sissy-code-review-squad:sissy-squad <MR_URL>` | Pick agents, provision a worktree, run the full review, clean up |
| Codex CLI | `$sissy-squad <MR_URL>` | Run the same canonical initial-review workflow |
| Claude Code | `/sissy-code-review-squad:follow-up-review <MR_URL>` | Verify developer fixes on addressed threads and resolve/reply |
| Codex CLI | `$follow-up-review <MR_URL>` | Run the same canonical follow-up workflow |
| Claude Code only | `/sissy-code-review-squad:clear-mr-comments <MR_URL>` | Remove all Sissy discussions and notes from an MR |

## Example Output

After running the command, you'll see:

1. **Individual comments** posted to specific lines in the MR
2. **Agent summary notes** from each agent with their findings
3. **Final summary** with aggregated results:

```markdown
## Comprehensive Code Review Summary

### Review Results by Agent

| Agent | ❗ Blocking | 💡 Suggestions | 💅 Nits |
|-------|------------|----------------|---------|
| 🦯 Colorblind Sissy | 1 | 3 | 2 |
| 🔒 SecuSissy | 0 | 1 | 0 |
| ⚡ TurboSissy | 0 | 2 | 1 |
| ... | ... | ... | ... |
| **Total** | **1** | **12** | **8** |

### Verdict
⚠️ **CHANGES REQUESTED** - Blocking issues must be resolved
```

## Troubleshooting

### "Project not found" error
- Verify the MR URL is correct and accessible
- Check your GitLab token has `read_api` scope
- Ensure the project path matches exactly

### "No MR found for branch" error
- The MR might not exist yet - create it first
- Check if the MR is in a different state (closed, merged)

### Agents not posting comments
- Verify GitLab token has `api` scope (not just `read_api`)
- Check if the MR allows comments from your account

### Configuration not loading
- Ensure `.sissy/review-config.yml` is valid YAML
- Check the file path is exactly `.sissy/review-config.yml`

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Built with 💜 for better code reviews**
