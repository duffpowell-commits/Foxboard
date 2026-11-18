# Foxboard: rules for Claude

- Single file app: everything lives in `index.html` (inline CSS/JS). No frameworks, no build step, no CDNs except Google Fonts.
- The live copy is the Claude artifact `408d3d4e-8800-4a0e-9cdc-1251d2b400a7`. After changing `index.html`, republish it with publish_files (mode patch, `as: index.html`) and commit here. Done means both: on main and live.
- Declared artifact capabilities: `downloads`, `sample` (images), `artifact`. Gaining a capability: declare first, then publish. The `artifact` capability stores user templates in `templates/library.json` on the artifact. Never overwrite or delete that file from here.
- Duff is phone-only (Android). Every feature must work by touch on a ~390px-wide screen. No desktop-only steps.
- Madison and Brittany (iPhone/Safari) may use it too: test that features degrade gracefully when `window.claude` is absent.
- Built-in templates and AI prompts must stay original: no copyrighted characters or logos.
- Run both scripts in `tests/` before shipping. New tests must be seen failing once before they count.
