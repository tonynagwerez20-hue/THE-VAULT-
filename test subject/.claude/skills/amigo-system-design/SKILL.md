---
name: amigo-system-design
description: Design or simplify the whole AMIGO trading system around explicit ownership, causal data contracts and minimal native-first components. Use within an authorized redesign, not to expand a targeted bug fix into a rewrite.
---

# Minimal system design

Read [the operating contract](../amigo-redesign-loop/references/contract.md). Trace the active system before drawing its replacement. Classify components KEEP, CONNECT, SIMPLIFY or REPLACE with a concrete reason. A redesign may keep most code when its behavior is sound.

Aim for the smallest coherent path: immutable observations -> causal feature/context snapshot -> strategy proposal and horizon selection -> one authoritative risk/account admission -> one execution/reconciliation owner -> position management -> auditable ledger. These are logical responsibilities, not necessarily new services/classes/files.

MQL5 is the execution authority for native acceptance. Python may acquire/validate data and independently analyze results. Do not build a second Python trading engine merely because it is easier to run. If a cross-language reference is necessary, keep it a test oracle with explicit scope, golden inputs and numerical tolerances, not a competing production authority.

Define only contracts that cross real boundaries: instrument/timezone, observation timestamp versus availability time, closed-period boundary, data-quality flags, snapshot/proposal/horizon identity, requested versus executed volume, immutable risk approval, transaction outcome and position owner. Preserve IDs through retries, partial fills and recovery. Specify ordering, units and missing-data behavior before adding fields.

Unify duplicate risk, sizing, daily-entry and ledger decisions. A shared helper is justified by shared semantics, not similar names. Distinguish strategy intent from broker execution facts. No horizon may borrow another horizon's signal or silently change a saved position's policy.

Define scalp/intraday/swing behavior from actual requirements: entry/context/authority timeframes, causal signal, invalidation, SL/TP, minimum RR, management, maximum/conditional holding rules, sessions and costs. Decide whether the system is a single selected horizon or independent concurrent books based on approved requirements; do not silently change this architecture. Position trading is optional only if separately required.

Before replacing a subsystem, specify the smallest acceptance fixture that demonstrates required behavior and the migration boundary. Preserve old evidence and provide a reversible isolated change. Do not maintain two live competing paths indefinitely. Remove obsolete wiring only after references and ownership have been checked.

Reject speculative abstractions, plugin systems, microservices, generic event buses, dashboards, ML filters and optimization infrastructure unless a measured requirement requires them. Use existing libraries and simple data structures when adequate. Every new dependency/component must answer: which acceptance failure cannot be solved more simply?

Deliver a concise architecture map, ownership/contract table, keep/replace decisions, migration order and first vertical-slice acceptance check. Then implement through the loop rather than producing an endless design document. Surface unresolved trading-policy decisions; do not fill them with invented alpha rules.
