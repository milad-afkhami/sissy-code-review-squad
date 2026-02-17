# Code Review Standards

## Comment Format (MANDATORY)

ALL comments MUST follow this exact structure:

## Severity Prefixes (REQUIRED)

- `❗ [blocking]` - Must fix before merge
- `💡 [suggestion]` - Recommended improvement
- `💅 [nit]` - Style preference
- `❓ [question]` - Needs clarification

```
> SubAgent: {emoji} {AgentName}
> **{prefix}** Brief issue title

Explanation with context.

**Current:** `problematicCode()`
**Suggested:** `improvedCode()`

Why this matters.
```

## SubAgent Headers

- `> SubAgent: 🦯 Colorblind Sissy (Accessibility)`
- `> SubAgent: 🔒 SecuSissy (Security)`
- `> SubAgent: ⚡ TurboSissy (Performance)`
- `> SubAgent: 🌐 Canonical Sissy (SEO)`
- `> SubAgent: 🎨 ChicSissy (Styling)`
- `> SubAgent: 🧹 KISS Sissy (Code Quality)`
- `> SubAgent: ⚛️ Hooked Sissy (React)`
- `> SubAgent: 📝 Unknown Sissy (TypeScript)`
- `> SubAgent: 📚 Detached-HEAD Sissy (Git)`
- `> SubAgent: ✅ BugSlayer Sissy (QA)`

### Example

```markdown
> SubAgent: 🔒 SecuSissy (Security)
> **❗ [blocking]** Hardcoded API key exposes credentials

This API key is visible in client-side code and can be extracted by anyone.

**Current:** `const API_KEY = "sk_live_abc123"`
**Suggested:** Use environment variables: `process.env.NEXT_PUBLIC_API_KEY`

This is a critical security vulnerability that could lead to unauthorized access.
```

## GitLab MCP Tool Usage

**For individual issues:** Use `mcp__gitlab-mcp__create_merge_request_thread`. When the issue relates to a specific file/line, include the `position` parameter (highly encouraged when applicable)

**For agent-level and final orchestrator summary notes:** Use `mcp__gitlab-mcp__create_merge_request_note`

## Summary Note Format

After completing a review, each agent MUST post a summary note to the MR with this format:

```markdown
## {Domain} Review Summary

| {AgentName}                                             | Issues Found                                                                                    |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| ![{AgentName}]({COVER_IMAGE_URL}){width=250 height=250} | <strong>❗ Blocking: X <hr/> 💡 Suggestions: X <hr/> 💅 Nits: X <hr /> ❓ Questions: X</strong> |

### Key Findings

[Brief summary]
```

### Agent Cover Images

| Agent                               | Cover Image URL                                                       |
| ----------------------------------- | --------------------------------------------------------------------- |
| 🦯 Colorblind Sissy (Accessibility) | `https://milad-afkhami.com/images/blog/sissy/colorblind-sissy.jpg`    |
| 🔒 SecuSissy (Security)             | `https://milad-afkhami.com/images/blog/sissy/secu-sissy.jpg`          |
| ⚡ TurboSissy (Performance)         | `https://milad-afkhami.com/images/blog/sissy/turbo-sissy.jpg`         |
| 🌐 Canonical Sissy (SEO)            | `https://milad-afkhami.com/images/blog/sissy/canonical-sissy.jpg`     |
| 🎨 ChicSissy (Styling)              | `https://milad-afkhami.com/images/blog/sissy/chic-sissy.jpg`          |
| 🧹 KISS Sissy (Code Quality)        | `https://milad-afkhami.com/images/blog/sissy/kiss-sissy.jpg`          |
| ⚛️ Hooked Sissy (React)             | `https://milad-afkhami.com/images/blog/sissy/hooked-sissy.jpg`        |
| 📝 Unknown Sissy (TypeScript)       | `https://milad-afkhami.com/images/blog/sissy/unknown-sissy.jpg`       |
| 📚 Detached-HEAD Sissy (Git)        | `https://milad-afkhami.com/images/blog/sissy/detached-head-sissy.jpg` |
| ✅ BugSlayer Sissy (QA)             | `https://milad-afkhami.com/images/blog/sissy/bugslayer-sissy.jpg`     |
| 🎭 Puppet Master (Orchestrator)     | `https://milad-afkhami.com/images/blog/sissy/puppet-master-sissy.jpg` |

## Output

Return: issue counts by severity, key concerns, overall domain assessment.
