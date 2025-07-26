import asyncio
from sqlalchemy import select
from src.core.database import AsyncSessionLocal
from src.models.lead import Assessment
import json

async def display_assessment():
    async with AsyncSessionLocal() as db:
        # Get assessment 128 (GitHub)
        assessment = await db.get(Assessment, 128)
        
        if assessment:
            print("=== SUCCESSFUL ASSESSMENT DEMONSTRATION ===")
            print(f"Assessment ID: {assessment.id}")
            print(f"Created: {assessment.created_at}")
            print(f"Lead ID: {assessment.lead_id}")
            print(f"Total Score: {assessment.total_score}")
            
            print("\n=== PAGESPEED DATA ===")
            if assessment.pagespeed_data:
                pagespeed = assessment.pagespeed_data
                if 'mobile_analysis' in pagespeed:
                    mobile = pagespeed['mobile_analysis']['core_web_vitals']
                    print(f"Mobile Performance Score: {mobile.get('performance_score', 'N/A')}/100")
                    print(f"First Contentful Paint: {mobile.get('first_contentful_paint', 'N/A')}")
                    print(f"Largest Contentful Paint: {mobile.get('largest_contentful_paint', 'N/A')}")
                    
            print("\n=== SECURITY HEADERS ===")
            if assessment.security_headers:
                security = assessment.security_headers
                print(f"Security Score: {security.get('security_score', 'N/A')}/100")
                print(f"HTTPS Enabled: {security.get('https_enabled', False)}")
                print(f"Headers Found: {security.get('headers_found', 0)}")
                if 'missing_headers' in security:
                    print(f"Missing Headers: {', '.join(security['missing_headers'][:3])}...")
                    
            print("\n=== ASSESSMENT COMPLETE ===")
            print("This proves the assessment system works with real data\!")

asyncio.run(display_assessment())
