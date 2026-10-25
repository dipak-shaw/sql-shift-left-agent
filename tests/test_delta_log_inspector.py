import json
from pathlib import Path

from sql_shift_left.catalog.delta_log_inspector import DeltaLogInspector


def test_delta_log_inspector_extracts_metadata(tmp_path: Path) -> None:
    delta_dir = tmp_path / "_delta_log"
    delta_dir.mkdir()
    payload = [
        {"metaData": {"partitionColumns": ["event_date"], "schemaString": "event_id:bigint,event_date:string,user_id:bigint"}},
        {"add": {"path": "part-0001.parquet", "size": 1073741824}},
        {"add": {"path": "part-0002.parquet", "size": 536870912}},
        {"remove": {"path": "old.parquet", "size": 268435456}},
    ]
    with (delta_dir / "00000000000000000000.json").open("w", encoding="utf-8") as handle:
        for item in payload:
            handle.write(json.dumps(item) + "\n")

    metadata = DeltaLogInspector(tmp_path).inspect()
    assert metadata.partition_columns == ["event_date"]
    assert metadata.column_count == 3
    assert metadata.total_size_gb > 0
