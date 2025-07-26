#!/usr/bin/env python3

import asyncio
from src.assessment.decompose_metrics import sync_decompose_and_store_metrics

print("Testing decompose_metrics for assessment 36...")
result = sync_decompose_and_store_metrics(36)
print(f"Decomposition result: {result}")