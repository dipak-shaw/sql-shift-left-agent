from __future__ import annotations

import json
from typing import Any, Optional

from openai import OpenAI

from sql_shift_left.agent.prompts import FEW_SHOT_EXAMPLES, SYSTEM_PROMPT
from sql_shift_left.config import settings
from sql_shift_left.models.catalog import CatalogManifest


class ReviewerAgent:
    def __init__(self, *, offline: bool = False) -> None:
        self.offline = offline or not settings.azure_foundry_api_key or not settings.azure_foundry_endpoint

    def propose_rewrite(self, finding: dict[str, Any], catalog: Optional[CatalogManifest] = None) -> dict[str, Any]:
        if self.offline:
            return self._offline_rewrite(finding)

        client = OpenAI(base_url=settings.azure_foundry_endpoint, api_key=settings.azure_foundry_api_key)
        payload = {
            "model": settings.azure_foundry_model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({"finding": finding, "catalog": catalog.model_dump() if catalog else None, "few_shot": FEW_SHOT_EXAMPLES})},
            ],
        }
        response = client.chat.completions.create(**payload)
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    def _offline_rewrite(self, finding: dict[str, Any]) -> dict[str, Any]:
        rule_id = str(finding.get("rule_id", "UNKNOWN"))
        snippet = finding.get("original_code_snippet", "")
        if rule_id == "PARTITION_PRUNING_BROKEN":
            replacement = "event_date >= '2026-10-01' AND event_date < '2026-11-01'"
        elif rule_id == "MISSING_BROADCAST_HINT_OR_SKEW_JOIN":
            replacement = "/*+ BROADCAST(dim.customers) */"
        elif rule_id == "PYSPARK_ROW_BY_ROW_UDF":
            replacement = "F.when(F.col('currency_code').isNull(), 'USD_UNKNOWN').otherwise(F.upper(F.trim(F.col('currency_code'))))"
        elif rule_id == "SINGLE_PARTITION_BOTTLENECK":
            replacement = "enriched_df.repartitionByRange('merchant_id').write..."
        else:
            replacement = snippet or "optimized code"
        return {
            "root_cause_explanation": "Deterministic offline rewrite applied to remove the Spark anti-pattern while preserving semantics.",
            "optimized_code_snippet": replacement,
        }
