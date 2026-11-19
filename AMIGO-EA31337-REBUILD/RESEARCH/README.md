# AMIGO research replay and account-scenario verification

Latest report: [Scenario verification](evidence/SCENARIO_VERIFICATION.md).
Results: [Account comparison](evidence/account_scenario_comparison.csv) and [raw replay output](evidence/account_scenario_replay_20161118_1201.json).

Executed 18 November–1 December 2016 UTC, exclusive end, across ten initial balances from USD 5 to USD 10,000. Each scenario consumed 1,161,581 real quotes. The selected audit suite passed 102 tests.

**NOT READY for native AMIGO performance claims.** This is the existing Python prototype with assumed costs, fixed 0.5% risk and one position. Native multi-horizon execution and hedging/margin parity are not established. No ten-year profitability claim is made.

[Runner guide](runner/README.md) documents the immutable archive-backed dataset, exclusions and commands. The runner preserves the actual tested local E: paths and source hashes; this delivery is not a standalone data bundle. Tick ZIP archives remain on E: and are not committed. A different machine must explicitly provision those dependencies before running it.

Original source and tick files were not changed during the scenario audit. Evidence includes source/ZIP hashes and known data-quality exclusions. Older audit observations are identified as historical evidence in the latest report.
