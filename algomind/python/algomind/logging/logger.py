"""Minimal logging foundation for AlgoMind (Phase 0).

REQ-038 (D4): every trade has a unique decision ID; decisions, execution,
feature versionsand performance are logged so a trade can be reconstructed.
This foundation only configures the standard-library logger hierarchy honoring
the established ``config/logging`` settings (file, rotate_bytes, backup_count,
and ``system.log_level``). The exact storage/log format is NOT SPECIFIED
by the Build Specification (D4 Audit Logger), so records are written as
plain formatted text lines; structured transport/journals come in later phases.

"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from algomind.config.loader import AlgoMindConfig

_ROOT_LOGGER = "algomind"


def _config_log_level(config: AlgoMindConfig) -> int:
    level = config.get_str("system", "log_level", default="INFO")
    return getattr(logging, level.upper(), logging.INFO)


def _file_logging(config: AlgoMindConfig) -> tuple[Path | None, int, int]:
    """Resolve configured file/rotation settings ("" disables file logging).

    Returns (path, rotate_bytes, backup_count). Undocumented rotation
    behavior defaults conservative: plain log file.




   """
    file_name = config.get_str("logging", "file", default="") or ""
    if not file_name:
        return None, 0, 0
    rotate_bytes = config.get_int("logging", "rotate_bytes", default=0) or 0
    backup_count = config.get_int("logging", "backup_count", default=0) or 0
    return Path(file_name), rotate_bytes, backup_count


def setup_logging(config: AlgoMindConfig) -> None:
    """Configurethe ``algomind`` logger tree from a resolved configuration.
    Idempotent: repeated calls do not stack duplicate handlers.



   """
    root = logging.getLogger(_ROOT_LOGGER)
    root.setLevel(_config_log_level(config))
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    file_path, rotate_bytes, backup_count = _file_logging(config)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    if file_path is not None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if rotate_bytes > 0 and backup_count > 0:
            handler = logging.handlers.RotatingFileHandler(
                file_path, maxBytes=rotate_bytes, backupCount=backup_count, encoding="utf-8"
            )
        else:
            handler = logging.FileHandler(file_path, encoding="utf-8")
        handler.setFormatter(formatter)
        root.addHandler(handler)


def get_logger(name: str = "") -> logging.Logger:
    """Return a loggerbeneath the ``algomind`` root.


    Standard-library logging foundation only; no external infrastructure.





   """
    if name:
        return logging.getLogger(f"{_ROOT_LOGGER}.{name}")
    return logging.getLogger(_ROOT_LOGGER)
