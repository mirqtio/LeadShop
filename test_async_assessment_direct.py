"""
Direct test of async assessment without UI
"""
import asyncio
from src.assessment.async_orchestrator import orchestrator
from src.core.database import AsyncSessionLocal
from src.models.lead import Lead
from sqlalchemy import select
import json

async def test_assessment():
    print("Starting direct async assessment test...")
    
    async with AsyncSessionLocal() as db:
        # Create a test lead
        lead = Lead(
            company="Google",
            email="test@google.com",
            url="https://www.google.com",
            source="test"
        )
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        
        print(f"Created lead: {lead.id} - {lead.company}")
        
    # Execute assessment
    print("Starting assessment...")
    try:
        result = await orchestrator.execute_assessment(lead_id=lead.id)
        print(f"Assessment completed!")
        print(f"Task ID: {result['task_id']}")
        print(f"Assessment ID: {result['assessment_id']}")
        print(f"Status: {result['status']}")
        
        # Print results
        if 'results' in result:
            print("\nComponent Results:")
            for component, data in result['results'].items():
                status = "✓ Success" if data else "✗ Failed"
                print(f"  {component}: {status}")
                
    except Exception as e:
        print(f"Assessment failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_assessment())