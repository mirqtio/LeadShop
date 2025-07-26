#!/usr/bin/env python3
"""
Check existing assessments in the database and test decomposed scores display
"""

import asyncio
from sqlalchemy import select, desc
from src.core.database import AsyncSessionLocal
from src.models.lead import Assessment
from src.models.assessment_results import AssessmentResults

async def check_assessments():
    async with AsyncSessionLocal() as db:
        # Get recent assessments
        result = await db.execute(
            select(Assessment)
            .order_by(desc(Assessment.id))
            .limit(10)
        )
        assessments = result.scalars().all()
        
        print("📊 Recent Assessments in Database:")
        print("-" * 80)
        
        for assessment in assessments:
            # Check if decomposed results exist
            decomposed_result = await db.execute(
                select(AssessmentResults)
                .where(AssessmentResults.assessment_id == assessment.id)
            )
            decomposed = decomposed_result.scalar_one_or_none()
            
            if decomposed:
                metrics = decomposed.get_all_metrics()
                non_null = {k: v for k, v in metrics.items() if v is not None}
                metric_count = len(non_null)
            else:
                metric_count = 0
            
            print(f"ID: {assessment.id}")
            print(f"  Lead ID: {assessment.lead_id}")
            print(f"  Status: {assessment.status}")
            print(f"  PageSpeed Score: {assessment.pagespeed_score}")
            print(f"  Security Score: {assessment.security_score}")
            print(f"  Total Score: {assessment.total_score}")
            print(f"  Decomposed Metrics: {metric_count}/53")
            print(f"  Created: {assessment.created_at}")
            print("-" * 80)
        
        # Find an assessment with good data
        print("\n🔍 Looking for assessments with PageSpeed data...")
        
        pagespeed_result = await db.execute(
            select(Assessment)
            .where(Assessment.pagespeed_score > 0)
            .where(Assessment.pagespeed_data.isnot(None))
            .order_by(desc(Assessment.id))
            .limit(5)
        )
        pagespeed_assessments = pagespeed_result.scalars().all()
        
        for assessment in pagespeed_assessments:
            print(f"\nAssessment {assessment.id}:")
            print(f"  PageSpeed Score: {assessment.pagespeed_score}")
            if assessment.pagespeed_data:
                print(f"  Has PageSpeed Data: Yes")
                if 'mobile_analysis' in assessment.pagespeed_data:
                    print(f"  Has Mobile Analysis: Yes")
                if 'desktop_analysis' in assessment.pagespeed_data:
                    print(f"  Has Desktop Analysis: Yes")

if __name__ == "__main__":
    asyncio.run(check_assessments())