from pathlib import Path
from typing import Protocol

import yaml


class CardSource(Protocol):
    """Abstracts where card set data comes from (local files, GitHub, etc.)."""

    def list_sets(self) -> list[str]:
        """Return the IDs of all available card sets."""
        ...

    def load_set(self, set_id: str) -> dict:
        """Return the raw data for a single card set."""
        ...


class LocalFileCardSource:
    """Loads card sets from *.yaml files in a local directory."""

    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path

    def list_sets(self) -> list[str]:
        return [f.stem for f in sorted(self._base_path.glob("*.yaml"))]

    def load_set(self, set_id: str) -> dict:
        path = self._base_path / f"{set_id}.yaml"
        with path.open() as f:
            return yaml.safe_load(f) or {}
