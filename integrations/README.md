# Game-repo integrations

`duffquest-foxboard-inbox.patch`: adds `.github/workflows/foxboard_decode.yml`, makes build.yml skip
`grok_art/**`, and notes it in CLAUDE.md. Not applied on Nov 18 because another session was working in
duffquest (house rule: one session per repo). In a DuffQuest session: `git apply` it from the repo root,
run test_daily, push, then turn the decoder on in Foxboard's Style bible (DuffQuest tab).

Lethemoor already has the same workflow (live-tested Nov 18: decoded byte-for-byte, build skipped).
