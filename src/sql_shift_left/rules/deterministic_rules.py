from __future__ import annotations

from pathlib import Path
from typing import Union

from sql_shift_left.agent.finops_calculator import calculate_rule_savings
from sql_shift_left.catalog.json_catalog import load_catalog_manifest
from sql_shift_left.models.catalog import CatalogManifest
from sql_shift_left.models.findings import CodeRewriteSuggestion, PRFinOpsReviewReport, RuleId
from sql_shift_left.parsers.pyspark_ast_analyzer import analyze_python_file
from sql_shift_left.parsers.sql_ast_analyzer import analyze_sql_file


def _normalize_rule(rule_id: Union[str, RuleId]) -> RuleId:
    if isinstance(rule_id, RuleId):
        return rule_id
    return RuleId(rule_id)


def _build_suggestion_from_dict(file_path: str, payload: dict, catalog: CatalogManifest) -> CodeRewriteSuggestion:
    rule_id = _normalize_rule(payload["rule_id"])
    table_name = payload.get("target_table") or "unknown"
    table_size = float(payload.get("table_size_gb") or 0.0)
    if table_name in catalog.tables:
        table_size = catalog.tables[table_name].total_size_gb
    estimated = calculate_rule_savings(rule_id, table_size, catalog, payload.get("severity", "MEDIUM"))
    return CodeRewriteSuggestion(
        file_path=file_path,
        start_line=int(payload.get("start_line", 1)),
        end_line=int(payload.get("end_line", 1)),
        rule_id=rule_id,
        severity=payload.get("severity", "MEDIUM"),
        target_table=table_name,
        table_size_gb=float(table_size),
        title=payload.get("title", rule_id.value),
        root_cause_explanation=payload.get("root_cause_explanation", "No explanation available."),
        original_code_snippet=payload.get("original_code_snippet", ""),
        optimized_code_snippet=payload.get("optimized_code_snippet", ""),
        estimated_gb_scanned_before=estimated["gb_before"],
        estimated_gb_scanned_after=estimated["gb_after"],
        estimated_gb_saved_per_run=estimated["gb_saved"],
        estimated_monthly_cost_savings_usd=estimated["monthly_usd"],
        estimated_monthly_cost_savings_inr=estimated["monthly_inr"],
    )


def scan_source(path: Union[str, Path], catalog: Union[CatalogManifest, str, Path]) -> list[CodeRewriteSuggestion]:
    file_path = str(path)
    manifest = catalog if isinstance(catalog, CatalogManifest) else load_catalog_manifest(catalog)
    suffix = Path(file_path).suffix.lower()

    if suffix == ".sql":
        raw = analyze_sql_file(file_path, manifest)
    elif suffix == ".py":
        raw = analyze_python_file(file_path, manifest)
    else:
        raise ValueError(f"Unsupported source format: {suffix}")

    suggestions: list[CodeRewriteSuggestion] = []
    for payload in raw:
        suggestions.append(_build_suggestion_from_dict(file_path, payload, manifest))

    deduped: list[CodeRewriteSuggestion] = []
    seen: set[tuple[str, str, str]] = set()
    for item in suggestions:
        key = (item.file_path, item.rule_id, item.target_table)
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def scan_file(path: Union[str, Path], catalog_path: Union[str, Path, CatalogManifest]) -> list[CodeRewriteSuggestion]:
    manifest = catalog_path if isinstance(catalog_path, CatalogManifest) else load_catalog_manifest(catalog_path)
    return scan_source(path, manifest)


def build_report(findings: list[CodeRewriteSuggestion]) -> PRFinOpsReviewReport:
    total_gb_saved = round(sum(f.estimated_gb_saved_per_run for f in findings), 2)
    total_monthly_usd = round(sum(f.estimated_monthly_cost_savings_usd for f in findings), 2)
    total_monthly_inr = round(sum(f.estimated_monthly_cost_savings_inr for f in findings), 2)
    critical_count = sum(1 for f in findings if f.severity == "CRITICAL")
    high_count = sum(1 for f in findings if f.severity == "HIGH")
    risk_score = min(100, (critical_count * 30) + (high_count * 15) + len(findings) * 5)
    verdict = "BLOCK_MERGE" if critical_count > 0 or risk_score >= 80 else "WARN" if findings else "PASS"
    summary = (
        "Critical lakehouse scan and driver-side issues were detected in the change set. Tighten the partition predicates, add broadcast joins, and eliminate row-by-row UDFs or large driver materialization."
        if findings else "No material FinOps or performance risks were detected in the current scan."
    )
    return PRFinOpsReviewReport(
        overall_risk_score=risk_score,
        verdict=verdict,
        executive_summary=summary,
        total_gb_saved_per_run=total_gb_saved,
        total_monthly_savings_usd=total_monthly_usd,
        total_monthly_savings_inr=total_monthly_inr,
        findings=findings,
    )
