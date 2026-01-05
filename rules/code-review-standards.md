# Code Review Standards

## Principles

- Be kind, specific, and concise
- Explain _why_, not just _what_
- Suggest solutions when possible
- Assume good intent

## Comment Prefixes (Required)

| Prefix            | Meaning                               | Blocking? |
| ----------------- | ------------------------------------- | --------- |
| `❗ [blocking]`   | Must fix before merge                 | Yes       |
| `💡 [suggestion]` | Recommended improvement               | No        |
| `💅 [nit]`        | Style preference, Minor best practice | No        |
| `❓ [question]`   | Needs clarification                   | No        |

## Comment Format

All comments must start with a SubAgent identifier followed by the severity prefix:

```markdown
> SubAgent: {emoji} {AgentName}
> **{prefix}** Brief title

Explanation with context.

**Current:** `problematicCode()`
**Suggested:** `improvedCode()`

Why this matters.
```

### SubAgent Headers (The Squad)

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

### Example Comments

**Blocking Issue:**

```markdown
> SubAgent: 🔒 SecuSissy (Security)
> **❗ [blocking]** Hardcoded API key exposes credentials

This API key is visible in client-side code and can be extracted by anyone.

**Current:** `const API_KEY = "sk_live_abc123"`
**Suggested:** Use environment variables: `process.env.NEXT_PUBLIC_API_KEY`

This is a critical security vulnerability that could lead to unauthorized access.
```

**Suggestion:**

```markdown
> SubAgent: ⚛️ Hooked Sissy (React)
> **💡 [suggestion]** Extract repeated logic into custom hook

This component has duplicate data fetching logic that appears in 3 places.

**Current:** Inline fetch logic in each component
**Suggested:** Create `useUserData()` hook to centralize the logic

This improves maintainability and reduces bundle size.
```

**Nit:**

```markdown
> SubAgent: 📝 Unknown Sissy (TypeScript)
> **💅 [nit]** Use more specific type instead of generic object

**Current:** `data: object`
**Suggested:** `data: { id: number; name: string }`

More specific types improve IDE autocomplete and catch errors earlier.
```

## When to Use Each Prefix

**❗ Blocking:** Security vulnerabilities, WCAG A/AA violations, memory leaks, type safety violations (`any`), SEO content hidden from crawlers, missing error handling for critical paths.

**💡 Suggestion:** Pattern improvements, optimizations with measurable impact, better organization, WCAG AAA improvements.

**💅 Nit:** Code style, naming preferences, optional refactoring, minor documentation. Must be actionable with a concrete suggestion. Do not praise or congratulate the developer ("Great job!", "Nice work here!").

**❓ Question:** Unclear intent, potential issues needing confirmation, design decisions needing context.

## GitLab MCP Tool Usage

**CRITICAL: Use the correct MCP tool for each type of comment:**

### For Code-Specific Issues (Blocking/Suggestion/Nit/Question)

Use `mcp__gitlab-mcp__create_merge_request_thread`. When the issue relates to a specific file/line, include the `position` parameter (highly encouraged when applicable):

```
mcp__gitlab-mcp__create_merge_request_thread({
  project_id: project_id,
  merge_request_iid: mr_iid,
  body: "> SubAgent: 🦯 Colorblind Sissy (Accessibility)\n> **❗ [blocking]** Issue title\n\nDetailed explanation...",
  position: {
    base_sha: diff_refs.base_sha,
    head_sha: diff_refs.head_sha,
    start_sha: diff_refs.start_sha,
    position_type: "text",
    new_path: "path/to/file.tsx",
    old_path: "path/to/file.tsx",
    new_line: 42,
  },
});
```

For MR-level issues with no specific file (e.g., branch naming, commit messages, MR description), omit the `position` parameter:

```
mcp__gitlab-mcp__create_merge_request_thread({
  project_id: project_id,
  merge_request_iid: mr_iid,
  body: "> SubAgent: 📚 Detached-HEAD Sissy (Git)\n> **❗ [blocking]** Branch naming mismatch\n\nThe branch uses `fix/` prefix but commits use `feat` type...",
});
```

### For Summary Notes Only

Use `mcp__gitlab-mcp__create_merge_request_note` (NO position parameter):

```
mcp__gitlab-mcp__create_merge_request_note({
  project_id: project_id,
  merge_request_iid: mr_iid,
  body: "> SubAgent: 🦯 Colorblind Sissy (Accessibility)\n\n![Cover](...)\n\n## Summary...",
});
```

### Rules

- **NEVER** use `create_merge_request_note` for individual issues (blocking/suggestion/nit/question)
- **ALWAYS** use `create_merge_request_thread` for issues - with `position` when pointing to specific code, without position when MR-level
- **ONLY** use `create_merge_request_note` for summary notes (agent-level and final orchestrator summaries)

## Summary Note Format

After completing a review, each agent MUST post a summary note to the MR with this format:

```markdown
> SubAgent: {emoji} {AgentName}

![{AgentName}]({COVER_IMAGE_URL}){width=300 height=300}

## {Domain} Review Summary

### Issues Found

| Severity       | Count |
| -------------- | ----- |
| ❗ Blocking    | X     |
| 💡 Suggestions | X     |
| 💅 Nits        | X     |

### Key Findings

[Brief summary of main issues and recommendations]

### Verdict

{✅ No blocking issues | ⚠️ Blocking issues found | 💬 Questions need answers}
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
