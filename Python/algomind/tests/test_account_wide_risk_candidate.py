"""Offline source-contract tests and independent aggregate-risk oracles.

These do not execute MQL5 or prove terminal Global Variable semantics.
"""
from pathlib import Path
import unittest
from datetime import date


ROOT = Path(__file__).resolve().parents[3]
RISK = (ROOT / "MQL5" / "Include" / "Risk Engine.mqh").read_text(encoding="utf-8-sig")
ACCOUNT = (ROOT / "MQL5" / "Include" / "Account Execution Engine.mqh").read_text(encoding="utf-8-sig")
EXEC = (ROOT / "MQL5" / "Include" / "Execution Engine.mqh").read_text(encoding="utf-8-sig")
AMIGO = (ROOT / "MQL5" / "Experts" / "AMIGO.mq5").read_text(encoding="utf-8-sig")


def aggregate_risk_pct(equity, open_position_risks, pending_order_risks, candidate_risk):
    """Independent monetary oracle: gross stop-loss risks are additive."""
    if equity <= 0 or any(x < 0 for x in (*open_position_risks, *pending_order_risks)):
        raise ValueError("invalid risk input")
    return (sum(open_position_risks) + sum(pending_order_risks) + candidate_risk) / equity * 100


def margin_feasible(calc_succeeded, required_margin, free_margin):
    """Independent fail-closed oracle for broker margin feasibility."""
    import math
    return (calc_succeeded and math.isfinite(required_margin) and required_margin >= 0
            and math.isfinite(free_margin) and free_margin > 0
            and required_margin <= free_margin * 0.95)


def daily_rollover_loss(previous_observed_equity, first_new_day_equity, limit_pct):
    """Conservative proxy when no equity observation exists at midnight."""
    import math
    if (not math.isfinite(previous_observed_equity) or previous_observed_equity <= 0
            or not math.isfinite(first_new_day_equity) or first_new_day_equity <= 0
            or not math.isfinite(limit_pct) or limit_pct <= 0):
        return None
    loss_pct = (previous_observed_equity - first_new_day_equity) / previous_observed_equity * 100
    return loss_pct, loss_pct >= limit_pct


def equity_checkpoint_due(last_persisted_bar, current_bar, high_water_changed):
    return high_water_changed or (current_bar > 0 and current_bar > last_persisted_bar)


def equity_after_lock(caller_snapshot, current_account_equity):
    """The authoritative sample is acquired after serialization, not before."""
    _ = caller_snapshot
    return current_account_equity


def merge_legacy_risk(records, today):
    """Numeric merge oracle only; production migration requires a sole exact hash."""
    if not records:
        raise ValueError("no legacy risk state")
    if any(r["day"] > today for r in records):
        raise ValueError("future ledger date")
    if any(r["uncertain"] for r in records):
        raise ValueError("ambiguous opportunity")
    current = [r for r in records if r["day"] == today]
    if not current:
        raise ValueError("cannot establish current day baseline")
    return {
        # Higher baseline produces the greatest loss under
        # (baseline - equity) / baseline, so it is conservative on merge.
        "start_of_day_equity": max(r["day_start"] for r in current),
        "peak_equity": max(r["peak"] for r in records),
        "initial_equity": max(r["initial"] for r in records),
        "daily_locked": any(r["daily_locked"] for r in current),
        "total_locked": any(r["total_locked"] for r in records),
    }


def legacy_prefix_attributable(prefixes, current_symbol_prefix):
    """Legacy names are usable only when the sole hash matches current scope."""
    return len(prefixes) == 1 and prefixes[0] == current_symbol_prefix


class AccountWideRiskCandidateTests(unittest.TestCase):
    def test_daily_rollover_uses_last_observed_equity_and_does_not_baseline_after_gap(self):
        rollover = RISK.split("if(today!=g_risk.last_day)", 1)[1].split(
            "double daily_loss_pct", 1
        )[0]
        self.assertIn("double rollover_baseline=g_risk.adaptive_last_equity;", rollover)
        self.assertIn("g_risk.start_of_day_equity=rollover_baseline;", rollover)
        self.assertIn("g_risk.persistence_ok=false;", rollover)
        self.assertNotIn("g_risk.start_of_day_equity=eq", rollover)

        # The expected baseline is the last persisted observation before the
        # unobserved closure. A 3% gap against a 2% daily limit must lock; using
        # first post-gap equity as its own baseline would incorrectly report 0%.
        self.assertEqual(daily_rollover_loss(1000.0, 970.0, 2.0), (3.0, True))
        self.assertEqual(daily_rollover_loss(1000.0, 990.0, 2.0), (1.0, False))
        self.assertIsNone(daily_rollover_loss(0.0, 970.0, 2.0))
        self.assertIsNone(daily_rollover_loss(float("nan"), 970.0, 2.0))

    def test_latest_equity_checkpoint_is_bounded_to_new_execution_bars(self):
        controller = (ROOT / "MQL5" / "Include" / "RiskController.mqh").read_text(
            encoding="utf-8-sig"
        )
        update = controller.split("bool RiskControllerUpdate(", 1)[1].split(
            "//+------------------------------------------------------------------+\n//| Piecewise-Linear", 1
        )[0]
        self.assertIn("static datetime g_last_equity_persist_bar=0;", controller)
        self.assertIn("observation_bar=iTime(g_cfg.symbol,g_cfg.tf_exec,0);", update)
        self.assertIn("observation_bar>g_last_equity_persist_bar", update)
        self.assertIn("g_risk.adaptive_last_equity=equity;", update)
        self.assertIn("if(high_water_changed || observation_bar_due)", update)
        persist = update.index("ok=RiskPersist(false);")
        advance = update.index("g_last_equity_persist_bar=observation_bar;", persist)
        self.assertLess(persist, advance)

        assert equity_checkpoint_due(500, 500, False) is False
        assert equity_checkpoint_due(500, 500, True) is True
        assert equity_checkpoint_due(500, 600, False) is True
        assert equity_checkpoint_due(600, 500, False) is False
        assert equity_checkpoint_due(0, 500, False) is True

    def test_cross_chart_wait_cannot_persist_prelock_equity_snapshot(self):
        controller = (ROOT / "MQL5" / "Include" / "RiskController.mqh").read_text(
            encoding="utf-8-sig"
        )
        update = controller.split("bool RiskControllerUpdate(", 1)[1].split(
            "//+------------------------------------------------------------------+\n//| Piecewise-Linear", 1
        )[0]
        acquire = update.index("if(!RiskAcquireAccountLock()) return false;")
        refresh = update.index("if(!RiskAccountRefresh())", acquire)
        equity_read = update.index("double equity=AccountInfoDouble(ACCOUNT_EQUITY);", refresh)
        self.assertLess(acquire, refresh)
        self.assertLess(refresh, equity_read)
        self.assertNotIn("RiskControllerUpdate(double", controller)

        evaluate = controller.split("AdaptiveRiskResult RiskControllerEvaluate(", 1)[1]
        update_call = evaluate.index("!RiskControllerUpdate()")
        refreshed_equity = evaluate.index("cur_eq=AccountInfoDouble(ACCOUNT_EQUITY);", update_call)
        self.assertLess(update_call, refreshed_equity)

        # A chart's $1,000 snapshot can become stale while waiting for the
        # shared lock. The ledger must store the $1,070 account value observed
        # after it acquires the lock, not overwrite it with that old snapshot.
        self.assertEqual(equity_after_lock(1000.0, 1070.0), 1070.0)

    def test_numeric_aggregate_counts_cross_symbol_positions_and_orders(self):
        # $1000 equity; existing positions $6+$4 and pending risk $3; new $7 => 2%.
        self.assertEqual(aggregate_risk_pct(1000, [6, 4], [3], 7), 2.0)

    def test_aggregate_above_ceiling_is_over_two_percent(self):
        self.assertGreater(aggregate_risk_pct(1000, [6, 4], [3], 7.01), 2.0)

    def test_account_risk_scan_covers_positions_and_pending_orders(self):
        self.assertIn("PositionsTotal()", ACCOUNT)
        self.assertIn("OrdersTotal()", ACCOUNT)
        self.assertIn("POSITION_MAGIC", ACCOUNT)
        self.assertNotIn("ORDER_MAGIC", ACCOUNT)  # Exposure covers every account order.
        self.assertIn("ORDER_PRICE_STOPLIMIT", ACCOUNT)
        self.assertIn("OrderCalcProfit", ACCOUNT)

    def test_unknown_exposure_fails_closed_at_sizing_and_send(self):
        self.assertIn("ACCOUNT_EXPOSURE_UNKNOWN:", ACCOUNT)
        self.assertIn("FINAL_ACCOUNT_EXPOSURE_UNKNOWN:", EXEC)
        self.assertIn("return false;", ACCOUNT[ACCOUNT.index("bool AccountEstimatedStopRisk"):ACCOUNT.index("//+------------------------------------------------------------------+\n//| Populate Account")])

    def test_aggregate_cap_applied_after_normalized_volume_and_again_before_send(self):
        self.assertIn("AccountVolumeFloorToStep(env.raw_volume,env.symbol_cap.volume_step)", ACCOUNT)
        self.assertLess(ACCOUNT.index("AccountVolumeFloorToStep(env.raw_volume"), ACCOUNT.index("AGGREGATE_AMIGO_STOP_RISK_ABOVE_2PCT"))
        self.assertIn("FINAL_AGGREGATE_AMIGO_STOP_RISK_ABOVE_2PCT", EXEC)
        self.assertIn("AMIGO_MAX_ESTIMATED_STOP_LOSS_PERCENT", ACCOUNT)
        self.assertIn("AMIGO_MAX_ESTIMATED_STOP_LOSS_PERCENT", EXEC)

    def test_opportunity_lock_is_account_server_scoped_across_magic_and_symbol(self):
        lock = RISK.split("string RiskOpportunityLockKey()", 1)[1].split("bool RiskLegacyAdmissionLocksClear", 1)[0]
        self.assertIn("ACCOUNT_SERVER", lock)
        self.assertNotIn("magic_number", lock)
        self.assertNotIn("g_cfg.symbol", lock)
        self.assertIn("GlobalVariableSetOnCondition", RISK)

    def test_expected_cross_chart_lock_contention_defers_without_latching_corruption(self):
        # The account lock is deliberately shared across symbols. A chart that
        # loses the compare-and-set race should skip this tick; ledger failures
        # still take the existing admission-quarantine path.
        acquire = RISK.split("bool RiskAcquireAccountLock()", 1)[1].split(
            "bool RiskReleaseAccountLock()", 1
        )[0]
        self.assertIn("g_risk_lock_contended=false;", acquire)
        self.assertIn("GlobalVariableSetOnCondition(key,token,0.0)", acquire)
        self.assertIn("g_risk_lock_contended=GlobalVariableCheck(key);", acquire)
        self.assertIn("bool RiskAccountLockWasContended()", RISK)

        tick = AMIGO.split("void OnTick()", 1)[1]
        first_defer = tick.index("!risk_update_ok && RiskAccountLockWasContended()")
        latch = tick.index("PositionManagerLatchStateFault(\"risk ledger update failed")
        self.assertLess(first_defer, latch)
        self.assertIn("if(risk_update_ok) risk_update_ok=RiskControllerUpdate();", tick)
        self.assertEqual(tick.count("!risk_update_ok && RiskAccountLockWasContended()"), 2)

    def test_margin_unavailable_or_invalid_data_rejects(self):
        self.assertFalse(margin_feasible(False, 10, 100))
        self.assertFalse(margin_feasible(True, 10, 0))
        self.assertFalse(margin_feasible(True, 10, float("nan")))
        self.assertFalse(margin_feasible(True, float("inf"), 100))
        self.assertTrue(margin_feasible(True, 95, 100))
        self.assertFalse(margin_feasible(True, 95.01, 100))

    def test_production_margin_path_has_no_leverage_fallback(self):
        block = ACCOUNT.split("//--- 9. Margin Verification", 1)[1].split("//--- 10. Final Action Resolution", 1)[0]
        self.assertIn("BROKER_MARGIN_CALCULATION_UNAVAILABLE", block)
        self.assertIn("ACCOUNT_FREE_MARGIN_INVALID", block)
        self.assertIn("MathIsValidNumber(margin_required)", block)
        self.assertIn("MathIsValidNumber(env.account.margin_free)", block)
        self.assertNotIn("Fallback margin estimate using leverage", block)
        self.assertNotIn("/ lev", block)

    def test_risk_controller_uses_first_legal_volume_step_for_minimum_risk(self):
        controller = (ROOT / "MQL5" / "Include" / "RiskController.mqh").read_text(encoding="utf-8-sig")
        self.assertIn("double minimum_valid_volume=AccountVolumeCeilToStep(vol_min,vol_step);", controller)
        self.assertIn("maximum_valid_volume<minimum_valid_volume", controller)
        self.assertIn("res.minimum_lot_loss = minimum_valid_volume * risk_per_lot;", controller)
        self.assertIn("AccountSymbolLossTickValue(symbol)", controller)

    def test_numeric_ledger_merge_oracle_chooses_conservative_day_baseline(self):
        today = date(2026, 11, 4)
        merged = merge_legacy_risk([
            {"day": today, "day_start": 1000, "peak": 1200, "initial": 900,
             "daily_locked": False, "total_locked": False, "uncertain": False},
            {"day": today, "day_start": 980, "peak": 1250, "initial": 950,
             "daily_locked": True, "total_locked": True, "uncertain": False},
            {"day": date(2026, 11, 3), "day_start": 850, "peak": 1300, "initial": 920,
             "daily_locked": True, "total_locked": False, "uncertain": False},
        ], today)
        self.assertEqual(merged, {"start_of_day_equity": 1000, "peak_equity": 1300,
                                  "initial_equity": 950, "daily_locked": True,
                                  "total_locked": True})
        # At equity 900, baseline 1000 exposes a 10% drawdown while 800 would
        # incorrectly report no daily loss; use the higher baseline.
        self.assertEqual((1000 - 900) / 1000 * 100, 10.0)
        self.assertLessEqual((800 - 900) / 800 * 100, 0.0)

    def test_legacy_ledger_merge_rejects_missing_day_future_and_uncertain_states(self):
        base = {"day": date(2026, 11, 3), "day_start": 1000, "peak": 1200,
                "initial": 900, "daily_locked": False, "total_locked": False,
                "uncertain": False}
        today = date(2026, 11, 4)
        with self.assertRaises(ValueError):
            merge_legacy_risk([base], today)
        future = dict(base, day=date(2026, 11, 5))
        with self.assertRaises(ValueError):
            merge_legacy_risk([future], today)
        uncertain = dict(base, day=today, uncertain=True)
        with self.assertRaises(ValueError):
            merge_legacy_risk([uncertain], today)

    def test_legacy_migration_rejects_unattributable_or_multiple_hashes(self):
        current = "AMR.123.7.456."
        self.assertTrue(legacy_prefix_attributable([current], current))
        self.assertFalse(legacy_prefix_attributable([], current))
        self.assertFalse(legacy_prefix_attributable(["AMR.123.7.999."], current))
        self.assertFalse(legacy_prefix_attributable([current, "AMR.123.7.999."], current))


if __name__ == "__main__":
    unittest.main()
