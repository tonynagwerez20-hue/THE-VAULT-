/amigo-redesign-loop

Act as the accountable engineer and quantitative researcher for AMIGO. Use this redesign pack's `amigo-system-design`, `amigo-native-build` `amigo-quant-validation` and `amigo-remote-push` skills. Read their operating contract and acceptance gates. Own the work from discovery through implementation, native testing, quantitative evaluation and delivery; do not stop at a plan or another prototype report.

## My objective and authorization

Redesign the whole AMIGO system where necessary to make it coherent, maintainable and verifiably correct, without overengineering. You may retain, reconnect, simplify or replace existing subsystems based on evidence. A full redesign is permission to reconsider the system, not a demand to rewrite working code. Keep a single authoritative native execution/risk/accounting path. Use Python for data and independent analysis where useful, not as an unverified substitute trading engine.

For this assignment I authorize necessary source and test changes, native diagnostic instrumentation, an isolated offline MT5 tester, new justified versioned derived datasets, and ordinary Git commits/pushes of reviewed source and evidence to the confirmed ALGOMIND remote. This replaces earlier audit-only restrictions for this assignment. Preserve original tick archives, prior evidence, unrelated dirty edits and working production settings. Use an isolated checkout/worktree and test environment when needed.

No live trading, broker-account changes, paid services/data, copied credentials, changes to the installed live terminal, force pushes, main-branch merges or releases. Follow actual tool permissions; do not bypass failures or approvals.

## Starting points

Inspect `E:\AMIGO-EA31337-REBUILD` and `C:\Users\USER\Desktop\ALGOMIND`. Re-establish current instructions, root, branch, HEAD, working-tree state and actual active source paths. The historical remote is `https://github.com/tonynagwerez20-hue/THE-VAULT-.git`, delivery branch `fix/quant-tib`; verify both before writing. The handoff inside this skill pack identifies current evidence and historical blockers. Treat them as findings to revalidate, not permanent truths.

The previous Python runner and 102 passing tests are research evidence only. They do not establish native MQL5, hedging, horizon or full-decade acceptance. Begin by identifying the smallest end-to-end native slice that can produce verifiable decisions, simulated fills, positions and reconciled accounting.

## Preserve these requirements

- Account grid: USD **5, 10, 25, 50, 100, 250, 500, 1,000, 5,000, 10,000**, independently initialized under identical experiment assumptions.
- Native hedge-account behavior must be demonstrated. Explicitly specify currency/cent denomination, contract and tick values, legal volumes, leverage/margin, commissions/swaps and clock/session rules. Do not infer contract type from account size.
- Support the intended scalp, intraday and swing behavior with explicit identity, authority, stops/targets, management, holding/session and recovery rules. Do not invent position trading or independent concurrent books without a requirement.
- Preserve the approved equity-dependent risk policy: maximum distortion 5, daily hard stop 2%, no drawdown throttle, no unsafe minimum-lot override, initial RR>=2, maximum five confirmed new entries per actual broker day. Rejects/failures do not count; retries/partial fills of one entry do not double-count. Preserve the separate established estimated-stop-exposure ceiling. Do not loosen constraints to make small accounts trade.
- Verify MVE with T(E)=E*R(E)/100 and B(E)=T(E)*D, first E satisfying B(E)>=L_min; normal threshold D=1. Costs, margin and daily/absolute limits remain separate.
- Target XAUUSD tick history from **2016-11-18T00:00:00Z to 2026-11-18T00:00:00Z**, exclusive end, with sufficient earlier warm-up. Do not silently move dates or call a shortened test a decade.
- Use verifiable free data stored on E:. Preserve original sequence/provenance. Do not silently sort bad timestamps, guess DST corrections, remove duplicates, fabricate gaps or replace ticks with OHLC. Any justified derivation must be traceable. Keep unsupported intervals blocked and report them honestly.

## Work continuously in bounded cycles

Discover → choose the most important failing/unproven acceptance condition → design the smallest necessary change → implement → execute relevant checks → challenge the result → record evidence → continue.

Create and maintain a concise resumable state file and experiment index. At every cycle boundary record the current source identity, completed checks, unresolved issues and next concrete action. Resume from that state after context/session interruptions. This prompt does not schedule an unattended process: do not claim to work after the session ends.

Continue authorized work without repeated requests for routine decisions. Ask only when a missing trading-policy or broker input materially affects correctness and cannot be discovered; continue independent work while waiting. Diagnose actual native startup failures rather than replacing them with Python successes. After repeated identical external failures, stop that operation and report exactly what must change; do not loop forever or mark the gate passed.

Keep the architecture small. No speculative services, dashboards, generic frameworks, plugin systems, ML filters or parameter searches. Every new component must solve a demonstrated acceptance problem more simply than alternatives. Separate necessary correctness work from strategy research. Do not optimize for profit before execution validity is established.

## Required evidence

Prove native compilation, initialization and a short replay first. Verify causal higher-timeframe decisions and TIB observation semantics, data import/readback and tester fallback behavior. Then verify the actual lifecycle, risk, margin, daily limits, retries, partials, exits and recovery with a native ledger. Only then scale to the supported account/horizon/window matrix.

Retain run/source/data/binary hashes, exact commands and configs, native logs, per-decision/entry/position/horizon identity, actual execution timestamps and prices/volumes, rejection reasons, costs, daily baselines/locks/counts, realized cash and marked open equity. Recalculate performance independently from those facts. Distinguish marking from liquidation and document all assumed broker costs.

Freeze experiment definitions before evaluating performance. Use declared development/validation/held-out periods, suitable walk-forward or rolling checks, sensible parameter sensitivity and cost/execution stress. Record all trials. Avoid look-ahead, tuning against holdout results, unsupported statistical confidence and cherry-picking account sizes. A correctly tested losing strategy is an acceptable finding; a fabricated profitable result is not.

## Completion and delivery

Deliver the working redesigned source, focused tests, architecture/ownership map, data provenance/coverage, native run evidence, full ledger, account and horizon comparison, metric definitions, robustness assessment and P0–P3 findings. Separate implemented, runtime verified, economically measured and unverified claims. If full completion is blocked, provide completed artifacts and the exact unresolved gate with its next required action.

Give each supported horizon and the combined system a scoped readiness assessment. Choose one overall verdict: QUANTITATIVELY VERIFIED, CONDITIONALLY VERIFIED, NOT READY or INSUFFICIENT EVIDENCE. Do not infer completion from file/test counts or claim future profitability.

Use `/amigo-remote-push` to deliver tested, reviewable milestones and the final evidence package; do not stop at a local commit or ask again for the ordinary pushes already authorized here. Review and push only intended source, tests, small manifests and honest reports to the verified ALGOMIND delivery branch. Keep raw ticks and private terminal state off Git. Verify the remote SHA and provide its link. Continue until the acceptance work is complete or a specific external prerequisite genuinely prevents further authorized progress.
