"""Offline checks that failed bridge reads remain fail-closed and throttled."""
from pathlib import Path


ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "MQL5" / "Experts" / "AMIGO.mq5").is_file()
)
AMIGO = (ROOT / "MQL5" / "Experts" / "AMIGO.mq5").read_text(encoding="utf-8-sig")


def should_read(now: int, last_read: int) -> bool:
    """Independent expected cadence for the configured 5-second poll."""
    return now - last_read >= 5


def test_failed_external_read_invalidates_news_and_advances_retry_throttle():
    start = AMIGO.index("//--- External context refresh (throttled to one read every 5 seconds)")
    end = AMIGO.index("//--- Decision only on new closed bar", start)
    block = AMIGO[start:end]
    failure = block.split("else\n      {", 1)[1].split("\n      }", 1)[0]

    assert "TimeCurrent() - g_last_ext_read >= 5" in block
    assert "g_last_ext_read = TimeCurrent();" in block.split("if(ReadExternalContext", 1)[1].split("\n      else", 1)[0]
    assert "g_last_ext_read = TimeCurrent();" in failure
    assert "g_ext.news_valid=false;" in failure

    # A failed read at t=100 schedules the next read at t>=105, while
    # news remains invalid and cannot be interpreted as confirmed no-event.
    assert should_read(100, 95)
    assert not should_read(104, 100)
    assert should_read(105, 100)


if __name__ == "__main__":
    test_failed_external_read_invalidates_news_and_advances_retry_throttle()
