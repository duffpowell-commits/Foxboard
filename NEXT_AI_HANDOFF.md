# Next AI handoff

Updated (UTC): 2026-11-23
Repository: duffpowell-commits/Foxboard
Goal: Integrate phone-friendly studio marketing card creation into Foxboard.
Branch: feat/studio-marketing-templates
PR: https://github.com/duffpowell-commits/Foxboard/pull/11
Completed: Added standalone `marketing/studio_cards.html` card creator, `marketing/README.md`, Playwright smoke test `tests/test_marketing_cards.py`, and checkpoint protocol `AI_CHECKPOINTS.md`.
Tests actually run: None verified in this session. Automated test has been committed but not executed.
Blockers: Browser/Android QA and review outstanding; standalone card maker not integrated into main editor.
Next steps: Run Playwright test; fix any issues; inspect PR checks; review and merge when safe; add a menu entry in `index.html` for the marketing tool and test on phone.
Safety: No publishing, scheduling, video export or audio editing has been implemented.

## Cross-project checkpoint, 2026-11-23 22:58 UTC
New parallel Foxboard PR: https://github.com/duffpowell-commits/Foxboard/pull/12 (`ccr-b3be762e-9zd48v`, head `b6a33cc0eb2f3baf58529567319c51de64a95fde`), titled *Test Forge 3D stage-timing parser*. GitHub reports mergeable, but no combined commit statuses were returned. No tests were executed in this checkpoint. Review this PR independently and coordinate any integration with the marketing-card branch; do not assume it is merged or validated.
Existing marketing-card PR #11 head before this handoff update: `ca9ee5f334ea83438b4f80f67da116b00fb9d47e`. Its browser/Android QA remains unverified. Next: run `tests/test_marketing_cards.py`, inspect PR checks, review independently, then merge only after required gates pass.
