from __future__ import annotations

from typing import Optional

from sql_shift_left.config import settings
from sql_shift_left.models.catalog import CatalogManifest
from sql_shift_left.models.findings import RuleId


def calculate_rule_savings(rule_id: RuleId, table_size_gb: float, catalog: Optional[CatalogManifest] = None, severity: str = "MEDIUM") -> dict[str, float]:
    if rule_id == RuleId.PARTITION_PRUNING_BROKEN:
        gb_before = table_size_gb
        effective_partitions = 12
        if catalog:
            for table in catalog.tables.values():
                if table.total_size_gb == table_size_gb:
                    effective_partitions = max(table.distinct_partition_count / 12, 2)
                    break
        gb_after = round(table_size_gb / max(effective_partitions, 2), 2)
    elif rule_id == RuleId.SELECT_STAR_ON_WIDE_TABLE:
        gb_before = table_size_gb
        gb_after = round(gb_before * (6 / max(48, 10)), 2)
    elif rule_id == RuleId.MISSING_BROADCAST_HINT_OR_SKEW_JOIN:
        gb_before = table_size_gb
        gb_after = round(max(table_size_gb * 0.65, 0.1), 2)
    elif rule_id == RuleId.CARTESIAN_OR_NON_EQUI_JOIN:
        gb_before = table_size_gb
        gb_after = round(max(table_size_gb * 0.50, 0.1), 2)
    elif rule_id == RuleId.PYSPARK_DRIVER_OOM_RISK:
        gb_before = table_size_gb
        gb_after = 0.05
    elif rule_id == RuleId.PYSPARK_ROW_BY_ROW_UDF:
        gb_before = table_size_gb
        gb_after = round(max(table_size_gb * 0.60, 0.1), 2)
    elif rule_id == RuleId.SINGLE_PARTITION_BOTTLENECK:
        gb_before = table_size_gb
        gb_after = round(max(table_size_gb * 0.75, 0.1), 2)
    elif rule_id == RuleId.REDUNDANT_ACTION_WITHOUT_CACHE:
        gb_before = table_size_gb
        gb_after = round(max(table_size_gb * 0.70, 0.1), 2)
    else:
        gb_before = table_size_gb
        gb_after = round(max(table_size_gb * 0.5, 0.1), 2)

    gb_saved = round(max(gb_before - gb_after, 0.05), 2)
    monthly_usd = round((gb_saved / 1024.0) * settings.cost_per_tb_scanned_usd * settings.default_runs_per_month, 2)
    if severity in {"HIGH", "CRITICAL"} and gb_saved >= 1.0:
        monthly_usd = max(monthly_usd, 15.0)
    monthly_inr = round(monthly_usd * settings.usd_to_inr_rate, 2)
    return {
        "gb_before": round(gb_before, 2),
        "gb_after": round(gb_after, 2),
        "gb_saved": gb_saved,
        "monthly_usd": monthly_usd,
        "monthly_inr": monthly_inr,
    }
