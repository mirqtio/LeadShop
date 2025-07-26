#!/usr/bin/env python3
"""
Check for assessments with GBP data
"""

import asyncio
from sqlalchemy import select, desc
from src.core.database import AsyncSessionLocal
from src.models.lead import Assessment
from src.models.gbp import GBPAnalysis

async def check_gbp_data():
    async with AsyncSessionLocal() as db:
        # Find assessments with GBP data
        result = await db.execute(
            select(Assessment, GBPAnalysis)
            .join(GBPAnalysis, Assessment.id == GBPAnalysis.assessment_id)
            .order_by(desc(Assessment.id))
            .limit(10)
        )
        
        rows = result.all()
        
        print(f"📊 Assessments with GBP Data: {len(rows)}")
        print("-" * 80)
        
        for assessment, gbp in rows:
            print(f"Assessment ID: {assessment.id}")
            print(f"  Business: {gbp.business_name}")
            print(f"  Rating: {gbp.average_rating} ({gbp.total_reviews} reviews)")
            print(f"  Photos: {gbp.total_photos}")
            print(f"  Match Confidence: {gbp.match_confidence:.0%}")
            print(f"  Status: {'Closed' if gbp.is_permanently_closed else 'Open'}")
            print("-" * 80)
        
        # Also check JSON data
        print("\n📊 Assessments with GBP JSON data:")
        json_result = await db.execute(
            select(Assessment)
            .where(Assessment.gbp_data.isnot(None))
            .order_by(desc(Assessment.id))
            .limit(5)
        )
        
        json_assessments = json_result.scalars().all()
        
        for assessment in json_assessments:
            if assessment.gbp_data and isinstance(assessment.gbp_data, dict):
                print(f"\nAssessment {assessment.id}:")
                print(f"  Found: {assessment.gbp_data.get('found', False)}")
                if assessment.gbp_data.get('found'):
                    print(f"  Confidence: {assessment.gbp_data.get('confidence', 0):.0%}")
                    print(f"  Business: {assessment.gbp_data.get('name', 'N/A')}")
                    print(f"  Rating: {assessment.gbp_data.get('rating', 'N/A')}")
                    print(f"  Total Reviews: {assessment.gbp_data.get('total_reviews', 0)}")

if __name__ == "__main__":
    asyncio.run(check_gbp_data())