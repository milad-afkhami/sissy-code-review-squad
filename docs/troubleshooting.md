# Troubleshooting Guide

Common issues and their solutions when using the Sissy Code Review Squad.

## Installation Issues

### Plugin Not Found After Installation

**Symptom:** `/sissy-squad` command not available after installing.

**Solutions:**
1. Restart Claude Code:
   ```bash
   claude --restart
   ```

2. Verify installation:
   ```bash
   claude plugins list
   ```

3. If installed via npm link, ensure the path is correct:
   ```bash
   claude plugins link /absolute/path/to/sissy-code-review-squad
   ```

### npm Installation Fails

**Symptom:** `npm install` or `claude plugins install` fails.

**Solutions:**
1. Check Node.js version (requires 18+):
   ```bash
   node --version
   ```

2. Clear npm cache:
   ```bash
   npm cache clean --force
   ```

3. Try installing with verbose output:
   ```bash
   npm install -g sissy-code-review-squad --verbose
   ```

---

## GitLab Connection Issues

### "GitLab API Error: 401 Unauthorized"

**Symptom:** Review fails with authentication error.

**Solutions:**
1. Verify your GitLab personal access token has `api` scope
2. Check token hasn't expired
3. Verify GitLab MCP configuration:
   ```json
   {
     "mcpServers": {
       "gitlab-mcp": {
         "env": {
           "GITLAB_TOKEN": "your-valid-token"
         }
       }
     }
   }
   ```

### "Project Not Found" Error

**Symptom:** Can't find the GitLab project.

**Solutions:**
1. Verify you have access to the project
2. Check the project ID format - use either:
   - Numeric ID: `12345`
   - URL-encoded path: `group%2Fsubgroup%2Fproject`
3. For private projects, ensure your token has access

### "Merge Request Not Found"

**Symptom:** MR exists but plugin can't find it.

**Solutions:**
1. Verify the MR URL is correct
2. Check if MR is in a different project than expected
3. Ensure your token has access to the MR's project
4. Try using numeric IID instead of URL

### Self-Hosted GitLab Issues

**Symptom:** Works with gitlab.com but not self-hosted instance.

**Solutions:**
1. Update `GITLAB_URL` in MCP config:
   ```json
   {
     "env": {
       "GITLAB_URL": "https://your-gitlab-instance.com"
     }
   }
   ```
2. Ensure no trailing slash in URL
3. Check if your instance requires specific API version

---

## Configuration Issues

### "Invalid Configuration" Error

**Symptom:** Review fails with schema validation error.

**Solutions:**
1. Validate YAML syntax (use online YAML validator)
2. Check for common typos:
   ```yaml
   # Wrong
   agents:
     security:
       enabled: tru  # Should be 'true'

   # Wrong
   agents:
     securityy:      # Typo in agent name
       enabled: true
   ```

3. Valid agent keys are:
   - `accessibility`
   - `security`
   - `performance`
   - `seo`
   - `styling`
   - `code-quality`
   - `react`
   - `typescript`
   - `git`
   - `qa`

### Configuration File Not Found

**Symptom:** Plugin uses defaults instead of your config.

**Solutions:**
1. Ensure file is at `.claude/review-config.yml` (not `.yaml`)
2. Check file permissions
3. Verify you're running from project root

---

## Agent Issues

### Agent Timeout

**Symptom:** Some agents don't complete or show timeout errors.

**Solutions:**
1. Large MRs may take longer - wait for completion
2. Check network connectivity
3. Reduce number of enabled agents for faster completion
4. Try running again - transient issues may resolve

### Agent Posts No Comments

**Symptom:** Agent completes but finds no issues.

**Solutions:**
1. This is normal if code is clean!
2. Check agent is enabled in config
3. Verify the agent is relevant (e.g., React agent for React code)
4. Check if files changed are in agent's scope

### Duplicate Comments

**Symptom:** Same issue posted multiple times.

**Solutions:**
1. This may happen if review is run multiple times
2. Future versions will detect existing comments
3. For now, manually resolve duplicate threads

### Wrong Line Numbers in Comments

**Symptom:** Comments appear on wrong lines.

**Solutions:**
1. Ensure MR diff is up-to-date (no new commits after review started)
2. This can happen with rebased branches - rerun review
3. Check if the file was modified after review started

---

## Performance Issues

### Review Takes Too Long

**Symptom:** Full review takes more than 10 minutes.

**Solutions:**
1. Disable agents you don't need:
   ```yaml
   agents:
     seo:
       enabled: false  # Skip for non-web projects
   ```

2. Large MRs naturally take longer - consider:
   - Breaking MR into smaller chunks
   - Running focused reviews (fewer agents)

3. Check network latency to GitLab

### High API Call Volume

**Symptom:** Rate limiting from GitLab.

**Solutions:**
1. Wait and retry after rate limit window
2. Reduce parallel agent count
3. For large MRs, consider reviewing in batches

---

## Common Error Messages

### "MCP Server Not Available"

The GitLab MCP server isn't running or configured.

**Fix:** Ensure GitLab MCP is in your Claude Code configuration.

### "No Diffs Found"

The MR has no code changes to review.

**Fix:** Verify the MR has actual code changes (not just merge commits).

### "Architecture Discovery Failed"

The discovery agent couldn't analyze the codebase.

**Fix:**
1. Ensure changed files exist
2. Check file permissions
3. This may be transient - retry the review

### "Failed to Post Comment"

GitLab rejected the comment posting.

**Fix:**
1. Verify write access to the project
2. Check if MR is locked or archived
3. Ensure token has `api` scope

---

## Getting Help

### Diagnostic Information

When reporting issues, include:

1. Plugin version:
   ```bash
   npm list -g sissy-code-review-squad
   ```

2. Claude Code version:
   ```bash
   claude --version
   ```

3. Node.js version:
   ```bash
   node --version
   ```

4. Error messages (full output)

5. Configuration (redact tokens):
   ```bash
   cat .claude/review-config.yml
   ```

### Report a Bug

Open an issue at: https://github.com/milad-afkhami/sissy-code-review-squad/issues

Include:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Diagnostic information above

### Request a Feature

Use the same issue tracker with the `enhancement` label.

---

## FAQ

**Q: Can I run a single agent instead of all of them?**
A: Currently no. Disable other agents in config for focused review.

**Q: Does this work with GitHub?**
A: Not yet. GitHub support is planned for a future release.

**Q: Can I add custom agents?**
A: Not in the current version. Custom agents are planned.

**Q: How do I update the plugin?**
A: Run `claude plugins update sissy-code-review-squad`

**Q: Can I use this in CI/CD?**
A: The plugin is designed for manual invocation. CI/CD integration is a future goal.
