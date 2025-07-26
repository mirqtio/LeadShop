#!/usr/bin/env python3
"""
Re-run decomposition for an existing assessment to extract more metrics
"""

import asyncio
from src.assessment.decompose_metrics import decompose_and_store_metrics
from src.core.database import AsyncSessionLocal

async def rerun_decomposition(assessment_id: int):
    async with AsyncSessionLocal() as db:
        result = await decompose_and_store_metrics(db, assessment_id)
        if result:
            print(f"✅ Successfully decomposed metrics for assessment {assessment_id}")
            # Get all metrics
            all_metrics = result.get_all_metrics()
            non_null = {k: v for k, v in all_metrics.items() if v is not None}
            print(f"📊 Metrics extracted: {len(non_null)} / 53")
            print("\n🔍 Extracted metrics:")
            for metric, value in non_null.items():
                print(f"  - {metric}: {value}")
        else:
            print(f"❌ Failed to decompose metrics for assessment {assessment_id}")

if __name__ == "__main__":
    # Rerun for assessment 102 (Airbnb)
    asyncio.run(rerun_decomposition(102))