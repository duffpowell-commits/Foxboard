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
```
`test_gif_templates.py` decodes the exported GIF with Pillow, an independent decoder, and checks frames, loop, timing and transparency.

## Forge (image engine, bake-off stage)
`forge/` + `.github/workflows/forge.yml`: FLUX.1-schnell (Apache-2.0, commercial use OK) on GitHub's free
public-repo runners through stable-diffusion.cpp. No GPU, no API bill, no cooldown; minutes per image.
Edit `forge/prompts.json` to render; PNGs + timings land in `forge/out/`. Only runs while the repo is public
(private runners are too small and cost minutes). Prompts and outputs here are public.
