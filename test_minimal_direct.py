"""
Direct test of minimal assessment
"""
import asyncio
import sys
sys.path.append('/app')
from minimal_async_orchestrator import minimal_orchestrator
from src.core.database import AsyncSessionLocal
from src.models.lead import Lead
from sqlalchemy import select
import json

async def test_minimal():
    print("Starting minimal assessment test...")
    
    async with AsyncSessionLocal() as db:
        # Create a test lead
        lead = Lead(
            company="Test Company",
            email="test@example.com",
            url="https://www.example.com",
            source="test"
        )
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        
        print(f"Created lead: {lead.id} - {lead.company}")
        
    # Execute assessment
    print("\nStarting assessment...")
    try:
        result = await minimal_orchestrator.execute_assessment(lead_id=lead.id)
        print(f"\nAssessment completed!")
        print(f"Task ID: {result['task_id']}")
        print(f"Assessment ID: {result['assessment_id']}")
        print(f"Status: {result['status']}")
        print(f"Score: {result['score']}")
        
        # Print results
        if 'results' in result:
            print("\nComponent Results:")
            for component, data in result['results'].items():
                status = "✓ Success" if data else "✗ Failed"
                print(f"  {component}: {status}")
                if data:
                    if component == "pagespeed" and isinstance(data, dict):
                        mobile = data.get("mobile_analysis", {}).get("core_web_vitals", {})
                        print(f"    Mobile Score: {mobile.get('performance_score', 'N/A')}")
                    elif component == "security":
                        if hasattr(data, 'security_score'):
                            print(f"    Security Score: {data.security_score}")
                        elif isinstance(data, dict):
                            print(f"    Security Score: {data.get('security_score', 'N/A')}")
                
    except Exception as e:
        print(f"Assessment failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_minimal())