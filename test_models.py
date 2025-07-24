#!/usr/bin/env python3
"""
Test script for model imports and relationships
"""

import asyncio
import sys
import os

# Ensure we're using the Docker environment paths
sys.path.insert(0, '/app/src')

from src.core.database import AsyncSessionLocal
from src.models.lead import Lead
from src.models.assessment_cost import AssessmentCost

async def test_models():
    print("Testing model relationships...")
    
    async with AsyncSessionLocal() as db:
        # Try to create a Lead instance (don't commit, just test the model)
        lead = Lead(
            company="Test Company",
            email="test@example.com",
            source="test",
            city="Test City",
            state="CA"
        )
        
        # Try to create an AssessmentCost instance
        cost = AssessmentCost.create_pagespeed_cost(
            lead_id=1,
            cost_cents=0.25,
            response_status="success",
            response_time_ms=1500
        )
        
        print(f"✅ Lead model works: {lead}")
        print(f"✅ AssessmentCost model works: {cost}")
        print(f"✅ Cost in dollars: ${cost.cost_dollars:.4f}")

if __name__ == "__main__":
    asyncio.run(test_models())