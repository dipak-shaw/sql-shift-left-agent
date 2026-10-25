from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from sql_shift_left.models.catalog import CatalogManifest


class JsonCatalogProvider:
    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)

    def load(self) -> CatalogManifest:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return CatalogManifest.model_validate(data)


def load_catalog_manifest(path: Union[str, Path]) -> CatalogManifest:
    return JsonCatalogProvider(path).load()
