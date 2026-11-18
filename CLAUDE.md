# Foxboard: rules for Claude

- Single file app: everything lives in `index.html` (inline CSS/JS). No frameworks, no build step, no CDNs except Google Fonts.
- The live copy is the Claude artifact `408d3d4e-8800-4a0e-9cdc-1251d2b400a7`. After changing `index.html`, republish it with publish_files (mode patch, `as: index.html`) and commit here. Done means both: on main and live.
- Declared artifact capabilities: `downloads`, `sample` (images), `artifact`, `mcp` (connector `github`, tool `create_or_update_file`), `db` (rule: `bible` read view / write admin), `user` (scope profile). Gaining a capability: declare first, then publish. Losing one: publish first, then declare. Every redeclare must list ALL of them.
- `artifact` stores user templates in `templates/library.json` on the artifact. Never overwrite or delete that file from here.
- `db` holds the shared library (`library/<id>` meta + `libchunks/<id>_<n>` body chunks under 180k chars, `libnotes/<id>`) and the style bible (`bible/main`). The bible's built-in default lives in `DEFAULT_BIBLE` in index.html; the db copy wins once Duff saves.
- Send to game: commits `<inbox>/<date>-foxboard/<name>-<HHMMSS>.<png|gif>.b64` to the game repo's main through the viewer's GitHub connector (text only, hence base64). Each game repo needs `.github/workflows/foxboard_decode.yml` + `grok_art/**` in build.yml's paths-ignore. Lethemoor has it (verified live Nov 18). DuffQuest: apply `integrations/duffquest-foxboard-inbox.patch` in a DuffQuest session, then flip its decoder on in the bible. The connector only sees PUBLIC repos until Duff grants the Claude GitHub app access to private ones.
- Duff is phone-only (Android). Every feature must work by touch on a ~390px-wide screen. No desktop-only steps.
- Madison and Brittany (iPhone/Safari) may use it too: test that features degrade gracefully when `window.claude` is absent.
- Built-in templates and AI prompts must stay original: no copyrighted characters or logos.
- Run every script in `tests/` before shipping. New tests must be seen failing once before they count.
