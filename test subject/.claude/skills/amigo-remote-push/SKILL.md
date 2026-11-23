---
name: amigo-remote-push
description: Commit and push authorized AMIGO redesign milestones and final evidence to the verified ALGOMIND Git remote, preserving dirty work and verifying the delivered remote commit.
---

# AMIGO remote delivery

Read [the repository contract](../amigo-redesign-loop/references/contract.md). The initiation prompt authorizes ordinary commits and pushes for its redesign assignment. Reuse that authorization without asking again for routine delivery, unless the scope or destination changes. In audit-only or preparation-only assignments, do not infer push authorization from the skill being available.

## Resolve the destination

Inspect the current repository root, branch, HEAD, working-tree/index status and `git remote -v`. The historical ALGOMIND remote is `https://github.com/tonynagwerez20-hue/THE-VAULT-.git`, with delivery branch `fix/quant-tib`; verify current state rather than hardcoding an old tip. Distinguish the Desktop root layout from the E: rebuild and nested remote package. Never overwrite one with another merely because their names match.

Protect pre-existing edits with an isolated checkout/worktree where necessary. Do not reset, clean, switch the user's dirty branch, stage all changes or publish unrelated files. Check the intended remote branch tip before preparing a commit.

## Deliver meaningful milestones

Push a tested, coherent redesign milestone when it is independently reviewable, and push the final evidence package at completion. Do not push every experiment or create empty checkpoint commits. A milestone may document an unresolved blocker, but its description must state the incomplete acceptance gate rather than claim success. Keep a local resumable state record between milestones.

Stage explicit paths only: intended source, necessary tests, compact configurations without credentials, hashes/manifests, reproduction commands and honest reports. Keep raw tick archives, account identifiers/credentials, private terminal state, caches and installed binaries out of Git. Document local path and external data dependencies. Do not package an E:-bound runner as a standalone portable executable.

Review the staged diff and file sizes, scan for accidental sensitive data, check whitespace and relevant validation. Confirm that source/binary/test evidence corresponds to the committed source version. Hash delivery files after Git line-ending normalization when the manifest describes Git blobs; preserve original market-data hashes as original-byte evidence. Do not rerun an expensive economic test for documentation-only changes.

Commit with a title and description stating the actual change, validation and limitations. Use ordinary non-force push to the confirmed branch/ref. Do not merge main, rewrite shared history, publish releases or send messages without separate explicit authorization. If the remote has advanced, inspect and integrate compatible work in isolation; never discard it to make a push succeed.

## Verify and record

After push, query the remote ref and confirm that it equals the intended commit SHA. Record remote URL, branch, commit, included artifacts, validation scope and remaining gates in the redesign state. Provide a clickable commit or branch link. A local commit or a queued push is not a completed delivery.

If authentication, permissions, approval review, usage limits or network access block delivery, preserve the local commit, report the exact failure and continue independent authorized work. Retry through the legitimate mechanism only when appropriate; never bypass a denied check or repeatedly retry the same unchanged failure. Mark delivery BLOCKED rather than marking the redesign fully delivered.
