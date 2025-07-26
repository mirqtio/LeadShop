#!/usr/bin/env python

import asyncio
from src.core.database import AsyncSessionLocal
from src.models.lead import Assessment
from sqlalchemy import select, desc

async def show_latest_assessment():
    async with AsyncSessionLocal() as session:
        # Get assessments with actual data
        result = await session.execute(
            select(Assessment)
            .where(Assessment.pagespeed_data.isnot(None))
            .where(Assessment.security_headers.isnot(None))
            .where(Assessment.semrush_data.isnot(None))
            .order_by(desc(Assessment.created_at))
            .limit(5)
        )
        assessment = result.scalar_one_or_none()
        
        if assessment:
            print(f"Assessment ID: {assessment.id}")
            print(f"Lead ID: {assessment.lead_id}")
            print(f"Created: {assessment.created_at}")
            print(f"Total Score: {assessment.total_score}")
            print()
            
            if assessment.pagespeed_data:
                print("✅ PageSpeed Data:")
                if isinstance(assessment.pagespeed_data, dict):
                    mobile = assessment.pagespeed_data.get('mobile_analysis', {})
                    desktop = assessment.pagespeed_data.get('desktop_analysis', {})
                    if mobile:
                        print(f"   Mobile Score: {mobile.get('core_web_vitals', {}).get('performance_score', 'N/A')}")
                    if desktop:
                        print(f"   Desktop Score: {desktop.get('core_web_vitals', {}).get('performance_score', 'N/A')}")
            else:
                print("❌ PageSpeed Data: None")
                
            if assessment.security_headers:
                print("✅ Security Data:")
                if isinstance(assessment.security_headers, dict):
                    print(f"   Security Score: {assessment.security_headers.get('security_score', 'N/A')}")
                    print(f"   HTTPS: {assessment.security_headers.get('has_https', 'N/A')}")
            else:
                print("❌ Security Data: None")
                
            if assessment.semrush_data:
                print("✅ SEMrush Data:")
                if isinstance(assessment.semrush_data, dict):
                    print(f"   Domain Authority: {assessment.semrush_data.get('domain_score', 'N/A')}")
                    print(f"   Organic Traffic: {assessment.semrush_data.get('organic_traffic', 'N/A')}")
            else:
                print("❌ SEMrush Data: None")
                
            if assessment.gbp_data:
                print("✅ GBP Data:")
                if isinstance(assessment.gbp_data, dict):
                    print(f"   Found: {assessment.gbp_data.get('found', 'N/A')}")
                    print(f"   Confidence: {assessment.gbp_data.get('confidence_score', 'N/A')}")
            else:
                print("❌ GBP Data: None")
                
            if assessment.visual_analysis:
                print("✅ Visual Analysis: Complete")
            else:
                print("❌ Visual Analysis: None")
                
            # Count successful components
            successful = sum(1 for data in [
                assessment.pagespeed_data,
                assessment.security_headers,
                assessment.semrush_data,
                assessment.gbp_data,
                assessment.visual_analysis
            ] if data is not None)
            
            print(f"\nSuccessful Components: {successful}/5")
        else:
            print("No assessments found in database")

if __name__ == "__main__":
    asyncio.run(show_latest_assessment())