"""Offline source-contract tests for honest shadow-harness result reporting."""
from pathlib import Path

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "MQL5" / "Scripts").is_dir()) / "MQL5"
HARNESS = (ROOT / "Scripts" / "Test_ShadowHarness.mq5").read_text(encoding="utf-8-sig")


def test_preflight_rejection_is_not_misreported_as_order_submission():
    block = HARNESS.split("if(er.risk_guard_blocked)", 1)[1].split("else if(er.comment", 1)[0]
    assert "preflight_block_count++" in block
    assert "unexpected_path_count++" not in block
    shadow = HARNESS.split("else if(er.comment == \"SHADOW_MODE_EXECUTION_BLOCKED\")", 1)[1].split("else", 1)[0]
    assert "shadow_intercept_count++" in shadow
    assert "mock_submission_count" not in HARNESS


def test_harness_requires_shadow_setting_and_classifies_unexpected_paths():
    assert "if(!g_cfg.shadow_only)" in HARNESS
    assert "unexpected_path_count++" in HARNESS
    assert "no_order_not_proven=true" in HARNESS
    assert "preflight_block_count+shadow_intercept_count==test_count" in HARNESS
    assert "All 3 valid test intents reached ExecuteIntent()" not in HARNESS
