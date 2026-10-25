from __future__ import annotations

import json

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from sql_shift_left.rules.deterministic_rules import build_report, scan_file

app = typer.Typer(add_completion=False, help="Catalog-aware FinOps & performance PR reviewer for Spark SQL and PySpark.")
console = Console()


@app.command("scan")
def scan_command(
    path: str = typer.Argument(..., help="Path to a .sql or .py file to scan."),
    catalog: str = typer.Option(..., "--catalog", help="Path to a JSON catalog or Delta log directory."),
    format: str = typer.Option("table", "--format", help="Output format: table, markdown, or json."),
    fail_on: str = typer.Option("NONE", "--fail-on", help="Fail on CRITICAL/HIGH/NONE thresholds."),
) -> None:
    findings = scan_file(path, catalog)
    report = build_report(findings)

    if format == "markdown":
        console.print(report.to_markdown())
    elif format == "json":
        console.print(json.dumps(report.model_dump(mode="json"), indent=2))
    else:
        table = Table(title="sql-shift-left-agent FinOps Scorecard", box=box.SIMPLE_HEAVY)
        table.add_column("Metric", style="bold cyan")
        table.add_column("Value", style="green")
        table.add_row("Verdict", report.verdict)
        table.add_row("Risk Score", str(report.overall_risk_score))
        table.add_row("GB Saved/Run", f"{report.total_gb_saved_per_run} GB")
        table.add_row("Monthly Savings", f"${report.total_monthly_savings_usd} USD / ₹{report.total_monthly_savings_inr} INR")
        console.print(table)

        findings_table = Table(title="Findings", box=box.MINIMAL_DOUBLE_HEAD)
        findings_table.add_column("Rule", style="bold")
        findings_table.add_column("Severity", style="bold")
        findings_table.add_column("Table")
        findings_table.add_column("GB Saved")
        for finding in report.findings:
            findings_table.add_row(finding.rule_id, finding.severity, finding.target_table, f"{finding.estimated_gb_saved_per_run} GB")
        console.print(findings_table)

    fail_threshold = fail_on.upper()
    if fail_threshold == "CRITICAL" and any(f.severity == "CRITICAL" for f in report.findings):
        raise typer.Exit(code=1)
    if fail_threshold == "HIGH" and any(f.severity in {"HIGH", "CRITICAL"} for f in report.findings):
        raise typer.Exit(code=1)
    raise typer.Exit(code=0)


@app.command("inspect-catalog")
def inspect_catalog(path: str = typer.Argument(..., help="Path to a catalog JSON file or Delta log directory.")) -> None:
    from sql_shift_left.catalog.json_catalog import load_catalog_manifest

    manifest = load_catalog_manifest(path)
    table = Table(title=f"Catalog: {manifest.catalog_name}", box=box.SIMPLE_HEAVY)
    table.add_column("Table")
    table.add_column("GB")
    table.add_column("TB")
    table.add_column("Partitions")
    table.add_column("Clustering")
    for name, metadata in manifest.tables.items():
        table.add_row(
            name,
            f"{metadata.total_size_gb:.2f}",
            f"{metadata.total_size_gb / 1024:.2f}",
            ", ".join(metadata.partition_columns) if metadata.partition_columns else "-",
            ", ".join(metadata.clustering_columns) if metadata.clustering_columns else "-",
        )
    console.print(table)


if __name__ == "__main__":
    app()
