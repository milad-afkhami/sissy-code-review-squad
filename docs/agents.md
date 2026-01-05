# Agents Reference

The Sissy Code Review Squad consists of 10 specialized agents, each focused on a specific domain. All agents run in parallel through the Puppet Master orchestrator.

## Agent Overview

| Agent | Emoji | Focus Area | Blocking Criteria |
|-------|-------|------------|-------------------|
| Colorblind Sissy | :white_cane: | Accessibility | WCAG A/AA violations |
| SecuSissy | :lock: | Security | OWASP Top 10, secrets exposure |
| TurboSissy | :zap: | Performance | Memory leaks, CWV blockers |
| Canonical Sissy | :globe_with_meridians: | SEO | Content hidden from crawlers |
| ChicSissy | :art: | Styling | Design system violations |
| KISS Sissy | :broom: | Code Quality | Critical code smells |
| Hooked Sissy | :atom_symbol: | React | Hook violations, memory leaks |
| Unknown Sissy | :memo: | TypeScript | `any` usage, type safety |
| Detached-HEAD Sissy | :books: | Git | Secrets in commits |
| BugSlayer Sissy | :white_check_mark: | QA | Missing requirements |

---

## :white_cane: Colorblind Sissy (Accessibility)

**Focus:** WCAG 2.1 compliance, ARIA implementation, semantic HTML

### Blocking Issues (:exclamation:)
- Missing or empty `alt` attributes on images
- Missing form labels or `aria-label`
- Color contrast ratios below WCAG AA (4.5:1 for text)
- Keyboard navigation traps
- Missing focus indicators
- Inaccessible interactive elements

### Suggestions (:bulb:)
- WCAG AAA improvements (enhanced contrast)
- Better semantic HTML usage
- Improved ARIA landmarks

### Nits (:nail_care:)
- Redundant ARIA attributes
- Minor semantic improvements

### Example Comment
```markdown
> SubAgent: :white_cane: Colorblind Sissy (Accessibility)
> **:exclamation: [blocking]** Image missing alt attribute

Screen readers cannot describe this image to visually impaired users.

**Current:** `<img src="logo.png" />`
**Suggested:** `<img src="logo.png" alt="Company Logo" />`

This is a WCAG 2.1 Level A violation (1.1.1 Non-text Content).
```

---

## :lock: SecuSissy (Security)

**Focus:** OWASP Top 10, secrets management, authentication

### Blocking Issues (:exclamation:)
- Hardcoded API keys or credentials
- XSS vulnerabilities (unsanitized HTML injection)
- SQL injection risks
- Missing authentication checks
- Exposed sensitive data in client-side code
- Insecure dependencies

### Suggestions (:bulb:)
- CSRF protection improvements
- Rate limiting recommendations
- Input validation patterns

### Nits (:nail_care:)
- Defense-in-depth improvements
- Security header recommendations

### Example Comment
```markdown
> SubAgent: :lock: SecuSissy (Security)
> **:exclamation: [blocking]** Hardcoded API key exposes credentials

This API key is visible in client-side code and can be extracted by anyone.

**Current:** `const API_KEY = "sk_live_abc123"`
**Suggested:** Use environment variables: `process.env.NEXT_PUBLIC_API_KEY`

This is a critical security vulnerability that could lead to unauthorized access.
```

---

## :zap: TurboSissy (Performance)

**Focus:** Core Web Vitals, bundle size, memory management

### Blocking Issues (:exclamation:)
- Memory leaks (uncleared intervals, listeners)
- Render-blocking resources
- Synchronous operations blocking main thread

### Suggestions (:bulb:)
- Bundle size optimizations
- Image optimization (using Next.js Image)
- Code splitting opportunities
- Memoization for expensive computations

### Nits (:nail_care:)
- Minor performance improvements
- `useCallback`/`useMemo` opportunities

### Example Comment
```markdown
> SubAgent: :zap: TurboSissy (Performance)
> **:exclamation: [blocking]** Memory leak from uncleared interval

This interval is never cleared, causing memory to grow indefinitely.

**Current:**
useEffect(() => {
  setInterval(() => fetchData(), 1000);
}, []);

**Suggested:**
useEffect(() => {
  const id = setInterval(() => fetchData(), 1000);
  return () => clearInterval(id);
}, []);
```

---

## :globe_with_meridians: Canonical Sissy (SEO)

**Focus:** Search engine optimization, meta tags, crawlability

### Blocking Issues (:exclamation:)
- Content hidden from crawlers (client-only rendering)
- Missing critical meta tags on public pages
- Broken canonical URLs

### Suggestions (:bulb:)
- Structured data (JSON-LD) improvements
- Meta description optimization
- Open Graph tags

### Nits (:nail_care:)
- Minor meta tag improvements
- Sitemap recommendations

### Example Comment
```markdown
> SubAgent: :globe_with_meridians: Canonical Sissy (SEO)
> **:bulb: [suggestion]** Add Open Graph meta tags for social sharing

This page lacks Open Graph tags, reducing social media preview quality.

**Suggested:** Add to page head:
<meta property="og:title" content="Page Title" />
<meta property="og:description" content="Description" />
<meta property="og:image" content="/preview.jpg" />
```

---

## :art: ChicSissy (Styling)

**Focus:** Tailwind CSS, design system adherence, RTL support

### Blocking Issues (:exclamation:)
- Design system violations (if project has one)
- Breaking visual regressions
- Missing RTL support for RTL content

### Suggestions (:bulb:)
- Tailwind best practices
- Consistent spacing/color usage
- Responsive design improvements

### Nits (:nail_care:)
- Arbitrary value usage instead of theme values
- Class ordering preferences

### Example Comment
```markdown
> SubAgent: :art: ChicSissy (Styling)
> **:nail_care: [nit]** Use theme spacing instead of arbitrary value

**Current:** `p-[17px]`
**Suggested:** `p-4` (16px) or add `17` to theme spacing

Arbitrary values reduce design system consistency.
```

---

## :broom: KISS Sissy (Code Quality)

**Focus:** Clean code, DRY principles, complexity management

### Blocking Issues (:exclamation:)
- Duplicated critical logic
- Functions exceeding complexity thresholds
- Dead code in production paths

### Suggestions (:bulb:)
- Refactoring opportunities
- Function extraction
- Naming improvements

### Nits (:nail_care:)
- Minor code style preferences
- Optional improvements

### Example Comment
```markdown
> SubAgent: :broom: KISS Sissy (Code Quality)
> **:bulb: [suggestion]** Extract duplicated fetch logic

This fetch pattern appears in 3 components with identical structure.

**Suggested:** Create `useFetchUser` hook to centralize the logic.
```

---

## :atom_symbol: Hooked Sissy (React)

**Focus:** React patterns, hooks rules, Next.js specifics

### Blocking Issues (:exclamation:)
- Missing keys in lists
- Hook rule violations (conditional hooks)
- Memory leaks in useEffect

### Suggestions (:bulb:)
- Custom hook extraction
- State management improvements
- Server vs Client component optimization

### Nits (:nail_care:)
- Minor React best practices
- Component structure suggestions

### Example Comment
```markdown
> SubAgent: :atom_symbol: Hooked Sissy (React)
> **:exclamation: [blocking]** Missing key prop in list

List items without stable keys cause reconciliation issues.

**Current:** `items.map(item => <Item {...item} />)`
**Suggested:** `items.map(item => <Item key={item.id} {...item} />)`
```

---

## :memo: Unknown Sissy (TypeScript)

**Focus:** Type safety, strict typing, TypeScript best practices

### Blocking Issues (:exclamation:)
- `any` type usage
- Unsafe type assertions (`as`)
- Non-null assertions without checks

### Suggestions (:bulb:)
- More specific type definitions
- Utility type usage
- Type guard improvements

### Nits (:nail_care:)
- Import type syntax
- Type inference preferences

### Example Comment
```markdown
> SubAgent: :memo: Unknown Sissy (TypeScript)
> **:exclamation: [blocking]** Using `any` type defeats TypeScript benefits

**Current:** `const data: any = await fetch(...)`
**Suggested:** `const data: UserResponse = await fetch(...)`

Define proper types for API responses.
```

---

## :books: Detached-HEAD Sissy (Git)

**Focus:** Commit hygiene, branch naming, MR quality

### Blocking Issues (:exclamation:)
- Secrets committed to repository
- Credentials in commit history

### Suggestions (:bulb:)
- Commit message improvements
- Branch naming conventions
- MR description quality

### Nits (:nail_care:)
- Minor commit message style
- Jira reference formatting

### Example Comment
```markdown
> SubAgent: :books: Detached-HEAD Sissy (Git)
> **:nail_care: [nit]** Commit message should use imperative mood

**Current:** "Added user authentication"
**Suggested:** "Add user authentication"

Conventional commits use imperative mood: "Add", not "Added".
```

---

## :white_check_mark: BugSlayer Sissy (QA)

**Focus:** Requirements compliance, edge cases, test checklists

### Blocking Issues (:exclamation:)
- Missing acceptance criteria implementation
- Critical edge cases unhandled
- Requirements mismatch

### Suggestions (:bulb:)
- Additional test coverage
- Edge case handling
- Error state improvements

### Nits (:nail_care:)
- Minor UX improvements
- Optional enhancements

### Output Format

BugSlayer Sissy provides two outputs:
1. **QA Analysis** - Requirements checklist and bug findings
2. **Test Checklist** - GitLab-compatible checkbox list for manual testing

---

## How Agents Coordinate

1. **Orchestrator** (`/sissy-squad`) receives MR URL
2. **MR Parser** extracts project ID and MR IID
3. **Discovery Agent** analyzes codebase architecture
4. **All enabled agents** spawn in parallel with shared context
5. Each agent posts findings as **discussion threads** (line-specific)
6. Each agent posts a **summary note** with counts
7. **Orchestrator** aggregates results and posts final summary

## Next Steps

- [Configuration Guide](./configuration.md) - Enable/disable specific agents
- [Troubleshooting](./troubleshooting.md) - Agent-specific issues
