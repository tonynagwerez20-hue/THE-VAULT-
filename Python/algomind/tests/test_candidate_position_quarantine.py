"""Source-contract checks for fail-closed position lifecycle quarantine.

These checks do not execute MQL5 or simulate broker outcomes.
"""
from pathlib import Path
import unittest

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "MQL5" / "Include").is_dir()) / "MQL5"
MANAGER = (ROOT / "Include" / "Position Manager.mqh").read_text(encoding="utf-8-sig")
AMIGO = (ROOT / "Experts" / "AMIGO.mq5").read_text(encoding="utf-8-sig")


class PositionQuarantineCandidate(unittest.TestCase):
    def test_registration_rejects_invalid_fill_geometry_before_state_allocation(self):
        register = MANAGER.split("void PositionManagerRegister(", 1)[1].split(
            "//+------------------------------------------------------------------+\n//| Close or remove", 1
        )[0]
        self.assertIn("MathIsValidNumber(entry)", register)
        self.assertIn("MathIsValidNumber(stop)", register)
        self.assertIn("MathIsValidNumber(target)", register)
        self.assertIn("MathIsValidNumber(atr)", register)
        self.assertIn("MathIsValidNumber(filled_volume)", register)
        self.assertIn("dir==+1 && stop<entry && target>entry", register)
        self.assertIn("dir==-1 && stop>entry && target<entry", register)
        self.assertIn("horiz<HORIZON_SCALPING || horiz>HORIZON_SWING", register)
        reject = register.index("PositionManagerLatchStateFault")
        allocation = register.index("ArrayResize(g_positions, n + 1)")
        self.assertLess(reject, allocation)

        # Independently derive the admissible lifecycle geometry. Stop and
        # target must bracket entry in the direction-consistent order.
        import math

        def valid(direction, entry, stop, target, volume, atr):
            vals = (entry, stop, target, volume, atr)
            if not all(math.isfinite(x) and x > 0 for x in vals):
                return False
            return ((direction == 1 and stop < entry < target) or
                    (direction == -1 and target < entry < stop))

        self.assertTrue(valid(1, 2000, 1990, 2020, 0.1, 2))
        self.assertTrue(valid(-1, 2000, 2010, 1980, 0.1, 2))
        for args in ((1, 2000, 2010, 2020, 0.1, 2),
                     (-1, 2000, 1990, 1980, 0.1, 2),
                     (0, 2000, 1990, 2020, 0.1, 2),
                     (1, float("nan"), 1990, 2020, 0.1, 2),
                     (1, 2000, 1990, 2020, float("inf"), 2),
                     (1, 2000, 1990, 2020, 0.1, 0)):
            with self.subTest(args=args):
                self.assertFalse(valid(*args))

    def test_runtime_position_owner_symbol_magic_and_direction_are_revalidated(self):
        identity = MANAGER.split("bool PositionManagerSelectedIdentityMatches(", 1)[1].split(
            "// CTrade's bool", 1
        )[0]
        for required in (
            "POSITION_IDENTIFIER", "POSITION_SYMBOL", "POSITION_MAGIC",
            "POSITION_TYPE", "POSITION_TYPE_BUY", "POSITION_TYPE_SELL",
        ):
            self.assertIn(required, identity)

        tick = MANAGER.split("void PositionManagerTick(", 1)[1].split(
            "//+------------------------------------------------------------------+\n//| Timer", 1
        )[0]
        initial_select = tick.index("PositionSelectByIdentifier(pid, position_ticket)")
        identity_check = tick.index("PositionManagerSelectedIdentityMatches", initial_select)
        stop_repair = tick.index("PositionManagerRestoreMissingProtectiveStop", identity_check)
        self.assertLess(initial_select, identity_check)
        self.assertLess(identity_check, stop_repair)
        self.assertIn("ownership or direction changed during management", tick)

        restore = MANAGER.split("bool PositionManagerRestoreMissingProtectiveStop(", 1)[1].split(
            "//--- Round a raw volume", 1
        )[0]
        before_modify = restore.index("PositionManagerSelectedIdentityMatches(p,cfg.symbol,cfg.magic_number)")
        modify = restore.index("g_trade.PositionModify(ticket,recovery_stop,cur_tp)")
        after_reselect = restore.index("PositionSelectByTicket(verified_ticket)")
        after_modify = restore.index("PositionManagerSelectedIdentityMatches(p,cfg.symbol,cfg.magic_number)", before_modify + 1)
        self.assertLess(before_modify, modify)
        self.assertLess(modify, after_reselect)
        self.assertLess(after_reselect, after_modify)

        remove = MANAGER.split("void PositionManagerRemove(", 1)[1].split(
            "void PositionManagerTick(", 1
        )[0]
        select = remove.index("PositionSelectByIdentifier(pid, current_ticket)")
        check = remove.index("PositionManagerSelectedIdentityMatches", select)
        close = remove.index("g_trade.PositionClose(current_ticket)")
        self.assertLess(select, check)
        self.assertLess(check, close)
        self.assertIn("close target %I64u ownership or direction changed", remove)

        # Independent owner oracle: identifier alone is insufficient; any
        # identity/direction mismatch must prevent a broker lifecycle action.
        def may_manage(saved, broker):
            return all(saved[key] == broker[key]
                       for key in ("id", "symbol", "magic", "direction"))

        saved = {"id": 91, "symbol": "XAUUSD", "magic": 42, "direction": "BUY"}
        self.assertTrue(may_manage(saved, dict(saved)))
        for key, value in (("id", 92), ("symbol", "EURUSD"),
                           ("magic", 43), ("direction", "SELL")):
            with self.subTest(key=key):
                self.assertFalse(may_manage(saved, dict(saved, **{key: value})))

    def test_confirmed_close_record_removal_requires_observed_position_absence(self):
        remove = MANAGER.split("void PositionManagerRemove(", 1)[1].split("void PositionManagerTick(", 1)[0]
        self.assertIn("PositionLookupByIdentifier(pid,remaining_ticket)", remove)
        self.assertIn("remaining!=POSITION_LOOKUP_ABSENT", remove)
        self.assertIn("PositionManagerLatchStateFault", remove)
        self.assertLess(remove.index("remaining!=POSITION_LOOKUP_ABSENT"),
                        remove.index("ArrayResize(g_positions, ArraySize(g_positions) - 1)"))

    def test_identifier_lookup_distinguishes_found_absent_and_unknown(self):
        lookup = MANAGER.split("ENUM_POSITION_LOOKUP_STATUS PositionLookupByIdentifier(", 1)[1].split("bool PositionSelectByIdentifier(", 1)[0]
        self.assertIn("POSITION_LOOKUP_UNKNOWN", lookup)
        self.assertIn("POSITION_LOOKUP_FOUND", lookup)
        self.assertIn("POSITION_LOOKUP_ABSENT", lookup)
        self.assertIn("candidate_ticket == 0) return POSITION_LOOKUP_UNKNOWN", lookup)

    def test_unresolved_identifier_is_retained_and_quarantines(self):
        block = MANAGER.split("if(!PositionSelectByIdentifier(pid, position_ticket))", 1)[1].split("\n      }", 1)[0]
        self.assertIn("PositionManagerLatchStateFault", block)
        self.assertNotIn("ArrayResize(g_positions", block)

    def test_position_state_save_failures_quarantine(self):
        self.assertIn("if(!PositionSaveState(cfg))\n      PositionManagerLatchStateFault", MANAGER)
        self.assertIn("if(state_dirty && !PositionSaveState(cfg))", MANAGER)

    def test_admission_is_blocked_before_new_bar_processing(self):
        on_tick = AMIGO.split("void OnTick()", 1)[1].split("void OnClosedBar()", 1)[0]
        gate = on_tick.index("if(!PositionManagerAdmissionAllowed()) return;")
        consume = on_tick.index("OnClosedBar(opportunity_id)")
        self.assertLess(gate, consume)

    def test_ambiguous_partial_is_not_retried_in_runtime_loop(self):
        self.assertIn("if(!g_positions[i].partial_done && PositionManagerAdmissionAllowed())", MANAGER)
        self.assertIn("partial-close outcome requires reconciliation", MANAGER)

    def test_partial_close_requires_full_retcod_and_confirmed_remaining_volume(self):
        start = MANAGER.index("bool partial_call_ok = g_trade.PositionClosePartial")
        end = MANAGER.index("//--- Invalid TP check guard", start)
        block = MANAGER[start:end]
        self.assertIn("PositionManagerTradeSucceeded(partial_call_ok, false)", block)
        self.assertNotIn("PositionManagerTradeSucceeded(partial_call_ok, true)", block)
        self.assertIn("PositionSelectByIdentifier(pid,refreshed_ticket)", block)
        self.assertIn("MathAbs(remaining_volume-(vol-part))<=tolerance", block)
        self.assertIn("PositionManagerLatchStateFault(StringFormat(\"partial-close volume mismatch", block)
        self.assertIn("if(!PositionSaveState(cfg))", block)

        # Independent outcome oracle: only full acknowledgement plus exact
        # broker volume confirms the intended reduction. Partial/unknown result,
        # stale position selection, and persistence failure all quarantine.
        def outcome(full_done, observed_remaining, expected_remaining, saved):
            if not full_done or observed_remaining is None:
                return "QUARANTINE"
            if abs(observed_remaining - expected_remaining) > 1e-8 or not saved:
                return "QUARANTINE"
            return "PARTIAL_CONFIRMED"

        self.assertEqual(outcome(True, 0.70, 0.70, True), "PARTIAL_CONFIRMED")
        self.assertEqual(outcome(False, 0.85, 0.70, True), "QUARANTINE")
        self.assertEqual(outcome(True, 0.85, 0.70, True), "QUARANTINE")
        self.assertEqual(outcome(True, None, 0.70, True), "QUARANTINE")
        self.assertEqual(outcome(True, 0.70, 0.70, False), "QUARANTINE")

    def test_accepted_live_execution_without_position_id_quarantines(self):
        block = AMIGO.split("if(er.position_id == 0 && !g_cfg.shadow_only && er.accepted)", 1)[1].split("else if(er.position_id == 0 && g_cfg.shadow_only)", 1)[0]
        self.assertIn("PositionManagerLatchStateFault", block)

    def test_duplicate_position_registration_is_rejected(self):
        block = MANAGER.split("for(int i=0; i<ArraySize(g_positions); i++)", 1)[1].split("int n = ArraySize(g_positions);", 1)[0]
        self.assertIn("duplicate registration", block)
        self.assertIn("return;", block)

    def test_runtime_volume_mismatch_quarantines_before_lifecycle_actions(self):
        tick = MANAGER.split("void PositionManagerTick(", 1)[1].split("//+------------------------------------------------------------------+\n//| Timer", 1)[0]
        repair = tick.index("PositionManagerRestoreMissingProtectiveStop")
        reselect = tick.index("PositionSelectByIdentifier(pid,position_ticket)", repair)
        volume_check = tick.index("MathAbs(broker_volume-g_positions[i].current_volume)", reselect)
        mismatch_latch = tick.index("runtime volume mismatch for position", volume_check)
        partial_close = tick.index("g_trade.PositionClosePartial", volume_check)
        stop_modify = tick.index("g_trade.PositionModify", volume_check)
        self.assertLess(repair, reselect)
        self.assertLess(reselect, volume_check)
        self.assertLess(volume_check, mismatch_latch)
        self.assertLess(mismatch_latch, partial_close)
        self.assertLess(mismatch_latch, stop_modify)
        self.assertIn("POSITION_VOLUME", tick[reselect:volume_check])
        self.assertIn("volume_step*0.25", tick[reselect:volume_check])

        def volume_matches(saved, observed, step):
            import math
            if not all(math.isfinite(value) and value > 0.0 for value in (saved, observed, step)):
                return False
            return abs(saved - observed) <= step * 0.25

        self.assertTrue(volume_matches(0.10, 0.10, 0.01))
        self.assertTrue(volume_matches(0.10, 0.102, 0.01))
        self.assertFalse(volume_matches(0.10, 0.105, 0.01))
        self.assertFalse(volume_matches(0.10, float("nan"), 0.01))

    def test_existing_entry_or_better_stop_does_not_infer_be_transition(self):
        start = MANAGER.index("bool is_be_improvement =")
        end = MANAGER.index("// If trailing is off", start)
        block = MANAGER[start:end]
        no_improvement = block.split("else\n               {", 1)[1]
        self.assertIn("do not infer history", no_improvement)
        self.assertNotIn("g_positions[i].be_activated = true", no_improvement)
        self.assertIn("g_positions[i].be_activated      = true", block)


if __name__ == "__main__":
    unittest.main()
