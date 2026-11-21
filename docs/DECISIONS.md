# Decisions

## 2026-11-21 (America/Chicago)

### Style reference on Forge is a style-board workaround, not IP-Adapter

**Why.** Duff approved making the art guide's "attach a style reference" method work on Forge. The model Forge already uses is FLUX.1-schnell through stable-diffusion.cpp on free GitHub CPU runners. sd.cpp's `--ip-adapter` path only supports SD 1.5 and SDXL, not FLUX. FLUX.1 Redux and Kontext are different models; adding them would not fit the runner budget (16 GB RAM, disk after the existing schnell q4 + T5 q8 download, and the time cap) and would change the look of every take. So `ref` / `forge/jobs/<id>.ref.b64` plus `ref_strength` (default 0.55) builds a shuffled crop board from the reference (`forge/style_ref.py`) and runs schnell img2img at a high strength (0.72–0.92) so the text prompt still composes a new picture. Palette and brushwork can bleed through. This will not hold a character the way Grok's attached reference does, and a full character photo used as `ref` can still leak shapes if you push `ref_strength` too high. Prefer a style-only crop. `init` stays "start from this picture" (sketch). A job cannot set both `init` and `ref`.

### Job-only commits may go to Foxboard main; code still goes through a PR

**Why.** `.github/workflows/forge.yml` renders only on a push to `main` under `forge/jobs/**`, and only while the repo is public. A job committed on a feature branch never runs. `art_loop.py queue` now publishes a commit whose parent is `origin/main` and whose tree is `origin/main` plus the new job files, then pushes that SHA to `main`, so a feature branch cannot sneak through. `.githooks/pre-push` (enable with `git config core.hooksPath .githooks`) allows a local push to main only when every file in the push is under `forge/jobs/**`, and it refuses a force-push to main. GitHub's merge button and the Actions bot do not use this hook.

### `init` on `mode: "new"` switches to sketch; it is never ignored

**Why.** The first art guide told Claude to attach `init` without requiring `mode: "sketch"`. `render_one.py` only loaded `init` for sketch/edit/expand/upscale, so those jobs rendered as plain text-to-image. The queue, `forgeBuild`, and the renderer now switch the job to `sketch` and print a warning.

### Cleanup goes through `art_loop.py score` and `cut`

**Why.** The first guide hand-rolled a chroma-key formula and cited a Lethemoor `--shadow` script that is not in Foxboard. Foxboard already scores key holes, floor shadow, off-palette colour, baked glow and texture seams, and cuts a take to a transparent, cropped, despilled PNG. Point Claude at those first.
