from pathlib import Path

from sql_shift_left.catalog.json_catalog import load_catalog_manifest
from sql_shift_left.rules.deterministic_rules import scan_file


def test_sql_scan_detects_expected_rules() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    catalog = load_catalog_manifest(repo_root / "examples" / "mock_catalog.json")
    findings = scan_file(repo_root / "examples" / "bad_etl_orders.sql", catalog)
    rule_ids = {finding.rule_id.value for finding in findings}
    assert "SELECT_STAR_ON_WIDE_TABLE" in rule_ids
    assert "PARTITION_PRUNING_BROKEN" in rule_ids
    assert "MISSING_BROADCAST_HINT_OR_SKEW_JOIN" in rule_ids
    assert "CARTESIAN_OR_NON_EQUI_JOIN" in rule_ids
