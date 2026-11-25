"""Offline reference and source-contract tests for final MQL execution preflight."""
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path
import math
import re
import unittest

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "MQL5" / "Include" / "Execution Engine.mqh").is_file())
EXECUTION = (ROOT / "MQL5" / "Include" / "Execution Engine.mqh").read_text(encoding="utf-8-sig")


def on_grid(value, step):
    value, step = Decimal(str(value)), Decimal(str(step))
    return value > 0 and step > 0 and value % step == 0


def volume_valid(volume, minimum, maximum, step):
    vals = (volume, minimum, maximum, step)
    if not all(math.isfinite(float(x)) for x in vals):
        return False
    volume, minimum, maximum, step = map(Decimal, map(str, vals))
    minimum_valid = ((minimum / step).to_integral_value(rounding=ROUND_CEILING) * step
                     if minimum > 0 and step > 0 else Decimal("0"))
    maximum_valid = (maximum / step).to_integral_value(rounding=ROUND_FLOOR) * step if step > 0 else Decimal("0")
    return (minimum > 0 and maximum >= minimum and minimum_valid <= volume <= maximum
            and maximum_valid >= minimum_valid and on_grid(volume, step))


def geometry_valid(direction, quote, stop, target, tick):
    if not all(math.isfinite(float(x)) and float(x) > 0 for x in (quote, stop, target, tick)):
        return False
    quote, stop, target, tick = map(Decimal, map(str, (quote, stop, target, tick)))
    if not all(on_grid(x, tick) for x in (quote, stop, target)):
        return False
    return stop < quote < target if direction == 1 else target < quote < stop if direction == -1 else False


def filling_policy(execution, fok, ioc):
    if execution not in {"REQUEST", "INSTANT", "MARKET", "EXCHANGE"}:
        return None
    if execution in {"REQUEST", "INSTANT"}:
        return "FOK"  # MQL5 permits these regardless of SYMBOL_FILLING_MODE.
    if fok:
        return "FOK"
    return None  # no cancellable full-fill policy: reject the entry


DEFINITIVE_REJECTION_CODES = {
    10004, 10006, 10007, 10013, 10014, 10015, 10016, 10017, 10018,
    10019, 10020, 10021, 10022, 10024, 10026, 10027, 10030, 10032,
    10033, 10034, 10035, 10040, 10041, 10042, 10043, 10044, 10045, 10046,
}


def classify_send_result(retcode):
    """Independent result oracle: only documented explicit refusals are retryable."""
    if retcode == 10009:
        return "FILLED"
    if retcode == 10010:
        return "UNCERTAIN_PARTIAL"
    if retcode == 10008:
        return "UNCERTAIN_PLACED"
    if retcode in DEFINITIVE_REJECTION_CODES:
        return "REJECTED"
    return "UNCERTAIN"


class ExecutionPreflightCandidate(unittest.TestCase):
    def test_volume_min_max_and_step_contract(self):
        self.assertTrue(volume_valid("0.09", "0.03", "0.10", "0.03"))
        self.assertFalse(volume_valid("0.10", "0.03", "0.10", "0.03"))
        self.assertFalse(volume_valid("0.02", "0.03", "1.00", "0.01"))
        self.assertFalse(volume_valid("0.05", "0.01", "1.00", "0.03"))
        self.assertTrue(volume_valid("0.03", "0.01", "0.10", "0.03"))
        self.assertFalse(volume_valid("0.06", "0.01", "0.05", "0.03"))

    def test_invalid_metadata_and_nonfinite_volume_fail_closed(self):
        self.assertFalse(volume_valid(float("nan"), 0.01, 1.0, 0.01))
        self.assertFalse(volume_valid(0.1, 0.01, 1.0, 0.0))
        self.assertFalse(volume_valid(0.1, 0.04, 0.10, 0.03))

    def test_refreshed_quote_geometry_and_tick_alignment(self):
        self.assertTrue(geometry_valid(1, "2000.25", "1999.75", "2001.00", "0.25"))
        self.assertFalse(geometry_valid(1, "2000.25", "2000.50", "2001.00", "0.25"))
        self.assertFalse(geometry_valid(-1, "2000.25", "1999.75", "2001.00", "0.25"))
        self.assertFalse(geometry_valid(1, "2000.10", "1999.75", "2001.00", "0.25"))

    def test_preflight_runs_before_profit_check_and_order_apis(self):
        execute = EXECUTION.split("ExecutionResult ExecuteIntent(", 1)[1]
        volume_gate = execute.index("ExecutionVolumeValid(ti.symbol,lots,preflight_reason)")
        quote_gate = execute.index("SymbolInfoTick(ti.symbol,execution_quote)")
        spread_gate = execute.index('r.comment="EXECUTION_SPREAD_LIMIT_EXCEEDED_OR_INVALID"')
        price_gate = execute.index("ExecutionPricesValid(ti.symbol,ti.direction,req.price,req.sl,req.tp,preflight_reason)")
        risk_calc = execute.index("OrderCalcProfit(req.type")
        check = execute.index("OrderCheck(req, chk)")
        send = execute.index("OrderSend(req, res)")
        self.assertLess(volume_gate, risk_calc)
        self.assertLess(quote_gate, spread_gate)
        self.assertLess(spread_gate, price_gate)
        self.assertLess(price_gate, risk_calc)
        self.assertLess(risk_calc, check)
        self.assertLess(check, send)
        self.assertIn("AMIGO_LIVE_EXECUTION_READY==0", execute)

    def test_source_rejects_volume_or_price_grid_failures(self):
        self.assertIn('reason="REQUEST_VOLUME_OUTSIDE_BROKER_GRID"', EXECUTION)
        self.assertIn('reason="BROKER_VOLUME_METADATA_INVALID"', EXECUTION)
        self.assertIn('reason="REQUEST_PRICE_TICK_GRID_INVALID"', EXECUTION)
        self.assertIn('reason="REQUEST_GEOMETRY_CROSSED_CURRENT_QUOTE"', EXECUTION)
        self.assertIn('r.comment="EXECUTION_QUOTE_UNAVAILABLE_OR_STALE"', EXECUTION)
        self.assertIn("ExecutionVolumeCeilToStep(minimum,step)", EXECUTION)
        self.assertIn("volume<minimum_valid-volume_tolerance", EXECUTION)
        floor_helper = EXECUTION.split("double ExecutionVolumeFloorToStep(", 1)[1].split("bool ExecutionVolumeValid(", 1)[0]
        self.assertIn("!MathIsValidNumber(steps)", floor_helper)

    def test_market_entries_require_full_fill_or_reject(self):
        self.assertEqual(filling_policy("REQUEST", False, False), "FOK")
        self.assertEqual(filling_policy("INSTANT", False, False), "FOK")
        self.assertEqual(filling_policy("MARKET", True, False), "FOK")
        self.assertIsNone(filling_policy("MARKET", False, False))
        self.assertIsNone(filling_policy("MARKET", False, True))
        self.assertEqual(filling_policy("EXCHANGE", True, False), "FOK")
        self.assertIsNone(filling_policy("EXCHANGE", False, True))
        self.assertIsNone(filling_policy("EXCHANGE", False, False))
        self.assertIsNone(filling_policy("UNKNOWN", True, False))
        helper = EXECUTION.split("bool ExecutionSelectFilling(", 1)[1].split("\n}", 1)[0]
        helper_code = re.sub(r"//[^\n]*", "", helper)
        self.assertIn("execution==SYMBOL_TRADE_EXECUTION_REQUEST", helper)
        self.assertIn("execution==SYMBOL_TRADE_EXECUTION_INSTANT", helper)
        self.assertIn('reason="NO_SUPPORTED_FULL_FILL_POLICY"', helper)
        self.assertNotIn("ORDER_FILLING_RETURN", helper_code)
        self.assertNotIn("ORDER_FILLING_IOC", helper_code)
        self.assertIn("execution!=SYMBOL_TRADE_EXECUTION_MARKET", helper)
        self.assertIn('reason="TRADE_EXECUTION_MODE_UNKNOWN"', helper)
        execute = EXECUTION.split("ExecutionResult ExecuteIntent(", 1)[1]
        self.assertLess(execute.index("ExecutionSelectFilling("), execute.index("OrderCheck(req, chk)"))

    def test_order_send_unclassified_results_are_quarantined(self):
        # Expected categories are derived from the MQL5 server-code meanings:
        # DONE is complete; PLACED and PARTIAL require reconciliation; explicit
        # request refusals are no-fill; transport/processing/new codes are unknown.
        self.assertEqual(classify_send_result(10009), "FILLED")
        self.assertEqual(classify_send_result(10008), "UNCERTAIN_PLACED")
        self.assertEqual(classify_send_result(10010), "UNCERTAIN_PARTIAL")
        self.assertEqual(classify_send_result(10006), "REJECTED")
        for retcode in (10011, 10012, 10028, 10031, 10099):
            self.assertEqual(classify_send_result(retcode), "UNCERTAIN")

        recon=(ROOT / "MQL5" / "Include" / "TransactionRecon.mqh").read_text()
        self.assertIn("return ReconRetcodeIsDefinitiveRejection(retcode);", EXECUTION)
        helper = recon.split("bool ReconRetcodeIsDefinitiveRejection(", 1)[1].split("\n}", 1)[0]
        for constant in ("TRADE_RETCODE_REJECT", "TRADE_RETCODE_INVALID_STOPS",
                         "TRADE_RETCODE_MARKET_CLOSED", "TRADE_RETCODE_HEDGE_PROHIBITED"):
            self.assertIn(constant, helper)
        for ambiguous in ("TRADE_RETCODE_ERROR", "TRADE_RETCODE_TIMEOUT",
                          "TRADE_RETCODE_LOCKED", "TRADE_RETCODE_CONNECTION"):
            self.assertNotIn(ambiguous, helper)

        execute = EXECUTION.split("ExecutionResult ExecuteIntent(", 1)[1]
        classified = execute.index("ExecutionRetcodeIsDefinitiveRejection(res.retcode)")
        uncertain = execute.index("r.outcome_uncertain=true;", classified)
        self.assertLess(classified, uncertain)
        self.assertIn('"ORDERSEND_OUTCOME_UNCLASSIFIED:', execute[classified:])


class IntentBoundarySourceTests(unittest.TestCase):
    def test_intent_is_validated_before_broker_metadata_or_submission(self):
        execute = EXECUTION.split("ExecutionResult ExecuteIntent(", 1)[1]
        validate = execute.index("ValidateIntent(ti,cfg,preflight_reason)")
        self.assertLess(validate, execute.index("ExecutionVolumeValid("))
        self.assertIn("return r;", execute[validate:execute.index("ExecutionVolumeValid(")])

    def test_horizon_and_nonfinite_prices_fail_closed(self):
        validate = EXECUTION.split("bool ValidateIntent(", 1)[1].split("bool ExecutionDealMatchesIntent(", 1)[0]
        for horizon in ("SCALPING", "INTRADAY", "SWING"):
            self.assertIn("ti.horizon!=HORIZON_" + horizon, validate)
        self.assertIn('reason="INVALID_HORIZON";', validate)
        for price in ("entry_reference", "stop", "target"):
            self.assertIn("!MathIsValidNumber(ti." + price + ")", validate)
        self.assertIn('reason="INVALID_INTENT_PRICE";', validate)


if __name__ == "__main__":
    unittest.main()
