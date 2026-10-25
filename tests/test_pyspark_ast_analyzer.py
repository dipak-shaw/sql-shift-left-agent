from pathlib import Path

from sql_shift_left.catalog.json_catalog import load_catalog_manifest
from sql_shift_left.rules.deterministic_rules import scan_file


def test_pyspark_scan_detects_expected_rules() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    catalog = load_catalog_manifest(repo_root / "examples" / "mock_catalog.json")
    findings = scan_file(repo_root / "examples" / "bad_pyspark_job.py", catalog)
    rule_ids = {finding.rule_id.value for finding in findings}
    assert "PYSPARK_ROW_BY_ROW_UDF" in rule_ids
    assert "PARTITION_PRUNING_BROKEN" in rule_ids
    assert "MISSING_BROADCAST_HINT_OR_SKEW_JOIN" in rule_ids
    assert "REDUNDANT_ACTION_WITHOUT_CACHE" in rule_ids
    assert "PYSPARK_DRIVER_OOM_RISK" in rule_ids
    assert "SINGLE_PARTITION_BOTTLENECK" in rule_ids
