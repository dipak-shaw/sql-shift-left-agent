from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class RuleId(str, Enum):
    PARTITION_PRUNING_BROKEN = "PARTITION_PRUNING_BROKEN"
    SELECT_STAR_ON_WIDE_TABLE = "SELECT_STAR_ON_WIDE_TABLE"
    MISSING_BROADCAST_HINT_OR_SKEW_JOIN = "MISSING_BROADCAST_HINT_OR_SKEW_JOIN"
    CARTESIAN_OR_NON_EQUI_JOIN = "CARTESIAN_OR_NON_EQUI_JOIN"
    PYSPARK_DRIVER_OOM_RISK = "PYSPARK_DRIVER_OOM_RISK"
    PYSPARK_ROW_BY_ROW_UDF = "PYSPARK_ROW_BY_ROW_UDF"
    SINGLE_PARTITION_BOTTLENECK = "SINGLE_PARTITION_BOTTLENECK"
    REDUNDANT_ACTION_WITHOUT_CACHE = "REDUNDANT_ACTION_WITHOUT_CACHE"


class CodeRewriteSuggestion(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    rule_id: RuleId
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    target_table: str
    table_size_gb: float
    title: str
    root_cause_explanation: str
    original_code_snippet: str
    optimized_code_snippet: str
    estimated_gb_scanned_before: float
    estimated_gb_scanned_after: float
    estimated_gb_saved_per_run: float
    estimated_monthly_cost_savings_usd: float
    estimated_monthly_cost_savings_inr: float


class PRFinOpsReviewReport(BaseModel):
    overall_risk_score: int = Field(ge=0, le=100)
    verdict: Literal["PASS", "WARN", "BLOCK_MERGE"]
    executive_summary: str
    total_gb_saved_per_run: float
    total_monthly_savings_usd: float
    total_monthly_savings_inr: float
    findings: list[CodeRewriteSuggestion]

    def to_markdown(self) -> str:
        lines = [
            "# sql-shift-left-agent FinOps Review",
            f"- Verdict: **{self.verdict}**",
            f"- Overall Risk Score: **{self.overall_risk_score} / 100**",
            f"- Total GB Saved / Run: **{self.total_gb_saved_per_run:.2f} GB**",
            f"- Monthly Savings: **${self.total_monthly_savings_usd:.2f} USD / ₹{self.total_monthly_savings_inr:.2f} INR**",
            "",
            "## Findings",
        ]
        for finding in self.findings:
            snippet = finding.original_code_snippet or "N/A"
            opt = finding.optimized_code_snippet or "N/A"
            lines.extend([
                f"### {finding.rule_id} ({finding.severity})",
                f"- Table: {finding.target_table}",
                f"- GB Saved: {finding.estimated_gb_saved_per_run:.2f} GB",
                f"- Monthly Savings: ${finding.estimated_monthly_cost_savings_usd:.2f} USD / ₹{finding.estimated_monthly_cost_savings_inr:.2f} INR",
                f"- Root cause: {finding.root_cause_explanation}",
                "```sql",
                snippet,
                "```",
                "```sql",
                opt,
                "```",
            ])
        return "\n".join(lines)
