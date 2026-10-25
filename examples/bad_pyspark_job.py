"""
Sample Nightly PySpark Job with High-Cost Data Engineering Anti-Patterns.
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

spark = SparkSession.builder.appName("NightlyOrderEnrichment").getOrCreate()


@F.udf(returnType=StringType())
def normalize_currency(code: str, amount: float) -> str:
    if not code:
        return "USD_UNKNOWN"
    tier = "HIGH" if amount and amount > 1000 else "STD"
    return f"{code.strip().upper()}_{tier}"


def run_pipeline() -> None:
    clicks_df = spark.sql("""
        SELECT *
        FROM silver.clickstream
        WHERE SUBSTRING(CAST(dt AS STRING), 1, 7) = '2026-10'
    """)

    orders_df = spark.table("silver.orders").filter(
        F.year(F.col("order_month")) == 2026
    )

    customers_df = spark.table("dim.customers")

    enriched_df = orders_df.join(customers_df, on="customer_id", how="left").withColumn(
        "currency_tag",
        normalize_currency(F.col("currency_code"), F.col("total_amount")),
    )

    total_rows = enriched_df.count()
    print(f"Processing {total_rows} enriched orders...")

    pdf_sample = clicks_df.toPandas()
    print(f"Loaded {len(pdf_sample)} clickstream rows into driver.")

    (
        enriched_df.coalesce(1)
        .write.mode("overwrite")
        .format("delta")
        .saveAsTable("gold.enriched_orders_export")
    )


if __name__ == "__main__":
    run_pipeline()
