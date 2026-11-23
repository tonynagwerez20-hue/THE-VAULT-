# AMIGO: finish the native implementation and verify the account sweep

Use `/amigo-native-verification` as the main workflow, with `/amigo-tick-provenance`, `/amigo-account-sweep` and `/amigo-git-delivery` where applicable. Read the skills and their project handoff before acting.

## Objective and authorization

I want AMIGO's actual MQL5 implementation, including TIB and its intended trading horizons, to produce valid, reproducible backtests across account sizes from USD 5 to USD 10,000. Complete the necessary implementation and verification, not just another audit report or a short Python demonstration.

For this assignment I authorize narrowly scoped source fixes, necessary tests/instrumentation, new versioned derived data where its transformation is justified, and a dedicated isolated native tester environment. This implementation authorization replaces the earlier audit-only restriction for this assignment. Preserve original archives, existing evidence and unrelated working-tree edits. Make only the necessary connections; no redesign, new trading framework, extra services, dashboard or parameter tuning to manufacture profitable results.

I authorize committing and pushing the completed, checked source and evidence to the confirmed ALGOMIND GitHub remote on an appropriate delivery branch. Do not merge to main, force-push or publish a release. No live trading, broker-account changes, paid data/services, changes to installed terminal settings/binaries, credential copying or exposure. Follow actual tool permissions; do not bypass approval or authentication failures.

## Known workspace and evidence

- Rebuild: `E:\AMIGO-EA31337-REBUILD`.
- ALGOMIND: `C:\Users\USER\Desktop\ALGOMIND`.
- Confirmed previous remote: `https://github.com/tonynagwerez20-hue/THE-VAULT-.git`; last delivery branch `fix/quant-tib`. Verify before use.
- Native source is under `AMIGO_BASELINE\MQL5` in the rebuild; the Desktop root layout differs. Inspect the actual files and call path.
- Read the latest `SCENARIO_VERIFICATION.md` and manifests from the local Codex output folder listed in the handoff, or from remote `AMIGO-EA31337-REBUILD/RESEARCH/evidence`.
- Original HistData ZIPs are on E: under `research-data\histdata`; the existing research wrapper is under `research-data\amigo-research-v1`.

Re-establish root, branch, HEAD, staged/unstaged/untracked state and applicable project instructions. Do not treat a historical report or commit as the current source snapshot. Use an isolated checkout for delivery when needed to protect dirty work.

## Required outcome

1. **Native evidence first.** Compile against the intended repository includes, then prove native initialization and a short isolated tester run with real recorded inputs. Capture actual native decisions, orders/deals, positions, exits and assertion output. A successful compile, Python reference simulator or source-string test is not MQL5 runtime verification.
2. **Correct horizon behavior.** Establish which of scalping, intraday, swing and position trading are actually implemented. Verify closed-timeframe authority, causality, originating horizon through the entire lifecycle, deterministic arbitration, stop/target geometry, partials, break-even/trailing, holding/session rules and restart recovery. Do not add position trading just to fill a matrix. Address demonstrated inconsistencies with minimal changes; do not invent an alternate strategy architecture.
3. **Qualified ticks.** Preserve source bid/ask and sequence provenance. Investigate excluded HistData clock/ordering anomalies and missing end-date coverage. Never silently sort, shift hours, delete duplicate ticks, interpolate or replace ticks with candles. A justified derived version needs input/output hashes, original-row mapping and a documented transformation; otherwise quarantine or obtain independently verifiable free replacement coverage. Do not join different sources or disconnected periods without disclosure and a justified experiment design.
4. **Requested decade.** Target `2016-11-18T00:00:00Z` through `2026-11-18T00:00:00Z`, end exclusive, with sufficient earlier warm-up. Do not roll these dates forward or call a shorter slice a ten-year result. Verify actual imported readback and tester logs; selecting real-tick mode does not prove that no ticks were synthesized. If the exact window cannot be supported, identify its unresolved coverage precisely and complete valid independent work without fabricating data.
5. **All account scenarios.** Run USD **5, 10, 25, 50, 100, 250, 500, 1,000, 5,000 and 10,000**, each starting independently with the same strategy and data assumptions. Hedge-account behavior must be exercised in the native tester before it is claimed. Specify broker/account currency and denomination, tick/contract values, legal lot grid, leverage/margin, costs and rollover rules. Where historical specifications are unavailable, label cost/account runs as assumptions and stress scenarios, not verified broker history. Do not equate small equity with a cent contract.
6. **Risk invariants.** Preserve maximum distortion 5.0, daily hard stop 2%, no drawdown throttle, NO_TRADE for infeasible minimum lots, initial RR at least 2, and no more than five successfully executed new entries per actual broker day. Rejections/failed submissions do not count; retries and partial fills of the same new entry must not double-count. Verify actual fill-day and restart behavior. Preserve the approved equity-dependent risk curve. Do not loosen rules to make a USD 5 account trade.
7. **MVE.** Verify `T(E)=E*R(E)/100`, `B(E)=T(E)*D` and the first equity satisfying `B(E)>=L_min`; normal operation uses `D=1`. Include relevant cost/currency effects and broker volume constraints. Distinguish this diagnostic from margin feasibility, daily locks and any separate absolute exposure ceiling. Report the interpretation of partial-exit RR explicitly rather than silently changing it.
8. **Auditable results.** Retain per-entry/per-day evidence: run/source/data hashes, UTC/server timestamps, horizon/hypothesis, decision/intent/fill/position identities, risk/volume/margin, rejection reasons, daily successful-entry count, costs, realized cash and marked open equity. Reconcile the trade ledger before calculating net expectancy, profit factor, drawdown or holding/exposure metrics. Distinguish marking an open position from liquidating it. Record missing metrics as unverified; do not invent Sharpe ratios or confidence intervals.
9. **Robustness after correctness.** Only after native execution acceptance, perform clearly separated held-out/rolling validation and sensible cost/slippage sensitivity on the supported coverage. Keep development and evaluation periods identifiable. Do not optimize thresholds on the same data and call the result out-of-sample. No profitability claim without credible evidence.

## Working loop

Discover the next material blocker → reproduce it → apply the smallest authorized repair → run the relevant test → verify real behavior → record evidence → advance to the next acceptance gate. Prefer existing components and explicit ownership to parallel implementations.

Do not stop after a plan, compilation, the previous 102 tests, a Python pilot or a packaging milestone. Continue through the native acceptance and scenario sweep where the environment and data support them. Keep a resumable progress record with completed actions, exact commands, failures and the next concrete step. Give concise updates when a finding or outcome changes. Do not repeat identical failed network/tool calls indefinitely, bypass denied actions or promise background work after ending the session.

Use existing authorization for reversible work; do not ask again for routine implementation choices. Ask one targeted question only when an unresolved policy/broker input would materially change correctness and cannot be established from available evidence. Continue independent work while waiting. If external prerequisites make a gate impossible, report the exact blocker, completed work and next required action; do not mark that gate complete.

## Deliverables and completion

Provide tested source changes, provenance/import manifests, native logs and run configurations, full trade/daily ledgers, an account comparison covering all ten balances, a horizon implementation/readiness matrix, mathematical/risk/metric checks, Python/MQL5 differences, test commands/results, and a P0–P3 findings register. Separate VERIFIED, PARTIALLY VERIFIED, NOT VERIFIED, NOT IMPLEMENTED, NOT SPECIFIED, REQUIRES DECISION, ENGINEERING GAP and CONFLICT.

Answer whether horizons operate independently, decisions are causal, execution costs are realistic, risk/MVE/daily counts are correct, native/Python behavior agrees and statistical evidence is sufficient. Give each supported horizon and the combined system an evidence-based verdict. For overall readiness choose exactly one: QUANTITATIVELY VERIFIED, CONDITIONALLY VERIFIED, NOT READY or INSUFFICIENT EVIDENCE. Do not derive a completion percentage from file/test counts.

Push only intended source, tests, small manifests and honest reports to the verified ALGOMIND remote. Keep tick archives and private terminal state on E:. Confirm the remote commit/ref, then report the link, exact tested scope, unresolved limitations and next narrowly scoped task. A negative strategy result is acceptable; a fabricated successful verification is not.
