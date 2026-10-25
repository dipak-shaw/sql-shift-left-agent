from sql_shift_left.agent.finops_calculator import calculate_rule_savings
from sql_shift_left.models.findings import RuleId


def test_finops_calculator_returns_expected_costs() -> None:
    result = calculate_rule_savings(RuleId.PARTITION_PRUNING_BROKEN, 450.0, severity="CRITICAL")
    assert result["gb_saved"] > 0
    assert result["monthly_usd"] >= 15.0
    assert result["monthly_inr"] > result["monthly_usd"]
