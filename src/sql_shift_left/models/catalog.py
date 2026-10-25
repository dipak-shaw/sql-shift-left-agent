from pydantic import BaseModel, Field


class TableMetadata(BaseModel):
    table_name: str
    format: str = "DELTA"
    total_size_gb: float
    row_count: int = 0
    column_count: int = 0
    partition_columns: list[str] = Field(default_factory=list)
    clustering_columns: list[str] = Field(default_factory=list)
    num_files: int = 1
    avg_file_size_mb: float = 128.0
    distinct_partition_count: int = 1
    columns: list[str] = Field(default_factory=list)


class CatalogManifest(BaseModel):
    catalog_name: str = "enterprise_lakehouse"
    storage_account: str = "datawisecode"
    default_schedule_runs_per_month: int = 30
    tables: dict[str, TableMetadata]
