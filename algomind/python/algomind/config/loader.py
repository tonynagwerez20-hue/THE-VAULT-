"""Configuration loading for AlgoMind."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from algomind.core.errors import ConfigurationError


@dataclass(frozen=False )
class AlgoMindConfig :
    """Typed view over the resolved configuration."""
    data: dict[str, Any] = field(default_factory=dict )
    config_path: Path | None = None

    def get_str(self, *keys: str, default: str | None = None ) -> str | None :
        """Nested lookup returning a string."""
        value = self._get_nested(keys )
        if value is None :
            return default
        if not isinstance(value, str ) :
            raise ConfigurationError(f"Expected string at.. at {keys}, got {type(value).__name__}")
        return value

    def get_float(self, *keys: str, default: float | None = None ) -> float | None :
        value = self._get_nested(keys )
        if value is None :
            return default
        if not isinstance(value,(int, float) ) or isinstance(value,bool ) :
            raise ConfigurationError(f"Expected number at.. at {keys}, got {type(value).__name__}")
        return float(value )

    def get_int(self, *keys: str, default: int | None = None ) -> int | None :
        value = self._get_nested(keys )
        if value is None :
            return default
        if not isinstance(value,int ) or isinstance(value,bool ) :
            raise ConfigurationError(f"Expected integer at.. at {keys}, got {type(value).__name__}")
        return value

    def _get_nested(self, keys: tuple[str, ...] ) -> Any :
        node: Any = self.data
        for key in keys :
            if not isinstance(node,dict ) :
                return None
            node = node.get(key )
        return node

    def __repr__(self ) -> str :
        path = str(self.config_path ) if self.config_path else "<inline>"
        return f"AlgoMindConfig({len(self.data)} sections, source={path})"


def default_config_path() -> Path :
    """Path to the bundled default.yaml."""
    return Path(__file__).resolve().parents[3] / "config" / "default.yaml"


def load_config(path: Path | str | None = None ) -> AlgoMindConfig :
    """Load configuration from YAML into a typed view.

    Falls back to the bundled defaults when path is None.
    """
    if path is None :
        resolved = default_config_path( )
    else :
        resolved = Path(path )
    if not resolved.is_file() :
        raise ConfigurationError(f"Configuration file not found: {resolved}")
    try:
        with open(resolved, "r", encoding="utf-8") as fh :
            data = yaml.safe_load(fh )
    except OSError as exc :
        raise ConfigurationError(f"Cannot read configuration {resolved}: {exc}") from exc
    except yaml.YAMLError as exc :
        raise ConfigurationError(f"Invalid YAML in {resolved}: {exc}") from exc
    if data is None :
        data = {}
    if not isinstance(data,dict ) :
        raise ConfigurationError(f"Configuration root must be a mapping, got {type(data).__name__}")
    return AlgoMindConfig(data=data, config_path=resolved )

