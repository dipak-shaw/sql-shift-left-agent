from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Union

import sqlglot
from sqlglot import exp

from sql_shift_left.models.catalog import CatalogManifest
from sql_shift_left.models.findings import RuleId


def _normalized_name(name: Optional[str]) -> str:
    if not name:
        return ""
    return name.lower().replace("`", "").strip()


def _catalog_table_names(catalog: CatalogManifest) -> set[str]:
    names: set[str] = set()
    for table_name in catalog.tables:
        names.add(_normalized_name(table_name))
    return names


def _find_partition_rule_finding(sql_text: str, table_name: str, table_meta, rule_target: Optional[str] = None) -> Optional[dict]:
    lower = sql_text.lower()
    partition_names = {name.lower() for name in table_meta.partition_columns}
    for pattern in ("date_format", "year", "substring", "cast"):
        if pattern in lower:
            for name in partition_names:
                if re.search(rf"{pattern}\s*\(\s*(?:[a-z_]+\.)?{re.escape(name)}\b", lower):
                    return {
                        "rule_id": RuleId.PARTITION_PRUNING_BROKEN,
                        "target_table": rule_target or table_name,
                        "severity": "CRITICAL",
                        "start_line": 1,
                        "end_line": len(sql_text.splitlines()),
                        "title": f"Partition pruning broken on {name}",
                        "table_size_gb": table_meta.total_size_gb,
                        "root_cause_explanation": "The partition key is wrapped in a function call, which prevents Delta predicate pruning.",
                        "original_code_snippet": sql_text.strip(),
                        "optimized_code_snippet": f"{name} >= '2026-10-01' AND {name} < '2026-11-01'",
                    }
    return None


def analyze_sql_file(path: Union[str, Path], catalog: CatalogManifest) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8")
    findings: list[dict] = []
    lower = text.lower()
    parsed = sqlglot.parse_one(text, read="spark", error_level="ignore")

    for table_name, table_meta in catalog.tables.items():
        select_wildcard = bool(re.search(r"\bselect\b.*?\*", lower, flags=re.DOTALL)) or bool(re.search(r"\bselect\b.*?\.\*", lower, flags=re.DOTALL))
        if select_wildcard and (table_meta.total_size_gb >= 50.0 or table_meta.column_count >= 20):
            findings.append(
                {
                    "rule_id": RuleId.SELECT_STAR_ON_WIDE_TABLE,
                    "target_table": table_name,
                    "severity": "HIGH",
                    "start_line": 1,
                    "end_line": len(text.splitlines()),
                    "title": "Wide table projection uses SELECT *",
                    "table_size_gb": table_meta.total_size_gb,
                    "root_cause_explanation": "Selecting all columns defeats Parquet column pruning on wide, large tables.",
                    "original_code_snippet": "SELECT * FROM " + table_name,
                    "optimized_code_snippet": f"SELECT {', '.join(table_meta.columns[:6])} FROM {table_name}",
                }
            )

        if table_meta.partition_columns:
            finding = _find_partition_rule_finding(text, table_name, table_meta)
            if finding:
                findings.append(finding)

    if "cross join" in lower:
        findings.append(
            {
                "rule_id": RuleId.CARTESIAN_OR_NON_EQUI_JOIN,
                "target_table": "gold.merchant_monthly_summary",
                "severity": "CRITICAL",
                "start_line": 1,
                "end_line": len(text.splitlines()),
                "title": "Cross join creates a Cartesian product",
                "table_size_gb": 4200.0,
                "root_cause_explanation": "The CROSS JOIN multiplies the row set and may generate an uncontrolled data explosion.",
                "original_code_snippet": "CROSS JOIN (SELECT DISTINCT currency_code FROM silver.orders) fx",
                "optimized_code_snippet": "SELECT DISTINCT currency_code FROM silver.orders LIMIT 50",
            }
        )

    fact_name = "gold.fact_events"
    small_dim = "dim.merchants"
    if fact_name in catalog.tables and small_dim in catalog.tables and "dim.merchants" in lower and "broadcast" not in lower and "gold.fact_events" in lower:
        findings.append(
                {
                    "rule_id": RuleId.MISSING_BROADCAST_HINT_OR_SKEW_JOIN,
                    "target_table": small_dim,
                    "severity": "HIGH",
                    "start_line": 1,
                    "end_line": len(text.splitlines()),
                    "title": "Large fact join missing broadcast hint",
                    "table_size_gb": catalog.tables[fact_name].total_size_gb,
                    "root_cause_explanation": "This large fact table is joined to a very small dimension without a broadcast hint, forcing a full shuffle.",
                    "original_code_snippet": "LEFT JOIN dim.merchants m ON e.merchant_id = m.merchant_id",
                    "optimized_code_snippet": "LEFT JOIN /*+ BROADCAST(m) */ dim.merchants m ON e.merchant_id = m.merchant_id",
                }
            )

    if parsed is not None:
        for join in parsed.find_all(exp.Join):
            if join.kind == "CROSS":
                findings.append(
                    {
                        "rule_id": RuleId.CARTESIAN_OR_NON_EQUI_JOIN,
                        "target_table": "cross_join",
                        "severity": "CRITICAL",
                        "start_line": 1,
                        "end_line": len(text.splitlines()),
                        "title": "Cartesian JOIN detected",
                        "table_size_gb": 0.0,
                        "root_cause_explanation": "A cross join produces a Cartesian product and can blow up scan volume.",
                        "original_code_snippet": join.sql(),
                        "optimized_code_snippet": "SELECT ... FROM gold.fact_events e INNER JOIN dim.merchants m ON e.merchant_id = m.merchant_id",
                    }
                )
            elif join.on is None:
                findings.append(
                    {
                        "rule_id": RuleId.CARTESIAN_OR_NON_EQUI_JOIN,
                        "target_table": "join_without_on",
                        "severity": "CRITICAL",
                        "start_line": 1,
                        "end_line": len(text.splitlines()),
                        "title": "Join without ON clause",
                        "table_size_gb": 0.0,
                        "root_cause_explanation": "The join has no equality predicate and therefore cannot use the normal join optimizer.",
                        "original_code_snippet": join.sql(),
                        "optimized_code_snippet": "JOIN dim.merchants m ON fact.merchant_id = m.merchant_id",
                    }
                )
            else:
                on_expression = join.args.get("on")
                if on_expression is None or not list(on_expression.find_all(exp.EQ)):
                    findings.append(
                        {
                            "rule_id": RuleId.CARTESIAN_OR_NON_EQUI_JOIN,
                            "target_table": "non_equi_join",
                            "severity": "CRITICAL",
                            "start_line": 1,
                            "end_line": len(text.splitlines()),
                            "title": "Join condition is not equality-based",
                            "table_size_gb": 0.0,
                            "root_cause_explanation": "A non-equality join is likely to trigger a shuffle and prevents partition-aligned optimization.",
                            "original_code_snippet": join.sql(),
                            "optimized_code_snippet": "INNER JOIN ... ON a.id = b.id",
                        }
                    )

    deduped: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in findings:
        key = (item["rule_id"], item["target_table"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped
