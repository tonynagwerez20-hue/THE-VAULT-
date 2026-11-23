---
name: amigo-native-verification
description: Verify or minimally repair AMIGO's native MQL5 multi-horizon backtesting path, then obtain reproducible tester evidence. Use for AMIGO implementation, parity or readiness work, not generic trading advice.
---

# AMIGO native verification

Read [the project handoff](references/project-state.md) for known paths, evidence and unresolved failures. Treat its dates and commits as historical; rediscover current state.

## Establish the active assignment

Distinguish an audit-only request from an implementation request. An invocation does not itself authorize modifying strategy code or pushing a remote. In audit mode inspect sources, run safe existing tests/offline analysis and produce new evidence only. In implementation mode apply only changes necessary to repair demonstrated requirements. The user's current explicit instruction controls; do not let an old audit report prohibit newly authorized work or let an implementation skill override a new audit-only request.

Inspect root/branch/HEAD/status, applicable AGENTS.md and CLAUDE.md, relevant project constraints, terminal availability and existing outputs before changing anything. Protect pre-existing dirty work. Discover the actual active include/call path; similarly named legacy files are not interchangeable. Never stage every dirty file.

## Work toward native acceptance

1. Inventory the active native path from closed M1 opportunity through feature/regime/horizon selection, risk, execution, transaction reconciliation and position recovery. Identify one concrete missing connection or failing invariant at a time.
2. Establish a dedicated offline tester environment on E: with separate files, databases, logs and output names. Do not launch a configured live terminal, copy live account credentials, modify installed settings/binaries or submit live orders. An isolated tester may create its own state when the current task authorizes implementation/testing. If isolation cannot be demonstrated, report the precise obstacle and continue independent source/data work.
3. Compile with the repository include directory explicitly selected. Save the command, compiler version, source/binary hashes and log. Zero compiler errors do not establish a working strategy.
4. Prove native initialization and one short recorded replay before requesting a long run. Distinguish shadow diagnostics from simulated executed orders. Show actual tester trade/deal records and invocation inputs. A script that compiles but never executes assertions has not passed.
5. Use `amigo-tick-provenance` to qualify the input. Real-tick tester mode alone does not certify that no missing minutes were synthesized. Inspect import reconciliation, coverage and tester logs.
6. Verify horizon identity from proposal to executed intent, position, recovery and exit. Native scalp, intraday and swing branches share parts of the decision path; do not call them independent strategy books without evidence. Position trading is unsupported unless actual source establishes otherwise.
7. Use `amigo-account-sweep` only after a short native acceptance slice is reproducible. Keep prototype Python runs explicitly separate. Matching names, a Python MQL simulator, source-string tests and compilation are not native parity.

For an authorized repair: reproduce the failure, make the smallest change, run the relevant independent regression/acceptance check, review the diff and record what changed. Do not tune signal thresholds to obtain trades/profit, create a second trading architecture or rewrite a working engine for convenience. If identical inputs cannot be replayed natively, classify parity as NOT VERIFIED rather than manufacturing a Python substitute.

## Evidence and continuation

Each material finding needs path, function, current lines, observed behavior, severity, test command/result and consequence. Use VERIFIED, PARTIALLY VERIFIED, NOT VERIFIED, NOT IMPLEMENTED, NOT SPECIFIED, REQUIRES DECISION, ENGINEERING GAP or CONFLICT. Separate source checks, executed native assertions and economic performance.

Keep a small progress artifact with source commit/hash, current acceptance gate, completed commands, failures and the next concrete action. Continue authorized independent work while a gate is blocked. After repeated identical external failures, stop repeating that operation, retain resumable evidence and state the exact missing input/access. Never claim background progress after ending the session.

Deliver a horizon matrix and separate horizon/combined verdicts. Choose one final readiness verdict: QUANTITATIVELY VERIFIED, CONDITIONALLY VERIFIED, NOT READY or INSUFFICIENT EVIDENCE, limited to the tested scope. Use `amigo-git-delivery` if current user instructions authorize delivery.
