# Amigo â€” Document Authority & Governance Record

Status: governance clarification (non-substantive). Does not alter any Amigo technical requirement or specification.

## Document Authority Hierarchy

For all future Amigo implementation, apply this precedence when documents conflict:

| Level | Document | Role |
|---|---|---|---|
| 1 | D4 â€” `Amigo_Engineering_Ready_Master_Specification_Implementation_Blueprint` | Engineering/build authority. Controls implementation sequence, acceptance criteria, engineering gaps, and unresolved decisions. |
| 2 | D3 â€” `Amigo_Master_Harmonized_Specification_v1_0` | Master requirements source, subordinate to D4 where the documents conflict. |
| 3 | D1 â€” `Amigo_Project_Foundation_Agenda_Detailed_Revised_CFTC` | Approved project foundation source. |
| 4 | D5 â€” `Amigo_Detailed_Specification_CFTC_Integrated` | Supporting/detailed contextual specification. |
| 5 | D6 â€” `Amigo_Above_Chats_Extensive_Project_Documentation` | Historical/design context only. |
| 6 | D2 â€” `Amigo_Project_Foundation_Agenda_Detailed` | Superseded by D1; used only for continuity/conflict identification. |

Where documents conflict, apply the higher-authority document.

## Conflict Resolution Rules

- Do not silently reconcile conflicting requirements.
- Where D4 explicitly states ã€ŒNOT SPECIFIEDã€ã€ã€ŒREQUIRES DECISIONã€ã€ã€ŒENGINEERING GAPã€ã€orã€ŒCONFLICTING REQUIREMENTã€, preserve that status exactly.
- Do not invent a resolution.


## Governing Architecture(Established Project Decisions)

- MQL5 owns the Amigo core trading system: final authority over trading, risk, execution,and position management.
- Python exists only as an external-information provider for information MQL5 cannot obtain itself; itmust not become the trading brain, bypass MQL5 hard-risk controls, or outsource core Amigo logicã€‚

## Phase-0 Baseline

- Phase-0 commit: `1a1c334b95ce2a93710adf173054c014dd2b5948` â€” `feat(Amigo: implement phase 0 foundation)`.
- Phase-0 exit criterion (contracts are frozen and testable) satisfied: 16/16 contract tests pass against the pristine committed tree.
- Phase-0 scope: schemas/contracts, repository foundation, configuration,and logging only;no Phase-1 functionality includedã€‚
