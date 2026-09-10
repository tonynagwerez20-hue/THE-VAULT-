"""Logging foundation tests (Phase 0)."""

from __future__ import annotations

import logging
from pathlib import Path

from algomind.config.loader import AlgoMindConfig
from algomind.logging import get_logger, setup_logging


def _make_config(log_file: Path) -> AlgoMindConfig:
    base = {
        "system": {"environment": "research", "timezone": "UTC", "log_level": "INFO"},
        "logging": {
            "file": str(log_file),
            "rotate_bytes": 1048576,
            "backup_count": 3,
        },
    }
    return AlgoMindConfig(data=base, config_path=None)


def test_setup_logging_writes_file(tmp_path: Path) -> None:
    log_file = tmp_path / "algomind.log"
    config = _make_config(log_file)
    setup_logging(config)
    get_logger("tests").info("hello phase zero")
    for handler in get_logger("").handlers:
        handler.flush()
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "hello phase zero" in content
    assert "INFO" in content


def test_setup_logging_idempotent(tmp_path: Path) -> None:
    log_file = tmp_path / "algomind.log"
    config = _make_config(log_file)
    setup_logging(config)
    setup_logging(config)
    root = get_logger("")
    file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
    assert len(file_handlers) == 1
