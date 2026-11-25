# Fresh-eyes review (before any Foxboard PR merges)

Copied from godot-game-starter's gate (Nov 24, 2026). Why: on Nov 23-24 fresh reviewers found real
bugs in most "green" PRs across Duff's repos, and Foxboard had no gate at all (#11's card layout
dropped lines and crashed on a logo; #7 changed a rule on its own).
CI sets a `fresh-eyes` status on the PR's head commit: **pending** until a PR review on that exact
commit says `FRESH-EYES REVIEW: PASS`. A new push resets it. Pending is not green: sessions check
the combined status and don't merge. Job-only pushes to main (`forge/jobs/**`) aren't PRs, so
they're not gated.

## Steps (the session that opened the PR does this)
1. Start a reviewer with no history (a subagent or the `code-review` skill). Give it ONLY the PR
   number/diff and CLAUDE.md. Never your summary of the change.
2. It checks, and reports with file:line:
   - Does the diff do what the PR title says, and nothing else?
   - Bugs, and CLAUDE.md's rules: single `index.html`, no CDNs but Google Fonts, every feature has a
     `window.Foxboard` command + an `API_DOC` line, works by touch at 390px and in WebKit, degrades
     without `window.claude`, db rules/capabilities unchanged unless that's the point.
   - Trust the diff, not the claim: `tools/claude/check.sh` was actually run; look at the screenshots.
   - Rule lock (Nov 24): the head commit has a `rule-lock` status. Missing = block (the workflow was
     deleted or crashed). If it passed on `duff-ok`, the label's events (`issues/<n>/events`) show it
     was added after the last push, by a tap, with no agent message near it asking for or adding it.
   - A PR that changes CLAUDE.md's rules says so in its body and is Duff's call.
3. Blocking findings: fix, push, review again (new commit = new review).
4. No blockers: post a PR review (event COMMENT) on the head commit whose body starts with
   `FRESH-EYES REVIEW: PASS <short sha>`, then the non-blocking notes, then the Claude Code footer.

Never write the PASS line without a fresh reviewer having read the diff. It makes the gate lie.
