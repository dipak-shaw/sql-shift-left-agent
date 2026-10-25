from pathlib import Path

from sql_shift_left.rules.deterministic_rules import build_report, scan_file


def test_cli_and_report_generation() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    catalog_path = repo_root / "examples" / "mock_catalog.json"
    sql_path = repo_root / "examples" / "bad_etl_orders.sql"
    findings = scan_file(sql_path, catalog_path)
    report = build_report(findings)
    assert report.verdict in {"WARN", "BLOCK_MERGE"}
    assert report.total_gb_saved_per_run >= 0
    assert len(report.findings) > 0
