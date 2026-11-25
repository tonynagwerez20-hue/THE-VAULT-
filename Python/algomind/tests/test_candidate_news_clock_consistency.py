"""Offline contract checks for UTC news freshness at both AMIGO gates."""
from pathlib import Path


ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "MQL5" / "Include" / "Strategy Engine.mqh").is_file()
)
STRATEGY = (ROOT / "MQL5" / "Include" / "Strategy Engine.mqh").read_text(
    encoding="utf-8-sig"
)
CONTEXT = (ROOT / "MQL5" / "Include" / "External Context Compactor.mqh").read_text(
    encoding="utf-8-sig"
)


def news_allowed(valid: bool, observed_utc: int, event_utc: int, active: bool,
                 released: bool, now_utc: int, max_age: int) -> bool:
    """Independent expected filter contract using UTC for all timestamps."""
    if (not valid or observed_utc <= 0 or observed_utc > now_utc or max_age <= 0
            or now_utc - observed_utc > max_age or event_utc < 0
            or (released and event_utc > now_utc)):
        return False
    return not active


def test_strategy_and_admission_gates_use_same_utc_freshness_basis():
    decide = STRATEGY.split("DecisionResult Decide(", 1)[1]
    news = decide.split("//--- NEWS policy", 1)[1].split("//--- Score gate", 1)[0]
    early_gate = (ROOT / "MQL5" / "Experts" / "AMIGO.mq5").read_text(
        encoding="utf-8-sig"
    )

    assert "datetime news_now=TimeGMT();" in news
    assert "AmigoNewsAdmission(ext,cfg.news_mode,news_now," in news
    assert "ExternalNewsFilterAllows(g_ext,g_cfg.news_mode,TimeGMT()," in early_gate
    policy=(ROOT / "MQL5/Include/News Policy.mqh").read_text()
    assert "ctx.news_observed_ts>now" in policy
    assert "return AmigoNewsAdmission(ctx,mode,now,max_age_seconds,reason);" in CONTEXT

    # A fresh UTC observation remains valid even if broker-server time is
    # offset by several hours. The old TimeCurrent comparison rejected the
    # +03:00 case as stale and the -05:00 case as future-dated.
    assert news_allowed(True, 1_000, 0, False, False, 1_010, 30)
    assert not news_allowed(True, 1_000, 0, False, False, 1_010 + 10_800, 30)
    assert not news_allowed(True, 1_000, 0, False, False, 1_010 - 18_000, 30)
    assert not news_allowed(True, 1_000, 1_020, False, True, 1_010, 30)
    assert not news_allowed(True, 1_000, -1, False, False, 1_010, 30)
    assert not news_allowed(True, 1_000, 0, True, False, 1_010, 30)


if __name__ == "__main__":
    test_strategy_and_admission_gates_use_same_utc_freshness_basis()
