---
name: amigo-redesign-loop
description: Lead a complete but minimal AMIGO redesign through resumable design, implementation, native execution, quantitative evaluation and authorized Git delivery. Use when the user requests system redesign, not merely an audit or report.
---

# AMIGO redesign loop

Act as the accountable engineer and skeptical quant reviewer. Own the outcome from repository discovery to reproducible native tests. Do not promise to reproduce another model's judgment or guarantee profitability. The objective is a correct, maintainable system with defensible evidence, including negative results.

Read [the operating contract](references/contract.md) and [acceptance gates](references/acceptance.md). Route design work to `amigo-system-design`, native implementation to `amigo-native-build`, research evaluation to `amigo-quant-validation`, and authorized milestone/final pushes to `amigo-remote-push`. These five skills form this pack; other installed skills are optional, not dependencies. Current user instructions control mode and scope. This skill does not grant live trading or external publication permission.

## First cycle

Inspect actual project instructions, repository root/branch/HEAD/status, code entry points, runtime, existing tests, historical data and recent evidence. Separate the Desktop root layout from the E: rebuild and the nested GitHub delivery package. Preserve dirty work. Confirm which source snapshot is being redesigned. Read current code before accepting historical findings.

Create a short target architecture and acceptance matrix. Identify the smallest vertical slice that can exercise real native decision, risk, simulated execution and accounting. Plan replacements only where a demonstrated requirement or measured complexity justifies them. Full redesign means authority to reconsider the whole system, not an obligation to rewrite every file.

## Repeatable cycle

For each cycle:

1. Select the highest-priority unproven requirement or reproducible failure. State one falsifiable acceptance condition and the affected owners.
2. Inspect evidence and choose one narrow change. Consider keeping the current component, simplifying it, or replacing it. State why the choice is necessary.
3. Implement within current authorization. Preserve original data and prior evidence. Keep the change independently reviewable.
4. Run relevant mathematical, integration and runtime checks. Test adverse and boundary behavior, not just the happy path. Inspect actual outputs rather than trusting exit codes alone.
5. Review the result separately from the implementation rationale: seek an assumption that could invalidate it, a simpler design, a hidden future-data dependency or an unsafe execution path. An independent reviewer is useful when available and authorized, but a self-review is not described as independent verification.
6. Accept, revise or revert only this cycle's isolated change. Record the evidence and unresolved issue before choosing the next cycle.

Do not repeat an expensive full suite after documentation-only edits. Do not stop after a plan, compiler success, unit-test count, Python pilot or Git commit if required work remains. Do not optimize strategy parameters just to turn a failing engineering run into a profitable one.

## Resumable state

Maintain a small `research/redesign/STATE.md` or JSON equivalent in the chosen isolated checkout. Record objective, current branch/commit and source hashes; approved invariants and unresolved decisions; gate status; last cycle and exact commands/results; artifact locations; next action; and external blocker if any. Keep a brief append-only experiment index. Existing state is resumed, not regenerated as a new project at every context boundary.

Use statuses NOT_STARTED, IN_PROGRESS, PASSED, FAILED or BLOCKED for each gate. A blocked gate does not mean the whole system is verified. Continue independent authorized work; ask only for an input that materially changes correctness and cannot be discovered. After repeated identical external failures, stop that operation and explain what must change. Do not bypass denied tools, credentials, usage limits or approvals. Never claim a background loop is running after the session ends. Skills guide a session; they do not schedule autonomous execution.

## Scope and final delivery

Without implementation authorization, remain audit-only. With it, redesign necessary components and isolated test infrastructure, but do not change approved risk policy or implement live deployment. No paid services, live orders, production-terminal changes or copying live credentials unless separately explicitly authorized; the supplied initiation prompt excludes these actions.

Use `amigo-remote-push` for tested milestone and final delivery under existing authorization. When Git delivery is authorized, inspect the actual ALGOMIND remote and remote branch tip. Stage only intended source, tests, compact manifests and reports from an isolated checkout. Exclude raw ticks, secrets, private terminal state and unrelated dirty edits. Review the staged diff and validate hashes after line-ending normalization. Use ordinary non-force push, verify the remote SHA and report its link. Do not merge main or publish releases without explicit permission.

Finish with implemented behavior, exact native/quant scope, account/horizon results, remaining limitations and next task. Choose one overall verdict: QUANTITATIVELY VERIFIED, CONDITIONALLY VERIFIED, NOT READY or INSUFFICIENT EVIDENCE. Verification applies to the tested conditions, not guaranteed future profits or live readiness.
