from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from sql_shift_left.models.catalog import CatalogManifest, TableMetadata


class DeltaLogInspector:
    def __init__(self, table_path: Union[str, Path]) -> None:
        self.table_path = Path(table_path)

    def inspect(self) -> TableMetadata:
        delta_dir = self.table_path / "_delta_log"
        if not delta_dir.exists():
            raise FileNotFoundError(f"No _delta_log directory found under {self.table_path}")

        partition_columns: list[str] = []
        columns: list[str] = []
        total_bytes = 0
        num_files = 0
        json_files = sorted(delta_dir.glob("*.json"))

        for path in json_files:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                metadata = record.get("metaData")
                if metadata:
                    partition_columns = metadata.get("partitionColumns", []) or partition_columns
                    schema_string = metadata.get("schemaString")
                    if schema_string:
                        columns = [
                            item.split(":", 1)[0].strip().replace("`", "")
                            for item in schema_string.split(",")
                            if item.strip()
                        ]

                add = record.get("add")
                if isinstance(add, dict):
                    total_bytes += int(add.get("size", 0) or 0)
                    num_files += 1

                remove = record.get("remove")
                if isinstance(remove, dict):
                    total_bytes -= int(remove.get("size", 0) or 0)

        size_gb = max(0.0, total_bytes / (1024 * 1024 * 1024))
        avg_size_mb = (total_bytes / max(1, num_files) / (1024 * 1024)) if num_files else 128.0
        return TableMetadata(
            table_name=self.table_path.name,
            total_size_gb=round(size_gb, 2),
            row_count=0,
            column_count=len(columns),
            partition_columns=partition_columns,
            clustering_columns=[],
            num_files=max(1, num_files),
            avg_file_size_mb=round(avg_size_mb, 2),
            distinct_partition_count=max(1, len(partition_columns) or 1),
            columns=columns,
        )


def load_delta_table_manifest(path: Union[str, Path]) -> CatalogManifest:
    table_path = Path(path)
    metadata = DeltaLogInspector(table_path).inspect()
    return CatalogManifest(catalog_name="delta_log_catalog", tables={metadata.table_name: metadata})
