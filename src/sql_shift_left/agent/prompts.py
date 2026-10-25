SYSTEM_PROMPT = """You are a Spark SQL and PySpark optimization engineer. Re-write the given SQL or Python snippet to preserve semantics while reducing scan volume, avoiding OOMs, and respecting Delta/Lakehouse partitioning semantics."""

FEW_SHOT_EXAMPLES = [
    {"input": "DATE_FORMAT(event_date, 'yyyy-MM') = '2026-10'", "output": "event_date >= '2026-10-01' AND event_date < '2026-11-01'"},
    {"input": "JOIN dim.customers ON ...", "output": "JOIN /*+ BROADCAST(dim.customers) */ ..."},
    {"input": "@F.udf def clean(x): ...", "output": "F.when(F.isnull(x), 'unknown').otherwise(F.upper(F.trim(x)))"},
]
