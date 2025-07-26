import asyncio
from sqlalchemy import select, desc
from src.core.database import AsyncSessionLocal
from src.models.lead import Lead, Assessment
import json

async def check_assessment():
    async with AsyncSessionLocal() as db:
        # Find Airbnb lead
        result = await db.execute(
            select(Lead)
            .where(Lead.url.like('%airbnb%'))
            .order_by(desc(Lead.created_at))
            .limit(1)
        )
        lead = result.scalar_one_or_none()
        
        if lead:
            print(f"Found lead: {lead.company} - {lead.url}")
            
            # Get latest assessment
            result = await db.execute(
                select(Assessment)
                .where(Assessment.lead_id == lead.id)
                .order_by(desc(Assessment.created_at))
                .limit(1)
            )
            assessment = result.scalar_one_or_none()
            
            if assessment:
                print(f"\nAssessment ID: {assessment.id}")
                print(f"Created at: {assessment.created_at}")
                print(f"Total score: {assessment.total_score}")
                
                # Check each component
                components = {
                    'PageSpeed': assessment.pagespeed_data,
                    'Security': assessment.security_headers,
                    'SEMrush': assessment.semrush_data,
                    'GBP': assessment.gbp_data,
                    'Screenshots': assessment.screenshots,
                    'Visual Analysis': assessment.visual_analysis
                }
                
                print("\nComponent Status:")
                for name, data in components.items():
                    status = "✓ Has data" if data else "✗ No data"
                    print(f"  {name}: {status}")
                    
                # Count successful components
                successful = sum(1 for data in components.values() if data)
                print(f"\nSuccessful components: {successful}/6")
            else:
                print("No assessment found")
        else:
            print("No Airbnb lead found")

asyncio.run(check_assessment())
