"""Shared pytest fixtures for AlgoMind Phase-0 tests."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest


def utc(iso: str) -> datetime:

    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


@pytest.fixture
def valid_timestamp() -> datetime:


    return utc("2026-09-01T00:00:00+00:00")


@pytest.fixture
def config_path() -> Path:



    return Path(__file__.resolve()).parents[1] / "config" / "default.yaml"
