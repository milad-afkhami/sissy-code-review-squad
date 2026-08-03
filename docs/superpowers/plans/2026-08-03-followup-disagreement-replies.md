# Follow-Up Replies to Disagreed Threads — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `follow-up-review` post one in-thread reply per developer disagreement — conceding, countering, or flagging as your-call — grounded in the current source, while resolving nothing.

**Architecture:** The Python helper `classify_discussions.py` enriches the `disagreements` payload with the same notes+position data it already emits for `addressed`. Police Sissy (`thread-evaluator.md`) then adjudicates disagreements in the same per-file pass it already uses for addressed threads (Approach B). The `follow-up-review` orchestrator opens a worktree whenever there are addressed **or** disagreed threads, buckets both kinds by file, and posts the resulting replies without resolving.

**Tech Stack:** Python 3 (stdlib only) for the helper + test; Markdown prompt files for the agent and command; GitLab MCP tools for posting.

## Global Constraints

- Disagreement replies **never auto-resolve** a thread — the human decides resolution on all of them.
- Disagreement verdict vocabulary is exactly `conceded | countered | unsure`; addressed stays `resolved | insufficient`.
- Reply tone: factual, brief, non-adversarial; never re-post the full original review; never condescending.
- The count reconciliation invariant must still hold: `addressed_count + disagreement_count + untouched_count == total_unresolved`, and `conceded + countered + unsure == disagreement_count`.
- Helper script stays **stdlib-only** (no new dependencies) — it runs in a bare subagent shell.
- Do not touch `sissy-squad`; this is follow-up only.
- Release as **2.3.0** across all three version files (`package.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`) per `RELEASE.md`.

---

### Task 1: Enrich the assembled `disagreements` payload (helper + test + doc)

**Files:**
- Modify: `scripts/classify_discussions.py:221-226` (the `disagreement` branch of `cmd_assemble`)
- Create: `scripts/test_classify_discussions.py`
- Modify: `agents/classify-mr-discussions.md:186-188` (Output Format example)

**Interfaces:**
- Produces: the classifier's `disagreements[]` entries now have the shape
  `{discussion_id: str, new_path: str|null, new_line: int|null, notes: [{author, body}], reason: str}`
  (was `{discussion_id, new_path, reason}`). `addressed[]`, all counts, and the reconciliation invariant are unchanged.

- [ ] **Step 1: Write the failing test**

Create `scripts/test_classify_discussions.py` (stdlib-only, runnable directly):

```python
#!/usr/bin/env python3
"""Tests for classify_discussions.assemble — disagreement payload enrichment."""
import json
import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(__file__), "classify_discussions.py")


def _run_assemble(filtered, classification):
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "filtered.json"), "w") as fh:
            json.dump(filtered, fh)
        cls_path = os.path.join(d, "classification.json")
        with open(cls_path, "w") as fh:
            json.dump(classification, fh)
        out = subprocess.check_output(
            [sys.executable, SCRIPT, "assemble", "--dir", d, "--classification", cls_path],
            text=True,
        )
        return json.loads(out)


def test_disagreement_carries_notes_and_position():
    filtered = [
        {"discussion_id": "d1", "new_path": "src/a.css", "new_line": 12,
         "notes": [{"author": "milad", "body": "This causes reflow."},
                   {"author": "dev", "body": "Intentional; scrollbar breaks otherwise."}],
         "has_reply": True},
    ]
    classification = {"d1": {"bucket": "disagreement", "reason": "declined; scrollbar"}}
    result = _run_assemble(filtered, classification)

    assert result["disagreement_count"] == 1
    dis = result["disagreements"][0]
    assert dis["discussion_id"] == "d1"
    assert dis["new_path"] == "src/a.css"
    assert dis["new_line"] == 12                      # NEW: position preserved
    assert dis["reason"] == "declined; scrollbar"     # existing field kept
    assert dis["notes"] == filtered[0]["notes"]        # NEW: full notes preserved


def test_counts_still_reconcile():
    filtered = [
        {"discussion_id": "a1", "new_path": "src/x.tsx", "new_line": 3,
         "notes": [{"author": "milad", "body": "n+1"}, {"author": "dev", "body": "fixed"}],
         "has_reply": True},
        {"discussion_id": "d1", "new_path": "src/y.tsx", "new_line": 9,
         "notes": [{"author": "milad", "body": "unsafe"}, {"author": "dev", "body": "no, it's fine"}],
         "has_reply": True},
        {"discussion_id": "u1", "new_path": "src/z.tsx", "new_line": 1,
         "notes": [{"author": "milad", "body": "typo"}], "has_reply": False},
    ]
    classification = {"a1": {"bucket": "addressed", "reason": ""},
                      "d1": {"bucket": "disagreement", "reason": "disputes premise"}}
    result = _run_assemble(filtered, classification)

    assert result["addressed_count"] == 1
    assert result["disagreement_count"] == 1
    assert result["untouched_count"] == 1
    assert (result["addressed_count"] + result["disagreement_count"]
            + result["untouched_count"] == result["total_unresolved"] == 3)


if __name__ == "__main__":
    test_disagreement_carries_notes_and_position()
    test_counts_still_reconcile()
    print("OK")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 scripts/test_classify_discussions.py`
Expected: FAIL — `AssertionError` on `dis["new_line"]` (KeyError) or the `notes` assertion, because the current `assemble` emits only `{discussion_id, new_path, reason}`.

- [ ] **Step 3: Enrich the `disagreement` branch**

In `scripts/classify_discussions.py`, replace the `else:  # disagreement` block (lines 221-226):

```python
        else:  # disagreement
            disagreements.append({
                "discussion_id": discussion_id,
                "new_path": record["new_path"],
                "new_line": record["new_line"],
                "notes": record["notes"],
                "reason": (entry["reason"] if entry else "") or "",
            })
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 scripts/test_classify_discussions.py`
Expected: `OK`

- [ ] **Step 5: Update the classifier Output Format doc**

In `agents/classify-mr-discussions.md`, replace the `disagreements` example (lines 186-188) so it matches the enriched shape:

```json
  "disagreements": [
    {
      "discussion_id": "def…",
      "new_path": "src/foo.css",
      "new_line": 17,
      "notes": [
        {"author": "milad-afkhami", "body": "Full original review comment text"},
        {"author": "dev.alisalehi", "body": "Declined — this is intentional because…"}
      ],
      "reason": "declined; out of scope"
    }
  ],
```

- [ ] **Step 6: Commit**

```bash
git add scripts/classify_discussions.py scripts/test_classify_discussions.py agents/classify-mr-discussions.md
git commit -m "feat: enrich disagreement payload with notes and position"
```

---

### Task 2: Teach Police Sissy to adjudicate disagreements

**Files:**
- Modify: `agents/thread-evaluator.md` (Your Task, Evaluation Rules, Tone Rules, Output Format)

**Interfaces:**
- Consumes: each thread block in the prompt now carries a `**Kind:** addressed | disagreement` line (produced by Task 3), and disagreement threads carry the enriched `notes` (from Task 1).
- Produces: the returned JSON array now contains, per thread:
  - addressed → `{discussion_id, verdict: "resolved"|"insufficient", explanation, confidence}` (unchanged)
  - disagreement → `{discussion_id, verdict: "conceded"|"countered"|"unsure", reply, confidence}`

*(No unit-test harness exists for prompt files; verification is static consistency + the end-to-end run in Task 6.)*

- [ ] **Step 1: Add `Kind` awareness to "Your Task"**

In `agents/thread-evaluator.md`, after the numbered list in "## Your Task", add:

```markdown
Each thread is tagged **Kind: `addressed`** or **Kind: `disagreement`** in the prompt above.

- For **`addressed`** threads, verify the fix (rules under "Verdict Rules" → resolved/insufficient).
- For **`disagreement`** threads, the developer pushed back on the concern. Judge the pushback against the current code and return a **`conceded`**, **`countered`**, or **`unsure`** verdict with a `reply` to post in-thread (rules under "Disagreement Rules"). You never resolve a disagreement — the human decides.
```

- [ ] **Step 2: Add the "Disagreement Rules" section**

Insert a new section immediately after the existing "### Verdict Rules" block (before "### Tone Rules"):

```markdown
### Disagreement Rules (Kind: disagreement)

The first note is the original concern; the developer's reply/replies push back. Read the current code at `{Project Root}/{File Path}` (or, for a general comment / missing file, judge on the thread text) and return exactly one verdict, plus a `reply` — the prose to post in the thread.

Return **"conceded"** when the developer's pushback holds — the concern does not apply to the current code (e.g. it's genuinely intentional, the pattern is correct here, or the suggested change would cause the harm the developer describes). The `reply` states that you agree and the one concrete reason.

Return **"countered"** when the concern still stands — the problematic pattern the concern names is still present and the developer's reason does not actually neutralize it. The `reply` gives the specific failure case or why it still holds — one or two factual sentences, no re-litigating tone.

Return **"unsure"** when it is genuinely contestable — missing information, a product/UX judgment call, or a tradeoff with no objective answer from the code alone. The `reply` lays out the consideration on both sides and takes no side.

Default bias: prefer **"unsure"** over guessing. A neutral note is the honest signal when the code cannot decide it; the human resolves it either way.
```

- [ ] **Step 3: Extend the Tone Rules to cover disagreement replies**

Under "### Tone Rules", append:

```markdown
The same tone governs disagreement `reply` text:

- Factual and brief; state your position and the single concrete reason.
- Do NOT re-post the full original review or the developer's reply back at them.
- Do NOT be adversarial, condescending, or use "as I said" phrasing — you are engaging an argument in good faith, not winning it.
- For `conceded`, acknowledge plainly ("You're right — …"). For `unsure`, be explicit that it's the reviewer's call.
```

- [ ] **Step 4: Update the Output Format**

In "## Output Format", replace the "### Verdict Values" list and add a disagreement example. The verdict-values block becomes:

```markdown
### Verdict Values

- `verdict` (Kind addressed): `"resolved"` or `"insufficient"` — include `explanation`.
- `verdict` (Kind disagreement): `"conceded"`, `"countered"`, or `"unsure"` — include `reply` (the in-thread prose) instead of `explanation`.
- `confidence`: `"high"` or `"medium"` (all kinds).
```

Then add this example under "### Examples":

```markdown
**Disagreement threads (mixed verdicts):**

```json
[
  {
    "discussion_id": "def456",
    "verdict": "countered",
    "reply": "The concern still applies: `parseUserInput` is still called on the raw value at line 30 before the guard, so the injection path the review flagged is open on that branch.",
    "confidence": "high"
  },
  {
    "discussion_id": "ghi789",
    "verdict": "conceded",
    "reply": "You're right — this runs only inside the already-authenticated admin layout, so the extra check would be redundant. Agreed.",
    "confidence": "high"
  },
  {
    "discussion_id": "jkl012",
    "verdict": "unsure",
    "reply": "This is a judgment call: eager-loading trades a larger initial payload for fewer round-trips. The code doesn't settle which matters more here — leaving this for your decision.",
    "confidence": "medium"
  }
]
```
```

- [ ] **Step 5: Verify static consistency**

Run: `grep -nE "conceded|countered|unsure|Kind: |reply" agents/thread-evaluator.md`
Expected: matches in Your Task, Disagreement Rules, Tone Rules, and Output Format (all four locations present).

Run: `grep -c "resolved" agents/thread-evaluator.md`
Expected: ≥ 1 (the addressed path is still documented — not accidentally removed).

- [ ] **Step 6: Commit**

```bash
git add agents/thread-evaluator.md
git commit -m "feat: adjudicate disagreements in the thread-evaluator pass"
```

---

### Task 3: Orchestrator — gating, file_filter union, and buckets with kind

**Files:**
- Modify: `commands/follow-up-review.md` — Step 2 tail (`:85`), Step 3 (`:89`, `:96`), Step 3b note (`:128`), Step 5 buckets + prompt (`:142-194`), Step 8 (`:302`, `:311`), Pipeline Overview (`:323`)

**Interfaces:**
- Consumes: `disagreements[]` (enriched, from Task 1) with `new_path`, `new_line`, `notes`.
- Produces: per-file buckets containing both addressed and disagreed threads, each thread tagged `Kind:` in the evaluator prompt (consumed by Task 2). A worktree exists whenever `addressed_count > 0 OR disagreement_count > 0`.

- [ ] **Step 1: Flip the skip-to-summary gate (Step 2 tail, line 85)**

Replace:

```markdown
If `addressed_count == 0`, skip directly to Step 7 (post summary). **No worktree is created and no cleanup is needed** in that case.
```

with:

```markdown
If `addressed_count == 0` **and** `disagreement_count == 0`, skip directly to Step 7 (post summary). **No worktree is created and no cleanup is needed** in that case. If either count is > 0, continue.
```

- [ ] **Step 2: Widen the Steps 3–6 gate and the file_filter (Step 3)**

Replace line 89:

```markdown
**Only proceed with Steps 3–6 if `{addressed_count} > 0`.**
```

with:

```markdown
**Only proceed with Steps 3–6 if `{addressed_count} > 0` OR `{disagreement_count} > 0`.**
```

Replace the `file_filter` bullet (line 96):

```markdown
- `file_filter`: array of unique `new_path` values from the `addressed` threads classified in Step 2 (exclude nulls)
```

with:

```markdown
- `file_filter`: array of unique `new_path` values from **both** the `addressed` and `disagreements` threads classified in Step 2 (union; exclude nulls)
```

- [ ] **Step 3: Update the worktree-path handoff note (Step 3b, line 128)**

Replace:

```markdown
- `WORKTREE_PATH=<path>` → store `<path>` as `{worktree_path}` for Steps 4, 5, and 8.
```

with (no logic change — just accurate now that disagreements also use it):

```markdown
- `WORKTREE_PATH=<path>` → store `<path>` as `{worktree_path}` for Steps 4, 5, and 8. A disagreement-only MR (no addressed threads) still reaches this step, so the worktree is available to judge pushbacks against.
```

- [ ] **Step 4: Bucket both kinds with a `kind` tag (Step 5)**

Replace the bucketing pseudocode (lines 149-153):

```markdown
buckets = {}
for each thread in addressed:
  key = thread.new_path ?? "__general__"
  buckets[key].push(thread)
```

with:

```markdown
buckets = {}
for each thread in addressed:
  key = thread.new_path ?? "__general__"
  buckets[key].push({ ...thread, kind: "addressed" })
for each thread in disagreements:
  key = thread.new_path ?? "__general__"
  buckets[key].push({ ...thread, kind: "disagreement" })
```

- [ ] **Step 5: Emit the `Kind` line in the evaluator prompt (Step 5 template)**

In the "## Threads to Evaluate" template, replace the `**Original Line:**` line (line 171):

```markdown
**Original Line:** {thread.new_line or "N/A" if null}
```

with:

```markdown
**Original Line:** {thread.new_line or "N/A" if null}
**Kind:** {thread.kind}
```

- [ ] **Step 6: Include disagreements in cleanup gating (Step 8)**

Replace line 302:

```markdown
If a worktree was provisioned in Step 3b (i.e. `addressed_count > 0`), remove it.
```

with:

```markdown
If a worktree was provisioned in Step 3b (i.e. `addressed_count > 0` OR `disagreement_count > 0`), remove it.
```

Replace the tail of line 311:

```markdown
`addressed_count == 0`, there is no worktree to remove — skip this step.
```

with:

```markdown
`addressed_count == 0` and `disagreement_count == 0`, there is no worktree to remove — skip this step.
```

- [ ] **Step 7: Update the Pipeline Overview skip note (line 323)**

Replace:

```markdown
   - If 0 addressed → skip to summary (no worktree)
```

with:

```markdown
   - If 0 addressed AND 0 disagreements → skip to summary (no worktree)
```

- [ ] **Step 8: Verify static consistency**

Run: `grep -nE "disagreement_count|kind|OR .disagreement|union" commands/follow-up-review.md`
Expected: the OR-gates (Steps 2, 3, 8), the union file_filter, and the `kind` tag all present.

- [ ] **Step 9: Commit**

```bash
git add commands/follow-up-review.md
git commit -m "feat: route disagreements through the worktree + evaluator pipeline"
```

---

### Task 4: Orchestrator — post disagreement replies and update the summary

**Files:**
- Modify: `commands/follow-up-review.md` — Step 6 (`:200-232`), Step 7 summary (`:234-290`), notify-send (`:295`), How It Works (`:16` block), Developer Workflow (`:32`), Skip policy note (`:356`)

**Interfaces:**
- Consumes: evaluator verdicts `conceded | countered | unsure` with a `reply` field (from Task 2).
- Produces: an in-thread note per disagreement (never resolved) and updated summary counts `{conceded_count, countered_count, unsure_count}` (sum == `disagreement_count`).

- [ ] **Step 1: Add the disagreement branch to Step 6**

After the `**For \`verdict == "insufficient"\`:**` block (ends line 230, before "Store counts" at line 232), insert:

```markdown
**For `verdict == "conceded" | "countered" | "unsure"` (Kind: disagreement):**

Post the evaluator's `reply` to the thread and **do NOT resolve it** — the human decides. Pick the badge/headline by verdict:

| verdict | badge | headline |
| --- | --- | --- |
| `conceded` | `✅ [agrees]` | Your pushback holds |
| `countered` | `↩️ [counter]` | Concern may still stand |
| `unsure` | `🤔 [your-call]` | Judgment call |

```
mcp__gitlab-mcp__create_merge_request_discussion_note(
  project_id: "{project_id}",
  merge_request_iid: "{mr_iid}",
  discussion_id: "{discussion_id}",
  body: "> SubAgent: 👮 Police Sissy (Follow-Up Review)\n> **{badge}** {headline}\n\n{reply}\n\n_You have the final call on this thread — resolve it or reply if you disagree._"
)
```

Never call `resolve_merge_request_thread` for a disagreement verdict.
```

- [ ] **Step 2: Extend the stored counts (Step 6, line 232)**

Replace:

```markdown
Store counts: `{resolved_count}`, `{insufficient_count}`
```

with:

```markdown
Store counts: `{resolved_count}`, `{insufficient_count}`, `{conceded_count}`, `{countered_count}`, `{unsure_count}`. The three disagreement counts must sum to `{disagreement_count}`.
```

- [ ] **Step 3: Update the summary status table (Step 7, line 259)**

Replace the disagreement row:

```markdown
| 💬 Developer disagreed — skipped (needs human review) | {disagreement_count} |
```

with:

```markdown
| 💬 Developer disagreed — replied, your decision (✅ {conceded_count} agree · ↩️ {countered_count} counter · 🤔 {unsure_count} your-call) | {disagreement_count} |
```

- [ ] **Step 4: Rewrite the "Threads Awaiting Human Review" section (Step 7, lines 274-278)**

Replace:

```markdown
{If disagreement_count > 0:}

### Threads Awaiting Human Review

{For each thread in `disagreements`, list its `new_path` (or "general comment" if null) and its `reason` — the developer pushed back, so a human reviewer should evaluate these. These are never auto-resolved or auto-replied to.}
```

with:

```markdown
{If disagreement_count > 0:}

### Disagreements — Police Sissy Replied, Your Decision

{For each disagreement, list its `new_path` (or "general comment" if null), Police Sissy's stance (✅ agrees / ↩️ counter / 🤔 your-call), and a one-line gist of the reply. Police Sissy has posted a position in each thread but resolved none — you make the final call.}
```

- [ ] **Step 5: Keep the ✅ terminal-state guard correct (Step 7, line 282)**

Confirm the "all threads addressed" condition still requires `disagreement_count == 0` (a replied-but-undecided disagreement must NOT flip the MR to ✅). The existing line 282 already reads `... AND disagreement_count == 0 AND untouched_count == 0` — leave it as-is. Add a clause after the `notify-send` block description so the disagreement label reads "replied" not "disagreed":

Replace the notify-send body fragment (line 295) `💬 {disagreement_count} disagreed` with `💬 {disagreement_count} replied`.

- [ ] **Step 6: Update the prose (How It Works, Developer Workflow, Skip policy)**

In "## How It Works", replace items 4–5 of the numbered list:

```markdown
4. For addressed threads, provisions an isolated worktree of the MR's **source branch** and spawns evaluator agents to verify each fix against the current code in that worktree
5. Resolves verified threads; replies with feedback on inadequate fixes
```

with:

```markdown
4. For addressed **and disagreed** threads, provisions an isolated worktree of the MR's **source branch** and spawns evaluator agents against the current code in that worktree
5. Resolves verified fixes; replies with feedback on inadequate fixes; and posts a position on each disagreement (agree / counter / your-call) — **never resolving a disagreement**, so you keep the final call
```

In "### Developer Workflow", replace the disagree bullet (line 32):

```markdown
- If they disagree: reply explaining why. A reply that declines or defers the change is treated as a disagreement (skipped for human review), no matter how politely it's phrased.
```

with:

```markdown
- If they disagree: reply explaining why. A reply that declines or defers the change is treated as a disagreement — Police Sissy will post a position on it (agree / counter / your-call) but never resolve it, leaving the final call to a human. Tone doesn't change the classification; the conclusion does.
```

In the "## Important Notes" Skip-policy item (line 356), replace:

```markdown
10. **Skip policy**: Threads where the developer disagreed and untouched threads are always skipped.
```

with:

```markdown
10. **Skip policy**: Untouched threads are always skipped (awaiting the developer). Disagreements are NOT skipped — Police Sissy posts a position in each, but never auto-resolves; the human decides.
```

- [ ] **Step 7: Verify static consistency**

Run: `grep -nE "conceded_count|countered_count|unsure_count|your decision|replied" commands/follow-up-review.md`
Expected: counts referenced in Step 6 and the summary; "replied"/"your decision" present in the table, section, and notify-send.

Run: `grep -n "skipped (needs human review)" commands/follow-up-review.md`
Expected: no matches (the old "skipped" framing is fully gone).

- [ ] **Step 8: Commit**

```bash
git add commands/follow-up-review.md
git commit -m "feat: post disagreement positions and report them in the summary"
```

---

### Task 5: End-to-end validation, version bump, and release

**Files:**
- Modify: `package.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (version → `2.3.0`)

**Interfaces:** none (integration + release).

- [ ] **Step 1: Re-run the helper unit test**

Run: `python3 scripts/test_classify_discussions.py`
Expected: `OK`

- [ ] **Step 2: Manual end-to-end validation (needs a real GitLab MR with a disagreement)**

Run `/follow-up-review <MR_URL>` against a test MR and confirm the spec's Testing checklist:

1. Disagreement-only MR → a worktree is provisioned, one reply per disagreement, **zero threads resolved**, summary shows "replied — your decision".
2. Mixed MR (a file with both a fix and a pushback) → the file is read once; both a fix verdict and a disagreement reply come back.
3. General-comment disagreement (`new_path` null) → reply posted, no crash from a missing file.
4. Concede case → thread gets an `✅ [agrees]` reply and stays **unresolved**.
5. Counts reconcile: `conceded + countered + unsure == disagreement_count`, and the Step 2 guardrail holds.

Record the result. If any check fails, fix in the relevant task before releasing.

- [ ] **Step 3: Bump the version in all three files to `2.3.0`**

Edit each of `package.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, changing `"version": "2.2.x"` → `"version": "2.3.0"`.

Run: `grep -h '"version"' package.json .claude-plugin/plugin.json .claude-plugin/marketplace.json`
Expected: three lines all showing `2.3.0`.

- [ ] **Step 4: Commit the version bump**

```bash
git add package.json .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: bump version to 2.3.0"
```

- [ ] **Step 5: Tag, push, and publish the release (per RELEASE.md)**

```bash
git tag -a v2.3.0 -m "Release v2.3.0"
git push origin main
git push origin v2.3.0
gh release create v2.3.0 --title "v2.3.0" --notes "## What's Changed

### ✨ Features
- Follow-up review now posts an in-thread position on every developer disagreement — agree, counter, or your-call — grounded in the current source. Disagreements are never auto-resolved; the human keeps the final call.

**Full Changelog**: https://github.com/milad-afkhami/sissy-code-review-squad/compare/v2.2.1...v2.3.0"
```

- [ ] **Step 6: Update the local plugin**

Run: `claude plugin update sissy-code-review-squad@sissy-code-review-squad`
Then reload the Claude Code window.

---

## Self-Review

**Spec coverage:**
- Change 1 (classifier payload) → Task 1. ✓ (refined: the enrichment is in `assemble`, not the agent's judgment prose — noted in Task 1.)
- Change 2 (gating + batching) → Task 3. ✓
- Change 3 (evaluator verdicts) → Task 2. ✓
- Change 4 (Step 6 processing + summary) → Task 4. ✓
- Change 5 (prose updates) → Task 4 Step 6. ✓
- Testing section → Task 5 Step 2. ✓
- Release (2.3.0) → Task 5. ✓

**Type/name consistency:** verdict strings `conceded|countered|unsure` and the `reply` field are defined in Task 2 (evaluator output) and consumed identically in Task 4 (Step 6 branch). The `kind` tag is produced in Task 3 (buckets/prompt) and consumed in Task 2. Counts `conceded_count|countered_count|unsure_count` introduced in Task 4 Step 2 and used in Task 4 Steps 3–5. Enriched disagreement shape defined in Task 1 and consumed by Task 3 (buckets) and Task 2 (notes in prompt). Consistent.

**Ordering:** Task 1 (payload) → Task 2 (evaluator contract) → Task 3 (input plumbing) → Task 4 (output) → Task 5 (validate + release). Each task ends with a committable, independently reviewable deliverable.
