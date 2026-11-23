---
name: amigo-account-sweep
description: Run and independently assess AMIGO account-size and horizon scenarios from USD 5 to USD 10000, separating native results from prototype diagnostics and assumed broker costs.
---

# AMIGO account-scenario acceptance

Use the approved grid **5, 10, 25, 50, 100, 250, 500, 1000, 5000, 10000 USD**. Start accounts independently with identical time windows and strategy parameters. Use actual account currency/denomination conversion; a 500-cent balance is not USD 500. Account size is not account type. Do not infer cent-contract size, leverage, commissions or swap from a label.

Read [the handoff](../amigo-native-verification/references/project-state.md) for known replay limitations and policy. Discover whether the selected executable is native MQL5 or the Python prototype before interpreting results. The present prototype cannot certify native hedging, margin or horizon behavior. A user-approved hypothetical cost scenario is valid research only when named as such; it cannot be relabeled as verified broker history.

## Acceptance before scaling

For native sweeps require an initialized isolated tester, qualified data, explicit hedge/netting mode, account currency, contract/tick values, loss-side conversion, legal volume grid, margin/leverage, stop/freeze restrictions, commissions, swaps including rollover calendar, spread, slippage and execution-delay assumptions. Missing historical tariffs remain NOT VERIFIED even if today's specification is known. Use `amigo-native-verification` and `amigo-tick-provenance` for prerequisites.

Run a short native slice first. Verify each horizon's identity, closed-bar authority, stop/target construction, partials, break-even, trailing, session/time exits and recovery. Keep a separate diagnostic for each horizon and a combined native run with the real arbitration policy. A timeframe label is not an independent strategy and a Python MQL simulator is not a native test.

Where implementation is authorized, record an immutable ledger that makes these checks possible:

- Run ID, source/binary/data hashes and actual UTC/server times.
- Decision, signal, opportunity, intent, submission, confirmed entry and position identities.
- Originating hypothesis/horizon preserved through modifications, fills, partial exits and recovery.
- Equity, R(E), theoretical budget, permitted distortion, estimated minimum-lot loss, executable volume, margin and acceptance/rejection reason.
- Gross P/L, commission, swap, slippage assumptions, realized cash, marked unrealized P/L, daily baseline/lock and actual successful-entry count.

In audit-only mode do not add instrumentation to production code; inspect available logs and explicitly mark fields that cannot be verified. Zero trades require rejection/warm-up evidence before assigning a cause.

Verify max distortion 5, daily stop 2%, no drawdown throttle, no unsafe forced minimum lot, initial RR>=2 and at most five confirmed new entries per actual broker day. Count neither rejected proposals nor failed submissions; deduplicate retries/partial fills of one new entry. Exercise midnight fills, restart recovery and multiple EA instances if account-wide enforcement is claimed. Estimated stop risk and a daily hard stop do not guarantee losses remain bounded during gaps.

Verify MVE against E*R(E)/100*D, normal threshold with D=1 and the actual approved curve. Do not mistake passing MVE for sufficient margin or risk permission. Test metadata missing/NaN, volume step flooring, loss-side tick value, small accounts, commissions and currency conversion without relaxing rules to force trades.

## Results and statistics

Reconcile realized balance, closed trade net P/L, financing/cash adjustments and marked open equity. State whether the final position is marked or actually liquidated and which exit costs are reserved. Attribute costs to trades before computing net profit factor/expectancy. Use consistent equity-return denominators; do not annualize tick returns as if sampling were regular. Define drawdown basis, cash flows, no-loss/no-trade cases and open exposure. Do not pool returns from independent starting balances or disconnected data windows into one equity curve.

Report per account and per supported horizon: entries, rejections by cause, closed/open positions, net realized/marked P/L, drawdown, holding/exposure and cost totals when ledgers support them. Include commands, exact dates, configuration, source hashes, tests and known omissions. Never invent unobservable metrics.

Only after execution acceptance, assess held-out periods, regime coverage, parameter sensitivity and realistic cost/slippage stress without selecting the best test result as evidence of general profitability. Do not tune until every small account trades. An infeasible USD 5 account should remain NO_TRADE.

End with separate horizon and combined readiness verdicts plus one narrow next task. A profitable prototype interval cannot override missing native evidence; a passing compile/unit suite is not economic validation.
