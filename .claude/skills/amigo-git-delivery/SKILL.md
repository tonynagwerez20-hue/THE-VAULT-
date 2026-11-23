---
name: amigo-git-delivery
description: Package and deliver explicitly authorized AMIGO source changes and verification evidence to the ALGOMIND Git remote while preserving dirty worktrees and excluding large market-data archives.
---

# AMIGO Git delivery

Use only when the current user request authorizes a commit/push or preparing a delivery. The skill's availability does not authorize publishing. Read [the handoff's repository map](../amigo-native-verification/references/project-state.md); inspect current remote/branch/HEAD rather than trusting old values.

The Desktop ALGOMIND working tree has historically contained extensive unrelated edits. The E: rebuild and remote nested package are not identical layouts. Prepare an isolated checkout/worktree if needed; do not reset, clean, switch or blanket-stage the user's dirty tree. Reuse a known delivery branch only after checking its current remote tip. Do not force-push or rewrite shared history.

Before commit, make the exact staged set reviewable: changed source, targeted tests, commands, hashes, manifests and honest reports. Exclude raw multi-gigabyte ticks, credentials/account identifiers, private terminal state, transient caches and installed binaries. Explicitly document any local absolute paths/dependencies so a path-bound research package is not advertised as portable.

Check the diff, whitespace and accidental secrets; ensure packaged checksum manifests correspond to the actual Git blob bytes after line-ending normalization. Preserve original market-data checksums even if the text evidence package is normalized. Do not alter source or tests merely to package a report.

Commit only the intended paths with a concrete description of the final behavior and validation scope. Push to the confirmed repository/ref with an ordinary fast-forward operation. If the remote moved, inspect the change and preserve both parties' work; never silently overwrite it. If approval/authentication/network access fails, record the actual failure and do not bypass it. Retry only through the legitimate mechanism after the cause or user guidance changes.

Verify the remote ref equals the delivered commit. Report repository link, branch, commit and what was included/excluded. A successful local commit is not a successful push. Do not merge to main, publish a release or send messages unless separately authorized by the current request.
