"""
Decompose metrics for assessment ID 33
"""

import asyncio
from src.assessment.decompose_metrics import sync_decompose_and_store_metrics

if __name__ == "__main__":
    result = sync_decompose_and_store_metrics(33)
    print(f"Decomposition result: {result}")