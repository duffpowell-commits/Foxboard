# HANDOFF: Foxboard (Duff's art app + Forge)

Plain handoff for any coding AI (Claude, Grok, Codex...) or person. Duff, Nov 26, 2026: "keep logs
for another ai to build where you stop". Update this file in every code PR. The rules and the detail
of every feature are in `CLAUDE.md` (its rules are rule-locked: changing them needs Duff's `duff-ok` label). History and
why: `docs/DECISIONS.md`. Outbox delivery: `SWEEP.md`.

## Current state (checked 2026-11-26)
- What it is: a single-file phone art app (`index.html`, inline CSS/JS) plus **Forge**, free FLUX image
  rendering on GitHub runners (`forge/`, `.github/workflows/forge.yml`). It is the default home for all
  game art; finished pieces go in its Shared library or straight to a game repo.
- Live: Claude artifact https://claude.ai/code/artifact/408d3d4e-8800-4a0e-9cdc-1251d2b400a7 (republish
  after every `index.html` change; done = on main AND republished). Installable copy for iPhone:
  https://foxboard-gamma.vercel.app (loads `site/index.html` from jsDelivr; rebuild with
  `python3 tools/build_site.py`, push, purge jsDelivr).
- Forge is busy daily: most commits on main are job/result commits (`forge/jobs/**`, `forge/results/**`),
  pushed straight to main by design. Code still goes through a PR.
- Last code merges: #7 Quase art library, #9 textured 3D drafts, #11 marketing card generator, #12-#13 Forge timing +
  auto-send to game repos, #14 fresh-eyes gate, #15 rule lock (Nov 23-25).
- Open PRs:
  - **#10 in-browser 3D Texture Studio: needs Duff.** It conflicts with main and breaks the "no CDNs
    except Google Fonts" rule, so it can't merge as is. Duff decides: allow the CDN (a rule change, his
    tap) or rebuild it without one.
  - #1 (Nov 19, Claude link): old. A Claude link is already on main (CLAUDE.md "Claude link"), so diff it against main before doing anything; leave it for Duff.

## Next steps, in order
1. Duff's call on #10 (above).
2. Keep Forge healthy: a hung render becomes a failed take after 3x its expected time; check
   `forge/results/<id>/done.json` and `tools/claude/forge_wait.py` before assuming a job is lost.

## Build and test
- No build step. Tests: `tools/claude/check.sh` (Chromium, then WebKit, then 390px screenshots in
  /tmp/foxboard-shots; look at them). New tests must be seen failing once.
- Headless scripting: `node tools/claude/fb.js script.js` (`Foxboard.help()` lists the API).
- Queue art: `python3 tools/claude/art_loop.py queue ...`, wait with `forge_wait.py <id>` in the background.
- Once per clone: `git config core.hooksPath .githooks`.

## Gotchas
- This repo is public: prompts and outputs are public. No private info. Duff's likeness is OK (his call).
- Never overwrite `templates/library.json` on the artifact, and never delete db rows (outbox, library,
  `toclaude`, `diag`) without Duff's OK. Sweeps blank delivered chunks, they don't delete.
- Every artifact capability redeclare must list ALL of them (CLAUDE.md has the list).
- Must work by touch at ~390px and degrade cleanly when `window.claude` is absent (iPhone testers).
- Magic edit uses FLUX.2 klein; don't go back to schnell inpaint (it scribbled junk).

## Log (newest first)
- 2026-11-26 Claude: wrote this file (handoff refresh across every project). No code changed.
