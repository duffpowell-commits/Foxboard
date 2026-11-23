# AI work checkpoints and handoffs

Every AI editing Foxboard should save work incrementally so an unexpected model usage limit or chat interruption does not discard completed work.

1. Read this file, README, and the current handoff before edits. Inspect current branch and PRs, and avoid concurrent edits.
2. Before long image/video generations, large code changes, or expensive tests, commit the previous completed, safe chunk to a feature branch.
3. After each meaningful chunk, commit and verify the remote SHA. Mark incomplete or untested work clearly; never call it finished.
4. Update `NEXT_AI_HANDOFF.md` on the active branch with timestamp (UTC), branch/SHA, goal, completed work, files changed, tests actually run, blockers, PR links, and exact next steps.
5. Before handing off or ending the session, verify the handoff is remotely saved. If GitHub is unavailable, use an authorized project folder in Google Drive, or provide a copyable handoff in chat.
6. Never store tokens, credentials, private uploads, or secrets in a public repository. Do not overwrite newer work or bypass reviews.
7. ChatGPT cannot detect its remaining usage quota or rescue inaccessible unsaved work. Hourly automations are supplemental.

This rule is for AI contributors; it does not claim Foxboard has background autosave of remote development sessions.
