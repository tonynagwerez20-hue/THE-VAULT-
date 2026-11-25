"""Offline source-contract regressions for the current AMIGO candidate.

These tests do not compile or execute MQL5 and do not prove terminal durability,
broker behavior, or MQL5 parity. Small state-machine examples are independent
oracles for the stated at-most-once and exposure contracts.
"""
from pathlib import Path
import unittest

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "MQL5" / "Experts" / "AMIGO.mq5").is_file())
AMIGO = (ROOT / "MQL5" / "Experts" / "AMIGO.mq5").read_text(encoding="utf-8-sig")
RISK = (ROOT / "MQL5" / "Include" / "Risk Engine.mqh").read_text(encoding="utf-8-sig")
RISK_CONTROLLER = (ROOT / "MQL5" / "Include" / "RiskController.mqh").read_text(encoding="utf-8-sig")
ACCOUNT_EXECUTION = (ROOT / "MQL5" / "Include" / "Account Execution Engine.mqh").read_text(encoding="utf-8-sig")
EXECUTION = (ROOT / "MQL5" / "Include" / "Execution Engine.mqh").read_text(encoding="utf-8-sig")
FEATURE = (ROOT / "MQL5" / "Include" / "FeatureVector.mqh").read_text(encoding="utf-8-sig")
RECOVERY = (ROOT / "MQL5" / "Include" / "PositionRecovery.mqh").read_text(encoding="utf-8-sig")
MANAGER = (ROOT / "MQL5" / "Include" / "Position Manager.mqh").read_text(encoding="utf-8-sig")
TRANSACTION = (ROOT / "MQL5" / "Include" / "TransactionRecon.mqh").read_text(encoding="utf-8-sig")


def admit_estimated_loss(equity, loss):
    """Independent oracle for the explicit 2% estimated-loss ceiling."""
    return equity > 0 and loss > 0 and loss / equity <= 0.02


def opportunity_state(previous_bar, previous_outcome, new_bar):
    """Independent model: only completed prior opportunities admit a later bar."""
    if previous_outcome in (1, 5) or new_bar <= previous_bar:
        return "BLOCK"
    return "RESERVE"


def score_inputs_valid(threshold, margin):
    """Score values are fractions; zero gates can permit a zero-score tie."""
    import math
    return (math.isfinite(threshold) and 0.0 < threshold <= 1.0
            and math.isfinite(margin) and 0.0 < margin <= 1.0)


def partial_inputs_valid(partial_rr, partial_fraction):
    import math
    return (math.isfinite(partial_rr) and partial_rr > 0.0
            and math.isfinite(partial_fraction) and 0.0 < partial_fraction < 1.0)


def trailing_inputs_valid(mode, atr_mult, activate_r):
    import math
    if mode not in (0, 1, 2):  # OFF, implemented dynamic 25%, ATR
        return False
    return mode != 2 or (math.isfinite(atr_mult) and atr_mult > 0.0
                         and math.isfinite(activate_r) and activate_r > 0.0)


def interleaved_mutex_outcomes(initializer_resets_existing):
    """Model the critical schedule where two charts observe a missing key."""
    value = None
    chart_a_saw_missing = chart_b_saw_missing = value is None
    if chart_a_saw_missing:
        value = 0  # create or unsafe set(0)
    acquired_a = value == 0
    if acquired_a:
        value = "A"
    if chart_b_saw_missing:
        if initializer_resets_existing or value is None:
            value = 0
        # create-once leaves A's token intact when B races after A acquired.
    acquired_b = value == 0
    if acquired_b:
        value = "B"
    return acquired_a, acquired_b


def deal_matches_intent(deal, intent):
    """Independent identity oracle; only an exact fresh-entry match is valid."""
    return (deal["magic"] == intent["magic"]
            and deal["symbol"] == intent["symbol"]
            and deal["direction"] == intent["direction"]
            and deal["entry"] == "IN"
            and deal["order"] > 0
            and intent["order"] > 0
            and deal["order"] == intent["order"])


def independent_position_checksum(values):
    """Independent arithmetic oracle for the documented 31-bit record hash."""
    modulus = 2_147_483_647
    state = 146_959_810
    for value in values:
        state = (state * 16_777_619 + value % modulus) % modulus
    return state


def call_is_inside_shadow_guard(source, call_pos):
    guard_pos = source.rfind("if(!cfg.shadow_only)", 0, call_pos)
    if guard_pos < 0:
        return False
    open_brace = source.find("{", guard_pos, call_pos)
    if open_brace < 0:
        return False
    depth = 0
    for pos in range(open_brace, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return call_pos < pos
    return False


class CriticalRemediationCandidate(unittest.TestCase):
    def test_unimplemented_trailing_modes_fail_startup_instead_of_silent_no_trail(self):
        self.assertIn("AMIGOTrailingInputsValid(InpTrailMode,InpTrailATRMult,InpTrailActivateR)", AMIGO)
        validator = AMIGO.split("bool AMIGOTrailingInputsValid(", 1)[1].split("}\n", 1)[0]
        for mode in ("TRAIL_OFF", "TRAIL_DYNAMIC_25_PERCENT", "TRAIL_ATR"):
            self.assertIn(f"mode!={mode}", validator)
        for mode in ("TRAIL_STRUCTURE", "TRAIL_ATR_PLUS_STRUCTURE"):
            self.assertNotIn(mode, validator)
        manager = MANAGER.split("void PositionManagerTick(", 1)[1]
        self.assertIn("g_positions[i].trailing_mode == TRAIL_DYNAMIC_25_PERCENT", manager)
        self.assertIn("g_positions[i].trailing_mode == TRAIL_ATR", manager)

        self.assertTrue(trailing_inputs_valid(0, float("nan"), float("nan")))
        self.assertTrue(trailing_inputs_valid(1, float("nan"), float("nan")))
        self.assertTrue(trailing_inputs_valid(2, 1.5, 1.0))
        self.assertFalse(trailing_inputs_valid(3, 1.5, 1.0))
        self.assertFalse(trailing_inputs_valid(4, 1.5, 1.0))
        self.assertFalse(trailing_inputs_valid(2, 0.0, 1.0))
        self.assertFalse(trailing_inputs_valid(2, 1.5, float("inf")))

    def test_partial_lifecycle_configuration_rejects_invalid_fraction(self):
        self.assertIn("AMIGOPartialInputsValid(InpPartialRR,InpPartialFraction)", AMIGO)
        validator = AMIGO.split("bool AMIGOPartialInputsValid(", 1)[1].split("}\n", 1)[0]
        self.assertIn("MathIsValidNumber(partial_rr) && partial_rr>0.0", validator)
        self.assertIn("MathIsValidNumber(partial_fraction) && partial_fraction>0.0 && partial_fraction<1.0", validator)
        init = AMIGO.split("int OnInit()", 1)[1].split("void OnDeinit", 1)[0]
        self.assertLess(init.index("AMIGOPartialInputsValid"), init.index("RiskInit("))

        self.assertTrue(partial_inputs_valid(2.0, 0.5))
        for values in ((0.0, 0.5), (-1.0, 0.5), (2.0, 0.0),
                       (2.0, 1.0), (2.0, 1.1), (float("nan"), 0.5),
                       (2.0, float("inf"))):
            with self.subTest(values=values):
                self.assertFalse(partial_inputs_valid(*values))

    def test_score_configuration_rejects_zero_nonfinite_and_out_of_range_gates(self):
        self.assertIn("AMIGOScoreInputsValid(InpScoreThreshold,InpScoreMargin)", AMIGO)
        validator = AMIGO.split("bool AMIGOScoreInputsValid(", 1)[1].split("}\n", 1)[0]
        self.assertIn("MathIsValidNumber(score_threshold)", validator)
        self.assertIn("MathIsValidNumber(score_margin)", validator)
        self.assertIn("score_threshold>0.0 && score_threshold<=1.0", validator)
        self.assertIn("score_margin>0.0 && score_margin<=1.0", validator)
        init = AMIGO.split("int OnInit()", 1)[1].split("void OnDeinit", 1)[0]
        self.assertLess(init.index("AMIGOScoreInputsValid"), init.index("RiskInit("))
        self.assertIn("INIT_PARAMETERS_INCORRECT", init)

        self.assertTrue(score_inputs_valid(0.35, 0.05))
        self.assertTrue(score_inputs_valid(1.0, 1.0))
        for values in ((0.0, 0.05), (0.35, 0.0), (-0.1, 0.05),
                       (0.35, 1.1), (float("nan"), 0.1), (0.1, float("inf"))):
            with self.subTest(values=values):
                self.assertFalse(score_inputs_valid(*values))

    def test_transaction_commit_follows_final_execution_and_registration(self):
        on_closed = AMIGO.split("int OnClosedBar(", 1)[1].split("void OnTradeTransaction(", 1)[0]
        commit = on_closed.rindex("g_snap = candidate_snap;")
        self.assertGreater(commit, on_closed.index("ExecutionResult er = ExecuteIntent"))
        self.assertGreater(commit, on_closed.index("PositionManagerRegister(er.position_id"))
        self.assertGreater(commit, on_closed.index("if(!PositionManagerAdmissionAllowed())"))
        self.assertNotIn("WriteSnapshotForExternal", on_closed[:on_closed.index("StrategyScores ss")])

    def test_failed_stages_return_without_mutating_accepted_snapshot(self):
        on_closed = AMIGO.split("int OnClosedBar(", 1)[1].split("void OnTradeTransaction(", 1)[0]
        commit = on_closed.rindex("g_snap = candidate_snap;")
        for gate in ("if(!snap_res)", "if(!feat_res)", "if(!EvaluateTopDownContext", "if(!RiskAllows", "if(acc_env.final_action != ACTION_TRADE)"):
            if gate in on_closed:
                self.assertLess(on_closed.index(gate), commit)
        self.assertIn("return RISK_OP_REJECTED;", on_closed[:commit])

    def test_consumed_identity_is_reserved_before_decision_and_persisted(self):
        tick = AMIGO.split("void OnTick()", 1)[1].split("int OnClosedBar(", 1)[0]
        self.assertLess(tick.index("RiskBeginOpportunity(bar_time,opportunity_id)"), tick.index("OnClosedBar(opportunity_id)"))
        self.assertGreater(tick.index("RiskCompleteOpportunity(outcome)"), tick.index("OnClosedBar(opportunity_id)"))
        self.assertIn("last_opportunity_bar", RISK)
        self.assertIn("GlobalVariableSetOnCondition", RISK)
        self.assertIn("RISK_OP_RESERVED", RISK)
        self.assertIn("OPPORTUNITY_RECOVERY_AMBIGUOUS", RISK)

    def test_repeated_and_ambiguous_opportunities_block_in_independent_oracle(self):
        self.assertEqual(opportunity_state(100, 3, 100), "BLOCK")
        self.assertEqual(opportunity_state(100, 3, 99), "BLOCK")
        self.assertEqual(opportunity_state(100, 1, 101), "BLOCK")
        self.assertEqual(opportunity_state(100, 5, 101), "BLOCK")
        self.assertEqual(opportunity_state(100, 3, 101), "RESERVE")

    def test_risk_references_are_loaded_not_reset_on_restart(self):
        init = RISK.split("bool RiskInitLocked(", 1)[1].split("bool RiskInit(", 1)[0]
        controller_init = RISK_CONTROLLER.split("bool RiskControllerInit", 1)[1].split("bool RiskControllerUpdate", 1)[0]
        self.assertIn("RiskLedgerSlotRead", init)
        self.assertIn("RiskLegacyAggregate", init)
        self.assertIn("if(legacy_count<0 || legacy_count>0 || !allow_explicit_bootstrap) return false;", init)
        self.assertIn("g_risk.initial_equity", controller_init)
        self.assertNotIn("high_water_equity    = equity", controller_init)
        self.assertIn("GlobalVariablesFlush", RISK)

    def test_account_drawdown_ledger_is_shared_but_opportunity_state_is_per_symbol(self):
        account_prefix = RISK.split("string RiskAccountLedgerPrefix()", 1)[1].split("string RiskOpportunityLockKey", 1)[0]
        symbol_prefix = RISK.split("string RiskLedgerPrefix()", 1)[1].split("string RiskAccountLedgerPrefix", 1)[0]
        self.assertIn("ACCOUNT_SERVER", account_prefix)
        self.assertIn("magic_number", account_prefix)
        self.assertNotIn("g_cfg.symbol", account_prefix)
        self.assertIn("g_cfg.symbol", symbol_prefix)
        self.assertIn("RiskServerDayBoundary", RISK)
        self.assertIn("RiskCopyAccountFields(g_risk,latest)", RISK)
        self.assertIn("account_state.last_opportunity_bar=0", RISK)
        self.assertIn("if(!RiskAcquireAccountLock()) return false;", RISK)

    def test_account_risk_ledger_is_bound_to_currency_modes_and_contract_version(self):
        identity = RISK.split("double RiskAccountIdentityCode()", 1)[1].split("bool RiskAccountSlotIdentityValid", 1)[0]
        marker = RISK.split("bool RiskAccountSlotIdentityValid", 1)[1].split("string RiskLedgerPrefix", 1)[0]
        persist = RISK.split("bool RiskPersistAccount()", 1)[1].split("bool RiskPersist(", 1)[0]
        self.assertIn("ACCOUNT_CURRENCY", identity)
        self.assertIn("ACCOUNT_MARGIN_MODE", identity)
        self.assertIn("ACCOUNT_TRADE_MODE", identity)
        self.assertIn("Amigo_RISK_STATE_POLICY_VERSION", identity)
        self.assertIn('prefix+slot+".XG"', marker)
        self.assertIn("actual_generation==(double)generation", marker)
        self.assertIn('target+".XG"', persist)
        self.assertIn("GlobalVariablesFlush()", persist)
        # The generation tag binds metadata to a committed ledger slot.
        self.assertIn('prefix+target+".XG",(double)account_state.generation', persist)

    def test_account_mutex_initializer_never_resets_an_existing_owner(self):
        acquire = RISK.split("bool RiskAcquireAccountLock()", 1)[1].split("bool RiskReleaseAccountLock", 1)[0]
        lock_key = RISK.split("string RiskOpportunityLockKey()", 1)[1].split("bool RiskAcquireAccountLock", 1)[0]
        self.assertIn("GlobalVariableTemp(key)", acquire)
        self.assertNotIn("GlobalVariableSet(key,0.0)", acquire)
        self.assertIn(".M3", lock_key)
        self.assertIn("GlobalVariableSetOnCondition(key,token,0.0)", acquire)
        self.assertEqual(interleaved_mutex_outcomes(True), (True, True))
        self.assertEqual(interleaved_mutex_outcomes(False), (True, False))

    def test_legacy_account_risk_migration_uses_conservative_merge_and_blocks_ambiguity(self):
        aggregate = RISK.split("bool RiskLegacyAggregate(", 1)[1].split("bool RiskInitLocked", 1)[0]
        self.assertIn("if(count!=1) return false;", aggregate)
        self.assertIn("if(prefixes[0]!=current_symbol_prefix) return false;", aggregate)
        self.assertIn("MathMax(max_day_equity,state.start_of_day_equity)", aggregate)
        self.assertIn("MathMax(account_state.peak_equity,state.peak_equity)", aggregate)
        self.assertIn("MathMax(account_state.adaptive_high_water,state.adaptive_high_water)", aggregate)
        self.assertIn("account_state.total_locked=(account_state.total_locked", aggregate)
        self.assertIn("state.last_opportunity_outcome==RISK_OP_UNCERTAIN", aggregate)
        self.assertIn("if(!any || !any_today", aggregate)
        self.assertIn("Old ambiguous intents cannot be automatically attributed", RISK)

    def test_shared_risk_updates_refresh_account_state_without_overwriting_symbol_opportunity(self):
        begin = RISK.split("bool RiskBeginOpportunity(", 1)[1].split("bool RiskCompleteOpportunity", 1)[0]
        tick = RISK.split("bool RiskTick(", 1)[1].split("bool RiskAllows", 1)[0]
        controller = RISK_CONTROLLER.split("bool RiskControllerUpdate", 1)[1].split("double InterpolateRiskCurve", 1)[0]
        self.assertLess(begin.index("RiskAccountRefresh()"), begin.index("RiskSymbolRefresh()"))
        self.assertLess(begin.index("RiskSymbolRefresh()"), begin.rindex("boundary<=g_risk.last_opportunity_bar"))
        self.assertIn("RiskPersist(false)", tick)
        self.assertIn("RiskPersist(false)", controller)
        self.assertIn("RiskServerDayBoundary()", tick)
        self.assertNotIn("iTime(g_cfg.symbol,PERIOD_D1,0)", tick)

    def test_risk_recovery_failure_blocks_entries_but_does_not_skip_position_recovery(self):
        on_init = AMIGO.split("int OnInit()", 1)[1].split("void OnDeinit", 1)[0]
        on_tick = AMIGO.split("void OnTick()", 1)[1].split("int OnClosedBar(", 1)[0]
        self.assertIn("bool risk_state_ready=RiskInit", on_init)
        self.assertNotIn("return INIT_FAILED;", on_init[on_init.index("bool risk_state_ready=RiskInit"):on_init.index("int recovery_status=PositionReconcileState")])
        self.assertIn("PositionReconcileState(g_cfg)", on_init)
        self.assertLess(on_init.index("PositionReconcileState(g_cfg)"), on_init.index("EventSetTimer(5)"))
        self.assertLess(on_tick.index("if(!g_risk_admission_ready) return;"), on_tick.index("RiskTick()"))
        self.assertIn("bool            g_risk_admission_ready = false;", AMIGO)

    def test_required_lifecycle_timer_failure_prevents_successful_initialization(self):
        # Source-contract evidence only: EventSetTimer itself is not executed.
        on_init = AMIGO.split("int OnInit()", 1)[1].split("void OnDeinit", 1)[0]
        failure = on_init.split("if(!EventSetTimer(5))", 1)[1].split("}", 1)[0]
        self.assertIn("g_risk_admission_ready=false;", failure)
        self.assertIn("return INIT_FAILED;", failure)
        self.assertIn("GetLastError()", failure)
        self.assertLess(on_init.index("if(!EventSetTimer(5))"), on_init.index("return INIT_SUCCEEDED;"))
        timer = AMIGO.split("void OnTimer()", 1)[1]
        self.assertIn("PositionManagerTick(g_cfg);", timer)

    def test_existing_account_ledger_allows_new_symbol_opportunity_state_without_reset(self):
        init = RISK.split("bool RiskInitLocked(", 1)[1].split("bool RiskInit(", 1)[0]
        self.assertIn("bool account_ledger_found=(account_va || account_vb);", init)
        self.assertIn("if(!symbol_found && !allow_explicit_bootstrap && !account_ledger_found) return false;", init)
        self.assertIn("if(account_ledger_found)", init)
        self.assertIn("RiskCopyAccountFields(g_risk,account_state);", init)
        # Existing account ledger permits a fresh symbol record; without either
        # account state or explicit baseline authorization, admission is denied.
        def may_seed_symbol(account_valid, explicit_bootstrap):
            return account_valid or explicit_bootstrap
        self.assertTrue(may_seed_symbol(True, False))
        self.assertFalse(may_seed_symbol(False, False))
        self.assertTrue(may_seed_symbol(False, True))

    def test_missing_broker_risk_metadata_fails_closed(self):
        self.assertIn('res.reason="INVALID_BROKER_RISK_METADATA";', RISK_CONTROLLER)
        self.assertNotIn("if(vol_min <= 0.0) vol_min = 0.01;", RISK_CONTROLLER)

    def test_order_placed_is_uncertain_and_fill_identity_comes_from_deal(self):
        placed = EXECUTION.index("if(res.retcode == TRADE_RETCODE_PLACED)")
        done = EXECUTION.index("if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_DONE_PARTIAL)")
        self.assertLess(placed, done)
        placed_block = EXECUTION[placed:done]
        self.assertIn("ExecutionCancelPlacedOrder(r.order_ticket,ti.symbol,req.magic)", placed_block)
        self.assertIn('r.comment = "ORDER_PLACED_UNCONFIRMED:"+cancel_status;', placed_block)
        self.assertIn("r.outcome_uncertain = true;", placed_block)
        self.assertNotIn("r.accepted = true;", placed_block)
        cancel = EXECUTION.split("string ExecutionCancelPlacedOrder(", 1)[1].split("struct ExecutionResult", 1)[0]
        self.assertLess(cancel.index("OrderSelect(ticket)"), cancel.index("g_trade.OrderDelete(ticket)"))
        self.assertIn("active_symbol!=symbol || active_magic!=magic", cancel)
        self.assertIn("CANCEL_UNCONFIRMED_CALL=", cancel)
        self.assertIn("CANCEL_ACCEPTED_OUTCOME_STILL_UNCERTAIN", cancel)
        fill_block = EXECUTION[done:]
        self.assertIn("HistoryDealGetInteger(r.deal_ticket, DEAL_POSITION_ID)", fill_block)
        self.assertNotIn("PositionSelect(ti.symbol)", fill_block)
        self.assertIn("if(er.outcome_uncertain)", AMIGO)
        self.assertIn("ExecutionHasManagedWorkingOrder(g_cfg)", AMIGO)
        matcher = EXECUTION.split("bool ExecutionDealMatchesIntent(", 1)[1].split("ExecutionResult ExecuteIntent(", 1)[0]
        for field in ("DEAL_MAGIC", "DEAL_SYMBOL", "DEAL_TYPE", "DEAL_ENTRY", "DEAL_ORDER", "expected_order==0"):
            self.assertIn(field, matcher)
        self.assertLess(EXECUTION.index("ExecutionDealMatchesIntent(r.deal_ticket"),
                        EXECUTION.index("r.accepted = true;"))
        valid_intent = {"magic": 7, "symbol": "XAUUSD", "direction": "BUY", "order": 101}
        valid_deal = {"magic": 7, "symbol": "XAUUSD", "direction": "BUY", "entry": "IN", "order": 101}
        self.assertTrue(deal_matches_intent(valid_deal, valid_intent))
        self.assertFalse(deal_matches_intent(valid_deal, dict(valid_intent, order=0)))
        for change in ({"magic": 9}, {"symbol": "EURUSD"}, {"direction": "SELL"},
                       {"entry": "INOUT"}, {"order": 102}, {"order": 0}):
            self.assertFalse(deal_matches_intent(dict(valid_deal, **change), valid_intent))
        failed_send = EXECUTION.split("if(!send_ok)", 1)[1].split("r.retcode      = res.retcode", 1)[0]
        self.assertIn("r.outcome_uncertain = true;", failed_send)

    def test_confirmed_partial_fill_is_managed_before_quarantine(self):
        partial = EXECUTION.split("if(res.retcode==TRADE_RETCODE_DONE_PARTIAL", 1)[1].split("else\n      {\n         r.comment", 1)[0]
        self.assertIn("r.outcome_uncertain=true;", partial)
        self.assertIn("PARTIAL_FILL_REQUIRES_RECONCILIATION", partial)
        self.assertIn("HistoryDealGetDouble(r.deal_ticket,DEAL_PRICE)", EXECUTION)
        self.assertIn("HistoryDealGetDouble(r.deal_ticket,DEAL_VOLUME)", EXECUTION)
        self.assertIn("response_mismatch", EXECUTION)
        on_closed = AMIGO.split("int OnClosedBar(", 1)[1].split("void OnTradeTransaction(", 1)[0]
        uncertain = on_closed.index("if(er.outcome_uncertain)")
        register = on_closed.index("PositionManagerRegister(er.position_id", uncertain)
        quarantine = on_closed.index("PositionManagerLatchStateFault(\"execution outcome is uncertain", uncertain)
        self.assertLess(register, quarantine)

    def test_confirmed_live_fill_requires_visible_position_and_aggregate_risk_before_commit(self):
        on_closed = AMIGO.split("int OnClosedBar(", 1)[1].split("void OnTradeTransaction(", 1)[0]
        commit = on_closed.rindex("g_snap = candidate_snap;")
        visible = on_closed.index("AccountManagedPositionVisible(er.position_id")
        risk_check = on_closed.index("AccountEstimatedStopRisk(reconciled_stop_risk")
        manager_registration = on_closed.rindex("PositionManagerRegister(er.position_id")
        self.assertLess(visible, risk_check)
        self.assertLess(visible, manager_registration)
        self.assertLess(manager_registration, risk_check)
        self.assertLess(risk_check, commit)
        self.assertIn("return RISK_OP_UNCERTAIN;", on_closed[visible:commit])

    def test_uncertain_order_stays_quarantined_and_reconciler_gap_is_explicit(self):
        self.assertIn("PositionManagerLatchStateFault(\"execution outcome is uncertain", AMIGO)
        self.assertIn("return RISK_OP_UNCERTAIN;", AMIGO)
        on_closed = AMIGO.split("int OnClosedBar(", 1)[1].split("void OnTradeTransaction(", 1)[0]
        self.assertLess(on_closed.index("if(er.outcome_uncertain)"),
                        on_closed.index("if(!er.accepted && !g_cfg.shadow_only)"))
        self.assertLess(on_closed.index("PositionManagerLatchStateFault(\"execution outcome is uncertain"),
                        on_closed.index("if(!er.accepted && !g_cfg.shadow_only)"))
        self.assertIn('LogMsg(LOG_ERROR,"EXEC_UNCERTAIN"', on_closed)
        self.assertIn("er.order_ticket,er.deal_ticket,er.retcode,er.comment", on_closed)
        self.assertIn("OnTradeTransaction(", AMIGO)
        self.assertIn("does NOT currently resolve an uncertain intent", TRANSACTION)
        self.assertNotIn("PositionManagerRegister", TRANSACTION)
        request_case = TRANSACTION.split("case TRADE_TRANSACTION_REQUEST:", 1)[1].split("default:", 1)[0]
        for field in ("request.comment", "request.magic", "result.request_id", "result.order", "result.deal"):
            self.assertIn(field, request_case)

    def test_position_recovery_does_not_infer_break_even_from_stop(self):
        self.assertNotIn("Restoring be_activated=true", RECOVERY)
        self.assertIn("does not prove AMIGO confirmed the", RECOVERY)

    def test_actual_fill_volume_is_registered_and_versioned_for_recovery(self):
        self.assertIn("double             initial_volume;", MANAGER)
        self.assertIn("double             current_volume;", MANAGER)
        self.assertIn("er.fill_volume,\n                                 dr.direction", AMIGO)
        self.assertIn("g_positions[i].current_volume = remaining_volume", MANAGER)
        self.assertIn("AMIGO_STATE_SCHEMA_VERSION 106", RECOVERY)
        self.assertIn("AMIGO_STATE_SCHEMA_LEGACY   104", RECOVERY)
        self.assertIn("FileWriteDouble(handle, g_positions[i].initial_volume)", RECOVERY)
        self.assertIn("FileWriteDouble(handle, g_positions[i].current_volume)", RECOVERY)

    def test_position_recovery_state_is_account_server_symbol_scoped(self):
        self.assertIn("PositionStatePaths(cfg,primary,temp,login,server_hash,symbol_hash,", RECOVERY)
        self.assertIn("ACCOUNT_LOGIN", RECOVERY)
        self.assertIn("ACCOUNT_SERVER", RECOVERY)
        self.assertIn("cfg.symbol", RECOVERY)
        self.assertIn("saved_login!=identity_login", RECOVERY)
        self.assertIn("saved_server_hash!=identity_server_hash", RECOVERY)
        self.assertIn("saved_symbol_hash!=identity_symbol_hash", RECOVERY)
        self.assertIn("if(PositionStateLegacyPresent())", RECOVERY)
        self.assertIn("ownership is ambiguous and recovery is blocked", RECOVERY)
        self.assertIn("AMIGO_STATE_HEADER_BYTES   76", RECOVERY)
        self.assertIn("ACCOUNT_CURRENCY", RECOVERY)
        self.assertIn("ACCOUNT_MARGIN_MODE", RECOVERY)
        self.assertIn("ACCOUNT_TRADE_MODE", RECOVERY)
        self.assertIn("saved_config_version!=identity_config_version", RECOVERY)
        self.assertIn("if(schema!=AMIGO_STATE_SCHEMA_VERSION)", RECOVERY)
        self.assertIn("Explicit recovery is required; admission blocked", RECOVERY)
        init = AMIGO.split("int OnInit()", 1)[1].split("void OnDeinit", 1)[0]
        recovery = init.index("int recovery_status=PositionReconcileState(g_cfg)")
        blocked = init.index("if(recovery_status<0)")
        self.assertLess(recovery, blocked)
        self.assertIn("return INIT_FAILED;", init[blocked:init.index("EventSetTimer(5)")])

    def test_position_state_checksum_vector_and_corruption_detection_contract(self):
        vector = [123456789, -1, 2000500000, 2010000000, 1980000000,
                  5000000, 10000000, 0, 2010000000, 0, 1990000000,
                  2010000000, 1, 2, 1790000000, 3, 120000, 120000]
        expected = 1326536074
        self.assertEqual(independent_position_checksum(vector), expected)
        corrupted = list(vector)
        corrupted[16] += 10000
        self.assertNotEqual(independent_position_checksum(corrupted), expected)
        self.assertIn("PositionStateRecordChecksum(p)", RECOVERY)
        self.assertIn("saved_record_checksum!=PositionStateRecordChecksum(p)", RECOVERY)
        self.assertIn("PositionStateHeaderChecksum", RECOVERY)
        self.assertIn("saved_header_checksum!=PositionStateHeaderChecksum", RECOVERY)

    def test_dynamic_trail_is_25_percent_for_all_horizons(self):
        start = MANAGER.index("if(g_positions[i].be_activated && g_positions[i].trailing_mode == TRAIL_DYNAMIC_25_PERCENT)")
        end = MANAGER.index("else if(g_positions[i].trailing_mode == TRAIL_ATR)", start)
        block = MANAGER[start:end]
        self.assertIn("double trail_factor = 0.25;", block)
        self.assertNotIn("HORIZON_SCALPING) trail_factor", block)
        self.assertNotIn("HORIZON_SWING) trail_factor", block)

    def test_tick_pressure_scoring_and_accumulators_disabled_by_default(self):
        self.assertIn("InpEnableTickPressure = false", AMIGO)
        self.assertIn("g_cfg.tick_pressure_enabled = InpEnableTickPressure", AMIGO)
        self.assertIn("if(!g_cfg.tick_pressure_enabled)", AMIGO)
        self.assertIn("decision_feat.fusion = 0.0", AMIGO)
        self.assertIn("if(InpEnableTickPressure)", AMIGO)
        self.assertIn("if(tick_session_started)\n      {\n         // These are streaming diagnostic accumulators", AMIGO)
        self.assertIn("g_footprint_engine.AddTick(last_price, tick_vol, 0);", AMIGO)
        self.assertIn("CommitFlowOpportunityDiagnostics(candidate_feature_rates", AMIGO)
        flow = FEATURE.split("if(cfg.tick_pressure_enabled)", 1)[1].split("else\n   {", 1)[0]
        self.assertIn("TryComputeDeltaA", flow)
        self.assertIn("fs.delta_a=0.0; fs.delta_b=0.0; fs.fusion=0.0;", FEATURE)

    def test_approved_two_percent_exposure_boundary_examples(self):
        self.assertTrue(admit_estimated_loss(100.0, 2.0))
        self.assertFalse(admit_estimated_loss(100.0, 2.000001))
        self.assertFalse(admit_estimated_loss(16.15, 0.89))

    def test_shadow_position_lifecycle_has_no_live_trade_calls(self):
        self.assertIn("InpShadowOnly        = true", AMIGO)
        self.assertIn("g_cfg.shadow_only         = InpShadowOnly", AMIGO)
        self.assertEqual(EXECUTION.count("OrderSend(req, res)"), 1)
        shadow_pos = EXECUTION.index("if(cfg.shadow_only)")
        send_guard_pos = EXECUTION.index("OrderSend(req, res)")
        self.assertLess(shadow_pos, send_guard_pos)
        remove = MANAGER.split("void PositionManagerRemove(", 1)[1].split("void PositionManagerTick(", 1)[0]
        tick = MANAGER.split("void PositionManagerTick(", 1)[1]
        close_pos = remove.index("g_trade.PositionClose(")
        self.assertTrue(call_is_inside_shadow_guard(remove, close_pos))
        self.assertIn("if(!cfg.shadow_only)\n      {\n         //--- Live Trading Mode", tick)
        self.assertEqual(tick.count("g_trade.PositionModify("), 3)
        self.assertEqual(tick.count("g_trade.PositionClosePartial("), 1)
        for method in ("PositionModify", "PositionClosePartial"):
            start = 0
            while True:
                pos = tick.find(f"g_trade.{method}(", start)
                if pos < 0:
                    break
                self.assertTrue(call_is_inside_shadow_guard(tick, pos), method)
                start = pos + 1

    def test_shadow_analysis_does_not_require_live_trading_permission(self):
        validate = ACCOUNT_EXECUTION.split("bool ValidateAccountIdentification(", 1)[1].split("void SymbolCapabilityBuild(", 1)[0]
        evaluate = ACCOUNT_EXECUTION.split("AccountExecutionEnvelope AccountExecutionEvaluate(", 1)[1]
        risk = RISK.split("bool RiskAllows(", 1)[1].split("double ComputeLotSize(", 1)[0]
        self.assertIn("require_trade_permissions && !acc.trade_allowed", validate)
        self.assertIn("require_trade_permissions && !acc.trade_expert", validate)
        self.assertIn("ValidateAccountIdentification(env.account, acc_err,!cfg.shadow_only)", evaluate)
        self.assertIn("if(!cfg.shadow_only && !MQLInfoInteger(MQL_TRADE_ALLOWED))", risk)
        self.assertIn("if(!cfg.shadow_only && !AccountInfoInteger(ACCOUNT_TRADE_EXPERT))", risk)
        shadow = EXECUTION.index("if(cfg.shadow_only)")
        order_check = EXECUTION.index("if(!OrderCheck(req, chk))")
        order_send = EXECUTION.index("OrderSend(req, res)")
        self.assertLess(shadow, order_check)
        self.assertLess(shadow, order_send)

    def test_live_execution_is_compile_gate_blocked_until_reconciliation_is_ready(self):
        contracts = (ROOT / "MQL5" / "Include" / "Contracts header.mqh").read_text(encoding="utf-8-sig")
        self.assertIn("#define AMIGO_LIVE_EXECUTION_READY 0", contracts)
        init = AMIGO.split("int OnInit()", 1)[1].split("void OnDeinit", 1)[0]
        self.assertLess(init.index("if(!g_cfg.shadow_only && AMIGO_LIVE_EXECUTION_READY==0)"),
                        init.index("bool risk_state_ready=RiskInit"))
        execute = EXECUTION.split("ExecutionResult ExecuteIntent(", 1)[1]
        self.assertLess(execute.index("LIVE_EXECUTION_BLOCKED_UNRECONCILED_ORDER_LIFECYCLE"),
                        execute.index("OrderSend(req, res)"))
        self.assertIn("InpShadowOnly        = true", AMIGO)


if __name__ == "__main__":
    unittest.main()
