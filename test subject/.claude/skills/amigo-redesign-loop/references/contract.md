# Operating contract and known starting point

## Discover these locations; do not assume unchanged state

- Main rebuild: `E:\AMIGO-EA31337-REBUILD`. Native source historically under `AMIGO_BASELINE/MQL5`, Python under `Python` and `AMIGO_BASELINE/Python`.
- Desktop delivery repository: `C:\Users\USER\Desktop\ALGOMIND`; its native/Python layout begins at the root and it has extensive pre-existing edits.
- Confirmed previous GitHub remote: `https://github.com/tonynagwerez20-hue/THE-VAULT-.git`; delivery branch `fix/quant-tib`; historical last commit `5985e2a388645b4e75293504d1d6adda561830d0`. Verify current origin and tip.
- Remote rebuild subtree: `AMIGO-EA31337-REBUILD`; research reports at `RESEARCH/evidence/SCENARIO_VERIFICATION.md` below it.
- Local reports: `C:\Users\USER\Documents\Codex\2026-11-18\e-amigo-ea31337-rebuild\outputs`. Read the scenario audit, source-state and acquisition manifests when relevant.
- Tick ZIPs: `E:\AMIGO-EA31337-REBUILD\research-data\histdata`. Research wrapper: `research-data\amigo-research-v1`.

These are discovery hints, not permission to overwrite. Read applicable AGENTS.md/CLAUDE.md and project policies. Earlier audit-only artifacts describe earlier assignments; a new explicit implementation request can authorize repairs, but skills cannot silently override an active audit-only request.

## User requirements to preserve

- USD initial equity grid: **5, 10, 25, 50, 100, 250, 500, 1,000, 5,000, 10,000**. Independent starts, identical experiment assumptions.
- Hedging requested. Demonstrate native account-mode behavior before claiming it. Account size, account type, currency denomination and contract scale are separate properties.
- Intended core instrument: XAUUSD. EURUSD, GBPUSD, USDJPY and BTCUSD are generalization targets only if specified/data-supported; do not infer tested support.
- Intended horizons: scalping, intraday and swing. Position trading must not be invented merely to complete a matrix.
- Requested historical window: **2016-11-18T00:00:00Z to 2026-11-18T00:00:00Z**, exclusive end, with earlier warm-up. Do not silently move the window forward with today's date.
- Maximum distortion 5.0; daily hard stop 2%; no drawdown throttle; no forced minimum lot when infeasible; initial reward/risk >=2; maximum five confirmed new trade entries per actual broker day. Failed proposals/submissions do not count; retries/partial fills of one entry must not double-count.
- Preserve the approved equity-dependent risk curve. The prototype's fixed 0.5% is not the native policy. Preserve any established separate 2% estimated-stop-exposure ceiling; do not confuse it with a guarantee against gap losses.
- MVE uses T(E)=E*R(E)/100 and B(E)=T(E)*D; find the first E with B(E)>=L_min for supplied fixed D. Normal threshold sets D=1. Margin, fees, currency conversion and other risk gates remain separate.
- Use free verifiable sources; put large assets on E:. Preserve originals. Minimize dependencies and new components.

When initial RR, net RR, partial exits or other policy meanings conflict, record the exact conflict and obtain a targeted decision if implementation depends on it. Never quietly loosen a safety rule or invent a trading-policy change as an engineering fix.

## Evidence as of 19 November 2026

The previous delivery includes native TIB source and compilation results, but no proven completed native hedge-account historical sweep. An isolated native assertion startup had failed. Existing tester presets can conflict with current M1/news-history guards. Diagnose current behavior rather than blindly reusing those presets.

124 downloaded archives contained roughly 505 million rows including warm-up. Thirteen months failed chronology: October 2019–2025 and June–November 2026. There were 72,512 backwards transitions and 234,028 adjacent duplicates. The newest November quote was 13 November 2026, short of the requested end. Current manifests/hashes must confirm these facts before reuse.

The research subset accepts 111 months but is discontinuous. The Python wrapper ran 18 November–1 December 2016 across all ten sizes with 1,161,581 quotes/account. USD 5–100 had no closed or open trades; larger accounts closed 15–24 trades; four retained positions. 102 selected tests passed. This was not a ten-year or native test.

Known gaps to revalidate: Python/native strategy and risk mismatch; missing native hedge/margin verification; inconsistent exhaustion/MR eligibility; partial-RR policy interpretation; daily fill-day/restart accounting; absent historical news/cost/session mapping; incomplete per-trade/per-day evidence. Do not preserve a confirmed bug merely because a prior report documented it, or assume a named feature works because a class exists.
