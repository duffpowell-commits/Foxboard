# Foxboard

A phone-first, Canva-style art editor for game art. One self-contained `index.html`: no build step, no server.

**Live (inside Claude):** https://claude.ai/artifact/8yKrPwMSvkXuyEDM8L8eu4

## What it does
- Canvas presets for sprites, tiles, boss cards, itch covers, wallpapers, or a custom size. Pixel-art mode gives crisp pixels, a grid and pixel snapping.
- Text with outlines and game fonts (pixel, comic, horror, fantasy, gothic), shapes, and images from your gallery.
- Move, resize and rotate with touch handles; snap to center; layers; undo/redo.
- Draw tools: pencil, eraser, fill bucket, eyedropper and a retro 16-color palette.
- Frames for animation, with onion skin and play preview. Export a single frame, a sprite sheet (PNG grid) or an animated GIF.
- Image tools: background removal, brightness/contrast/saturation/hue/grayscale/blur, flip.
- Magic eraser (image › 🪄): brush over something, tap Erase, and the gap fills from the rest of the picture (multi-scale patch fill, runs on the phone, free, instant). Best on small/medium things; big objects in busy photos smear.
- AI studio (runs on the viewer's own Claude plan, only inside Claude): pixel sprites, vector art, auto layouts, and art critique.
- Templates: 7 original built-ins plus your own saved templates.
- Style bible: per-game palette, sprite + illustration style, key color and characters (seeded from the DuffQuest/Lethemoor repos). AI prompts, the draw palette and "Snap to palette" all read it.
- Send to game: commits art straight into a game repo's `grok_art/` inbox through your GitHub connector; a GitHub Action in the game repo decodes it (see `integrations/`).
- Shared library: share canvases with everyone you've shared Foxboard with, open copies, leave notes (testers).
- Saving: autosaves in the browser. Use **Menu › Save project file** for a .json that reopens with every frame and layer editable.

## Running it elsewhere
Open `index.html` in any browser. Outside Claude the AI tab hides itself, Save image falls back to a long-press-to-save preview, and templates save to that browser only.

## Tests
```
pip install playwright pillow && python -m playwright install chromium
python tests/test_features.py
python tests/test_gif_templates.py
python tests/test_pipeline.py
python tests/test_forge_key.py
python tests/test_fbx.py
python tests/test_magic_eraser.py
```
`test_gif_templates.py` decodes the exported GIF with Pillow, an independent decoder, and checks frames, loop, timing and transparency.

## Forge (the default image generator)
`forge/` + `.github/workflows/forge.yml`: FLUX.1-schnell (Apache-2.0, commercial use OK) on GitHub's free
public-repo runners through stable-diffusion.cpp. No GPU, no API bill, no cooldown; minutes per image.
It's the go-to for all of Duff's image creation: in the app it's ✨AI › 🔥 Forge (first tab), and Claude chats
queue the same jobs (art-director skill). Canva is the fallback for private or urgent images.
Queue: `python3 tools/claude/art_loop.py queue --id … --prompt-file p.txt` (optional `--mode --init --mask --ref --ref-strength --strength --tile --seed --w/--h --key`), or commit `forge/jobs/<id>.json` plus any `.init.b64` / `.mask.b64` / `.ref.b64` in the same commit, onto **main**. `w`/`h` must be 256-1024 and a multiple of 64. `n` ≤ 4. `seed` is honored (take k uses seed+k). `ref` is a style-board workaround, not IP-Adapter. Prompts and outputs here are public.
Results: `forge/results/<id>/<k>.png` + `<k>.b64` + `done.json`. Key-colour jobs come back with an exact-key
background (`forge/keyfix.py`). Only runs while the repo is public. Prompts and outputs here are public.

## Claude → library tools
`tools/claude/fbx.py` packs art into the shared-library db format (`push-image`, `push-doc`) and unpacks it
(`pull`); `tools/claude/render.js` renders a doc with Foxboard's own renderer. Transport is the ArtifactData
tool on the Foxboard artifact (see the foxboard-link skill). Verified live Nov 19.

### Generate a 3D draft

See [Forge 3D image prep](docs/forge-3d-image-prep.md) for reference framing, pose, bust crops, and review checks.

Select one image layer, open its image tools, and tap **Generate 3D draft**. Confirm the public upload inside Claude with the GitHub connector enabled. **AI › Forge › Check now** shows when the GLB is ready to download. The reference and result are public in this repository.

The separate **Forge 3D** workflow uses TripoSR on a CPU runner and bakes a texture into the GLB. It produces an unrigged draft for review and cleanup in Blender. It does not send models to a game automatically. For scripting, use `Foxboard.forge({mode:'3d', id})` and `Foxboard.meshStatus(jobId)`.
