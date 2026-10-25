from __future__ import annotations

from typing import Protocol

from sql_shift_left.models.catalog import CatalogManifest


class CatalogProvider(Protocol):
    def load(self) -> CatalogManifest:
        ...
