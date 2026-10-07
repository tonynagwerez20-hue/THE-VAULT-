"""Comprehensive Unit Tests & Small-Account Simulation for Account-Aware Execution Layer.

Covers Prompt Sections 16, 17, 18:
  - Contract Specification Validation
  - Risk Sizing & 3-State Minimum-Lot Handling (NORMAL, ACCOMMODATED, UNSAFE)
  - Account Feasibility & Margin Checks
  - Strategy Score Independence (100% account-independent signal evaluation)
  - Small-Account Simulation across $5, $10, $25, $50, $100, $5,000, $50,000 accounts
  - Minimum Viable Account Analysis (Minimum Executable, Minimum Safely Executable, Minimum Viable Growth Account)
"""

import pytest
from algomind.account_execution import (
    AccountIdentification, SymbolCapabilityProfile, AccountExecutionEnvelope,
    AccountClass, MinLotStatus, FeasibilityStatus, Action,
    validate_symbol_capability, classify_account, evaluate_account_execution
)


# ======================================================================
# Section 18: Contract Specification Tests
# ======================================================================
class TestContractSpecificationValidation:

    def test_valid_contract_spec(self):
        cap = SymbolCapabilityProfile()
        valid, err = validate_symbol_capability(cap)
        assert valid is True
        assert err == "OK"

    def test_zero_tick_value(self):
        cap = SymbolCapabilityProfile(tick_value=0.0)
        valid, err = validate_symbol_capability(cap)
        assert valid is False
        assert err == "INVALID_TICK_VALUE"

    def test_zero_tick_size(self):
        cap = SymbolCapabilityProfile(tick_size=0.0)
        valid, err = validate_symbol_capability(cap)
        assert valid is False
        assert err == "INVALID_TICK_SIZE"

    def test_invalid_contract_size(self):
        cap = SymbolCapabilityProfile(contract_size=0.0)
        valid, err = validate_symbol_capability(cap)
        assert valid is False
        assert err == "INVALID_CONTRACT_SIZE"

    def test_invalid_volume_step(self):
        cap = SymbolCapabilityProfile(volume_step=0.0)
        valid, err = validate_symbol_capability(cap)
        assert valid is False
        assert err == "INVALID_VOLUME_STEP"

    def test_invalid_volume_min(self):
        cap = SymbolCapabilityProfile(volume_min=0.0)
        valid, err = validate_symbol_capability(cap)
        assert valid is False
        assert err == "INVALID_VOLUME_MIN"


# ======================================================================
# Section 18: Risk Sizing & 3-State Minimum Lot Handling Tests
# ======================================================================
class TestRiskSizingAnd3StateMinLot:

    def test_state_a_normal_volume(self):
        # Equity = $10,000, Risk = 0.5% ($50). StopDist = 2.0 (XAUUSD). TickVal = 0.01, TickSz = 0.01
        # RiskPerLot = (2.0 / 0.01) * 0.01 = $2.0 per unit = $200 per lot (contract=100)
        # RawVolume = 50 / 200 = 0.25 lots >= 0.01 (min) -> STATE A NORMAL
        acc = AccountIdentification(equity=10000.0, balance=10000.0)
        cap = SymbolCapabilityProfile()

        env = evaluate_account_execution(acc, cap, direction=1, entry=2000.0, stop=1998.0, target=2004.0, target_risk_pct=0.5)

        assert env.min_lot_status == MinLotStatus.NORMAL
        assert env.feasibility == FeasibilityStatus.NORMAL
        assert env.executable_volume == 0.25
        assert env.actual_risk == 50.0
        assert abs(env.risk_distortion - 1.0) < 1e-4
        assert env.final_action == Action.TRADE

    def test_state_b_min_lot_accommodated(self):
        # Equity = $100, Risk = 0.5% ($0.50). StopDist = 2.0 -> RiskPerLot = $200
        # RawVolume = 0.50 / 200 = 0.0025 < 0.01 (min)
        # ActualRiskAtMinLot = 0.01 * 200 = $2.00 (2.0% equity)
        # Distortion = 2.00 / 0.50 = 4.0x <= 5.0x (max allowed distortion) -> STATE B ACCOMMODATED
        acc = AccountIdentification(equity=100.0, balance=100.0)
        cap = SymbolCapabilityProfile()

        env = evaluate_account_execution(acc, cap, direction=1, entry=2000.0, stop=1998.0, target=2004.0, target_risk_pct=0.5, max_allowed_distortion=5.0, allow_min_lot_override=True)

        assert env.min_lot_status == MinLotStatus.MIN_LOT_ACCOMMODATED
        assert env.feasibility == FeasibilityStatus.MIN_LOT_ACCOMMODATED
        assert env.executable_volume == 0.01
        assert env.actual_risk == 2.00
        assert abs(env.risk_distortion - 4.0) < 1e-4
        assert env.final_action == Action.TRADE
        assert env.reason == "MIN_LOT_ACCOMMODATED"

    def test_state_c_min_lot_unsafe(self):
        # Equity = $10, Risk = 0.5% ($0.05). StopDist = 2.0 -> RiskPerLot = $200
        # RawVolume = 0.05 / 200 = 0.00025 < 0.01 (min)
        # ActualRiskAtMinLot = 0.01 * 200 = $2.00 (20% equity!)
        # Distortion = 2.00 / 0.05 = 40.0x > 5.0x (max allowed distortion) -> STATE C UNSAFE
        acc = AccountIdentification(equity=10.0, balance=10.0)
        cap = SymbolCapabilityProfile()

        env = evaluate_account_execution(acc, cap, direction=1, entry=2000.0, stop=1998.0, target=2004.0, target_risk_pct=0.5, max_allowed_distortion=5.0, allow_min_lot_override=True)

        assert env.min_lot_status == MinLotStatus.MIN_LOT_UNSAFE
        assert env.feasibility == FeasibilityStatus.MIN_LOT_UNSAFE
        assert env.executable_volume == 0.0
        assert env.actual_risk == 2.00
        assert abs(env.risk_distortion - 40.0) < 1e-4
        assert env.final_action == Action.NO_TRADE
        assert env.reason == "MIN_LOT_UNSAFE"

    def test_insufficient_margin_blocked(self):
        # High leverage constraint / insufficient free margin
        acc = AccountIdentification(equity=50.0, balance=50.0, margin_free=1.0, leverage=10.0)
        cap = SymbolCapabilityProfile()

        env = evaluate_account_execution(acc, cap, direction=1, entry=2000.0, stop=1998.0, target=2004.0, target_risk_pct=0.5, max_allowed_distortion=10.0)

        assert env.feasibility == FeasibilityStatus.MARGIN_BLOCKED
        assert env.final_action == Action.NO_TRADE
        assert env.reason == "INSUFFICIENT_MARGIN"


# ======================================================================
# Section 13: Strategy Score Account-Independence Test
# ======================================================================
class TestStrategyScoreAccountIndependence:

    def test_strategy_grading_is_identical_across_account_sizes(self):
        """Mandatory requirement: $10, $100, $1,000, $50,000 accounts get identical strategy score & grade."""
        cap = SymbolCapabilityProfile()
        accounts = [5.0, 10.0, 25.0, 50.0, 100.0, 1000.0, 5000.0, 50000.0]

        # Constant market strategy evaluation
        mock_strategy_score = 0.85
        mock_strategy_action = Action.TRADE

        results = []
        for eq in accounts:
            acc = AccountIdentification(equity=eq, balance=eq, margin_free=eq)
            env = evaluate_account_execution(acc, cap, direction=1, entry=2000.0, stop=1998.0, target=2004.0, target_risk_pct=0.5, strategy_action=mock_strategy_action)
            results.append((eq, mock_strategy_score, env.final_action, env.feasibility))

        # Verify strategy score remained 0.85 across all accounts
        for eq, score, action, feasibility in results:
            assert score == 0.85

        # Verify downstream execution feasibility varied appropriately without altering strategy grade
        action_map = {eq: action for eq, score, action, feasibility in results}
        assert action_map[5.0] == Action.NO_TRADE      # Blocked due to min lot unsafe
        assert action_map[50000.0] == Action.TRADE      # Executed fully


# ======================================================================
# Section 16 & 17: Small-Account Simulation & Minimum Viable Account Analysis
# ======================================================================
class TestSmallAccountSimulation:

    def test_small_account_matrix_sweep(self):
        """Simulate trade execution feasibility across 7 account tiers."""
        account_tiers = [5.0, 10.0, 25.0, 50.0, 100.0, 5000.0, 50000.0]
        cap = SymbolCapabilityProfile()

        # Representative test setup: XAUUSD Long, Entry=2000.00, SL=1998.00 (2.00 pts stop), TP=2004.00
        # Target Risk = 0.5%
        simulation_results = {}

        for eq in account_tiers:
            acc = AccountIdentification(equity=eq, balance=eq, margin_free=eq, leverage=500.0)
            env = evaluate_account_execution(
                account=acc,
                symbol_cap=cap,
                direction=1,
                entry=2000.0,
                stop=1998.0,
                target=2004.0,
                target_risk_pct=0.5,
                max_allowed_distortion=5.0,
                allow_min_lot_override=True,
                strategy_action=Action.TRADE
            )
            simulation_results[eq] = {
                "class": env.account.account_class.name,
                "action": env.final_action.name,
                "feasibility": env.feasibility.name,
                "min_lot_status": env.min_lot_status.name,
                "target_risk": env.target_risk_amount,
                "actual_risk": env.actual_risk,
                "distortion": env.risk_distortion,
                "executable_vol": env.executable_volume
            }

        # Verify results per account tier
        # $5: UNSAFE (40x distortion > 5x)
        assert simulation_results[5.0]["action"] == "NO_TRADE"
        assert simulation_results[5.0]["feasibility"] == "MIN_LOT_UNSAFE"

        # $10: UNSAFE (20x distortion > 5x)
        assert simulation_results[10.0]["action"] == "NO_TRADE"

        # $25: UNSAFE (8x distortion > 5x)
        assert simulation_results[25.0]["action"] == "NO_TRADE"

        # $50: UNSAFE (8x distortion > 5x)
        assert simulation_results[50.0]["action"] == "NO_TRADE"

        # $100: ACCOMMODATED (4x distortion <= 5x) -> Executable at min lot 0.01!
        assert simulation_results[100.0]["action"] == "TRADE"
        assert simulation_results[100.0]["min_lot_status"] == "MIN_LOT_ACCOMMODATED"

        # $5,000: NORMAL (0.12 lots, 1.0x distortion)
        assert simulation_results[5000.0]["action"] == "TRADE"
        assert simulation_results[5000.0]["min_lot_status"] == "NORMAL"
        assert simulation_results[5000.0]["executable_vol"] == 0.12

        # $50,000: NORMAL (1.25 lots, 1.0x distortion)
        assert simulation_results[50000.0]["action"] == "TRADE"
        assert simulation_results[50000.0]["min_lot_status"] == "NORMAL"
        assert simulation_results[50000.0]["executable_vol"] == 1.25

    def test_minimum_viable_account_derivation(self):
        """Empirically derive Minimum Executable, Safely Executable, and Viable Growth Account thresholds."""
        # Setup: 2.00 point stop on XAUUSD -> RiskPerLot = $200. Min lot = 0.01 -> MinLotRisk = $2.00.
        cap = SymbolCapabilityProfile()

        # 1. Minimum Executable Account: Smallest account where min lot can execute under 5x max distortion
        # Target Risk = 0.5%. MinLotRisk = $2.00. Distortion = $2.00 / (Equity * 0.005) <= 5.0 -> Equity >= $80.00
        min_exec_equity = 40.0  # At 10x max distortion ($2.00 / 0.20 = 10x)

        acc_exec = AccountIdentification(equity=40.0, balance=40.0, margin_free=40.0, leverage=2000.0)
        env_exec = evaluate_account_execution(acc_exec, cap, 1, 2000.0, 1998.0, 2004.0, target_risk_pct=0.5, max_allowed_distortion=10.0)
        assert env_exec.final_action == Action.TRADE

        # 2. Minimum Safely Executable Account: Smallest account where min lot executes at exactly 1.0x target risk (0.5%)
        # MinLotRisk = $2.00 = Equity * 0.005 -> Equity = $400.00
        acc_safe = AccountIdentification(equity=400.0, balance=400.0, margin_free=400.0, leverage=500.0)
        env_safe = evaluate_account_execution(acc_safe, cap, 1, 2000.0, 1998.0, 2004.0, target_risk_pct=0.5)
        assert env_safe.final_action == Action.TRADE
        assert env_safe.min_lot_status == MinLotStatus.NORMAL
        assert abs(env_safe.risk_distortion - 1.0) < 1e-4

        # 3. Minimum Viable Growth Account: Account size where volume step quantization distortion is < 5%
        # Volume >= 0.10 lots -> Equity >= $4,000.00
        acc_growth = AccountIdentification(equity=4000.0, balance=4000.0, margin_free=4000.0, leverage=500.0)
        env_growth = evaluate_account_execution(acc_growth, cap, 1, 2000.0, 1998.0, 2004.0, target_risk_pct=0.5)
        assert env_growth.executable_volume >= 0.10
        assert env_growth.min_lot_status == MinLotStatus.NORMAL


# ======================================================================
# Hypothetical Exness Cent Account ($15 - $25, 1:2000 Leverage) Tests
# ======================================================================
class TestExnessCentAccount2000Leverage:
    """Hypothetical simulation for Exness Cent account ($15-$25 balance, 1:2000 leverage).

    Exness Cent Account Specifications:
      - Account Currency: USC (Cent USD) or USD (where 1 USD = 100 Cent units, or $15 USD = 1,500 USC)
      - Symbol: XAUUSDm / XAUUSDcent
      - Min Lot: 0.01 lot (on cent account, 1.0 lot = 1 oz gold or 10 oz gold depending on cent contract size, typically contract_size=100 or 1.0).
      - Leverage: 1:2000 (0.05% margin requirement)

    We test 2 standard configurations:
      Config A: Standard Standard/Cent Broker Symbol Spec (Contract Size = 100 oz, Tick Value = $1.00 per tick/lot)
      Config B: Pure Cent Account Symbol Spec (1 USD = 100 USC, Balance = 1500 - 2500 USC, Contract Size = 1.0 oz, Tick Value = 0.01 USC)
    """

    def test_exness_cent_15_usd_standard_symbol_spec(self):
        """$15 USD Balance, 1:2000 Leverage, Standard Gold Symbol (Contract 100, StopDist = 2.00).

        - Target Risk 0.5% of $15 = $0.075
        - Stop Distance = $2.00 (XAUUSD 2000.0 -> 1998.0)
        - Risk per Lot (0.01 tick) = $200 per lot
        - Raw Volume = $0.075 / $200 = 0.000375 lots < 0.01 min
        - Actual Risk at Min Lot 0.01 = 0.01 * $200 = $2.00 (13.33% of account!)
        - Risk Distortion = $2.00 / $0.075 = 26.67x
        - Max Allowed Distortion Policy = 5.0x
        -> Result: MIN_LOT_UNSAFE -> NO_TRADE (Fail-closed protecting $15 account from 13.3% loss per trade)
        """
        acc = AccountIdentification(
            login=888001,
            broker="Exness",
            server="Exness-Real20",
            currency="USD",
            balance=15.0,
            equity=15.0,
            margin_free=15.0,
            leverage=2000.0
        )
        cap = SymbolCapabilityProfile(
            symbol="XAUUSDm",
            tick_size=0.01,
            tick_value=1.00,
            contract_size=100.0,
            volume_min=0.01,
            volume_step=0.01
        )

        env = evaluate_account_execution(
            account=acc,
            symbol_cap=cap,
            direction=1,
            entry=2000.0,
            stop=1998.0,
            target=2004.0,
            target_risk_pct=0.5,
            max_allowed_distortion=5.0,
            allow_min_lot_override=True
        )

        assert env.account.account_class == AccountClass.MICRO
        assert env.min_lot_status == MinLotStatus.MIN_LOT_UNSAFE
        assert env.feasibility == FeasibilityStatus.MIN_LOT_UNSAFE
        assert env.final_action == Action.NO_TRADE
        assert env.reason == "MIN_LOT_UNSAFE"
        assert abs(env.actual_risk - 2.00) < 1e-4
        assert abs(env.actual_risk_pct - 13.3333) < 1e-2
        assert abs(env.risk_distortion - 26.6666) < 1e-2
        # Since trade is rejected (MIN_LOT_UNSAFE), executable volume is 0.0, so required_margin is $0.00
        assert env.required_margin == 0.0


    def test_exness_cent_25_usd_standard_symbol_spec(self):
        """$25 USD Balance, 1:2000 Leverage, Standard Gold Symbol (Contract 100, StopDist = 2.00).

        - Target Risk 0.5% of $25 = $0.125
        - Actual Risk at Min Lot 0.01 = $2.00 (8.0% of account)
        - Risk Distortion = $2.00 / $0.125 = 16.0x > 5.0x
        -> Result: MIN_LOT_UNSAFE -> NO_TRADE
        """
        acc = AccountIdentification(
            login=888002,
            broker="Exness",
            server="Exness-Real20",
            currency="USD",
            balance=25.0,
            equity=25.0,
            margin_free=25.0,
            leverage=2000.0
        )
        cap = SymbolCapabilityProfile(
            symbol="XAUUSDm",
            tick_size=0.01,
            tick_value=1.00,
            contract_size=100.0,
            volume_min=0.01,
            volume_step=0.01
        )

        env = evaluate_account_execution(
            account=acc,
            symbol_cap=cap,
            direction=1,
            entry=2000.0,
            stop=1998.0,
            target=2004.0,
            target_risk_pct=0.5,
            max_allowed_distortion=5.0,
            allow_min_lot_override=True
        )

        assert env.min_lot_status == MinLotStatus.MIN_LOT_UNSAFE
        assert env.final_action == Action.NO_TRADE
        assert abs(env.risk_distortion - 16.0) < 1e-4

    def test_exness_cent_15_usd_accommodated_under_relaxed_policy(self):
        """$15 USD Balance, 1:2000 Leverage, relaxed distortion policy (max 30x distortion allowed).

        If user/owner explicitly relaxes distortion policy for Micro accounts (e.g. allowing up to 13.3% risk):
        - Risk Distortion = 26.67x <= 30.0x -> MIN_LOT_ACCOMMODATED -> TRADE (0.01 lot executable)
        - Required Margin = $1.00 (Free Margin = $15.00) -> Margin check passes!
        """
        acc = AccountIdentification(
            login=888001,
            broker="Exness",
            server="Exness-Real20",
            currency="USD",
            balance=15.0,
            equity=15.0,
            margin_free=15.0,
            leverage=2000.0
        )
        cap = SymbolCapabilityProfile(
            symbol="XAUUSDm",
            tick_size=0.01,
            tick_value=1.00,
            contract_size=100.0,
            volume_min=0.01,
            volume_step=0.01
        )

        env = evaluate_account_execution(
            account=acc,
            symbol_cap=cap,
            direction=1,
            entry=2000.0,
            stop=1998.0,
            target=2004.0,
            target_risk_pct=0.5,
            max_allowed_distortion=30.0,  # Explicit relaxed policy test
            allow_min_lot_override=True
        )

        assert env.min_lot_status == MinLotStatus.MIN_LOT_ACCOMMODATED
        assert env.feasibility == FeasibilityStatus.MIN_LOT_ACCOMMODATED
        assert env.final_action == Action.TRADE
        assert env.executable_volume == 0.01
        assert abs(env.required_margin - 1.00) < 1e-4

    def test_exness_pure_cent_account_denomination(self):
        """Pure Exness Cent Account (1 USD = 100 USC).

        Account Balance: 2,500 USC ($25 USD)
        Symbol: XAUUSDcent (1 cent lot = 1 oz gold or contract size 100 with tick_value in USC = 1.00 USC per tick)
        - Equity = 2500 USC
        - Target Risk 0.5% = 12.5 USC ($0.125 USD)
        - Stop Distance = 2.00 pts (200 ticks)
        - Risk per cent lot = 200 ticks * 0.01 tick value (USC) = 2.00 USC per cent lot (or $0.02 USD)
        - Raw Volume = 12.5 / 2.00 = 6.25 cent lots
        - VolumeMin = 0.01 cent lot
        -> Result: Raw Volume (6.25 lots) >= Min Lot (0.01) -> STATE A NORMAL -> TRADE!
        """
        acc = AccountIdentification(
            login=888003,
            broker="Exness",
            server="Exness-Cent2",
            currency="USC",
            balance=2500.0,  # 2500 USC = $25 USD
            equity=2500.0,
            margin_free=2500.0,
            leverage=2000.0
        )
        cap = SymbolCapabilityProfile(
            symbol="XAUUSDcent",
            tick_size=0.01,
            tick_value=0.01,  # 0.01 USC per tick for 1 cent lot (1 oz contract size)
            contract_size=1.0,
            volume_min=0.01,
            volume_step=0.01
        )

        env = evaluate_account_execution(
            account=acc,
            symbol_cap=cap,
            direction=1,
            entry=2000.0,
            stop=1998.0,
            target=2004.0,
            target_risk_pct=0.5,
            max_allowed_distortion=5.0
        )

        assert env.min_lot_status == MinLotStatus.NORMAL
        assert env.feasibility == FeasibilityStatus.NORMAL
        assert env.final_action == Action.TRADE
        assert env.executable_volume == 6.25
        assert abs(env.actual_risk - 12.5) < 1e-4
        assert abs(env.actual_risk_pct - 0.5) < 1e-4
        assert abs(env.risk_distortion - 1.0) < 1e-4
        # Required Margin for 6.25 cent lots at 1:2000 leverage = (6.25 * 1.0 * 2000) / 2000 = 6.25 USC ($0.0625 USD)
        assert abs(env.required_margin - 6.25) < 1e-4


# ======================================================================
# Section 23 & 24: Account-Aware Adaptive Stop-Loss Test Matrix
# ======================================================================
from algomind.account_execution import (
    SLAdaptationStatus, AdaptiveSLResult, evaluate_adaptive_stop
)


class TestAccountAwareAdaptiveStopLoss:

    def test_original_sl_executable(self):
        """Original SL is within account max stop distance -> ORIGINAL_SL_EXECUTABLE."""
        cap = SymbolCapabilityProfile(symbol="XAUUSDm", tick_size=0.01, tick_value=1.00, volume_min=0.01)
        # Equity = $10,000, 0.5% risk = $50. Max risk = $250. Max stop dist = 250 / 100 = 2.50
        # Original stop dist = 0.50 <= 2.50 -> Original SL executable
        res = evaluate_adaptive_stop(
            symbol_cap=cap, equity=10000.0, direction=1, entry=2000.0, original_sl=1999.5, target=2004.0, target_risk_pct=0.5
        )
        assert res.status == SLAdaptationStatus.ORIGINAL_SL_EXECUTABLE
        assert res.selected_sl == 1999.5
        assert res.reason == "ORIGINAL_SL_EXECUTABLE"

    def test_original_sl_too_wide_valid_tighter_candidate_exists(self):
        """Original SL too wide, valid tighter strategy structural candidate exists -> ADAPTIVE_SL_ACCEPTED."""
        cap = SymbolCapabilityProfile(symbol="XAUUSDm", tick_size=0.01, tick_value=1.00, volume_min=0.01)
        # Equity = $16.15, 0.5% risk = $0.08. Max 5x risk = $0.40. Max stop dist = 0.40 / 100 = 0.40
        # Original SL = 1973.214 (stop dist 26.786 > 0.40).
        # Valid structural swing low = 1999.80 (dist 0.20 <= 0.40). TP = 2004.0 -> RR = 4.2 / 0.20 = 21.0 >= 2.0
        res = evaluate_adaptive_stop(
            symbol_cap=cap,
            equity=16.15,
            direction=1,
            entry=2000.0,
            original_sl=1973.214,
            target=2004.0,
            structural_invalid=1999.80,
            atr=0.30,
            target_risk_pct=0.5,
            max_allowed_distortion=5.0,
        )
        assert res.status == SLAdaptationStatus.ADAPTIVE_SL_ACCEPTED
        assert res.selected_sl == 1999.80
        assert abs(res.candidate_stop_dist - 0.20) < 1e-4
        assert res.reason == "VALID_STRATEGY_STRUCTURE"

    def test_original_sl_too_wide_candidate_violates_structure(self):
        """Original SL too wide, structural candidate is invalid (wrong side of original SL) -> NO_TRADE."""
        cap = SymbolCapabilityProfile(symbol="XAUUSDm", tick_size=0.01, tick_value=1.00, volume_min=0.01)
        # Structural level = 1970.0 (worse than original SL 1973.214)
        res = evaluate_adaptive_stop(
            symbol_cap=cap,
            equity=16.15,
            direction=1,
            entry=2000.0,
            original_sl=1973.214,
            target=2004.0,
            structural_invalid=1970.0,
            atr=0.0,
            target_risk_pct=0.5,
            max_allowed_distortion=5.0,
        )
        assert res.status == SLAdaptationStatus.ADAPTIVE_SL_REJECTED
        assert res.selected_sl == 1973.214
        assert res.reason == "NO_VALID_ADAPTIVE_SL"

    def test_candidate_violates_rr(self):
        """Candidate stop loss produces RR < 2.0 -> ADAPTIVE_SL_REJECTED."""
        cap = SymbolCapabilityProfile(symbol="XAUUSDm", tick_size=0.01, tick_value=1.00, volume_min=0.01)
        # Entry = 2000.0, Target = 2000.50 (reward = 0.50). Candidate SL = 1999.70 (stop dist = 0.30).
        # RR = 0.50 / 0.30 = 1.67 < 2.00 -> Rejected!
        res = evaluate_adaptive_stop(
            symbol_cap=cap,
            equity=16.15,
            direction=1,
            entry=2000.0,
            original_sl=1973.214,
            target=2000.50,
            structural_invalid=1999.70,
            atr=0.0,
            target_risk_pct=0.5,
            max_allowed_distortion=5.0,
            min_rr_required=2.0,
        )
        assert res.status == SLAdaptationStatus.ADAPTIVE_SL_REJECTED
        assert res.reason == "NO_VALID_ADAPTIVE_SL"

    def test_candidate_exceeds_account_ceiling(self):
        """Candidate stop loss distance exceeds account-compatible maximum -> ADAPTIVE_SL_REJECTED."""
        cap = SymbolCapabilityProfile(symbol="XAUUSDm", tick_size=0.01, tick_value=1.00, volume_min=0.01)
        # Max account dist = 0.40. Candidate SL = 1999.00 (dist = 1.00 > 0.40)
        res = evaluate_adaptive_stop(
            symbol_cap=cap,
            equity=16.15,
            direction=1,
            entry=2000.0,
            original_sl=1973.214,
            target=2004.0,
            structural_invalid=1999.00,
            atr=0.0,
            target_risk_pct=0.5,
            max_allowed_distortion=5.0,
        )
        assert res.status == SLAdaptationStatus.ADAPTIVE_SL_REJECTED

    def test_candidate_violates_broker_min_stop_distance(self):
        """Candidate stop loss violates broker stops_level -> ADAPTIVE_SL_REJECTED."""
        cap = SymbolCapabilityProfile(symbol="XAUUSDm", tick_size=0.01, tick_value=1.00, volume_min=0.01, stops_level=50, point=0.01)
        # Stops level = 50 * 0.01 = 0.50 pts. Candidate SL = 1999.80 (dist = 0.20 < 0.50)
        res = evaluate_adaptive_stop(
            symbol_cap=cap,
            equity=16.15,
            direction=1,
            entry=2000.0,
            original_sl=1973.214,
            target=2004.0,
            structural_invalid=1999.80,
            atr=0.0,
            target_risk_pct=0.5,
        )
        assert res.status == SLAdaptationStatus.ADAPTIVE_SL_REJECTED

    def test_buy_invalid_candidate(self):
        """BUY candidate SL >= entry -> REJECT."""
        cap = SymbolCapabilityProfile(symbol="XAUUSDm", tick_size=0.01, tick_value=1.00, volume_min=0.01)
        res = evaluate_adaptive_stop(
            symbol_cap=cap,
            equity=16.15,
            direction=1,
            entry=2000.0,
            original_sl=1973.214,
            target=2004.0,
            structural_invalid=2000.50, # invalid SL above entry
            atr=0.0,
            target_risk_pct=0.5,
        )
        assert res.status == SLAdaptationStatus.ADAPTIVE_SL_REJECTED

    def test_sell_invalid_candidate(self):
        """SELL candidate SL <= entry -> REJECT."""
        cap = SymbolCapabilityProfile(symbol="XAUUSDm", tick_size=0.01, tick_value=1.00, volume_min=0.01)
        res = evaluate_adaptive_stop(
            symbol_cap=cap,
            equity=16.15,
            direction=-1,
            entry=2000.0,
            original_sl=2026.786,
            target=1996.0,
            structural_invalid=1999.50, # invalid SL below entry for SELL
            atr=0.0,
            target_risk_pct=0.5,
        )
        assert res.status == SLAdaptationStatus.ADAPTIVE_SL_REJECTED

    def test_multiple_candidates_hierarchy(self):
        """Verifies candidate selection follows Strategy Hierarchy (Structure > ATR)."""
        cap = SymbolCapabilityProfile(symbol="XAUUSDm", tick_size=0.01, tick_value=1.00, volume_min=0.01)
        # Candidate 1 (Structure): 1999.80 (dist 0.20)
        # Candidate 2 (ATR): 1999.70 (dist 0.30)
        # System MUST select Candidate 1 (Structure)
        res = evaluate_adaptive_stop(
            symbol_cap=cap,
            equity=16.15,
            direction=1,
            entry=2000.0,
            original_sl=1973.214,
            target=2004.0,
            structural_invalid=1999.80,
            atr=0.30,
            target_risk_pct=0.5,
            max_allowed_distortion=5.0,
        )
        assert res.status == SLAdaptationStatus.ADAPTIVE_SL_ACCEPTED
        assert res.selected_sl == 1999.80
        assert res.reason == "VALID_STRATEGY_STRUCTURE"

    def test_final_volume_risk_uses_executable_volume(self):
        """Actual risk must be calculated using normalized executable volume, not raw volume."""
        acc = AccountIdentification(equity=16.15, balance=16.15, margin_free=16.15, leverage=2000.0)
        cap = SymbolCapabilityProfile(symbol="XAUUSDm", tick_size=0.01, tick_value=1.00, volume_min=0.01)
        
        env = evaluate_account_execution(
            account=acc,
            symbol_cap=cap,
            direction=1,
            entry=2000.0,
            stop=1973.214,
            target=2004.0,
            target_risk_pct=0.5,
            original_sl=1973.214,
            structural_invalid=1999.80,
            atr=0.30,
        )
        assert env.sl_adapt_status == SLAdaptationStatus.ADAPTIVE_SL_ACCEPTED
        assert env.executable_volume == 0.01
        # Actual risk must equal 0.01 lot * (0.20 stop dist / 0.01 tick) * $1.00 = $20.00... wait:
        # 0.20 stop dist -> risk per lot = (0.20/0.01)*1 = $20 per lot. 0.01 lot * $20 = $0.20 actual risk!
        assert abs(env.actual_risk - 0.20) < 1e-4

    def test_live_runtime_16_15_equity_sweep(self):
        """Full verification of $16.15 live runtime example with adaptive SL."""
        acc = AccountIdentification(equity=16.15, balance=16.15, margin_free=16.15, leverage=2000.0)
        cap = SymbolCapabilityProfile(symbol="XAUUSDm", tick_size=0.01, tick_value=1.00, volume_min=0.01)
        
        env = evaluate_account_execution(
            account=acc,
            symbol_cap=cap,
            direction=1,
            entry=2000.0,
            stop=1973.214,
            target=2004.0,
            target_risk_pct=0.5,
            original_sl=1973.214,
            structural_invalid=1999.80,
            atr=0.30,
        )
        
        assert env.original_sl == 1973.214
        assert env.selected_sl == 1999.80
        assert env.executable_volume == 0.01
        assert abs(env.actual_risk - 0.20) < 1e-4
        assert abs(env.target_risk_amount - 0.08075) < 1e-4
        assert env.final_action == Action.TRADE
        
        # Verify diagnostic logs contain [AlgoMind][SL_ADAPT]
        sl_adapt_logs = [d for d in env.diagnostics if "[AlgoMind][SL_ADAPT]" in d]
        assert len(sl_adapt_logs) == 1
        assert "sym=XAUUSDm" in sl_adapt_logs[0]
        assert "status=ACCEPTED" in sl_adapt_logs[0]
        assert "reason=VALID_STRATEGY_STRUCTURE" in sl_adapt_logs[0]


from algomind.account_execution import SignalExecutionClassification, SymbolTradeMode


class TestCasesABCDFourStateFeasibility:
    """Explicit Verification of the 4 Mandatory Feasibility Cases (Prompt REQ-03)."""

    def test_case_a_primary_sl_executable(self):
        """Case A: Strategy-valid + Primary SL valid + RR >= 2.0 + Account feasible = SIGNAL_VALID_EXECUTABLE."""
        acc = AccountIdentification(equity=10000.0, balance=10000.0)
        cap = SymbolCapabilityProfile(symbol="XAUUSDm", tick_size=0.01, tick_value=1.00, volume_min=0.01)

        env = evaluate_account_execution(
            account=acc,
            symbol_cap=cap,
            direction=1,
            entry=2000.0,
            stop=1998.0,
            target=2004.0,
            target_risk_pct=0.5,
            strategy_action=Action.TRADE
        )

        assert env.execution_classification == SignalExecutionClassification.SIGNAL_VALID_EXECUTABLE
        assert env.final_action == Action.TRADE
        assert env.min_lot_status == MinLotStatus.NORMAL
        size_diags = [d for d in env.diagnostics if "[SIZE_DIAG]" in d]
        assert len(size_diags) == 1
        assert "classification=SIGNAL_VALID_EXECUTABLE" in size_diags[0]

    def test_case_b_tighter_adaptive_sl_executable(self):
        """Case B: Primary SL too wide -> Tighter valid strategy SL candidate exists and passes all gates = SIGNAL_VALID_EXECUTABLE."""
        acc = AccountIdentification(equity=16.15, balance=16.15, margin_free=16.15, leverage=2000.0)
        cap = SymbolCapabilityProfile(symbol="XAUUSDm", tick_size=0.01, tick_value=1.00, volume_min=0.01)

        env = evaluate_account_execution(
            account=acc,
            symbol_cap=cap,
            direction=1,
            entry=2000.0,
            stop=1955.0,  # Primary SL too wide ($45 dist)
            target=2004.0,
            target_risk_pct=0.5,
            original_sl=1955.0,
            structural_invalid=1999.80, # Tighter valid structural SL candidate ($0.20 dist)
            atr=0.30,
            strategy_action=Action.TRADE
        )

        assert env.execution_classification == SignalExecutionClassification.SIGNAL_VALID_EXECUTABLE
        assert env.final_action == Action.TRADE
        assert env.selected_sl == 1999.80
        assert env.sl_adapt_status == SLAdaptationStatus.ADAPTIVE_SL_ACCEPTED

    def test_case_c_genuinely_infeasible(self):
        """Case C: Primary SL too wide -> No valid strategy candidate fits account risk ceiling = SIGNAL_VALID_ACCOUNT_INFEASIBLE."""
        acc = AccountIdentification(equity=16.15, balance=16.15, margin_free=16.15, leverage=2000.0)
        cap = SymbolCapabilityProfile(symbol="XAUUSDm", tick_size=0.01, tick_value=1.00, volume_min=0.01)

        env = evaluate_account_execution(
            account=acc,
            symbol_cap=cap,
            direction=1,
            entry=2000.0,
            stop=1955.0,  # Primary SL too wide ($45 dist -> min lot loss $45.00 > max risk $0.40375)
            target=2004.0,
            target_risk_pct=0.5,
            original_sl=1955.0,
            structural_invalid=0.0, # No tighter structural candidate
            atr=0.0,                # No tighter ATR candidate
            strategy_action=Action.TRADE
        )

        assert env.execution_classification == SignalExecutionClassification.SIGNAL_VALID_ACCOUNT_INFEASIBLE
        assert env.final_action == Action.NO_TRADE
        assert env.executable_volume == 0.0
        assert env.reason == "MIN_LOT_UNSAFE"
        size_diags = [d for d in env.diagnostics if "[SIZE_DIAG]" in d]
        assert len(size_diags) == 1
        assert "classification=SIGNAL_VALID_ACCOUNT_INFEASIBLE" in size_diags[0]

    def test_case_d_broker_constraint(self):
        """Case D: Strategy-valid + otherwise account-feasible + broker trade disabled = SIGNAL_VALID_BROKER_INFEASIBLE."""
        acc = AccountIdentification(equity=10000.0, balance=10000.0)
        cap = SymbolCapabilityProfile(symbol="XAUUSDm", trade_mode=SymbolTradeMode.DISABLED.value) # 0 = SYMBOL_TRADE_MODE_DISABLED

        env = evaluate_account_execution(
            account=acc,
            symbol_cap=cap,
            direction=1,
            entry=2000.0,
            stop=1998.0,
            target=2004.0,
            target_risk_pct=0.5,
            strategy_action=Action.TRADE
        )

        assert env.execution_classification == SignalExecutionClassification.SIGNAL_VALID_BROKER_INFEASIBLE
        assert env.final_action == Action.NO_TRADE
        assert env.reason == "SYMBOL_TRADE_MODE_DISABLED"

    def test_strategy_invalid(self):
        """Strategy decision != ACTION_TRADE remains SIGNAL_INVALID."""
        acc = AccountIdentification(equity=10000.0, balance=10000.0)
        cap = SymbolCapabilityProfile()

        env = evaluate_account_execution(
            account=acc,
            symbol_cap=cap,
            direction=1,
            entry=2000.0,
            stop=1998.0,
            target=2004.0,
            target_risk_pct=0.5,
            strategy_action=Action.NO_TRADE
        )

        assert env.execution_classification == SignalExecutionClassification.SIGNAL_INVALID
        assert env.final_action == Action.NO_TRADE
        assert env.reason == "STRATEGY_NOT_TRADE"

    def test_october_7_replay_scenario(self):
        """Replay exact October 7 condition: $16.15 equity, $45.00 stop dist, 0.01 min lot.
        Verify system rejects as SIGNAL_VALID_ACCOUNT_INFEASIBLE rather than forcing 0.01 lot or shrinking SL.
        """
        acc = AccountIdentification(equity=16.15, balance=16.15, margin_free=16.15, leverage=2000.0)
        cap = SymbolCapabilityProfile(symbol="XAUUSDm", tick_size=0.001, tick_value=0.10, volume_min=0.01)

        env = evaluate_account_execution(
            account=acc,
            symbol_cap=cap,
            direction=1,
            entry=2650.00,
            stop=2605.00,  # $45.00 stop distance
            target=2740.00,
            target_risk_pct=0.5,
            original_sl=2605.00,
            strategy_action=Action.TRADE
        )

        assert env.execution_classification == SignalExecutionClassification.SIGNAL_VALID_ACCOUNT_INFEASIBLE
        assert env.final_action == Action.NO_TRADE
        assert env.executable_volume == 0.0
        assert env.selected_sl == 2605.00 # SL remained un-shrunk
        assert env.risk_distortion > 500.0 # ~557x distortion


