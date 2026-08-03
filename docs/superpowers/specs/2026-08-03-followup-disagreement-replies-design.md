# Follow-Up Replies to Disagreed Threads (2.3.0)

**Date:** 2026-08-03
**Status:** Approved for implementation
**Touches:** `commands/follow-up-review.md`, `agents/thread-evaluator.md`, `agents/classify-mr-discussions.md`

## Problem

`follow-up-review` classifies each unresolved thread as **addressed**,
**disagreement**, or **untouched**. Addressed threads get verified against the
code and are resolved or replied-to. Disagreements are deliberately hands-off:
never verified, never replied, just listed in the summary as "skipped — needs
human review" (`follow-up-review.md` Skip policy; summary "Threads Awaiting Human
Review").

That leaves the reviewer to open every disagreement, re-read the original
concern, re-read the developer's pushback, go read the current code, and decide
who's right — entirely by hand. The tool already has the code checked out and the
context loaded; it can do the analytical legwork and hand back a position.

## Resolution

When the developer disagrees, Police Sissy posts **one in-thread reply** that
takes a position on the pushback, and **resolves nothing**. Every disagreement
stays open for the human to make the final call.

The reply is one of three verdicts, judged against the current source:

- **`conceded`** — the developer's pushback holds; the original concern does not
  apply. Reply says so and why. Thread left open.
- **`countered`** — the concern may still stand. Reply gives a factual, concrete
  rebuttal (the specific failure case / why it holds), non-adversarial. Thread
  left open.
- **`unsure`** — genuinely contestable (missing info, a product/judgment call, a
  tradeoff with no objective answer). Reply lays out the consideration and takes
  no side. Thread left open.

**Nothing is ever auto-resolved**, including on `conceded`. The human decides
resolution on all disagreements.

### Why these choices (rejected alternatives)

- **Internal advisory instead of an in-thread reply** — rejected; the reviewer
  wants the position posted on the MR, engaging the developer directly.
- **Concede-and-close (auto-resolve on agreement)** — rejected; keeping resolution
  human is safer and was an explicit requirement.
- **Default `unsure` to concede or to counter** — rejected; a neutral note is the
  honest signal when the bot can't call it, and resolution is human anyway.
- **A new dedicated adjudicator agent** — rejected in favor of extending the
  existing evaluator (see Architecture), so one file-read serves both a fix and a
  pushback on the same file.
- **Diff-only judgment (skip the worktree for disagreement-only MRs)** — rejected;
  judging whether a concern still holds needs full source, the same lesson the
  performance agent encodes.

## Architecture

Police Sissy (`thread-evaluator.md`) already reads each file once and evaluates
all of that file's addressed threads in a single pass. This feature folds
disagreement adjudication into that same pass (**Approach B**): a file's bucket
now carries both its addressed and its disagreed threads, and the agent returns a
verdict for each, keyed by thread kind.

### Change 1 — Classifier payload (`classify-mr-discussions.md`)

Today the classifier compacts each disagreement to
`{discussion_id, new_path, reason}`. That is not enough to write a grounded
reply — the agent needs the original concern and the developer's actual reply and
the line position.

Upgrade the `disagreements` array to the **same rich shape already used for
`addressed`**: full note data (all non-system notes, author + body) and file
positions (`new_path`, `new_line`). Keep the existing `reason` field — the summary
still uses it. The `untouched` mechanical split and all reconciliation guarantees
are unchanged.

### Change 2 — Gating and batching (`follow-up-review.md`)

Every gate currently written as `addressed_count > 0` becomes
`addressed_count > 0 OR disagreement_count > 0`. Concretely:

- **Step 2 tail** — "if `addressed_count == 0`, skip to summary" becomes "if
  `addressed_count == 0` **and** `disagreement_count == 0`, skip to summary."
- **Step 3 (fetch)** — `file_filter` is the union of unique `new_path` values from
  **both** `addressed` and `disagreements` (exclude nulls).
- **Step 3b (worktree)**, **Step 4 (discovery)**, **Step 8 (cleanup)** — run when
  either count is > 0. This is what gives a disagreement-only MR a worktree to
  judge against.
- **Step 5 (buckets)** — bucket **both** addressed and disagreed threads by
  `new_path` (null → `"__general__"`). Each thread in a bucket is tagged
  `kind: "addressed" | "disagreement"`. General-comment disagreements
  (`new_path` null) land in `__general__` and are judged on thread text alone,
  using the evaluator's existing no-file fallback.

### Change 3 — Evaluator verdicts (`thread-evaluator.md`)

The agent now receives a `kind` per thread and returns:

- `kind == "addressed"` → existing `verdict: "resolved" | "insufficient"` (unchanged).
- `kind == "disagreement"` → new `verdict: "conceded" | "countered" | "unsure"`,
  plus a `reply` field: the exact prose to post in-thread.

Output stays a single JSON array with one object per thread. Each object carries
`discussion_id`, `verdict`, `confidence`, and either `explanation` (addressed) or
`reply` (disagreement). A new tone block governs the three disagreement replies:
factual and brief, state the position and the one concrete reason, never
condescending or adversarial, never re-post the whole original review.

### Change 4 — Verdict processing + summary (`follow-up-review.md`)

**Step 6** gains a disagreement branch. For `conceded` / `countered` / `unsure`,
post a reply via `create_merge_request_discussion_note` and **do not resolve**.
Reply body uses the existing Police Sissy prefix with a per-verdict badge and a
trailing line stating the human decides:

```
> SubAgent: 👮 Police Sissy (Follow-Up Review)
> **{badge}** {headline}

{reply}

_You have the final call on this thread — resolve it or reply if you disagree._
```

Badges: `conceded` → `✅ [agrees]` "Your pushback holds"; `countered` →
`↩️ [counter]` "Concern may still stand"; `unsure` → `🤔 [your-call]` "Judgment
call". Collect `{conceded_count}`, `{countered_count}`, `{unsure_count}`
(their sum is `disagreement_count`).

**Step 7 (summary)** — the disagreement row flips from "skipped (needs human
review)" to **"replied — your decision"**, and the "Threads Awaiting Human
Review" section lists each disagreement with Police Sissy's stance
(agrees / counter / your-call) and a one-line gist, so the reviewer can scan
positions instead of opening each thread. A replied disagreement is still awaiting
the human's decision, so it **continues to keep the MR out of the unconditional
"✅ all threads addressed" state** — the terminal message just reflects that these
threads are now replied and reviewer-owned rather than "skipped." The
`notify-send` line keeps a disagreement count; only its label changes.

### Change 5 — Prose updates (`follow-up-review.md`)

Update the outward description so it no longer claims disagreements are untouched:

- "How It Works" step 5 and the "Developer Workflow" note.
- "Pipeline Overview" (the classify + skip-to-summary line).
- The "Skip policy" note (disagreements are no longer skipped; only untouched is).

## Data flow

```
classify → addressed[] (rich) + disagreements[] (NOW rich) + untouched_count
   │
   ├─ addressed_count == 0 AND disagreement_count == 0 → summary only, no worktree
   │
   └─ else → fetch (file_filter = addressed ∪ disagreement paths)
             → worktree → discovery
             → buckets by file, each thread tagged kind
             → thread-evaluator per bucket (one file-read, both kinds)
             → verdicts:
                  resolved     → resolve thread, no reply
                  insufficient → reply, leave open
                  conceded     → reply (agrees),   leave open   ← new
                  countered    → reply (counter),  leave open   ← new
                  unsure       → reply (your-call),leave open   ← new
             → summary (disagreements: replied, your decision)
             → remove worktree
```

## Testing

No automated test harness exists in this repo; validation is by running the
command against real MRs. Manual checks before release:

1. **Disagreement-only MR** — provisions a worktree, posts one reply per
   disagreement, resolves nothing, summary shows "replied — your decision."
2. **Mixed MR** (a file with both an addressed fix and a disagreement) — the
   file is read once; both a fix verdict and a disagreement reply come back.
3. **General-comment disagreement** (`new_path` null) — judged on thread text,
   reply posted, no crash from a missing file.
4. **Concede case** — thread receives an `✅ [agrees]` reply and remains
   **unresolved**.
5. **Counts reconcile** — `conceded + countered + unsure == disagreement_count`,
   and the Step 2 guardrail still holds.

## Out of scope

- Auto-resolving conceded threads (explicitly human-owned).
- A separate adjudicator agent.
- Diff-only judgment.
- Any change to `sissy-squad` (this is follow-up only).

## Release

Minor version bump (new backward-compatible feature): **2.2.x → 2.3.0**, per
`RELEASE.md` (all three version files, tag, GitHub release).
