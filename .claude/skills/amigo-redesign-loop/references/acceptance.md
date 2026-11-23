# Acceptance gates

These are evidence gates, not a requirement for a large framework. A simple file and test can satisfy a gate. Keep independent gates progressing when another is blocked.

| Gate | Required evidence | What does not count |
|---|---|---|
| G0 Scope and ownership | Current repository snapshot, approved risk policy, single owners of signals/risk/execution/accounting, target design and safe work area | Architecture diagrams without tracing the active code |
| G1 Data | Immutable source hashes, UTC/server mapping, coverage/calendar assessment, warm-up, justified derivation or quarantine, imported readback | Downloaded ZIP names; blindly sorted ticks; real-tick mode selection |
| G2 Deterministic core | Causal time boundaries, indicator/math fixtures, stable identity, explicit missing-data behavior and risk feasibility | Matching function names or source-string tests alone |
| G3 Native execution | Isolated MQL5 initialization, actual native assertions and a short replay with decisions/deals/positions | Compilation or Python emulation called native parity |
| G4 Lifecycle and risk | Ledger reconciliation, fills/rejections/retries, partials, gap cases, restart and actual-day entry limits, account-mode/margin checks | Aggregate P/L alone; shadow output described as executed trades |
| G5 Account/horizon sweep | All ten balances, independent starts, per-horizon and combined native results under declared specs; infeasible cases explained | Forcing tiny accounts to trade; pooling balances; relabeling a prototype |
| G6 Quant validation | Frozen experiment definition, held-out evaluation, costs/stress/sensitivity, uncertainty and limitations | Choosing the best in-sample parameters or treating a short win streak as evidence |
| G7 Reproducibility/delivery | Commands, versions, data/source/binary hashes, run manifest, trade/day ledger, honest report and verified authorized remote SHA | A local commit described as pushed; giant data dumps or credentials in Git |

For each completed run, preserve: run ID and scope; implementation/version; start/end and warm-up; source and derived data hashes; broker/account/currency/contract details and their provenance; clock/session assumptions; strategy parameters and risk policy; exact commands; native logs and result paths; failure/skip reasons; and independent metric reconciliation.

Use three distinct claims: software behavior verified, historical economic result measured, and broker/live realism supported. Passing one does not imply the others. A strategy can be correctly implemented and unprofitable. A profitable run can still be invalid.

Readiness report must include the horizon matrix, account comparison, known source/runtime differences, P0–P3 findings, executed versus unexecuted checks and one narrow next step. Do not assign completion percentages from counts of files or tests.
