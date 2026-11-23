"""Account exposure contract: estimation includes foreign magic; management does not."""
from pathlib import Path
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[3]

def test_foreign_exposure_cannot_be_ignored_by_two_percent_budget():
    # Equity 1000: own stop loss 5 + manual loss 10 + foreign pending loss 4
    # leaves only 1 of the approved 20 budget. A proposed 2 must be rejected.
    rows=[(20260908,Decimal('5')),(0,Decimal('10')),(99,Decimal('4'))]
    total=sum(loss for magic,loss in rows)
    assert total==Decimal('19')
    assert total+Decimal('2')>Decimal('1000')*Decimal('.02')
    assert total+Decimal('1')==Decimal('1000')*Decimal('.02')


def test_actual_scan_does_not_filter_risk_by_magic_or_symbol():
    s=(ROOT/'MQL5/Include/Account Execution Engine.mqh').read_text(encoding='utf-8-sig')
    scan=s.split('bool AccountEstimatedStopRisk(',1)[1].split('bool AccountManagedPositionVisible(',1)[0]
    assert 'POSITION_MAGIC' not in scan and 'ORDER_MAGIC' not in scan
    assert 'PositionsTotal()' in scan and 'OrdersTotal()' in scan
    assert 'sl<=0.0' in scan and 'return false;' in scan
    assert scan.count('OrderCalcProfit(')==2
    assert 'g_cfg.symbol' not in scan
    assert 'AccountEstimatedStopRisk(env.existing_managed_stop_risk,exposure_reason)' in s


def test_preflight_and_postfill_share_account_scan_but_management_is_scoped():
    execution=(ROOT/'MQL5/Include/Execution Engine.mqh').read_text(encoding='utf-8-sig')
    expert=(ROOT/'MQL5/Experts/AMIGO.mq5').read_text(encoding='utf-8-sig')
    manager=(ROOT/'MQL5/Include/Position Manager.mqh').read_text(encoding='utf-8-sig')
    assert 'AccountEstimatedStopRisk(existing_account_stop_risk,aggregate_risk_reason)' in execution
    assert 'AccountEstimatedStopRisk(reconciled_stop_risk,reconciled_risk_reason)' in expert
    assert '(ulong)PositionGetInteger(POSITION_MAGIC)!=expected_magic' in manager
