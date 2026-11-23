---
name: amigo-native-build
description: Build and verify AMIGO's native MQL5 runtime, risk and position lifecycle in an isolated tester, with minimal changes and replayable transaction evidence.
---

# Native build and lifecycle evidence

Read [the contract](../amigo-redesign-loop/references/contract.md) and the active design decisions. Work only in the currently authorized mode. Keep all live trading and installed-terminal state out of this workflow.

Establish an isolated native tester on E: with its own configs, files, journals and output names. Inspect executables and configs before launching; do not copy credentials or assume a script labeled safe is safe. Use repo includes explicitly. Capture source/binary hashes, compiler version and logs. Distinguish clean compile, initialization, executed assertions and actual completed replay as separate outcomes.

Start with a small deterministic native fixture and a short real-data slice. Verify imported quotes through readback and tester logs. Do not use today's external news/context file as historical evidence. If a feature requires unavailable historical context, disable it only in an explicitly labeled separate experiment or block that strategy scope; do not pretend the intended system was tested unchanged.

Test causal closed-bar boundaries and higher-timeframe availability, not just timestamp ordering. Keep TIB observation ownership unambiguous: bid-change sign is a proxy; flat quotes and repeated observations need defined semantics; no tick belongs to two completed bars. Account for event coalescing and full-history reads. Reset or re-warm state across missing intervals according to the actual contract; do not stitch gaps by convenience.

Exercise native risk in account-currency monetary units using executable symbol properties, loss-side tick value/profit calculations, volume flooring, minimum/maximum volume, stop/freeze grids, fees and margin. Missing/invalid inputs fail closed. Verify the approved R(E), D cap, absolute exposure and daily controls separately. Do not force a minimum lot when unsafe or add drawdown throttling.

Write native entry/day evidence when instrumentation is authorized. Verify proposal rejection, request rejection, ambiguous outcomes, confirmed/partial fills, retries, same/opposing positions, hedge/netting differences, stop/target gap fills, partial exits, BE/trailing, expiry/session close and restart recovery. Bind each event to its original intent/horizon and actual fill day. Count one successfully executed new entry once even across retries/partial fills; failed submissions do not consume the successful-entry quota. Account-wide claims require account-wide concurrency tests.

Reconcile positions and cash from execution facts, not requested prices or intended volume. Recovered state must match broker/tester evidence; unknown state blocks new admission instead of guessing. Simulated hedge accounts require verified account mode and margin behavior, not a boolean label in a report.

Changes must address a demonstrated failure and preserve the approved strategy. Use boundary/fault fixtures with independent expected results. Run the focused checks, then the relevant integration gate. Avoid tests that only restate the changed implementation. Record native versus Python/reference execution explicitly.

A failed native startup must be diagnosed with the actual log/config/dependency evidence. Do not replace it with a Python success and advance the native gate. If tools/runtime cannot support a needed case, report exactly which case remains unverified and continue independent work.
