---
name: amigo-tick-provenance
description: Acquire, qualify and trace AMIGO bid/ask tick history for causal TIB replay, including HistData clock anomalies and missing periods. Use for data readiness or import verification, not price prediction.
---

# AMIGO tick provenance

Read [the handoff's data facts](../amigo-native-verification/references/project-state.md) when working on the existing archive. Verify manifests/hashes before reusing their conclusions.

Retain original archives byte-for-byte. Store large data on E: after checking capacity. Any authorized derived dataset gets a new version/location, transformation manifest, input/output hashes and an explicit calendar/timezone contract. Audit-only mode permits inspection and new evidence, not changing datasets.

Require timestamps plus bid and ask for TIB execution tests. Record provider/source URL, retrieval time, format, price scale, timezone, first/last/min/max timestamp, number of rows and checksum. Verify actual records; a provider landing page or a successful HTTP response is not coverage evidence. Use only free sources unless the user explicitly authorizes costs.

Measure invalid/crossed quotes, backwards timestamps, same-time observations, exact duplicates, gaps, precision changes and market-day coverage. Multiple distinct quotes at one timestamp are not automatically duplicates. Even identical repeated quotes may encode feed observations; deleting them changes tick counts and TIB behavior. Separate market closures from missing active-session records using a justified trading calendar. Validate pre-roll separately from the performance period.

For HistData, the documented clock is fixed EST without DST, but observed files have backwards jumps and recent extensive disorder. Do not assume every anomaly is DST. Adding five hours does not fix a backwards sequence. Never silently sort by timestamp, shift hours, delete duplicates or fabricate missing ticks. If an authorized repair is justified by independent provider evidence, document the rule, preserve original sequence/row IDs and label the derived data. If order cannot be established, quarantine the affected interval or obtain independently verified replacement coverage. Do not silently splice different broker feeds; preserve source boundaries and disclose comparability limits.

Produce a coverage manifest that separates acquired files, valid syntax, chronological acceptance and verified requested-window coverage. Excluding months creates gaps; reset/report separate experiments rather than compounding disconnected periods as continuous performance. Missing end-date data blocks the full-decade claim, not independent short-slice diagnostics.

When importing into an isolated MT5 custom symbol, reconcile source row counts, timestamps, quote sides, digits/tick size and imported readback. Test first/last boundaries and samples around gaps. Inspect tester logs for missing or synthesized ticks. MQL5 OnTick events may coalesce; verify the intended full tick history path rather than assuming every imported tick generated one callback.

Label quote-sign imbalance, tick volume, footprint, proxy DOM and proxy VWAP as proxies. Bid/ask history supplies neither exchange aggressive-trade signs nor actual depth/queue/fill history. Report what is TRUE in the records, PROXY, LIMITED or MISSING.

If a download fails, use bounded retries and resume from verified immutable files. Preserve failure evidence; a DNS or HTTP failure does not establish absent history. Do not repeatedly restart a multi-gigabyte acquisition or claim a complete dataset when only monthly names were found.
