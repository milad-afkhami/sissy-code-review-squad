# Configuration Guide

Customize the Sissy Code Review Squad to match your project's needs.

## Configuration File

Create `.claude/review-config.yml` in your project root. This file controls which agents run and their behavior.

## Schema Reference

### Full Configuration Example

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
    enabled: true
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

### Agent Options

Each agent supports:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `true` | Whether the agent should run |

## Agent Configuration

### accessibility

Reviews for WCAG 2.1 compliance (A/AA levels are blocking, AAA are suggestions).

```yaml
agents:
  accessibility:
    enabled: true   # Enable/disable accessibility reviews
```

**Enable when:** Building user-facing web applications
**Disable when:** Building CLI tools, backend services, or libraries

### security

Reviews for OWASP Top 10 vulnerabilities, secrets exposure, and auth issues.

```yaml
agents:
  security:
    enabled: true   # Always recommended
```

**Enable when:** Always (security is critical for all projects)
**Disable when:** Rarely - only for isolated test projects

### performance

Reviews for memory leaks, bundle size issues, and render optimizations.

```yaml
agents:
  performance:
    enabled: true
```

**Enable when:** Building production applications
**Disable when:** Prototypes or proof-of-concept projects

### seo

Reviews for meta tags, structured data, crawlability, and SSR/SSG patterns.

```yaml
agents:
  seo:
    enabled: true   # For web applications
    # enabled: false  # For non-web projects
```

**Enable when:** Building public-facing websites
**Disable when:** Internal tools, APIs, libraries, or CLI applications

### styling

Reviews for Tailwind CSS usage, design system adherence, and RTL support.

```yaml
agents:
  styling:
    enabled: true
```

**Enable when:** Projects using Tailwind CSS or design systems
**Disable when:** Headless libraries or backend services

### code-quality

Reviews for code smells, DRY violations, complexity, and naming conventions.

```yaml
agents:
  code-quality:
    enabled: true   # Always recommended
```

**Enable when:** Always
**Disable when:** Legacy codebases undergoing major refactoring (temporarily)

### react

Reviews for React best practices, hooks rules, component patterns, and Next.js specifics.

```yaml
agents:
  react:
    enabled: true   # For React/Next.js projects
    # enabled: false  # For Vue, Angular, or vanilla JS
```

**Enable when:** React or Next.js projects
**Disable when:** Non-React projects

### typescript

Reviews for type safety, `any` usage, type assertions, and TypeScript best practices.

```yaml
agents:
  typescript:
    enabled: true   # For TypeScript projects
    # enabled: false  # For JavaScript-only projects
```

**Enable when:** TypeScript projects
**Disable when:** Pure JavaScript projects

### git

Reviews for commit message conventions, branch naming, and MR quality.

```yaml
agents:
  git:
    enabled: true   # Always recommended
```

**Enable when:** Always
**Disable when:** Rarely

### qa

Reviews for requirements compliance, test coverage, and generates test checklists.

```yaml
agents:
  qa:
    enabled: true
```

**Enable when:** Projects with Jira integration or formal requirements
**Disable when:** Personal projects without formal tracking

## Configuration Presets

### Next.js Web Application (Full Stack)

```yaml
# Full review for production Next.js apps
agents:
  accessibility:
    enabled: true
  security:
    enabled: true
  performance:
    enabled: true
  seo:
    enabled: true
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

### React Component Library

```yaml
# Focus on code quality and React patterns
agents:
  accessibility:
    enabled: true
  security:
    enabled: true
  performance:
    enabled: true
  seo:
    enabled: false    # Libraries don't need SEO
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
    enabled: false    # Adjust based on test coverage needs
```

### Internal Admin Tool

```yaml
# Reduced scope for internal tools
agents:
  accessibility:
    enabled: true     # Still important for usability
  security:
    enabled: true     # Critical for admin tools
  performance:
    enabled: false    # Less critical for internal use
  seo:
    enabled: false    # Not needed for internal tools
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
    enabled: false
```

### Quick Code Quality Check

```yaml
# Minimal review for fast feedback
agents:
  accessibility:
    enabled: false
  security:
    enabled: true     # Always keep security
  performance:
    enabled: false
  seo:
    enabled: false
  styling:
    enabled: false
  code-quality:
    enabled: true
  react:
    enabled: false
  typescript:
    enabled: true
  git:
    enabled: true
  qa:
    enabled: false
```

## User-Defined Rules

The plugin reads from your project's `.claude/rules/` directory. Create these files to provide project context:

### tech-stack.md

```markdown
# Tech Stack

- React 18.3
- Next.js 15 (App Router)
- TypeScript 5.x
- Tailwind CSS 3.x
- React Query 5
- Jotai 2
```

This helps agents understand your specific stack and review accordingly.

## Validation

The configuration is validated against a JSON Schema. Invalid configurations will show helpful error messages:

```
Error: Invalid configuration
  - agents.security.enabled must be a boolean
  - agents.unknownAgent is not a valid agent key
```

## Environment Variables

The plugin respects these environment variables (via GitLab MCP):

| Variable | Description |
|----------|-------------|
| `GITLAB_URL` | GitLab instance URL (default: https://gitlab.com) |
| `GITLAB_TOKEN` | Personal access token with `api` scope |

## Next Steps

- [Agents Reference](./agents.md) - Detailed description of each agent
- [Troubleshooting](./troubleshooting.md) - Common configuration issues
