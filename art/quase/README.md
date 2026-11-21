# Quase · Art Team library (Nov 21 2026)

Finished, approved art from Quase · Art Team, organised by game, then by type.
Index: `manifest.json`, one entry per file with type, size, status, a prompt pointer and
the path of the full-res master in the game repo.

## Games
- `chaos/`: **Chaos Is the Mother of Order** (`duffpowell-commits/chaosisthemotheroforder`, private,
  branch `art/rail-yards-slice`, PR #7). Present-day American city, semi-realistic painted graphic-novel style.

## Size rules
Copies here are kept small. Masters stay in the game repo (the `master` field in the manifest):
- sprites: 512-tall RGBA PNG plus the 128-tall `display/` copy and the joint map JSON
- portraits: 512 JPEG; backdrops, stills, endings, woodcut frames: 960x540 JPEG
- posters: 576x768 JPEG; stamps and icons: 256 palette PNG plus 128 `display/` icons
- itch cover/banner: full size (630x500, 960x300) JPEG

## Duff's likeness
Duff is the player character "You". His sprites, portraits, identity pack, joint maps and the "captured"
ending are included. On Nov 21, 2026 he explicitly okayed his likeness being public in this repo (see CLAUDE.md).
`chaos/explorations/` holds approved early explorations. Each is labelled EXPLORATION in the manifest.

## Not here, on purpose
- Rejected drafts, first takes and pre-redo versions replaced at the same path (`docs/art-notes.md` in the game
  repo lists them). The layout drafts used for the backdrops are left out too, since the finals replace them.
- Grey-background sprite sources (`you_front_anchor.jpg`, `you_back.jpg` and the rest): the cut-out sprites duplicate
  them. Their paths are kept in the manifest's `source` field.

## Tools
Generic QA, lettering and joint-map scripts are in `tools/quase/` (see its README).
