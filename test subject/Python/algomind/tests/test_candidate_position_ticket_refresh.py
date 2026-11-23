"""Offline source-contract regression for position-ticket refresh.

This verifies source ordering only; it does not execute MQL5 or broker APIs.
"""
from pathlib import Path


ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "MQL5" / "Include" / "Position Manager.mqh").is_file()
)
MANAGER = (ROOT / "MQL5" / "Include" / "Position Manager.mqh").read_text(
    encoding="utf-8-sig"
)


def test_partial_close_refreshes_ticket_only_after_confirmed_volume():
    start = MANAGER.index("bool partial_call_ok = g_trade.PositionClosePartial")
    end = MANAGER.index("//--- Invalid TP check guard", start)
    block = MANAGER[start:end]

    # Independent expected contract: before a later stop update can use the
    # current ticket, the position must be reselected by stable id and its
    # resulting volume must match the expected reduction.
    assert "PositionSelectByIdentifier(pid,refreshed_ticket)" in block
    assert "MathAbs(remaining_volume-(vol-part))<=tolerance" in block
    assert block.index("MathAbs(remaining_volume-(vol-part))<=tolerance") < block.index(
        "position_ticket = refreshed_ticket;"
    )
    assert block.index("position_ticket = refreshed_ticket;") < block.index(
        "g_positions[i].partial_done = true;"
    )
    assert "PositionManagerLatchStateFault(StringFormat(\"partial-close volume mismatch" in block


if __name__ == "__main__":
    test_partial_close_refreshes_ticket_only_after_confirmed_volume()
