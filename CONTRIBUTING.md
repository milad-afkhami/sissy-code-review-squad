# Contributing to Sissy Code Review Squad

Thank you for your interest in contributing! This guide will help you get started.

## Code of Conduct

Be respectful, inclusive, and constructive. We welcome contributors of all backgrounds and experience levels.

## Ways to Contribute

1. **Report Bugs** - Open an issue describing the problem
2. **Suggest Features** - Open an issue with the `enhancement` label
3. **Improve Documentation** - Fix typos, add examples, clarify instructions
4. **Submit Code** - Fix bugs or implement features

## Development Setup

### Prerequisites

- Node.js 18+
- Claude Code CLI installed
- GitLab account with API access
- A test GitLab project with merge requests

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/milad-afkhami/sissy-code-review-squad.git
   cd sissy-code-review-squad
   ```

2. Link the plugin locally:
   ```bash
   claude plugins link .
   ```

3. Verify installation:
   ```bash
   claude plugins list
   # Should show: sissy-code-review-squad (linked)
   ```

4. Test with a real MR:
   ```bash
   claude
   # Then: /sissy-squad https://gitlab.com/your-project/-/merge_requests/123
   ```

### Project Structure

```
sissy-code-review-squad/
├── commands/           # User-invocable commands
│   └── sissy-squad.md  # Main orchestrator
├── agents/             # Agent definition files
│   ├── accessibility.md
│   ├── security.md
│   └── ...
├── rules/              # Auto-loaded rule files
│   └── code-review-standards.md
├── config/             # Configuration schema and defaults
├── templates/          # User config templates
├── docs/               # Documentation
└── .claude-plugin/     # Plugin manifest
```

## Making Changes

### Editing Agent Definitions

Agent files are in `agents/`. Each agent follows this structure:

```markdown
---
model: opus
---

# {Emoji} {Agent Name} ({Focus} Review Agent)

Review the merge request for {focus area}.

**IMPORTANT: Follow `@rules/code-review-standards.md` for all commenting formats.**

## Context

$ARGUMENTS

## Checklist

### Category 1
- [ ] Check item 1
- [ ] Check item 2

## Severity Guide

- **❗ Blocking**: {criteria}
- **💡 Suggestion**: {criteria}
- **💅 Nit**: {criteria}

## Output

1. Post issues as **threads** following code-review-standards.md
2. Post a summary note following the Summary Note Format
```

### Editing the Orchestrator

The main command is in `commands/sissy-squad.md`. This file:

1. Parses MR URL using the parse-mr-metadata agent
2. Reads configuration from `.claude/review-config.yml`
3. Fetches MR data from GitLab
4. Runs architecture discovery
5. Spawns enabled agents in parallel
6. Collects results and posts summary

### Editing Rules

Rules in `rules/` are auto-loaded by Claude Code. The main file is `code-review-standards.md` which defines:

- Comment prefixes (blocking, suggestion, nit, question)
- SubAgent headers
- Comment format template
- Summary note format
- Agent cover images

## Testing Your Changes

### Manual Testing

1. Link your local version:
   ```bash
   claude plugins link /path/to/sissy-code-review-squad
   ```

2. Create a test MR with intentional issues:
   - Missing alt text (accessibility)
   - Hardcoded secrets (security)
   - Memory leaks (performance)
   - Missing types (typescript)

3. Run the review:
   ```bash
   /sissy-squad https://gitlab.com/your-test-project/-/merge_requests/1
   ```

4. Verify:
   - All enabled agents post comments
   - Comments appear on correct lines
   - Summary note has accurate counts
   - No errors in output

### Testing Individual Agents

To test a single agent, temporarily disable others in config:

```yaml
# .claude/review-config.yml
agents:
  accessibility:
    enabled: true    # Only this one enabled
  security:
    enabled: false
  # ... all others false
```

## Pull Request Guidelines

### Before Submitting

1. **Test your changes** with a real MR
2. **Update documentation** if behavior changes
3. **Follow existing code style**
4. **Keep changes focused** - one feature/fix per PR

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
How did you test these changes?

## Checklist
- [ ] Tested with real MR
- [ ] Updated documentation
- [ ] No breaking changes (or documented)
```

### Review Process

1. Submit PR against `main` branch
2. Maintainer will review within 1 week
3. Address feedback if requested
4. Once approved, maintainer will merge

## Adding a New Agent

To add a new specialized agent:

1. Create `agents/your-agent.md` following the template above

2. Add agent key to config schema (`config/review-config.schema.json`):
   ```json
   "your-agent": {
     "type": "object",
     "properties": {
       "enabled": { "type": "boolean", "default": true }
     }
   }
   ```

3. Add to defaults (`config/defaults.yml`):
   ```yaml
   your-agent:
     enabled: true
   ```

4. Add to template (`templates/review-config.yml`):
   ```yaml
   your-agent:
     enabled: true
   ```

5. Update orchestrator (`commands/sissy-squad.md`) to spawn the agent

6. Add to documentation:
   - `docs/agents.md` - Agent description
   - `docs/configuration.md` - Config options
   - `README.md` - Agent table

7. Add cover image URL to `rules/code-review-standards.md`

## Release Process

Maintainers only:

1. Update version in `package.json`
2. Update CHANGELOG.md
3. Create git tag: `git tag v1.x.x`
4. Push tag: `git push origin v1.x.x`
5. Publish to npm: `npm publish`

## Getting Help

- **Questions**: Open a Discussion on GitHub
- **Bugs**: Open an Issue
- **Security Issues**: Email maintainer directly (don't open public issue)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
