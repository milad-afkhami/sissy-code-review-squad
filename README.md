# Sissy Code Review Squad

A multi-agent code review plugin for Claude Code that reviews GitLab merge requests across 10 specialized domains.

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

```bash
claude plugins install sissy-code-review-squad
```

## Quick Start

1. **Install the plugin** (see above)

2. **Copy the configuration template** to your project:
   ```bash
   cp node_modules/sissy-code-review-squad/templates/review-config.yml .claude/review-config.yml
   ```

3. **Run a review** on any GitLab MR:
   ```
   /sissy-code-review-squad:sissy-squad https://gitlab.com/your-org/your-project/-/merge_requests/123
   ```

That's it! The squad will review your MR and post comments directly to GitLab.

## Configuration

Edit `.claude/review-config.yml` to enable/disable agents:

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
│  2. LOAD CONFIGURATION                                      │
│     └── Read .claude/review-config.yml                      │
│                                                             │
│  3. FETCH MR DATA                                           │
│     └── Get MR details + diffs from GitLab                  │
│                                                             │
│  4. ARCHITECTURE DISCOVERY                                  │
│     └── Gather project context from .claude/rules/          │
│                                                             │
│  5. PARALLEL REVIEW                                         │
│     └── All enabled agents review simultaneously            │
│                                                             │
│  6. SUMMARY                                                 │
│     └── Post aggregated summary to MR                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- **Claude Code CLI** (v1.0.0 or later)
- **GitLab MCP Server** configured with access token
- **GitLab Project** with merge requests

### GitLab MCP Setup

Make sure you have the GitLab MCP server configured in your Claude Code settings:

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

| Command | Description |
|---------|-------------|
| `/sissy-code-review-squad:sissy-squad <MR_URL>` | Run full code review with all enabled agents |

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
- Ensure `.claude/review-config.yml` is valid YAML
- Check the file path is correct (`.claude/` not `claude/`)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Built with 💜 for better code reviews**
