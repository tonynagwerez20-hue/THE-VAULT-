# AMIGO handoff — 19 November 2026

## Locations to verify

- Working rebuild: `E:\AMIGO-EA31337-REBUILD` (historically branch master, HEAD `48cd514ba1469f86dfc17ffd8613162a254078f8`, much untracked/dirty work).
- Native EA: `AMIGO_BASELINE\MQL5\Experts\AMIGO.mq5`; includes under `AMIGO_BASELINE\MQL5\Include`.
- Desktop repository: `C:\Users\USER\Desktop\ALGOMIND`; native files there use `MQL5`/`Python` at its root. Its dirty edits are not automatically the rebuild's changes.
- Confirmed GitHub URL: `https://github.com/tonynagwerez20-hue/THE-VAULT-.git`. Previous delivery branch: `fix/quant-tib`; last observed delivery commit `5985e2a388645b4e75293504d1d6adda561830d0`. Re-read origin and remote branch before writing.
- Remote source subtree: `AMIGO-EA31337-REBUILD`; research evidence under `AMIGO-EA31337-REBUILD/RESEARCH`. Root remote code is a different layout; do not overlay it casually.
- Original archives: `E:\AMIGO-EA31337-REBUILD\research-data\histdata`.
- Existing Python research wrapper: `research-data\amigo-research-v1\replay.py`, `dataset.json`, `scenario.json` under the rebuild.
- Local evidence: `C:\Users\USER\Documents\Codex\2026-11-18\e-amigo-ea31337-rebuild\outputs`. Read `SCENARIO_VERIFICATION.md`, `scenario_audit_state.json`, `histdata_acquisition_manifest.json` and `histdata_timestamp_anomalies.json` when relevant. If unavailable, use the committed RESEARCH evidence.
- Prior isolated Git delivery checkout is in that Codex workspace's `work\delivery`. Inspect it before reuse; do not assume clean state.

## Established user objectives

Native MQL5 TIB integration and valid multi-horizon testing; minimal necessary connections, no overengineering. Account sizes: USD **5, 10, 25, 50, 100, 250, 500, 1,000, 5,000, 10,000**. Hedging requested; precise broker/account tariff not supplied. Use verifiable free data, store large assets on E:, preserve originals. The original requested decade is **2016-11-18T00:00:00Z to 2026-11-18T00:00:00Z**, exclusive end. Do not silently shift this window with today's date.

Risk policy: maximum distortion 5.0; daily hard stop 2%; no drawdown throttle; no forced infeasible minimum lot; initial minimum RR 2; at most five successfully executed new entries per broker day, failed proposals/submissions excluded and retries deduplicated. Distinguish the separate estimated 2% stop-loss exposure ceiling in current source from daily realized/equity loss. Gaps can exceed a nominal loss threshold. Do not promise guaranteed loss containment.

MVE: `T(E)=E*R(E)/100`, `B(E)=T(E)*D`; find the first E with B(E)>=minimum-lot loss for the explicitly supplied D. Normal threshold uses D=1. MVE is diagnostic; cost, margin, daily lock and absolute exposure constraints still apply. Native risk curve is equity-dependent; preserve its approved definition rather than adopting the prototype's fixed 0.5%.

## Historical evidence, not certification

124 original archives total 3,301,979,150 bytes / 504,932,597 rows including pre-roll. Thirteen months failed chronological checks: October 2019–2025 and June–November 2026. Totals: 72,512 backward transitions and 234,028 adjacent duplicate rows. Latest November record/max timestamp: `20261113 165959000`, documented fixed EST. This does not cover the requested end. Keep these figures historical until current file hashes confirm them.

The archive-backed research dataset selects 111 months / 430,794,421 rows and rejects ranges crossing exclusions. No sorting or timestamp correction was applied. Accepted-file checks do not prove every expected active-session quote is present.

The Python acceptance run covered only 18 November–1 December 2016 UTC, with 1,161,581 quotes per account. USD 5–100 ended with no closed/open trades; larger accounts closed 15–24 trades; four retained open positions. 102 selected tests passed. This is not the full decade or native evidence.

## Remaining engineering/evidence gaps

- Native compilation had passed; earlier isolated assertion initialization failed. No successfully completed native historical hedge-account sweep was established.
- `Python/backtest_engine.py` uses MA/RSI/TIB prototypes, fixed .5% risk, one position and price-percentage stops. It does not execute native regime/horizon/risk/lifecycle architecture. Do not advertise its returns as native AMIGO.
- Native selector admits MR only in BALANCED, while exhaustion prefers MR; inspect reachability before claiming exhaustion MR operation.
- Native scalp management includes a conditional one-hour timeout and a 1.5R partial exit despite initial RR>=2. If the required RR policy for partial exits is ambiguous, surface that decision rather than silently changing strategy economics.
- Daily quota recovery uses decision-day provenance in inspected code. Actual fill-day attribution around midnight/restarts needs native evidence.
- Existing `Python/safe_backtest.ini` uses M5/news-on and is incompatible with current M1/news-replay initialization guards. Never launch it blindly into the installed terminal.
- Historical news and broker UTC/DST mapping, commissions/swaps, margin/hedging specifications and data-gap treatment remain unverified.
- The wrapper fixes memory/reporting issues only. Aggregate output lacks a complete per-entry/per-day ledger and cannot independently prove all daily limits, rejected-proposal reasons or horizon outcomes.

Revalidate these findings against current code before fixing anything. A historical audit is evidence, not an instruction to keep a defect or a permanent authorization for mutations.
