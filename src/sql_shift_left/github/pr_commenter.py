from __future__ import annotations

from sql_shift_left.models.findings import PRFinOpsReviewReport


def render_pr_comment(report: PRFinOpsReviewReport) -> str:
    lines = [
        "## FinOps Review",
        f"- Verdict: **{report.verdict}**",
        f"- Risk Score: **{report.overall_risk_score}/100**",
        f"- GB Saved/Run: **{report.total_gb_saved_per_run:.2f} GB**",
        f"- Monthly Savings: **${report.total_monthly_savings_usd:.2f} USD / ₹{report.total_monthly_savings_inr:.2f} INR**",
    ]
    for finding in report.findings:
        lines.append(f"- {finding.rule_id}: {finding.title} ({finding.severity})")
    return "\n".join(lines)
